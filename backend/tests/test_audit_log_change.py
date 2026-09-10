"""`log_change` is best-effort about the audit table, not about the session.

Its blanket `except Exception: pass` was how the 7 Sep 2026 hang survived
the command timeout. When the statement that met the dropped pooler session
was the audit INSERT, the TimeoutError was swallowed, the seeder went on
to its next statement on the same connection — and asyncpg awaits the
pending cancel's reply before it arms any timeout on a later statement,
so that one waited for ever with no timeout, no error, no retry
(measured 10 Sep 2026; pinned in test_dropped_session_integration.py).
A dead session must propagate; an audit-table error must still not.
"""
from __future__ import annotations

import asyncpg
import pytest

# The bad-bind DataError: an InterfaceError that is also a ValueError.
# asyncpg.DataError is the server's SQLSTATE 22 class, a different thing.
from asyncpg.exceptions._base import DataError as ClientDataError

from backend.repositories import audit
from backend.services.seeder import seed_grammar


class _Conn:
    def __init__(self, error: BaseException | None = None):
        self.error = error
        self.calls = 0

    async def execute(self, *args):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return "INSERT 0 1"


async def _log(conn):
    await audit.log_change(conn, entity_type="grammar_point", entity_id="1",
                           action="seeded", language_id="x", note="test")


@pytest.mark.parametrize("err", [
    TimeoutError(),  # what asyncio.TimeoutError is since 3.11
    asyncpg.ConnectionDoesNotExistError("connection was closed in the middle of operation"),
    asyncpg.ConnectionFailureError("server closed the connection unexpectedly"),
    asyncpg.InterfaceError("connection is closed"),
    ConnectionResetError(54, "Connection reset by peer"),
])
async def test_a_dead_session_propagates(err):
    conn = _Conn(err)
    with pytest.raises(type(err)):
        await _log(conn)
    assert conn.calls == 1


@pytest.mark.parametrize("err", [
    asyncpg.UndefinedTableError('relation "content_change_log" does not exist'),
    asyncpg.UndefinedColumnError('column "note" does not exist'),
    asyncpg.NotNullViolationError("null value in column"),
    asyncpg.InsufficientPrivilegeError("permission denied"),
    ValueError("not JSON serialisable"),
    # In DEAD_SESSION by inheritance (InterfaceError), carved out by
    # ValueError: a wrong argument to the audit INSERT is audit-only.
    ClientDataError("invalid input for query argument $1: 'x' (an integer is required)"),
    asyncpg.ClientConfigurationError("unrecognized configuration parameter"),
])
async def test_an_audit_table_error_is_still_swallowed(err):
    # The migration that adds the table may not have landed; the content
    # write it annotates must go through regardless.
    conn = _Conn(err)
    await _log(conn)
    assert conn.calls == 1


async def test_a_clean_write_is_one_statement():
    conn = _Conn()
    await _log(conn)
    assert conn.calls == 1


def test_the_two_tuples_agree():
    # audit.DEAD_SESSION is what the audit lets through; seed_grammar.CUT_OFF
    # is what the seeder retries. If they drift, an error can be re-raised
    # by the audit and then not retried, or the reverse.
    assert set(audit.DEAD_SESSION) == set(seed_grammar.CUT_OFF)
