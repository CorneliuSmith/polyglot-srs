"""Trial-request queue — the public front door of the invite-only beta.

All access runs on the privileged connection: the request endpoint has no
authenticated user, and the queue (strangers' emails) is admin-read-only.
The table has RLS on with no policies, so nothing leaks through user
connections either way.
"""
from __future__ import annotations

import asyncpg


async def trials_table_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20260921 has landed. to_regclass, never raises —
    the login page's request form must get a clear 503, not a 500."""
    return bool(
        await conn.fetchval("SELECT to_regclass('trial_requests') IS NOT NULL")
    )


async def add_trial_request(
    conn: asyncpg.Connection, email: str, name: str | None, note: str | None
) -> bool:
    """Queue one request. Returns False when the email already has a row
    (any status) — the endpoint answers identically either way, so the form
    can't be used to enumerate who has asked or who has an account."""
    result = await conn.execute(
        """
        INSERT INTO trial_requests (email, name, note)
        VALUES (lower($1), $2, $3)
        ON CONFLICT (email) DO NOTHING
        """,
        email, name, note,
    )
    return result.endswith("1")


async def count_pending_trial_requests(conn: asyncpg.Connection) -> int:
    """How many requests are still undecided — the staff bell's signal.

    Email announcement is best-effort (it needs ADMIN_NOTIFY_EMAIL AND a
    Resend key, and either can be unset or rejected without anyone
    noticing). A stranger asking for access must not depend on that:
    this count puts the same fact in the app, where it cannot be lost.
    Probed, so a pre-migration deploy reads 0 rather than 500ing the bell.
    """
    if not await trials_table_present(conn):
        return 0
    return await conn.fetchval(
        "SELECT count(*) FROM trial_requests WHERE status = 'pending'"
    )


async def list_trial_requests(conn: asyncpg.Connection) -> list[dict]:
    """The admin queue: pending first, newest first within each group."""
    rows = await conn.fetch(
        """
        SELECT id, email, name, note, status, requested_at, decided_at
        FROM trial_requests
        ORDER BY (status = 'pending') DESC, requested_at DESC
        LIMIT 200
        """
    )
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "name": r["name"],
            "note": r["note"],
            "status": r["status"],
            "requested_at": r["requested_at"].isoformat(),
            "decided_at": r["decided_at"].isoformat() if r["decided_at"] else None,
        }
        for r in rows
    ]


async def get_trial_request(
    conn: asyncpg.Connection, request_id: str
) -> dict | None:
    row = await conn.fetchrow(
        "SELECT id, email, name, note, status FROM trial_requests WHERE id = $1",
        request_id,
    )
    if row is None:
        return None
    return {**dict(row), "id": str(row["id"])}


async def mark_trial_decided(
    conn: asyncpg.Connection, request_id: str, status: str, decided_by: str
) -> None:
    await conn.execute(
        """
        UPDATE trial_requests
        SET status = $2, decided_at = now(), decided_by = $3
        WHERE id = $1
        """,
        request_id, status, decided_by,
    )
