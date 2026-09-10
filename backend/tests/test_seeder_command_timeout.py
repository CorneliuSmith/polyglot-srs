"""Every content tool's production connection has a bounded wait AND a
bounded close.

On 7 Sep 2026 `seed_grammar -l all` hung for two hours after "OK en": the
pooler had reset the server side of its session and asyncpg, with no
command timeout, waited for a reply that was never coming — 0% CPU, one
ESTABLISHED socket, nothing on the server. The operator could not tell it
from a slow run. #433 added `command_timeout=COMMAND_TIMEOUT` to every
production connect and said a dropped session "now fails loudly".

It did not, quite. On 9 Sep 2026 the hang was reproduced with a proxy that
swallows server->client bytes while keeping TCP open: the statement DID
raise asyncio.TimeoutError after the timeout — and then the seeder's
`finally: await conn.close()` hung for ever behind it. asyncpg's
Protocol.close() awaits the cancelled statement's reply before it consults
any close timeout, and a dropped session never replies. So the guard was
reasoned about, not measured, and the timeout had moved the hang five
minutes to the right. `close_quietly` (bounded close, then terminate) is
what returns; `test_dropped_session_integration.py` proves it against a
real socket. This file reads the source so neither guard can be lost in a
refactor, and checks close_quietly's three outcomes with a fake connection.
"""
from __future__ import annotations

import asyncio
import inspect

import pytest

from backend.services.seeder import (
    base,
    prune_sentences,
    reconcile,
    seed_alphabet,
    seed_grammar,
    source_data,
)

GUARDED = [base, seed_grammar, reconcile, prune_sentences, seed_alphabet, source_data]


@pytest.mark.parametrize("module", GUARDED)
def test_every_production_connect_has_a_command_timeout(module):
    src = inspect.getsource(module)
    connects = [line for line in src.splitlines() if "asyncpg.connect(" in line]
    assert connects, f"{module.__name__} no longer connects? update this test"
    for line in connects:
        assert "command_timeout=" in line, (
            f"{module.__name__}: {line.strip()} has no command_timeout — "
            "a stalled pooler would hang it for ever (7 Sep 2026)")


@pytest.mark.parametrize("module", GUARDED)
def test_every_production_close_is_bounded(module):
    # `await conn.close()` is the line that re-hung on 9 Sep. close_quietly's
    # own docstring quotes it in backticks; code never does.
    src = inspect.getsource(module)
    bare = [line for line in src.splitlines()
            if "await conn.close()" in line and "`" not in line]
    assert not bare, (
        f"{module.__name__}: {bare[0].strip()} — an unbounded close hangs "
        "behind the command timeout on a dropped session (9 Sep 2026); "
        "use close_quietly(conn)")
    assert "close_quietly(conn)" in src, (
        f"{module.__name__} no longer closes through close_quietly")


def test_the_timeout_is_generous_but_finite():
    assert 60 <= base.COMMAND_TIMEOUT <= 900


def test_the_close_timeout_is_short_but_finite():
    assert 1 <= base.CLOSE_TIMEOUT <= 60


class _FakeConn:
    """Only what close_quietly touches: close() with a chosen behaviour, and
    terminate() that records it was called."""

    def __init__(self, behaviour):
        self._behaviour = behaviour
        self.terminated = False

    async def close(self):
        if self._behaviour == "hang":
            await asyncio.Event().wait()
        if isinstance(self._behaviour, Exception):
            raise self._behaviour

    def terminate(self):
        self.terminated = True


class TestCloseQuietly:
    async def test_a_close_that_never_returns_is_abandoned(self, monkeypatch):
        # The 9 Sep shape: close() waits on a reply the pooler will never
        # send. Bounded, then torn down.
        monkeypatch.setattr(base, "CLOSE_TIMEOUT", 0.05)
        conn = _FakeConn("hang")
        await asyncio.wait_for(base.close_quietly(conn), 2)
        assert conn.terminated

    async def test_a_close_that_raises_is_abandoned(self):
        # The 10 Sep shape: the pooler already closed the socket, so the
        # polite close fails at once. Same answer — and the error does not
        # escape the finally it runs in.
        conn = _FakeConn(ConnectionResetError(54, "Connection reset by peer"))
        await base.close_quietly(conn)
        assert conn.terminated

    async def test_a_clean_close_is_left_alone(self):
        conn = _FakeConn("clean")
        await base.close_quietly(conn)
        assert not conn.terminated
