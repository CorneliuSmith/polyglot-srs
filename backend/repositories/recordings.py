"""Contributor-recorded audio (migration 20261007).

Jamaican Patois has no neural voice, so its audio comes from people:
contributors submit clips for exact texts, reviewers approve them, and the
audio endpoint serves the approved clip where TTS would have been. Every
read probes the table with to_regclass (never raises inside a pooled
transaction) so a deploy ahead of the migration degrades to "no
recordings" instead of failing.
"""
from __future__ import annotations

import asyncpg


async def _recordings_present(conn: asyncpg.Connection) -> bool:
    return bool(await conn.fetchval(
        "SELECT to_regclass('contributor_recordings') IS NOT NULL"
    ))


async def submit_recording(
    conn: asyncpg.Connection,
    language_id: str,
    contributor_id: str,
    text: str,
    audio: bytes,
    mime: str,
) -> bool:
    """Store (or replace) one contributor's take on one text. A resubmit
    overwrites their previous clip and goes back to 'pending' — a new take
    is a new review. Returns False when the migration hasn't landed."""
    if not await _recordings_present(conn):
        return False
    await conn.execute(
        """
        INSERT INTO contributor_recordings
            (language_id, contributor_id, text, audio, mime)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (language_id, contributor_id, text) DO UPDATE SET
            audio = EXCLUDED.audio,
            mime = EXCLUDED.mime,
            status = 'pending',
            reviewed_by = NULL,
            updated_at = now()
        """,
        language_id, contributor_id, text, audio, mime,
    )
    return True


async def list_recordings(
    conn: asyncpg.Connection, language_id: str, status: str
) -> list[dict]:
    """The review queue (or an archive view): metadata only — audio bytes
    are fetched per clip when a reviewer actually presses play."""
    if not await _recordings_present(conn):
        return []
    rows = await conn.fetch(
        """
        SELECT r.id, r.text, r.mime, r.status, r.created_at,
               u.email AS contributor_email
        FROM contributor_recordings r
        JOIN auth.users u ON u.id = r.contributor_id
        WHERE r.language_id = $1 AND r.status = $2
        ORDER BY r.created_at
        LIMIT 200
        """,
        language_id, status,
    )
    return [
        {**dict(r), "id": str(r["id"]),
         "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


async def my_recordings(
    conn: asyncpg.Connection, contributor_id: str, language_id: str
) -> list[dict]:
    """The contributor's own submissions and their review states."""
    if not await _recordings_present(conn):
        return []
    rows = await conn.fetch(
        """
        SELECT id, text, mime, status, created_at
        FROM contributor_recordings
        WHERE contributor_id = $1 AND language_id = $2
        ORDER BY created_at DESC
        LIMIT 200
        """,
        contributor_id, language_id,
    )
    return [
        {**dict(r), "id": str(r["id"]),
         "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


async def get_recording_audio(
    conn: asyncpg.Connection, recording_id: str
) -> dict | None:
    """One clip's bytes + mime (for the review queue's play button)."""
    if not await _recordings_present(conn):
        return None
    row = await conn.fetchrow(
        "SELECT audio, mime, language_id, status FROM contributor_recordings "
        "WHERE id = $1",
        recording_id,
    )
    if row is None:
        return None
    return {"audio": bytes(row["audio"]), "mime": row["mime"],
            "language_id": str(row["language_id"]), "status": row["status"]}


async def review_recording(
    conn: asyncpg.Connection, recording_id: str, reviewer_id: str,
    *, approve: bool,
) -> str | None:
    """Set a clip's verdict. Returns the new status, or None when the clip
    doesn't exist (or the migration hasn't landed)."""
    if not await _recordings_present(conn):
        return None
    status = "approved" if approve else "rejected"
    updated = await conn.fetchval(
        """
        UPDATE contributor_recordings
        SET status = $2, reviewed_by = $3, updated_at = now()
        WHERE id = $1
        RETURNING status
        """,
        recording_id, status, reviewer_id,
    )
    return updated


async def approved_recording(
    conn: asyncpg.Connection, language_code: str, text: str
) -> dict | None:
    """The clip the audio endpoint serves: the newest APPROVED recording
    for this exact text. A human recording outranks a synthetic voice, and
    for voiceless languages (jam) it's the only audio there is."""
    if not await _recordings_present(conn):
        return None
    row = await conn.fetchrow(
        """
        SELECT r.audio, r.mime
        FROM contributor_recordings r
        JOIN languages l ON l.id = r.language_id
        WHERE l.code = $1 AND r.text = $2 AND r.status = 'approved'
        ORDER BY r.updated_at DESC
        LIMIT 1
        """,
        language_code, text,
    )
    if row is None:
        return None
    return {"audio": bytes(row["audio"]), "mime": row["mime"]}
