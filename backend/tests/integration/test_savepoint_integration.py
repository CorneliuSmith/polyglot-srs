"""`savepoint()` really does recover a transaction — on a REAL Postgres.

The unit suite can only show that the helper opens a nested transaction.
What it cannot show is the thing the helper exists for: that after a
statement fails INSIDE the block, the next statement on the same connection
succeeds. Without the savepoint, Postgres answers every later statement
with `InFailedSQLTransactionError` until the outer transaction rolls back
— which is exactly how the readiness endpoint 500ed on the deployed app
through a catch-and-retry that looked like a fallback and was not one.
"""
from __future__ import annotations

import asyncpg
import pytest

from backend.repositories.pool import savepoint

from .conftest import requires_db

pytestmark = requires_db


async def _wide_then_narrow(conn: asyncpg.Connection) -> int:
    """The shape every converted site has: try a column this deploy may be
    ahead of, fall back to one that has always existed."""
    try:
        async with savepoint(conn):
            return await conn.fetchval(
                "SELECT count(*) FROM languages WHERE no_such_column IS NULL"
            )
    except asyncpg.exceptions.UndefinedColumnError:
        return await conn.fetchval("SELECT count(*) FROM languages")


async def test_privileged_connection_survives_a_failed_probe(pool):
    async with pool.privileged_connection() as conn:
        count = await _wide_then_narrow(conn)
        # The transaction is still alive: an unrelated statement works, and
        # a write made afterwards commits with the block.
        assert await conn.fetchval("SELECT 1") == 1
        await conn.execute(
            "INSERT INTO languages (code, name) VALUES ('svp', 'Savepoint') "
            "ON CONFLICT (code) DO NOTHING"
        )
    assert isinstance(count, int)
    async with pool.privileged_connection() as conn:
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM languages WHERE code = 'svp')"
        )


async def test_rls_connection_survives_a_failed_probe(pool):
    async with pool.privileged_connection() as conn:
        user = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ('savepoint@t') RETURNING id"
        )
    async with pool.rls_connection(str(user)) as conn:
        count = await _wide_then_narrow(conn)
        assert await conn.fetchval("SELECT 1") == 1
        # The role and identity set by rls_connection are still in force
        # after the rollback-to-savepoint — a ROLLBACK of the whole
        # transaction would have dropped the SET LOCALs with it.
        assert await conn.fetchval("SELECT auth.uid()") == user
    assert isinstance(count, int)


async def test_without_a_savepoint_the_retry_itself_fails(pool):
    """Pins the failure mode the helper prevents, so nobody 'simplifies'
    the helper away: the bare catch-and-retry is not a fallback."""
    async with pool.privileged_connection() as conn:
        with pytest.raises(asyncpg.exceptions.UndefinedColumnError):
            await conn.fetchval(
                "SELECT count(*) FROM languages WHERE no_such_column IS NULL"
            )
        with pytest.raises(asyncpg.exceptions.InFailedSQLTransactionError):
            await conn.fetchval("SELECT count(*) FROM languages")
        # Leave the block on a dead transaction: the helper's __aexit__ must
        # roll back cleanly rather than raise a second error over the first.
