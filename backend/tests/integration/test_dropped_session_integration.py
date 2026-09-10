"""A dropped pooler session, reproduced against a real socket.

The 7 Sep 2026 hang was a pooler that stopped answering while TCP stayed
ESTABLISHED. `command_timeout` was added on reasoning alone, and on 9 Sep
a ten-second reproduction showed the statement does time out — and that
asyncpg's close() then hangs for ever behind it, because Protocol.close()
awaits the cancelled statement's reply before it looks at any timeout.
The 10 Sep shape is the other one: the pooler actively closed the socket
mid-statement, which asyncpg reports on its own as a connection error.

A TCP proxy in front of the integration Postgres reproduces both: forward
everything, then either swallow server->client bytes (blackhole: the 7 Sep
hang) or drop the client transport (reset: the 10 Sep error). asyncpg's
cancel request arrives as a SECOND connection through the same proxy, and
asyncpg waits for the server to close it; so the blackhole applies only to
sessions that were open when it was switched on. The cancel connection is
forwarded normally and hangs up when the server does — which is what a
real pooler does too, and is what makes the close hang on the cancelled
statement's reply rather than on the cancel itself.

No schema fixture: the tests only need a Postgres that answers `SELECT`.
"""
from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit

import asyncpg
import pytest

from backend.services.seeder import base, seed_grammar

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db


class _Proxy:
    """A blackholing / resetting TCP proxy on 127.0.0.1, one upstream."""

    def __init__(self, host: str, port: int):
        self.upstream = (host, port)
        self.blackhole = False
        self.reset = False
        self._server: asyncio.AbstractServer | None = None
        self._tasks: set[asyncio.Task] = set()
        self._client_writers: list[asyncio.StreamWriter] = []
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        # Cancel the pipes before closing the server: an in-flight
        # `await reader.read()` that is never cancelled is "Task was
        # destroyed but it is pending" at interpreter exit.
        for t in list(self._tasks):
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for w in self._client_writers:
            w.transport.abort()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    def cut(self) -> None:
        """The 10 Sep shape: close every client socket abruptly, now."""
        self.reset = True
        for w in self._client_writers:
            w.transport.abort()

    async def _pipe(self, reader, writer, *, drop_replies) -> None:
        """One direction. `drop_replies()` says whether this direction's
        bytes are the swallowed server->client half of a blackholed session."""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                if drop_replies():
                    continue  # swallow the reply; never close — 7 Sep
                writer.write(data)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            # A blackholed session keeps its client side open (that is the
            # hang); every other EOF is passed on — the cancel request's
            # connection in particular must be allowed to hang up.
            if not drop_replies() and not writer.transport.is_closing():
                writer.transport.close()

    async def _handle(self, client_r, client_w) -> None:
        self._client_writers.append(client_w)
        victim = not self.blackhole  # opened before the drop: the session under test
        up_r, up_w = await asyncio.open_connection(*self.upstream)
        a = asyncio.ensure_future(self._pipe(client_r, up_w, drop_replies=lambda: False))
        b = asyncio.ensure_future(self._pipe(
            up_r, client_w, drop_replies=lambda: victim and self.blackhole))
        self._tasks.update({a, b})
        try:
            await asyncio.gather(a, b, return_exceptions=True)
        finally:
            self._tasks.difference_update({a, b})
            up_w.transport.abort()


def _through(dsn: str, port: int) -> str:
    """The DSN with its host:port swapped for the proxy's."""
    parts = urlsplit(dsn)
    userinfo = parts.netloc.rsplit("@", 1)[0] + "@" if "@" in parts.netloc else ""
    return parts._replace(netloc=f"{userinfo}127.0.0.1:{port}").geturl()


@pytest.fixture
async def proxy():
    parts = urlsplit(INTEGRATION_DSN)
    p = _Proxy(parts.hostname or "127.0.0.1", parts.port or 5432)
    await p.start()
    try:
        yield p
    finally:
        await p.stop()


@pytest.fixture
def proxied_dsn(proxy):
    return _through(INTEGRATION_DSN, proxy.port)


async def _blackholed_after_timeout(proxy, dsn, command_timeout=1.0):
    """A connection whose session the proxy has dropped and whose statement
    has already timed out — the state the seeder's `finally` runs in."""
    conn = await asyncpg.connect(dsn, command_timeout=command_timeout)
    assert await conn.fetchval("SELECT 1") == 1
    proxy.blackhole = True
    t0 = time.monotonic()
    with pytest.raises(asyncio.TimeoutError):
        await conn.fetchval("SELECT 2")
    return conn, time.monotonic() - t0


class TestBlackholedSession:
    async def test_the_statement_times_out(self, proxy, proxied_dsn):
        # What #433 bought: the wait is bounded by command_timeout.
        conn, elapsed = await _blackholed_after_timeout(proxy, proxied_dsn, 1.0)
        try:
            assert elapsed < 1.0 + 3.0, f"timed out after {elapsed:.1f}s, not ~1s"
        finally:
            conn.terminate()

    async def test_a_plain_close_still_hangs_behind_it(self, proxy, proxied_dsn):
        """NEGATIVE CONTROL, pinning asyncpg's behaviour: after the timeout,
        `conn.close()` does not return — it awaits the cancelled statement's
        reply first, and the dropped session never sends it. If this starts
        failing, asyncpg fixed it and close_quietly can be retired."""
        conn, _ = await _blackholed_after_timeout(proxy, proxied_dsn, 1.0)
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(conn.close(), 2)
        finally:
            conn.terminate()
        assert conn.is_closed()

    async def test_close_quietly_returns(self, proxy, proxied_dsn, monkeypatch):
        monkeypatch.setattr(base, "CLOSE_TIMEOUT", 2)
        conn, _ = await _blackholed_after_timeout(proxy, proxied_dsn, 1.0)
        t0 = time.monotonic()
        await asyncio.wait_for(base.close_quietly(conn), 5)
        assert time.monotonic() - t0 < 5
        assert conn.is_closed()


class TestResetSession:
    async def test_a_reset_mid_statement_is_a_cut_off(self, proxy, proxied_dsn):
        # The 10 Sep shape: the pooler closed the socket while a statement
        # was in flight. Whatever asyncpg raises for that must be in the
        # tuple seed_grammar retries on, or the retry is decoration.
        conn = await asyncpg.connect(proxied_dsn, command_timeout=5)
        assert await conn.fetchval("SELECT 1") == 1

        async def cut_soon():
            await asyncio.sleep(0.2)
            proxy.cut()

        cutter = asyncio.ensure_future(cut_soon())
        try:
            with pytest.raises(Exception) as info:
                await conn.fetchval("SELECT pg_sleep(3)")
            assert isinstance(info.value, seed_grammar.CUT_OFF), (
                f"{type(info.value).__name__}: {info.value} is not in CUT_OFF")
        finally:
            await cutter
            conn.terminate()

    async def test_a_refused_connect_is_a_cut_off(self, proxy, proxied_dsn):
        # The three courses after `en` on 10 Sep: the pooler refused new
        # sessions for about a minute. connect() itself raises an OSError.
        await proxy.stop()
        with pytest.raises(Exception) as info:
            await asyncpg.connect(proxied_dsn, command_timeout=5)
        assert isinstance(info.value, seed_grammar.CUT_OFF), (
            f"{type(info.value).__name__}: {info.value} is not in CUT_OFF")
