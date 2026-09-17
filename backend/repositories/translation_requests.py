"""Learner requests for a support locale to be filled on a course.

The auto-translate toggle buys the BACKLOG DRAIN, not the right to be
served: `services/auto_translate.py` always translates what a learner is
waiting on (the demand lane) and buys a usage-scaled starter corpus for a
switched-off course in real use (the baseline lane). So a request here is
not "I am getting nothing" — it is "the rest of this course stays English
and I would like it filled", which is a budget decision only the owner can
make.

Everything is probed: migration 20261024 is owner-applied, and until it
lands the ask is simply unavailable rather than a 500 on the settings page
(the profile endpoint is on every page load — the is_visible outage taught
this once).
"""
from __future__ import annotations

import asyncpg


async def requests_table_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20261024 has landed. to_regclass, never raises."""
    return bool(
        await conn.fetchval("SELECT to_regclass('translation_requests') IS NOT NULL")
    )


async def add_request(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    locale: str, note: str | None = None,
) -> str:
    """Record one ask. Returns 'created', 'already' (this learner has asked
    before, any status), or 'unavailable' (migration not applied).

    Asking twice is asking once — the UNIQUE carries that, and the caller
    answers the same either way, so the button can never turn one impatient
    learner into a louder signal than a patient one.
    """
    if not await requests_table_present(conn):
        return "unavailable"
    result = await conn.execute(
        """
        INSERT INTO translation_requests (user_id, language_id, locale, note)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, language_id, locale) DO NOTHING
        """,
        user_id, language_id, locale, (note or "").strip()[:500] or None,
    )
    return "created" if result.endswith("1") else "already"


async def my_request(
    conn: asyncpg.Connection, user_id: str, language_id: str, locale: str,
) -> dict | None:
    """This learner's ask for this pair, if any. None when absent or when
    the migration has not landed."""
    if not await requests_table_present(conn):
        return None
    row = await conn.fetchrow(
        """SELECT status, requested_at, decided_at
             FROM translation_requests
            WHERE user_id = $1 AND language_id = $2 AND locale = $3""",
        user_id, language_id, locale,
    )
    if row is None:
        return None
    return {
        "status": row["status"],
        "requested_at": row["requested_at"].isoformat(),
        "decided_at": row["decided_at"].isoformat() if row["decided_at"] else None,
    }


async def open_request_counts(conn: asyncpg.Connection) -> dict[str, list[dict]]:
    """Open asks per course, grouped by locale, for the admin's language row.

    Keyed by language id as a string so the panel can look one up without a
    scan. The locale's display name comes from `languages` when the locale
    is itself a course; a locale that is only an interface language shows
    its code, which is what the admin picked it by anyway.
    """
    if not await requests_table_present(conn):
        return {}
    rows = await conn.fetch(
        """
        SELECT r.language_id, r.locale, l.name AS locale_name, count(*) AS n
          FROM translation_requests r
          LEFT JOIN languages l ON l.code = r.locale
         WHERE r.status = 'open'
         GROUP BY r.language_id, r.locale, l.name
         ORDER BY count(*) DESC, r.locale
        """
    )
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(str(r["language_id"]), []).append({
            "locale": r["locale"],
            "locale_name": r["locale_name"] or r["locale"],
            "learners": int(r["n"]),
        })
    return out


async def fulfil_requests(conn: asyncpg.Connection, language_id: str) -> int:
    """Close this course's open asks — called when the backlog drain is
    switched ON, which is exactly what they asked for. Returns how many.

    Never raises into the toggle: a request table that is not there yet
    must not stop an admin enabling translation.
    """
    if not await requests_table_present(conn):
        return 0
    result = await conn.execute(
        """UPDATE translation_requests
              SET status = 'fulfilled', decided_at = now()
            WHERE language_id = $1 AND status = 'open'""",
        language_id,
    )
    return int(result.rsplit(" ", 1)[-1] or 0)


async def count_open_requests(conn: asyncpg.Connection) -> int:
    """Total open asks — the staff bell's signal. Probed, so a pre-migration
    deploy reads 0 rather than 500ing the bell."""
    if not await requests_table_present(conn):
        return 0
    return int(await conn.fetchval(
        "SELECT count(*) FROM translation_requests WHERE status = 'open'"
    ) or 0)
