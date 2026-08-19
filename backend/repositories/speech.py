"""The speech ledger — what TTS and STT actually cost, by the event.

Writes are best-effort by design: a synthesis that succeeded must not fail
the learner's request because the accounting row could not be written, and
the table arrives in a migration the owner applies (20260927000000), so
every path here degrades to a log line when it isn't there yet.
"""

from __future__ import annotations

import logging

import asyncpg

from backend.repositories.pool import privileged_connection

logger = logging.getLogger("speech")

# Which surface spent it. 'content' is the app reading its own teaching
# material (a drill sentence, a vocabulary word); 'speak' is a conversation.
FEATURES = ("speak", "content")


async def log_speech_usage(
    conn: asyncpg.Connection,
    user_id: str | None,
    language_code: str | None,
    kind: str,
    feature: str,
    chars: int = 0,
    audio_ms: int = 0,
) -> None:
    """Record one BILLABLE speech event: a synthesis that reached the
    provider, or a transcription. A cache hit is not one — it costs
    nothing, so it writes nothing."""
    try:
        await conn.execute(
            """
            INSERT INTO speech_usage
                (user_id, language_code, kind, feature, chars, audio_ms)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id, language_code, kind, feature,
            max(0, chars), max(0, audio_ms),
        )
    except asyncpg.exceptions.UndefinedTableError:
        # Migration not applied yet. The learner heard their audio; the
        # cost view is simply blind to it until the table lands.
        logger.warning("speech_usage not migrated — %s event not recorded", kind)
    except Exception as exc:  # noqa: BLE001 — accounting never breaks playback
        logger.warning(
            "speech_usage write failed (%s): %s", type(exc).__name__, exc
        )


async def record_speech_event(
    user_id: str | None,
    language_code: str | None,
    kind: str,
    feature: str,
    chars: int = 0,
    audio_ms: int = 0,
) -> None:
    """Log one speech event on its own privileged connection.

    speech_usage is service-role-write like tts_audio (RLS on, no
    policies), so this cannot ride the caller's connection. Nothing here
    is allowed to reach the caller: the learner has already heard their
    audio, and a bookkeeping problem must never turn a working clip into
    a 500.
    """
    try:
        async with privileged_connection() as conn:
            await log_speech_usage(
                conn, user_id, language_code, kind, feature, chars, audio_ms
            )
    except Exception as exc:  # noqa: BLE001 — accounting never breaks playback
        logger.warning(
            "speech_usage not recorded (%s): %s", type(exc).__name__, exc
        )


async def aggregate_speech_usage(conn: asyncpg.Connection, since) -> list[dict]:
    """Per-(language, kind, feature) speech rollup since *since*.

    Privileged connection: speech_usage has RLS on with no policies, and
    this intentionally spans all users. The caller enforces admin first.
    Returns [] when the migration hasn't been applied, so the panel shows
    an empty speech section rather than a 500.
    """
    try:
        rows = await conn.fetch(
            """
            SELECT
                su.language_code,
                su.kind,
                su.feature,
                count(*)::int                         AS events,
                COALESCE(sum(su.chars), 0)::bigint    AS chars,
                COALESCE(sum(su.audio_ms), 0)::bigint AS audio_ms
            FROM speech_usage su
            WHERE su.created_at >= $1
            GROUP BY su.language_code, su.kind, su.feature
            ORDER BY su.kind, su.feature, su.language_code NULLS LAST
            """,
            since,
        )
    except asyncpg.exceptions.UndefinedTableError:
        return []
    return [dict(r) for r in rows]
