"""Languages repository — public table, no RLS needed."""

from __future__ import annotations

import asyncpg


async def get_all_languages(pool: asyncpg.Pool) -> list[dict]:
    """Return all seeded languages ordered by name."""
    rows = await pool.fetch(
        "SELECT id, code, name, rtl FROM languages ORDER BY name"
    )
    return [dict(r) for r in rows]
