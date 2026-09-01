"""Shared stand-ins for asyncpg connections in unit tests.

`backend.repositories.pool.savepoint` opens `conn.transaction()` around every
migration-tolerant query, so a fake connection has to answer that call with
an async context manager. A bare `AsyncMock()` answers with a coroutine
instead — the first savepoint then raises `TypeError: 'coroutine' object
does not support the asynchronous context manager protocol`, which looks
like a broken repository and is only a broken mock. Build connections with
`mock_conn()` (or give a hand-written fake a `transaction` method that
returns `FakeTransaction()`) and the savepoint is inert.
"""
from __future__ import annotations

from unittest.mock import AsyncMock


class FakeTransaction:
    """`conn.transaction()` as an inert async context manager.

    Never suppresses: `__aexit__` returns False so the UndefinedColumnError a
    test raises from inside the savepoint still reaches the `except` the
    code under test is built around.
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def mock_conn(**kwargs) -> AsyncMock:
    """An `AsyncMock` connection whose `transaction()` works under savepoint."""
    conn = AsyncMock(**kwargs)
    conn.transaction = FakeTransaction
    return conn
