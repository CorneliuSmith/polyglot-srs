"""Audio router — cached neural TTS for the app's own content (WP7a).

POST /api/audio/tts takes (language_code, text), verifies the text is
actually one of ours (a drill sentence, an example sentence, or a
vocabulary word in that language — this is NOT an open TTS proxy),
serves the cached clip if one exists, and otherwise synthesizes, uploads
to the public 'tts' storage bucket, records the cache row, and returns
the public URL. The client falls back to browser speechSynthesis on any
non-200 (uncovered language, unknown text, provider hiccup).
"""

from __future__ import annotations

import base64
import logging
import time

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.recordings import approved_recording
from backend.repositories.speech import record_speech_event
from backend.services.rate_limit import tts_limiter
from backend.services.tts import cache_key, synthesize, voice_for

logger = logging.getLogger("audio")
router = APIRouter()

MAX_TTS_CHARS = 300

# The DO deploy cannot reach Supabase's HTTP APIs — connections hang
# until timeout (same egress quirk as the account-creation admin API).
# Storage uploads are bounded tightly, and after a transport failure we
# stop attempting uploads for a cooldown so cache misses don't each pay
# the connect timeout before serving the clip inline.
_STORAGE_TIMEOUT = httpx.Timeout(4.0, connect=2.0)
_STORAGE_COOLDOWN_S = 600.0
_storage_down_until = 0.0


class TTSRequest(BaseModel):
    language_code: str = Field(min_length=2, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)


async def _text_is_ours(conn, language_code: str, text: str) -> bool:
    """Only synthesize content the learner legitimately sees: drill and
    example sentences, vocabulary words/readings, grammar point titles,
    and the learner's OWN cloze sentences (RLS scopes those rows — this
    runs on the caller's connection). Still not an open proxy."""
    return bool(await conn.fetchval(
        """
        SELECT EXISTS(
            SELECT 1
            FROM drill_sentences ds
            JOIN grammar_points gp ON ds.grammar_point_id = gp.id
            JOIN languages l ON gp.language_id = l.id
            WHERE l.code = $1
              AND (REPLACE(ds.sentence, '{{answer}}', ds.answer) = $2
                   -- listening mode speaks the sentence with the blank as a
                   -- pause (never the answer): the gapped form is ours too
                   OR REPLACE(ds.sentence, '{{answer}}', '…') = $2)
        ) OR EXISTS(
            SELECT 1
            FROM example_sentences es
            JOIN languages l ON es.language_id = l.id
            WHERE l.code = $1 AND es.sentence = $2
        ) OR EXISTS(
            SELECT 1
            FROM vocabulary v
            JOIN languages l ON v.language_id = l.id
            WHERE l.code = $1 AND (v.word = $2 OR v.reading = $2)
        ) OR EXISTS(
            SELECT 1
            FROM grammar_points gp
            JOIN languages l ON gp.language_id = l.id
            WHERE l.code = $1 AND gp.title = $2
        ) OR EXISTS(
            SELECT 1
            FROM user_cloze_cards cc
            JOIN languages l ON cc.language_id = l.id
            WHERE l.code = $1
              AND (cc.sentence = $2
                   OR REPLACE(cc.sentence, '{{answer}}', cc.answer) = $2
                   OR REPLACE(cc.sentence, '{{answer}}', '…') = $2)
        ) OR EXISTS(
            -- WP21: sentences from the learner's own generated readings
            -- (RLS scopes rows to the caller).
            SELECT 1
            FROM readings r
            JOIN languages l ON r.language_id = l.id,
            LATERAL jsonb_array_elements(r.content->'sentences') AS s
            WHERE l.code = $1 AND s->>'text' = $2
        )
        """,
        language_code, text,
    ))


def _public_url(settings, path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/tts/{path}"


async def _upload_clip(settings, storage_path: str, audio: bytes) -> bool:
    """Push one clip to the public bucket. True when it landed.

    Failure is never fatal here — the caller always has the bytes and can
    serve them inline. What matters is that a failure is REPORTED, so the
    caller records the clip in the database instead of losing it.
    """
    global _storage_down_until
    if not settings.supabase_service_role_key:
        return False
    if time.monotonic() < _storage_down_until:
        return False
    try:
        async with httpx.AsyncClient(timeout=_STORAGE_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.supabase_url.rstrip('/')}/storage/v1/object/tts/{storage_path}",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    "Content-Type": "audio/mpeg",
                    "x-upsert": "true",
                },
                content=audio,
            )
    except Exception as exc:  # noqa: BLE001 — storage outage ≠ no audio
        _storage_down_until = time.monotonic() + _STORAGE_COOLDOWN_S
        logger.error(
            "TTS upload errored (%s): %s — skipping storage for %.0fs",
            type(exc).__name__, exc, _STORAGE_COOLDOWN_S,
        )
        return False
    if resp.status_code in (200, 201):
        return True
    logger.error("TTS upload failed (%s): %s", resp.status_code, resp.text[:200])
    return False


