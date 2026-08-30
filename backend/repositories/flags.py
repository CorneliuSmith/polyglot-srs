"""App-wide runtime switches (app_flags) — currently one: 'monetization'.

The monetization master switch exists because the owner cannot run money
features until an employer conflict-of-interest clearance lands — so every
payment surface checks it, and it defaults OFF. Probed with to_regclass
(never raises) so a deploy ahead of migration 20261006 fails safe: the
flag reads as false and nothing payment-related shows anywhere.
"""
from __future__ import annotations

import asyncpg

MONETIZATION = "monetization"


async def _flags_present(conn: asyncpg.Connection) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass('app_flags') IS NOT NULL"))


async def get_flag(
    conn: asyncpg.Connection, key: str, *, default: bool = False
) -> bool:
    """The flag's stored value; *default* when the table or row is missing."""
    if not await _flags_present(conn):
        return default
    value = await conn.fetchval("SELECT enabled FROM app_flags WHERE key = $1", key)
    return default if value is None else bool(value)


async def set_flag(
    conn: asyncpg.Connection, key: str, enabled: bool, admin_id: str
) -> bool:
    """Admin-only (router enforces). Returns False when migration 20261006
    hasn't been applied — the router turns that into a clear 503; an
    admin's write failing silently is worse than a read degrading."""
    if not await _flags_present(conn):
        return False
    await conn.execute(
        """
        INSERT INTO app_flags (key, enabled, updated_by, updated_at)
        VALUES ($1, $2, $3, now())
        ON CONFLICT (key) DO UPDATE
        SET enabled = $2, updated_by = $3, updated_at = now()
        """,
        key, enabled, admin_id,
    )
    return True
