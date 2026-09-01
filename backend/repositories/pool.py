"""asyncpg pool lifecycle and RLS-aware connection context manager."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
async def privileged_connection() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection WITHOUT the authenticated RLS context.

    Runs as the pool's database role (which owns the content tables), so it
    can write content tables (e.g. grammar_points) that RLS would otherwise
    restrict. Authorization for these writes is enforced in the application
    layer BEFORE calling this — never expose it to unchecked user input.
    Wrapped in a transaction for atomicity.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn


@asynccontextmanager
async def rls_connection(user_id: str) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection with RLS context set for the given user.

    Sets request.jwt.claims and role so that auth.uid() returns
    the authenticated user's ID within RLS policies.

    CRITICAL: Third argument to set_config MUST be true (transaction-scoped)
    to prevent user context leaking across pooled connections.  That only
    works inside an explicit transaction — in autocommit mode each statement
    is its own transaction, so the setting would vanish before the next
    query.  All work on the yielded connection therefore runs in a single
    transaction (which also makes multi-statement handlers atomic).
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            claims = json.dumps({"sub": user_id, "role": "authenticated"})
            await conn.execute(
                "SELECT set_config('request.jwt.claims', $1, true)",
                claims,
            )
            await conn.execute(
                "SELECT set_config('role', 'authenticated', true)",
            )
            yield conn


@asynccontextmanager
async def savepoint(conn: asyncpg.Connection) -> AsyncIterator[None]:
    """Run a statement that MAY fail on a schema this deploy is ahead of,
    without poisoning the rest of the transaction.

    Both connection helpers above wrap everything in one transaction, and
    Postgres aborts a transaction at the first failed statement: every
    later statement raises `InFailedSQLTransactionError` until rollback.
    So the pattern

        try:
            await conn.fetch(<wide SELECT>)
        except UndefinedColumnError:
            await conn.fetch(<narrow SELECT>)     # <- raises anyway

    reads as a fallback and is not one — the retry is the second statement
    on a dead transaction. Thirty-six sites had that shape; the readiness
    endpoint 500ed through one of them on the deployed app.

    A savepoint scopes the failure: asyncpg's nested `transaction()` emits
    SAVEPOINT / RELEASE, and on an exception ROLLBACK TO SAVEPOINT, which
    puts the outer transaction back where it was. Outside any transaction
    this is simply a transaction, so the same code works on a bare pooled
    connection too.

        try:
            async with savepoint(conn):
                rows = await conn.fetch(<wide SELECT>)
        except UndefinedColumnError:
            rows = await conn.fetch(<narrow SELECT>)  # a live transaction

    Prefer asking first (`to_regclass`, information_schema — see
    docs/decisions/0001) when the probe is cheap and the answer is reused;
    use this when the attempt IS the cheapest probe.
    """
    async with conn.transaction():
        yield