async def _record_clip(
    language_code: str, voice: str, key: str,
    storage_path: str | None, audio: bytes | None,
) -> None:
    """Remember that this clip exists, whichever form we have it in.

    The audio column arrives in 20260924000000_tts_audio_durable.sql. Until
    that lands, a clip we could not upload cannot be recorded at all — so
    fall back to the old behaviour rather than failing the request. The
    learner still hears the audio; it just costs another synthesis next
    time, exactly as it did before.
    """
    try:
        async with privileged_connection() as conn:
            await conn.execute(
                """
                INSERT INTO tts_audio
                    (language_code, voice, text_hash, storage_path, audio)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (voice, text_hash) DO NOTHING
                """,
                language_code, voice, key, storage_path, audio,
            )
    except (asyncpg.exceptions.UndefinedColumnError,
            asyncpg.exceptions.NotNullViolationError):
        if storage_path is None:
            logger.warning(
                "tts_audio.audio not migrated — clip stays uncached and will "
                "be synthesized again next play"
            )
            return
        async with privileged_connection() as conn:
            await conn.execute(
                """
                INSERT INTO tts_audio
                    (language_code, voice, text_hash, storage_path)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (voice, text_hash) DO NOTHING
                """,
                language_code, voice, key, storage_path,
            )


async def _promote(
    settings, voice: str, key: str, storage_path: str, audio: bytes
) -> str | None:
    """Move a database-held clip up to the CDN, now that we're here anyway.

    The bytes column is a safety net, not the destination: it exists so a
    storage outage costs disk instead of a repeat synthesis. Once uploads
    work again the clip belongs in the bucket, and the row should stop
    carrying it — otherwise one bad afternoon leaves megabytes in Postgres
    forever. Returns the public URL on success.
    """
    if not await _upload_clip(settings, storage_path, audio):
        return None
    async with privileged_connection() as conn:
        await conn.execute(
            "UPDATE tts_audio SET storage_path = $3, audio = NULL "
            "WHERE voice = $1 AND text_hash = $2",
            voice, key, storage_path,
        )
    return _public_url(settings, storage_path)


@router.post("/tts")
async def tts(
    body: TTSRequest,
    user: dict = Depends(get_current_user),
):
    """Return a cached (or freshly synthesized) MP3 URL for one clip."""
    text = body.text.strip()

    # A human recording outranks a synthetic voice — and for languages with
    # no neural voice at all (jam), it's the only audio there is. Checked
    # BEFORE the voice gate so a voiceless language with an approved clip
    # serves it instead of 404ing. Served inline: clips are short, they sit
    # in the row (see migration 20261007), and no provider is billed.
    async with privileged_connection() as conn:
        human = await approved_recording(conn, body.language_code, text)
    if human:
        return {
            "url": None,
            "cached": True,
            "audio_b64": base64.b64encode(human["audio"]).decode(),
            "mime": human["mime"],
        }

    voice = voice_for(body.language_code)
    if voice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No TTS voice for language: {body.language_code}",
        )
    key = cache_key(voice, text)
    storage_path = f"{body.language_code}/{key}.mp3"
    settings = get_settings()

    # A cache hit must never reach the synthesis provider. The audio column
    # is absent until 20260924000000 lands, so read it defensively — an
    # unmigrated database still gets the storage_path behaviour it had.
    async with privileged_connection() as conn:
        try:
            cached = await conn.fetchrow(
                "SELECT storage_path, audio FROM tts_audio "
                "WHERE voice = $1 AND text_hash = $2",
                voice, key,
            )
        except asyncpg.exceptions.UndefinedColumnError:
            path = await conn.fetchval(
                "SELECT storage_path FROM tts_audio "
                "WHERE voice = $1 AND text_hash = $2",
                voice, key,
            )
            cached = {"storage_path": path, "audio": None} if path else None
    if cached:
        if cached["storage_path"]:
            return {
                "url": _public_url(settings, cached["storage_path"]),
                "cached": True,
            }
        # Held in the database because its upload failed once. Try to move it
        # to the CDN while we're here; serve it inline either way. What we do
        # NOT do is synthesize it again — that is the whole point.
        audio = bytes(cached["audio"])
        url = await _promote(settings, voice, key, storage_path, audio)
        if url:
            return {"url": url, "cached": True}
        return {
            "url": None,
            "cached": True,
            "audio_b64": base64.b64encode(audio).decode(),
        }

    # Only now (cache misses cost real work) gate + verify.
    if not await tts_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many audio requests — slow down a moment.",
        )
    async with rls_connection(user["id"]) as conn:
        if not await _text_is_ours(conn, body.language_code, text):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown text for this language",
            )

    try:
        audio = await synthesize(text, body.language_code)
    except Exception as exc:  # noqa: BLE001 — provider is best-effort
        logger.error("TTS synthesis failed (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Audio generation failed",
        ) from exc

    # Billable: the provider was called. Cache hits return above and write
    # nothing, which is the point — this counts characters actually bought.
    await record_speech_event(
        user["id"], body.language_code,
        kind="tts", feature="content", chars=len(text),
    )

    # Storage is an OPTIMIZATION, not a requirement: when the service key
    # is missing or the upload fails, the learner still gets the neural
    # clip inline (base64) and only the CDN delivery is lost. Beta lesson:
    # a broken cache layer must never regress audio to the browser voice.
    #
    # But it must not cost a repeat synthesis either. This clip has now been
    # paid for; whether it reached the bucket decides HOW it is remembered,
    # never WHETHER. A failed upload files the bytes in the database and the
    # next play promotes them, so the provider is charged once per distinct
    # (voice, text) however the network behaves.
    if not settings.supabase_service_role_key:
        logger.error(
            "TTS storage disabled: SUPABASE_SERVICE_ROLE_KEY is not set — "
            "keeping the clip in the database instead"
        )
    stored = await _upload_clip(settings, storage_path, audio)
    await _record_clip(
        body.language_code, voice, key,
        storage_path if stored else None,
        None if stored else audio,
    )
    if not stored:
        return {
            "url": None,
            "cached": False,
            "audio_b64": base64.b64encode(audio).decode(),
        }
    return {"url": _public_url(settings, storage_path), "cached": False}
