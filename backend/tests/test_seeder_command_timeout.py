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
real socket.

Returns — and, as first written, left the socket open: asyncpg's
Protocol.close() sets `closing` before it waits, and Protocol.abort()
returns at once when `closing` is set, so neither the cancelled close nor
terminate() after it touched the transport (measured 10 Sep 2026: the
Python object said closed, the fd was open, the proxy never saw EOF). So
close_quietly captures the transport first and aborts it by hand.

This file reads the source so neither guard can be lost in a refactor —
every connect has a timeout, every connect has a close_quietly — and
checks close_quietly's outcomes with a fake connection: on a hang or an
error the transport is torn down; on a clean close it is left alone.
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
    seed_sentences,
    source_data,
)

# The runbook's tools (docs/quality/refeed.md) — every one of these runs over
# the production pooler. The API-key tools (ai_check_vocab, generate_grammar,
# review_*, translate_english, harvest_sentences) are not here: see DEBT.md.
GUARDED = [base, seed_grammar, reconcile, prune_sentences, seed_alphabet,
           seed_sentences, source_data]


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
    # `await conn.close()` is the line that re-hung on 9 Sep — and
    # `conn.close(timeout=10)` is the refactor that looks like a fix and is
    # not, so any argument list is caught. Two exemptions: close_quietly's
    # docstring quotes the call in backticks, and its body is the one
    # place a close may appear — inside `asyncio.wait_for(`.
    src = inspect.getsource(module)
    lines = src.splitlines()
    bare = [line for line in lines
            if "conn.close(" in line and "`" not in line and "wait_for(" not in line]
    assert not bare, (
        f"{module.__name__}: {bare[0].strip()} — an unbounded close hangs "
        "behind the command timeout on a dropped session (9 Sep 2026); "
        "use close_quietly(conn)")
    # One bounded close per connect, so a module that gains a second
    # connection cannot close it some other way unnoticed.
    connects = sum("asyncpg.connect(" in line for line in lines)
    closes = sum("await close_quietly(conn)" in line for line in lines)
    assert closes == connects, (
        f"{module.__name__}: {connects} asyncpg.connect( sites but {closes} "
        "close_quietly(conn) sites — every production connection is closed "
        "through close_quietly")


def test_the_timeout_is_generous_but_finite():
    assert 60 <= base.COMMAND_TIMEOUT <= 900


def test_the_close_timeout_is_short_but_finite():
    assert 1 <= base.CLOSE_TIMEOUT <= 60


class _FakeTransport:
    def __init__(self):
        self.aborted = False

    def is_closing(self):
        return self.aborted

    def abort(self):
        self.aborted = True


class _FakeConn:
    """Only what close_quietly touches: close() with a chosen behaviour,
    terminate() that records it was called, and the private `_transport`
    slot asyncpg keeps the socket on."""

    def __init__(self, behaviour):
        self._behaviour = behaviour
        self.terminated = False
        self._transport = _FakeTransport()

    async def close(self):
        if self._behaviour == "hang":
            await asyncio.Event().wait()
        if isinstance(self._behaviour, BaseException):
            raise self._behaviour

    def terminate(self):
        self.terminated = True


class TestCloseQuietly:
    async def test_a_close_that_never_returns_is_abandoned(self, monkeypatch):
        # The 9 Sep shape: close() waits on a reply the pooler will never
        # send. Bounded, then torn down — the object AND the socket.
        monkeypatch.setattr(base, "CLOSE_TIMEOUT", 0.05)
        conn = _FakeConn("hang")
        await asyncio.wait_for(base.close_quietly(conn), 2)
        assert conn.terminated
        assert conn._transport.aborted

    async def test_a_close_that_raises_is_abandoned(self):
        # The 10 Sep shape: the pooler already closed the socket, so the
        # polite close fails at once. Same answer — and the error does not
        # escape the finally it runs in.
        conn = _FakeConn(ConnectionResetError(54, "Connection reset by peer"))
        await base.close_quietly(conn)
        assert conn.terminated
        assert conn._transport.aborted

    async def test_a_clean_close_is_left_alone(self):
        conn = _FakeConn("clean")
        await base.close_quietly(conn)
        assert not conn.terminated
        assert not conn._transport.aborted

    async def test_a_transport_asyncpg_already_closed_is_not_aborted_twice(self):
        # When close() failed because the socket is already gone, asyncpg
        # has closed the transport itself; abort() on it again is not
        # needed, and the guard is what keeps this from being one more
        # thing that can raise inside a finally.
        conn = _FakeConn(ConnectionResetError(54, "Connection reset by peer"))
        conn._transport.aborted = True  # is_closing() -> True

        def boom():
            raise AssertionError("abort() called on a closing transport")

        conn._transport.abort = boom
        await base.close_quietly(conn)
        assert conn.terminated

    async def test_a_cancelled_close_tears_down_then_propagates(self):
        # Ctrl-C while the close is waiting: the socket is still dropped,
        # and the cancellation is not swallowed — the seeder must stop.
        conn = _FakeConn(asyncio.CancelledError())
        with pytest.raises(asyncio.CancelledError):
            await base.close_quietly(conn)
        assert conn.terminated
        assert conn._transport.aborted

    async def test_a_connection_without_the_private_slot_still_closes(self, monkeypatch):
        # If an asyncpg release renames `_transport`, the bounded close and
        # terminate() must still happen; only the by-hand socket abort is
        # lost, and test_dropped_session_integration then fails loudly.
        monkeypatch.setattr(base, "CLOSE_TIMEOUT", 0.05)
        conn = _FakeConn("hang")
        del conn._transport
        await asyncio.wait_for(base.close_quietly(conn), 2)
        assert conn.terminated
