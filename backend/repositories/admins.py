"""Who the admins are, as email addresses — and when each was last written to.

Admin notifications used to go to ONE address from ADMIN_NOTIFY_EMAIL. That
is a config value nobody set (it wasn't even in .env.example), so trial
requests announced themselves into the void for weeks. The accounts holding
the admin role are already in the database and cannot drift out of date, so
they are the recipient list; the env var stays supported as an extra address
for a pager or a shared inbox that owns no account.
"""
from __future__ import annotations

import asyncpg


async def admin_recipients(conn: asyncpg.Connection) -> list[dict]:
    """Every account holding the admin role, with its email.

    An admin grant is language-scoped in the table but admin power never is
    (is_admin ignores language_id), so DISTINCT collapses someone granted it
    twice into one recipient rather than mailing them twice.
    """
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (u.id) u.id, u.email
        FROM contributor_roles cr
        JOIN auth.users u ON u.id = cr.user_id
        WHERE cr.role = 'admin'
          AND u.email IS NOT NULL
          AND u.email <> ''
        ORDER BY u.id
        """
    )
    return [{"id": str(r["id"]), "email": r["email"]} for r in rows]


async def digest_log_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20261008 has landed. to_regclass, never raises."""
    return bool(
        await conn.fetchval("SELECT to_regclass('admin_digest_log') IS NOT NULL")
    )


async def admins_due_for_digest(
    conn: asyncpg.Connection, min_hours: int
) -> list[dict]:
    """Admins who haven't been sent a digest in *min_hours*.

    Empty when the migration hasn't landed — the sweep would otherwise have
    no way to remember who it wrote to and would mail every admin on every
    pass. Silence is the right failure here; the staff bell carries the same
    facts in the app meanwhile.
    """
    if not await digest_log_present(conn):
        return []
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (u.id) u.id, u.email
        FROM contributor_roles cr
        JOIN auth.users u ON u.id = cr.user_id
        LEFT JOIN admin_digest_log d ON d.user_id = u.id
        WHERE cr.role = 'admin'
          AND u.email IS NOT NULL
          AND u.email <> ''
          AND (d.last_sent_at IS NULL
               OR d.last_sent_at < now() - make_interval(hours => $1))
        ORDER BY u.id
        """,
        min_hours,
    )
    return [{"id": str(r["id"]), "email": r["email"]} for r in rows]


async def mark_digest_sent(conn: asyncpg.Connection, user_id: str) -> None:
    """Stamp an ACCEPTED send. Never called for a rejected one, so a mail
    outage retries on the next pass rather than eating the report."""
    await conn.execute(
        """
        INSERT INTO admin_digest_log (user_id, last_sent_at)
        VALUES ($1, now())
        ON CONFLICT (user_id) DO UPDATE SET last_sent_at = now()
        """,
        user_id,
    )
