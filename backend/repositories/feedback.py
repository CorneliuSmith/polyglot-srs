"""General app feedback — the channel that is not about one card.

Reads and writes `app_feedback`. Learner-facing calls run on an RLS
connection (a user only ever touches their own rows); the triage calls run
privileged, after the router has checked the caller is staff — the same
pattern the contributor repositories use.
"""
from __future__ import annotations

import json

import asyncpg

CATEGORIES = ("bug", "confusing", "content", "idea", "other")

# Deployments that have not applied 20260906000000 yet: every feedback call
# below degrades to "no channel" rather than 500ing the home page. The
# dashboard renders the button from a capability flag, so a missing table
# hides the feature instead of breaking the page it sits on.
_MISSING = (asyncpg.exceptions.UndefinedTableError,)


async def submit_feedback(
    conn: asyncpg.Connection,
    user_id: str,
    *,
    category: str,
    message: str,
    language_id: str | None = None,
    page: str | None = None,
    variants: dict | None = None,
) -> str | None:
    """Record one piece of feedback. Returns its id, or None if the table
    isn't there yet.

    *variants* is which rollouts this account was in when they hit Send —
    resolved on the SERVER, never sent by the client, so it cannot be
    spoofed or arrive stale from a tab left open across a change. "The
    buttons are hard to see" is unusable without it and decisive with it.
    Dropped silently when 20260930 hasn't been applied: a report that
    reaches nobody is worse than a report with no label.
    """
    try:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO app_feedback
                    (user_id, language_id, category, message, page, variants)
                VALUES ($1, $2::uuid, $3, $4, $5, $6::jsonb)
                RETURNING id
                """,
                user_id, language_id, category, message.strip(), page,
                json.dumps(variants or {}),
            )
        except asyncpg.exceptions.UndefinedColumnError:
            row = await conn.fetchrow(
                """
                INSERT INTO app_feedback (user_id, language_id, category, message, page)
                VALUES ($1, $2::uuid, $3, $4, $5)
                RETURNING id
                """,
                user_id, language_id, category, message.strip(), page,
            )
    except _MISSING:
        return None
    return str(row["id"])


async def list_my_feedback(
    conn: asyncpg.Connection, user_id: str, limit: int = 20
) -> list[dict]:
    """What this user has already sent — so the app can say "we got it"
    rather than swallowing the message without trace."""
    try:
        rows = await conn.fetch(
            """
            SELECT id, category, message, page, status, admin_note, created_at
            FROM app_feedback
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id, limit,
        )
    except _MISSING:
        return []
    return [dict(r) | {"id": str(r["id"])} for r in rows]


async def list_feedback(
    conn: asyncpg.Connection,
    *,
    status: str | None = None,
    language_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """The triage list (privileged; router checks the role first).

    Joins the reporter's email so staff can follow up — feedback you cannot
    reply to is a suggestion box nailed shut.
    """
    try:
        rows = await conn.fetch(
            _TRIAGE_SQL.format(variants="f.variants,"),
            status, language_id, limit,
        )
    except asyncpg.exceptions.UndefinedColumnError:
        # 20260930 not applied: triage without the variant label rather than
        # no triage at all.
        rows = await conn.fetch(
            _TRIAGE_SQL.format(variants=""), status, language_id, limit,
        )
    except _MISSING:
        return []
    return [
        dict(r) | {
            "id": str(r["id"]),
            "user_id": str(r["user_id"]) if r["user_id"] else None,
            "variants": _loads(dict(r).get("variants")) or {},
        }
        for r in rows
    ]


# One statement, two shapes. `{variants}` is the only difference between
# them, so the ordering rule below can never drift between the migrated and
# the not-yet-migrated read.
_TRIAGE_SQL = """
    SELECT f.id, f.user_id, u.email, f.language_id, l.name AS language_name,
           {variants}
           f.category, f.message, f.page, f.status, f.admin_note, f.created_at
      FROM app_feedback f
      LEFT JOIN auth.users u ON u.id = f.user_id
      LEFT JOIN languages  l ON l.id = f.language_id
     WHERE ($1::text IS NULL OR f.status = $1)
       AND ($2::uuid IS NULL OR f.language_id = $2::uuid)
     ORDER BY
         -- Open first: a triage list sorted purely by date buries the
         -- thing that still needs doing under everything already done.
         CASE f.status WHEN 'open' THEN 0 WHEN 'triaged' THEN 1 ELSE 2 END,
         f.created_at DESC
     LIMIT $3
"""


def _loads(value):
    """asyncpg hands JSONB back as str unless a codec is registered."""
    return json.loads(value) if isinstance(value, str) else value


async def count_open_feedback(conn: asyncpg.Connection) -> int:
    try:
        return await conn.fetchval(
            "SELECT count(*) FROM app_feedback WHERE status = 'open'"
        ) or 0
    except _MISSING:
        return 0


async def feedback_summary(conn: asyncpg.Connection) -> dict:
    """How much is waiting, and when the newest arrived.

    Deliberately two scalars rather than the list: the dashboard asks this on
    every load to decide whether to show a prompt, and pulling the whole
    triage queue to count it would make the home page pay for a screen the
    learner may never open. *latest_at* is what lets the client tell "three
    open items I already looked at" from "something new since I was last
    here" without storing read state server-side.
    """
    try:
        row = await conn.fetchrow(
            "SELECT count(*) FILTER (WHERE status = 'open') AS open_count, "
            "       max(created_at) AS latest_at "
            "FROM app_feedback"
        )
    except _MISSING:
        # Migration 20260906 not applied — no feedback table, nothing waiting.
        return {"open_count": 0, "latest_at": None}
    return {
        "open_count": row["open_count"] or 0,
        "latest_at": row["latest_at"].isoformat() if row["latest_at"] else None,
    }


async def set_feedback_status(
    conn: asyncpg.Connection,
    feedback_id: str,
    *,
    status: str,
    admin_note: str | None = None,
) -> bool:
    """Triage one item. A None note leaves any existing note alone rather
    than wiping it — closing something should not erase why."""
    try:
        result = await conn.execute(
            """
            UPDATE app_feedback
            SET status = $2,
                admin_note = COALESCE($3, admin_note)
            WHERE id = $1::uuid
            """,
            feedback_id, status, admin_note,
        )
    except _MISSING:
        return False
    return result.endswith("1")
