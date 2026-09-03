"""Convenience reads of app_flags for routers that don't hold a connection."""
from __future__ import annotations

import asyncpg

from backend.repositories.flags import MONETIZATION, get_flag
from backend.repositories.pool import privileged_connection


async def monetization_enabled() -> bool:
    """Whether money features are switched on. Defaults OFF — including
    when migration 20261006 hasn't landed, and when the flag cannot be read
    at all (no pool yet, a database error) — so payment surfaces fail safe.
    Read on the allowance hot path too, where "off" is the answer that
    honours a chosen plan rather than the one that charges for it."""
    try:
        async with privileged_connection() as conn:
            return await get_flag(conn, MONETIZATION, default=False)
    except (AssertionError, asyncpg.PostgresError, OSError):
        return False
