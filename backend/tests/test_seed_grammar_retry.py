"""`seed_grammar` retries a course whose session was cut off, and says so.

On 10 Sep 2026 the owner's per-course loop printed "OK el", then
"FAIL en: connection was closed in the middle of operation", then three
courses of "[Errno 54] Connection reset by peer", then "OK ha" — a pooler
outage of about a minute cost four courses that a pause and a second try
would have recovered. And a course that hit the command timeout printed
"FAIL en: " with nothing after the colon, because str(TimeoutError()) is
empty. These tests drive `_main` end to end with transform and load
replaced, so the retry policy, the printed lines and the exception
classification are checked without a database.
"""
from __future__ import annotations

import sys

import asyncpg
import pytest

from backend.services.seeder import seed_grammar

FAKE_DATA = {
    "lists": [{"level": "A1", "title": "A1 Grammar"}],
    "points": [
        {"title": "P1", "level": "A1", "drills": [{"sentence": "a {{answer}}", "answer": "x"}]},
        {"title": "P2", "level": "A1", "drills": [{"sentence": "b {{answer}}", "answer": "y"},
                                                  {"sentence": "c {{answer}}", "answer": "z"}]},
        {"title": "P3", "level": "A1", "drills": []},
    ],
}


class _Load:
    """A load() stand-in that raises the scripted errors in order, then
    returns; records every call and the data it was handed. Installed on
    the class, so an instance is not bound: no `self` for the seeder."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    async def __call__(self, data):
        self.calls.append(data)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.fixture
def harness(monkeypatch):
    """Wire `_main` for one fake course: argv, transform, no real sleep.

    The pause is replaced through the seeder's own `_sleep` binding, not
    `asyncio.sleep` — that name is the one every other coroutine on the
    loop uses, pytest-asyncio's included."""
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(sys, "argv",
                        ["seed_grammar", "-l", "xx", "--db-url", "postgresql://fake"])
    monkeypatch.setattr(seed_grammar.GrammarSeeder, "transform",
                        lambda self: dict(FAKE_DATA))
    monkeypatch.setattr(seed_grammar, "RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(seed_grammar, "_sleep", fake_sleep)

    def install(load):
        monkeypatch.setattr(seed_grammar.GrammarSeeder, "load", load)
        return sleeps

    return install


async def _run(capsys) -> str:
    await seed_grammar._main()
    return capsys.readouterr().out


class TestRetryOnCutOff:
    async def test_the_10_sep_shape_recovers_on_the_second_try(self, harness, capsys):
        load = _Load(
            asyncpg.ConnectionDoesNotExistError(
                "connection was closed in the middle of operation"),
            3,
        )
        harness(load)
        out = await _run(capsys)
        assert "-> xx: 3 points, 3 drills" in out
        assert out.count("RETRY xx") == 1
        assert "RETRY xx in 0s (1/2): connection was closed in the middle of operation" in out
        assert "OK xx: 3 grammar points loaded" in out
        assert "FAIL" not in out
        assert len(load.calls) == 2
        # The same transformed data goes to every attempt — transform is
        # not re-run, and the second write completes the first.
        assert load.calls[0] is load.calls[1]

    async def test_a_refused_pooler_fails_after_two_retries(self, harness, capsys):
        load = _Load(*[ConnectionResetError(54, "Connection reset by peer")] * 3)
        harness(load)
        out = await _run(capsys)
        assert len(load.calls) == 3
        assert out.count("RETRY xx") == 2
        assert "FAIL xx: [Errno 54] Connection reset by peer" in out
        assert "OK xx" not in out

    async def test_a_timed_out_statement_names_its_error(self, harness, capsys):
        # str(TimeoutError()) is "", which printed "FAIL en: " on 7 Sep.
        load = _Load(TimeoutError(), TimeoutError(), TimeoutError())
        harness(load)
        out = await _run(capsys)
        assert "FAIL xx: TimeoutError" in out
        assert "FAIL xx: \n" not in out
        assert "RETRY xx in 0s (2/2): TimeoutError" in out

    async def test_a_file_error_is_not_retried(self, harness, capsys):
        load = _Load(ValueError("bad drill"))
        harness(load)
        out = await _run(capsys)
        assert len(load.calls) == 1
        assert "RETRY" not in out
        assert "FAIL xx: bad drill" in out

    async def test_a_transform_error_never_reaches_load(self, harness, capsys, monkeypatch):
        def broken(self):
            raise ValueError("paradigm gap: P1")

        monkeypatch.setattr(seed_grammar.GrammarSeeder, "transform", broken)
        load = _Load(3)
        harness(load)
        out = await _run(capsys)
        assert load.calls == []
        assert "FAIL xx: paradigm gap: P1" in out
        assert "-> xx" not in out
        assert "RETRY" not in out

    async def test_the_pauses_follow_retry_delays_in_order(self, harness, capsys, monkeypatch):
        monkeypatch.setattr(seed_grammar, "RETRY_DELAYS", (0.001, 0.002))
        load = _Load(TimeoutError(), TimeoutError(), 3)
        sleeps = harness(load)
        out = await _run(capsys)
        assert sleeps == [0.001, 0.002]
        assert "RETRY xx in 0.001s (1/2)" in out
        assert "RETRY xx in 0.002s (2/2)" in out
        assert "OK xx: 3 grammar points loaded" in out


class TestCutOffShapes:
    """The tuple matches what production actually threw, not what one
    would guess."""

    @pytest.mark.parametrize("err", [
        TimeoutError(),
        asyncpg.ConnectionDoesNotExistError("connection was closed in the middle of operation"),
        asyncpg.ConnectionFailureError("server closed the connection unexpectedly"),
        asyncpg.InterfaceError("connection is closed"),
        ConnectionResetError(54, "Connection reset by peer"),
        ConnectionRefusedError(61, "Connection refused"),
    ])
    def test_a_cut_off_session_is_retried(self, err):
        assert isinstance(err, seed_grammar.CUT_OFF)

    @pytest.mark.parametrize("err", [
        ValueError("paradigm gap"),
        KeyError("drills"),
        asyncpg.UniqueViolationError("duplicate key"),
        asyncpg.UndefinedColumnError("column does not exist"),
    ])
    def test_a_file_or_schema_error_is_not(self, err):
        assert not isinstance(err, seed_grammar.CUT_OFF)

    def test_the_delays_cover_a_one_minute_outage(self):
        # The 10 Sep pooler refused connections for about a minute. The
        # refused shape fails at once, so the pauses ARE the wall clock:
        # together they must outlast that minute or the course in flight
        # when the outage starts is lost anyway — (5, 30) would have saved
        # three of the four courses, not four. Two pauses, and not so long
        # that a real outage is waited out rather than looked at.
        assert len(seed_grammar.RETRY_DELAYS) == 2
        assert 60 <= sum(seed_grammar.RETRY_DELAYS) <= 120


def test_describe_never_returns_blank():
    assert seed_grammar._describe(TimeoutError()) == "TimeoutError"
    assert seed_grammar._describe(ValueError("x")) == "x"
    assert seed_grammar._describe(ConnectionResetError(54, "Connection reset by peer")) \
        == "[Errno 54] Connection reset by peer"
