"""Languages repository — public table, no RLS needed."""

from __future__ import annotations

import asyncpg


async def get_all_languages(pool: asyncpg.Pool) -> list[dict]:
    """Return every seeded language ordered by name, including hidden ones
    (is_visible=false) — the frontend filters those out of learner-facing
    pickers itself so admin surfaces (which need to reach a hidden language
    to build/manage it) don't need a second endpoint."""
    try:
        rows = await pool.fetch(
            "SELECT id, code, name, rtl, is_visible FROM languages ORDER BY name"
        )
        return [dict(r) for r in rows]
    except asyncpg.exceptions.UndefinedColumnError:
        # Migration 20260831 (is_visible) not applied yet. This endpoint is
        # load-bearing for the entire app — an empty language list blanks the
        # dashboard — so degrade to everything-visible instead of 500ing.
        # /api/health/schema names the pending migration.
        rows = await pool.fetch(
            "SELECT id, code, name, rtl FROM languages ORDER BY name"
        )
        return [{**dict(r), "is_visible": True} for r in rows]


async def set_language_visibility(
    conn: asyncpg.Connection, language_id: str, is_visible: bool
) -> bool:
    """Admin-only: show/hide a language in learner-facing pickers. Returns
    False for an unknown language_id (router 404s)."""
    result = await conn.execute(
        "UPDATE languages SET is_visible = $2 WHERE id = $1", language_id, is_visible
    )
    return result != "UPDATE 0"
