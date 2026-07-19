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

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.pool import privileged_connection, rls_connection
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


@router.post("/tts")
async def tts(
    body: TTSRequest,
    user: dict = Depends(get_current_user),
):
    """Return a cached (or freshly synthesized) MP3 URL for one clip."""
    voice = voice_for(body.language_code)
    if voice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No TTS voice for language: {body.language_code}",
        )
    text = body.text.strip()
    key = cache_key(voice, text)
    storage_path = f"{body.language_code}/{key}.mp3"
    settings = get_settings()

    async with privileged_connection() as conn:
        cached = await conn.fetchval(
            "SELECT storage_path FROM tts_audio WHERE voice = $1 AND text_hash = $2",
            voice, key,
        )
    if cached:
        return {"url": _public_url(settings, cached), "cached": True}

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

    # Storage is an OPTIMIZATION, not a requirement: when the service key
    # is missing or the upload fails, the learner still gets the neural
    # clip inline (base64) and only the CDN caching is lost. Beta lesson:
    # a broken cache layer must never regress audio to the browser voice.
    global _storage_down_until
    stored = False
    if settings.supabase_service_role_key and time.monotonic() >= _storage_down_until:
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
            if resp.status_code in (200, 201):
                stored = True
            else:
                logger.error(
                    "TTS upload failed (%s): %s", resp.status_code, resp.text[:200]
                )
        except Exception as exc:  # noqa: BLE001 — storage outage ≠ no audio
            _storage_down_until = time.monotonic() + _STORAGE_COOLDOWN_S
            logger.error(
                "TTS upload errored (%s): %s — skipping storage for %.0fs",
                type(exc).__name__, exc, _STORAGE_COOLDOWN_S,
            )
    elif settings.supabase_service_role_key:
        logger.warning("TTS storage in cooldown — serving audio inline")
    else:
        logger.error(
            "TTS storage disabled: SUPABASE_SERVICE_ROLE_KEY is not set — "
            "serving audio inline without caching"
        )

    if not stored:
        return {
            "url": None,
            "cached": False,
            "audio_b64": base64.b64encode(audio).decode(),
        }

    async with privileged_connection() as conn:
        await conn.execute(
            """
            INSERT INTO tts_audio (language_code, voice, text_hash, storage_path)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (voice, text_hash) DO NOTHING
            """,
            body.language_code, voice, key, storage_path,
        )
    return {"url": _public_url(settings, storage_path), "cached": False}
