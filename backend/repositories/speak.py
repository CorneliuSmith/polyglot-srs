"""Speak repository — sessions and turns for conversation practice.

Every read and write here tolerates the migration not having landed. The
tables arrive in 20260923000000_speak_sessions.sql, which the owner applies
by hand, so the code ships before the schema does: an UndefinedTableError
means "not yet", not "broken". The router turns that into an unavailable
feature rather than a 500, and nothing outside the Speak page ever touches
these tables, so a missing migration costs the learner one tile.
"""
from __future__ import annotations

import json

import asyncpg


class SpeakUnavailableError(RuntimeError):
    """The Speak tables aren't there yet (migration not applied)."""


async def tables_ready(conn: asyncpg.Connection) -> bool:
    """Cheap probe for the status endpoint, so the UI can hide the feature
    instead of offering a button that 503s."""
    try:
        await conn.fetchval("SELECT 1 FROM speak_sessions LIMIT 1")
    except asyncpg.exceptions.UndefinedTableError:
        return False
    return True


async def start_session(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    mode: str,
    topic: str | None,
) -> str:
    try:
        return str(await conn.fetchval(
            """
            INSERT INTO speak_sessions (user_id, language_id, mode, topic)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            user_id, language_id, mode, topic,
        ))
    except asyncpg.exceptions.UndefinedTableError as exc:
        raise SpeakUnavailableError from exc


async def get_session(
    conn: asyncpg.Connection, user_id: str, session_id: str
) -> dict | None:
    """One session, or None when it doesn't exist or isn't the caller's.

    The user_id predicate is belt-and-braces next to RLS: this repo is also
    reachable from a privileged connection, and a session id in someone
    else's URL should read as "not found" either way.
    """
    try:
        row = await conn.fetchrow(
            """
            SELECT id, language_id, mode, topic, started_at, ended_at,
                   turn_count, summary
              FROM speak_sessions
             WHERE id = $1 AND user_id = $2
            """,
            session_id, user_id,
        )
    except asyncpg.exceptions.UndefinedTableError as exc:
        raise SpeakUnavailableError from exc
    if not row:
        return None
    data = dict(row)
    data["id"] = str(data["id"])
    data["language_id"] = str(data["language_id"]) if data["language_id"] else None
    if isinstance(data.get("summary"), str):
        data["summary"] = json.loads(data["summary"])
    return data


async def list_turns(
    conn: asyncpg.Connection, session_id: str
) -> list[dict]:
    """Every turn of one session, oldest first — the model's context and the
    summary's input."""
    try:
        rows = await conn.fetch(
            """
            SELECT idx, learner_text, partner_text, audio_ms, errors
              FROM speak_turns
             WHERE session_id = $1
             ORDER BY idx
            """,
            session_id,
        )
    except asyncpg.exceptions.UndefinedTableError as exc:
        raise SpeakUnavailableError from exc
    turns = []
    for row in rows:
        turn = dict(row)
        errors = turn.get("errors")
        turn["errors"] = json.loads(errors) if isinstance(errors, str) else (
            errors or []
        )
        turns.append(turn)
    return turns


async def append_turn(
    conn: asyncpg.Connection,
    session_id: str,
    idx: int,
    learner_text: str,
    partner_text: str,
    errors: list[dict],
) -> None:
    """Record one exchange and bump the session's counter.

    ON CONFLICT DO NOTHING on (session_id, idx): a double-submitted turn —
    an impatient tap, a retried request — must not append the same exchange
    twice and desynchronise the transcript from what the learner saw.
    """
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO speak_turns
                    (session_id, idx, learner_text, partner_text, errors)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (session_id, idx) DO NOTHING
                """,
                session_id, idx, learner_text, partner_text,
                json.dumps(errors, ensure_ascii=False),
            )
            await conn.execute(
                """
                UPDATE speak_sessions
                   SET turn_count = (SELECT count(*) FROM speak_turns
                                      WHERE session_id = $1)
                 WHERE id = $1
                """,
                session_id,
            )
    except asyncpg.exceptions.UndefinedTableError as exc:
        raise SpeakUnavailableError from exc


async def end_session(
    conn: asyncpg.Connection, session_id: str, summary: dict
) -> None:
    """Close the session and store its breakdown.

    ended_at is only set once — re-ending a session (a double tap on Done,
    or reopening a finished summary) keeps the original time and the
    original summary rather than overwriting them with a second pass over
    the same transcript.
    """
    try:
        await conn.execute(
            """
            UPDATE speak_sessions
               SET ended_at = now(), summary = $2::jsonb
             WHERE id = $1 AND ended_at IS NULL
            """,
            session_id, json.dumps(summary, ensure_ascii=False),
        )
    except asyncpg.exceptions.UndefinedTableError as exc:
        raise SpeakUnavailableError from exc


async def list_recent_sessions(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    limit: int = 10,
) -> list[dict]:
    """Past sessions, newest first. Unfinished ones are included: the plan
    requires an interrupted session still be worth something."""
    try:
        rows = await conn.fetch(
            """
            SELECT id, mode, topic, started_at, ended_at, turn_count
              FROM speak_sessions
             WHERE user_id = $1 AND language_id = $2
             ORDER BY started_at DESC
             LIMIT $3
            """,
            user_id, language_id, limit,
        )
    except asyncpg.exceptions.UndefinedTableError as exc:
        raise SpeakUnavailableError from exc
    return [{**dict(r), "id": str(r["id"])} for r in rows]
