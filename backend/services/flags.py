"""Convenience reads of app_flags for routers that don't hold a connection."""
from __future__ import annotations

from backend.repositories.flags import MONETIZATION, get_flag
from backend.repositories.pool import privileged_connection


async def monetization_enabled() -> bool:
    """Whether money features are switched on. Defaults OFF — including
    when migration 20261006 hasn't landed — so payment surfaces fail safe."""
    async with privileged_connection() as conn:
        return await get_flag(conn, MONETIZATION, default=False)
