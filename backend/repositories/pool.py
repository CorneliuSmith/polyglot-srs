"""asyncpg pool lifecycle and RLS-aware connection context manager."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg

from backend.config import get_settings

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str) -> None:
    """Create the asyncpg connection pool."""
    global _pool
    settings = get_settings()
    kwargs: dict = {
        "dsn": dsn,
        "min_size": 2,
        "max_size": 10,
        "command_timeout": 30,
    }
    # Supavisor (port 6543) requires disabling prepared statement caching
    if settings.environment != "development":
        kwargs["statement_cache_size"] = 0
    _pool = await asyncpg.create_pool(**kwargs)


async def close_pool() -> None:
    """Close the connection pool if initialized."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the initialized pool. Asserts pool is ready."""
    assert _pool is not None, "Pool not initialized — call init_pool first"
    return _pool


@asynccontextmanager
async def rls_connection(user_id: str) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection with RLS context set for the given user.

    Sets request.jwt.claims and role so that auth.uid() returns
    the authenticated user's ID within RLS policies.

    CRITICAL: Third argument to set_config MUST be true (transaction-scoped)
    to prevent user context leaking across pooled connections.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        claims = json.dumps({"sub": user_id, "role": "authenticated"})
        await conn.execute(
            "SELECT set_config('request.jwt.claims', $1, true)",
            claims,
        )
        await conn.execute(
            "SELECT set_config('role', 'authenticated', true)",
        )
        yield conn
