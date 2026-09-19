"""The nightly judge step: its gates, its budget, its ledger and its rows
(docs/plans/quality-guardrails-telemetry.md §4.3 J1–J2, phase E).

Nothing here reaches a model. `content_judge.judge_for` is patched to a
fake that returns `(verdicts, usage)` the way both real providers do, and
an autouse fixture refuses `anthropic.AsyncAnthropic` outright — conftest's
guard covers `backend.services.generate`'s client, and the judge imports
its own inside `_judge_anthropic`, so this module closes that door too.
The repository reads the gates depend on are patched by name; the writes
(`record_run`, `record_verdicts`) run their real SQL against `mock_conn()`
so the columns and the run_id are what is asserted, not a mock's memory.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, contextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest

from backend.repositories import quality as quality_repo
from backend.repositories import verdicts as verdicts_repo
from backend.services import quality_loop
from backend.services.quality import content_judge as cj
from backend.services.quality import judge_step as js
from backend.tests.fakes import mock_conn

LANG_AR = "22222222-2222-2222-2222-222222222222"
LANG_RU = "11111111-1111-1111-1111-111111111111"

ON = {"judge_enabled": True, "judge_rows_per_cycle": 100,
      "judge_daily_token_cap": 10_000, "judge_model": "fake-checker"}
OFF = dict(quality_repo.SETTINGS_OFF)
TARGET_ON = {"judge_enabled": True, "max_bad_card_pct": 15, "max_judge_flag_pct": 5}
TARGET_OFF = {"judge_enabled": False, "max_bad_card_pct": 15, "max_judge_flag_pct": 5}
CODES = [{"id": LANG_AR, "code": "ar"}, {"id": LANG_RU, "code": "ru"}]


@pytest.fixture(autouse=True)
def _no_live_judge(monkeypatch):
    import anthropic

    def refuse(*_a, **_kw):
        raise AssertionError("a test reached the judge's live Anthropic client; "
                             "patch content_judge.judge_for")

    monkeypatch.setattr(anthropic, "AsyncAnthropic", refuse)


def _missing(name: str = "content_verdicts") -> asyncpg.exceptions.UndefinedTableError:
    return asyncpg.exceptions.UndefinedTableError(f'relation "{name}" does not exist')


def _uuid(i: int) -> str:
    return f"00000000-0000-0000-0000-{i:012d}"


def _items(n: int, entity_type: str = "example_sentence", field: str = "sentence",
           locale: str | None = None) -> list[dict]:
    """Candidate items the way `verdicts.candidates` shapes them: an id,
    the entity to write back to, and the register question's item fields."""
    return [
        {"id": f"{entity_type}:{_uuid(i)}",
         verdicts_repo.ENTITY_KEY: {"type": entity_type, "id": _uuid(i),
                                    "field": field, "locale": locale},
         "field": "sentence", "text": f"sentence {i}", "translation": f"gloss {i}",
         "headword": "w"}
        for i in range(n)
    ]


def _usage(input_tokens: int = 1000, output_tokens: int = 100, calls: int = 1) -> dict:
    return {"input_tokens": input_tokens, "output_tokens": output_tokens,
            "cache_write_tokens": 0, "cache_read_tokens": 0, "calls": calls}


def _fake_judge(verdict="msa", confidence: float = 0.9, per_item=None, fail_on: int | None = None):
    """A judge callable: `(verdicts, usage)` per batch, register-shaped.
    `per_item(i) -> (verdict, confidence)` overrides the flat answer;
    `fail_on` raises on that batch number (0-based) the way a timeout would."""
    calls: list[list[dict]] = []

    async def judge(payload: list[dict]) -> tuple[list[dict], dict]:
        if fail_on is not None and len(calls) == fail_on:
            calls.append(payload)
            raise TimeoutError("judge timed out")
        calls.append(payload)
        out = []
        for p in payload:
            v, c = per_item(p["i"]) if per_item else (verdict, confidence)
            out.append({"i": p["i"], "verdict": v, "variety": None, "evidence": ["ev"],
                        "kind": "lexeme" if v == "dialect" else None,
                        "msa": "rewrite" if v == "dialect" else None,
                        "meaning_kept": True, "confidence": c, "note": f"note {p['i']}"})
        return out, _usage()

    judge.calls = calls
    return judge


def _conn(*, codes=CODES, run_ids=("run-1", "run-2", "run-3", "run-4")):
    """A connection for the writes: fetch answers the languages query,
    fetchrow the quality_runs INSERTs (an id each), fetchval the
    content_verdicts INSERTs."""
    conn = mock_conn()
    conn.fetch.return_value = codes
    ids = iter(run_ids)

    async def fetchrow(sql, *args):
        assert "INSERT INTO quality_runs" in sql
        return {"id": next(ids)}

    conn.fetchrow.side_effect = fetchrow
    conn.fetchval.return_value = "verdict-row"
    return conn


@contextmanager
def _gates(*, settings=ON, spent: int = 0, targets=None, calibrated=None,
           candidates=None, judge=None):
    """The gate reads, patched by name; the judge, faked."""
    if targets is None:
        targets = {LANG_AR: TARGET_ON, LANG_RU: TARGET_OFF}
    if calibrated is None:
        calibrated = {("register", "ar")}
    if candidates is None:
        candidates = AsyncMock(side_effect=lambda conn, q, lang, code, limit: _items(limit))
    judge = judge or _fake_judge()
    with patch.object(quality_repo, "get_quality_settings",
                      new=AsyncMock(return_value=dict(settings))) as get_settings, \
         patch.object(quality_repo, "judge_tokens_spent_today",
                      new=AsyncMock(return_value=spent)) as spent_today, \
         patch.object(quality_repo, "get_language_targets",
                      new=AsyncMock(return_value=targets)) as get_targets, \
         patch.object(cj, "calibrated_pairs", return_value=set(calibrated)), \
         patch.object(verdicts_repo, "candidates", new=candidates), \
         patch.object(cj, "judge_for", return_value=judge) as judge_for, \
         patch.object(cj, "judge_name", return_value="fake-checker"):
        yield SimpleNamespace(settings=get_settings, spent=spent_today, targets=get_targets,
                              candidates=candidates, judge_for=judge_for, judge=judge)


def _runs(conn) -> list[dict]:
    rows = []
    for call in conn.fetchrow.await_args_list:
        kind, lang, locale, metric, value, population, sha, meta = call.args[1:]
        rows.append({"kind": kind, "language_id": lang, "locale": locale, "metric": metric,
                     "value": value, "population": population, "sha": sha,
                     "meta": json.loads(meta)})
    return rows


def _verdict_rows(conn) -> list[dict]:
    names = ("run_id", "language_id", "locale", "entity_type", "entity_id", "field",
             "question", "verdict", "category", "evidence", "confidence", "expected",
             "note", "judge")
    rows = []
    for call in conn.fetchval.await_args_list:
        if "INSERT INTO content_verdicts" not in call.args[0]:
            continue
        rows.append(dict(zip(names, call.args[1:], strict=True)))
    return rows


# ---------------------------------------------------------------------------
# The gates, in order
# ---------------------------------------------------------------------------


class TestGates:
    async def test_switch_off_reads_nothing_else_and_calls_no_judge(self):
        conn = _conn()
        with _gates(settings=OFF) as g:
            stats = await js.judge_step(conn, "abc123")
        assert stats["enabled"] is False
        assert stats["judged"] == 0 and stats["tokens"] == 0
        g.spent.assert_not_awaited()
        g.targets.assert_not_awaited()
        g.candidates.assert_not_awaited()
        g.judge_for.assert_not_called()
        conn.fetch.assert_not_awaited()
        conn.fetchrow.assert_not_awaited()

    async def test_cap_already_reached_stops_before_the_course_list(self):
        conn = _conn()
        with _gates(spent=10_000) as g:
            stats = await js.judge_step(conn, "abc123")
        assert stats["enabled"] is True
        assert stats["cap_reached"] is True
        g.spent.assert_awaited_once()
        g.targets.assert_not_awaited()
        g.judge_for.assert_not_called()
        assert _runs(conn) == []

    async def test_a_course_not_switched_on_is_not_judged(self):
        conn = _conn()
        with _gates(targets={LANG_AR: TARGET_OFF, LANG_RU: TARGET_OFF}) as g:
            stats = await js.judge_step(conn, "abc123")
        assert stats["courses"] == 0
        assert stats["skipped"] == []
        g.judge_for.assert_not_called()

    async def test_enabled_but_uncalibrated_is_skipped_by_name(self):
        conn = _conn()
        with _gates(calibrated=set()) as g:
            stats = await js.judge_step(conn, "abc123")
        assert stats["courses"] == 1
        assert sorted(stats["skipped"]) == sorted(
            f"ar.{name}: not calibrated" for name in cj.QUESTIONS)
        g.judge_for.assert_not_called()
        g.candidates.assert_not_awaited()
        assert stats["judged"] == 0

    async def test_only_the_calibrated_pair_runs_and_the_rest_are_named(self):
        conn = _conn()
        with _gates() as g:
            stats = await js.judge_step(conn, "abc123")
        g.judge_for.assert_called_once_with(cj.REGISTER, None, "fake-checker", "ar")
        assert sorted(stats["skipped"]) == sorted(
            f"ar.{name}: not calibrated" for name in cj.QUESTIONS if name != "register")
        assert stats["judged"] == 100
        assert stats["failures"] == []

    async def test_null_model_lets_content_judge_resolve_the_checker_tier(self):
        conn = _conn()
        with _gates(settings={**ON, "judge_model": None}) as g:
            await js.judge_step(conn, "abc123")
        g.judge_for.assert_called_once_with(cj.REGISTER, None, None, "ar")


# ---------------------------------------------------------------------------
# The budget and the cap
# ---------------------------------------------------------------------------


class TestBudget:
    async def test_rows_per_cycle_split_evenly_across_pairs_floor(self):
        conn = _conn()
        with _gates(settings={**ON, "judge_rows_per_cycle": 101},
                    calibrated={("register", "ar"), ("scripture", "ar")}) as g:
            stats = await js.judge_step(conn, "abc123")
        limits = [c.args[4] for c in g.candidates.await_args_list]
        assert limits == [50, 50]
        questions = [c.args[1].name for c in g.candidates.await_args_list]
        assert sorted(questions) == ["register", "scripture"]
        assert stats["judged"] == 100

    async def test_a_pair_with_no_rows_in_the_split_is_skipped_and_said(self):
        conn = _conn()
        with _gates(settings={**ON, "judge_rows_per_cycle": 1},
                    calibrated={("register", "ar"), ("scripture", "ar")}) as g:
            stats = await js.judge_step(conn, "abc123")
        assert sorted(s for s in stats["skipped"] if "0 rows" in s) == [
            "ar.register: 0 rows once 1 is split 2 ways",
            "ar.scripture: 0 rows once 1 is split 2 ways",
        ]
        g.judge_for.assert_not_called()

    async def test_no_candidates_is_skipped_not_judged(self):
        conn = _conn()
        with _gates(candidates=AsyncMock(return_value=[])) as g:
            stats = await js.judge_step(conn, "abc123")
        assert "ar.register: no rows to judge" in stats["skipped"]
        assert g.judge.calls == []
        assert _runs(conn) == []

    async def test_cap_is_rechecked_before_every_batch_and_the_ledger_still_written(self):
        # 60 rows = 3 batches of BATCH_SIZE at 1,100 tokens each; 8,000
        # already spent today against a 10,000 cap. Batch 1 runs (8,000),
        # batch 2 runs (9,100), batch 3 is refused (10,200 >= cap).
        conn = _conn()
        with _gates(settings={**ON, "judge_rows_per_cycle": 60}, spent=8_000) as g:
            stats = await js.judge_step(conn, "abc123")
        assert len(g.judge.calls) == 2
        assert stats["cap_reached"] is True
        assert stats["judged"] == 40
        assert stats["tokens"] == 2_200 and stats["calls"] == 2
        runs = _runs(conn)
        ledger = [r for r in runs if r["metric"] == "tokens"]
        assert len(ledger) == 1
        assert ledger[0]["kind"] == "judge"
        assert ledger[0]["value"] == 2_200
        assert ledger[0]["population"] == 2
        assert ledger[0]["meta"]["judged"] == 40
        assert len(_verdict_rows(conn)) == 40

    async def test_cap_reached_in_one_pair_skips_the_pairs_after_it(self):
        conn = _conn()
        with _gates(settings={**ON, "judge_rows_per_cycle": 40}, spent=9_500,
                    calibrated={("register", "ar"), ("scripture", "ar")}) as g:
            stats = await js.judge_step(conn, "abc123")
        # Pair 1: one batch runs (9,500 < cap), the second is refused.
        # Pair 2 never starts and says why.
        assert len(g.judge.calls) == 1
        assert stats["cap_reached"] is True
        assert "ar.scripture: daily token cap reached" in stats["skipped"]

    async def test_each_batch_is_one_run_items_call_at_batch_size(self):
        conn = _conn()
        calls = []
        real = cj.run_items

        async def spy(question, items, judge, **kw):
            calls.append((len(items), kw))
            return await real(question, items, judge, **kw)

        with _gates(settings={**ON, "judge_rows_per_cycle": 45}), \
             patch.object(cj, "run_items", new=spy):
            stats = await js.judge_step(conn, "abc123")
        assert [n for n, _ in calls] == [20, 20, 5]
        assert all(kw == {"batch_size": cj.BATCH_SIZE, "concurrency": js.CONCURRENCY}
                   for _, kw in calls)
        assert stats["judged"] == 45

    async def test_the_model_never_sees_the_entity_it_came_from(self):
        conn = _conn()
        with _gates(settings={**ON, "judge_rows_per_cycle": 3}) as g:
            await js.judge_step(conn, "abc123")
        for payload in g.judge.calls:
            for sent in payload:
                assert verdicts_repo.ENTITY_KEY not in sent
                assert "id" not in sent
                assert set(sent) == {"i", "field", "text", "translation", "headword"}


# ---------------------------------------------------------------------------
# What is written
# ---------------------------------------------------------------------------


class TestRows:
    async def test_tokens_row_flagged_row_and_verdicts_share_the_run_id(self):
        conn = _conn(run_ids=("tokens-row", "flagged-row"))

        def answers(i):
            return ("dialect", 0.95) if i == 0 else ("msa", 0.8)

        with _gates(settings={**ON, "judge_rows_per_cycle": 3},
                    judge=_fake_judge(per_item=answers)):
            stats = await js.judge_step(conn, "abc123")
        runs = _runs(conn)
        assert [r["metric"] for r in runs] == ["tokens", "flagged.register"]
        tokens, flagged = runs
        assert tokens["kind"] == flagged["kind"] == "judge"
        assert tokens["language_id"] == flagged["language_id"] == LANG_AR
        assert tokens["sha"] == flagged["sha"] == "abc123"
        assert tokens["value"] == 1_100 and tokens["population"] == 1
        assert tokens["meta"] == {
            "question": "register", "code": "ar", "model": "fake-checker",
            "usage": _usage(), "judged": 3, "flagged": 1,
        }
        assert flagged["value"] == 1 and flagged["population"] == 3
        assert flagged["meta"] == {"question": "register", "code": "ar", "model": "fake-checker"}

        rows = _verdict_rows(conn)
        assert len(rows) == 3
        assert all(r["run_id"] == "tokens-row" for r in rows)
        first = rows[0]
        assert first["language_id"] == LANG_AR
        assert first["locale"] is None
        assert first["entity_type"] == "example_sentence"
        assert first["entity_id"] == _uuid(0)
        assert first["field"] == "sentence"
        assert first["question"] == "register"
        assert first["verdict"] == "dialect"
        # register names its category `kind` and its rewrite `msa`; the
        # table names them category and expected.
        assert first["category"] == "lexeme"
        assert first["expected"] == "rewrite"
        assert first["evidence"] == ["ev"]
        assert first["confidence"] == Decimal("0.95")  # the short decimal, not Decimal(0.95)
        assert first["note"] == "note 0"
        assert first["judge"] == "fake-checker"
        assert rows[1]["verdict"] == "msa" and rows[1]["category"] is None
        assert stats["judged"] == 3 and stats["flagged"] == 1

    async def test_flagged_counts_only_the_positive_class_at_0_7(self):
        conn = _conn()
        table = {0: ("dialect", 0.9), 1: ("dialect", 0.69), 2: ("dialect", 0.7),
                 3: ("msa", 0.99), 4: ("classical", 0.99), 5: ("unsure", 0.9)}
        with _gates(settings={**ON, "judge_rows_per_cycle": 6},
                    judge=_fake_judge(per_item=lambda i: table[i])):
            stats = await js.judge_step(conn, "abc123")
        assert stats["flagged"] == 2       # 0.9 and 0.7; not 0.69, not msa/classical/unsure
        assert stats["judged"] == 6
        flagged = [r for r in _runs(conn) if r["metric"] == "flagged.register"]
        assert flagged[0]["value"] == 2 and flagged[0]["population"] == 6
        # The ledger and a SQL reader at the threshold name the same rows:
        # the 0.7 verdict is stored as Decimal("0.7"), not the float's
        # expansion, and is_flagged compares the stored value.
        stored = {r["entity_id"]: r for r in _verdict_rows(conn)}
        assert stored[_uuid(2)]["confidence"] == Decimal("0.7")
        by_sql = [r for r in stored.values()
                  if r["verdict"] == "dialect" and r["confidence"] >= Decimal("0.7")]
        assert len(by_sql) == flagged[0]["value"]

    async def test_absent_tables_are_counted_as_dropped_not_raised(self):
        conn = _conn()
        conn.fetchrow.side_effect = _missing("quality_runs")
        with _gates(settings={**ON, "judge_rows_per_cycle": 5}):
            stats = await js.judge_step(conn, "abc123")
        assert stats["failures"] == []
        assert stats["judged"] == 5
        # the tokens row, the flagged row and every verdict
        assert stats["dropped"] == 2 + 5
        assert _verdict_rows(conn) == []

    async def test_absent_verdicts_table_alone_drops_the_verdicts(self):
        conn = _conn()
        conn.fetchval.side_effect = _missing("content_verdicts")
        with _gates(settings={**ON, "judge_rows_per_cycle": 5}):
            stats = await js.judge_step(conn, "abc123")
        assert stats["failures"] == []
        assert stats["dropped"] == 5
        assert [r["metric"] for r in _runs(conn)] == ["tokens", "flagged.register"]

    async def test_a_broken_pair_costs_one_pair(self):
        conn = _conn()

        async def candidates(conn, question, lang, code, limit):
            if question.name == "scripture":
                raise RuntimeError("scope query exploded")
            return _items(limit)

        with _gates(settings={**ON, "judge_rows_per_cycle": 40},
                    calibrated={("register", "ar"), ("scripture", "ar")},
                    candidates=AsyncMock(side_effect=candidates)):
            stats = await js.judge_step(conn, "abc123")
        assert stats["failures"] == ["ar.scripture: RuntimeError: scope query exploded"]
        assert stats["judged"] == 20
        assert [r["metric"] for r in _runs(conn)] == ["tokens", "flagged.register"]

    async def test_a_batch_with_no_reply_is_a_failure_not_twenty_unsure_verdicts(self):
        # run_items turns a crashed batch into `unsure` rows; stored, those
        # would mark 20 rows judged on the strength of a timeout (quality
        # rule 14 in the ledger). The step keeps them out and says so.
        conn = _conn()
        with _gates(settings={**ON, "judge_rows_per_cycle": 40},
                    judge=_fake_judge(fail_on=1)):
            stats = await js.judge_step(conn, "abc123")
        assert stats["failures"] == ["ar.register: a batch of 20 got no reply"]
        assert stats["judged"] == 20
        assert stats["calls"] == 1 and stats["tokens"] == 1_100
        assert len(_verdict_rows(conn)) == 20
        assert all(r["verdict"] == "msa" for r in _verdict_rows(conn))

    async def test_every_batch_failing_writes_no_ledger_row(self):
        conn = _conn()

        async def dead(payload):
            raise ConnectionError("no route")

        with _gates(settings={**ON, "judge_rows_per_cycle": 20}, judge=dead):
            stats = await js.judge_step(conn, "abc123")
        assert stats["failures"] == ["ar.register: a batch of 20 got no reply"]
        assert stats["judged"] == 0 and stats["tokens"] == 0
        assert _runs(conn) == []


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------


def _record(**cols):
    """asyncpg.Record stand-in: a dict is subscriptable by name."""
    return cols


class TestCandidates:
    async def test_never_judged_first_then_top_band_then_oldest(self):
        conn = mock_conn()
        conn.fetchval.return_value = True  # both retired_at columns present
        conn.fetch.return_value = [
            _record(entity_type="example_sentence", entity_id=_uuid(1), field="sentence",
                    locale=None, frequency_rank=5, item_field="sentence",
                    text="s", translation="t", headword="w"),
            _record(entity_type="drill", entity_id=_uuid(2), field="sentence", locale=None,
                    frequency_rank=None, item_field="drill", text="d", translation=None,
                    headword=None),
        ]
        items = await verdicts_repo.candidates(conn, cj.REGISTER, LANG_AR, "ar", 10)
        sql, *args = conn.fetch.await_args.args
        assert args == [LANG_AR, "register", 10]
        # The priority order, as three ORDER BY keys in this sequence.
        order = sql[sql.index("ORDER BY"):]
        never = order.index("(judged.at IS NULL) DESC")
        band = order.index("s.frequency_rank NULLS LAST")
        oldest = order.index("judged.at,")
        assert never < band < oldest
        # "never judged" is a content_verdicts lookup keyed by the whole
        # entity, question included, with the locale compared NULL-safely.
        lookup = sql[sql.index("LATERAL"):sql.index("ORDER BY")]
        assert "FROM content_verdicts" in lookup
        for key in ("cv.entity_type = s.entity_type", "cv.entity_id   = s.entity_id",
                    "cv.field       = s.field", "cv.question    = $2",
                    "cv.locale IS NOT DISTINCT FROM s.locale"):
            assert key in lookup
        assert "LIMIT $3" in sql
        # Register reads example sentences AND drills, the drill with its
        # marker filled — and sends no rank (REGISTER_RULES treats a ranked
        # item as a frequency-list entry).
        assert "FROM example_sentences es" in sql and "FROM drill_sentences d" in sql
        assert "replace(d.sentence, '{{answer}}', COALESCE(d.answer, ''))" in sql
        assert items == [
            {"id": f"example_sentence:{_uuid(1)}",
             "entity": {"type": "example_sentence", "id": _uuid(1), "field": "sentence",
                        "locale": None},
             "field": "sentence", "text": "s", "translation": "t", "headword": "w"},
            {"id": f"drill:{_uuid(2)}",
             "entity": {"type": "drill", "id": _uuid(2), "field": "sentence", "locale": None},
             "field": "drill", "text": "d", "translation": "", "headword": ""},
        ]
        assert not any("rank" in item for item in items)
        # Retired words and retired points' drills are out of scope, each
        # behind its own column probe (migrations 20261016 and 20261017).
        assert "AND v.retired_at IS NULL" in sql
        assert "AND gp.retired_at IS NULL" in sql
        probes = [c.args[1:] for c in conn.fetchval.await_args_list
                  if "information_schema.columns" in c.args[0]]
        assert probes == [("vocabulary", "retired_at"), ("grammar_points", "retired_at")]

    async def test_retired_rows_leave_the_scope_only_where_the_column_exists(self):
        """Production on 18 Sep 2026: vocabulary.retired_at applied
        (20261016), grammar_points.retired_at still owed (20261017). A
        predicate on the absent column would fail the whole scope under its
        savepoint — the judge would read NOTHING for the course — so each
        is probed, not assumed, the way cards._retired_clause does it."""
        conn = mock_conn()
        conn.fetch.return_value = []
        conn.fetchval.side_effect = lambda sql, *args: args == ("vocabulary", "retired_at")
        await verdicts_repo.candidates(conn, cj.REGISTER, LANG_AR, "ar", 10)
        sql = conn.fetch.await_args.args[0]
        assert "AND v.retired_at IS NULL" in sql
        assert "gp.retired_at" not in sql
        # Neither column — the pre-20261016 shape: nothing filtered, the
        # SQL otherwise intact, and every question's scope filters on the
        # vocabulary column while only register's touches grammar_points.
        conn.fetchval.side_effect = None
        conn.fetchval.return_value = False
        conn.fetchval.reset_mock()
        for question in cj.QUESTIONS.values():
            await verdicts_repo.candidates(conn, question, LANG_AR, "ar", 10)
            sql = conn.fetch.await_args.args[0]
            assert "retired_at" not in sql, question.name
            assert "$1::uuid" in sql and "LIMIT $3" in sql, question.name
        probes = [c.args[1:] for c in conn.fetchval.await_args_list]
        assert probes.count(("vocabulary", "retired_at")) == len(cj.QUESTIONS)
        assert probes.count(("grammar_points", "retired_at")) == 1

    async def test_each_question_reads_its_own_scope_and_writes_back_to_it(self):
        conn = mock_conn()
        conn.fetch.return_value = []
        expect = {
            "sense": ("FROM vocabulary v", "t.locale = 'en'", "'definition' AS field"),
            "gloss": ("FROM translations t", "t.locale <> 'en'", "en.locale = 'en'",
                      "'translation' AS entity_type"),
            "scripture": ("FROM example_sentences es", "'sentence' AS field"),
            "card_shape": ("LEFT JOIN translations t", "'card' AS field",
                           "'vocabulary' AS entity_type"),
        }
        for name, fragments in expect.items():
            await verdicts_repo.candidates(conn, cj.QUESTIONS[name], LANG_AR, "ar", 5)
            sql = conn.fetch.await_args.args[0]
            for fragment in fragments:
                assert fragment in sql, (name, fragment)
            assert conn.fetch.await_args.args[2] == name

    async def test_items_carry_the_question_item_fields(self):
        conn = mock_conn()
        conn.fetch.return_value = [_record(
            entity_type="translation", entity_id=_uuid(3), field="definition", locale="es",
            frequency_rank=12, word="board", pos="noun", definition="a committee",
            gloss="tabla")]
        [item] = await verdicts_repo.candidates(conn, cj.GLOSS, LANG_AR, "en", 5)
        assert item["entity"] == {"type": "translation", "id": _uuid(3),
                                  "field": "definition", "locale": "es"}
        assert {k: item[k] for k in cj.GLOSS.item_fields} == {
            "word": "board", "pos": "noun", "definition": "a committee", "gloss": "tabla",
            "locale": "es"}

        conn.fetch.return_value = [_record(
            entity_type="vocabulary", entity_id=_uuid(4), field="definition", locale=None,
            frequency_rank=201, word="need", pos="verb", definition="require")]
        [item] = await verdicts_repo.candidates(conn, cj.SENSE, LANG_AR, "en", 5)
        assert {k: item[k] for k in cj.SENSE.item_fields} == {
            "word": "need", "rank": 201, "pos": "verb", "definition": "require"}

        conn.fetch.return_value = [_record(
            entity_type="example_sentence", entity_id=_uuid(5), field="sentence",
            locale=None, frequency_rank=1, sentence="x", translation="y")]
        [item] = await verdicts_repo.candidates(conn, cj.SCRIPTURE, LANG_AR, "ar", 5)
        assert {k: item[k] for k in cj.SCRIPTURE.item_fields} == {
            "sentence": "x", "translation": "y", "language": "ar"}

        conn.fetch.return_value = [_record(
            entity_type="vocabulary", entity_id=_uuid(6), field="card", locale=None,
            frequency_rank=1, word="й", pos="letter", definition=None)]
        [item] = await verdicts_repo.candidates(conn, cj.CARD_SHAPE, LANG_RU, "ru", 5)
        assert {k: item[k] for k in cj.CARD_SHAPE.item_fields} == {
            "word": "й", "pos": "letter", "definition": "", "language": "ru"}

    async def test_degrades_to_empty_without_the_table(self):
        conn = mock_conn()
        conn.fetch.side_effect = _missing()
        assert await verdicts_repo.candidates(conn, cj.REGISTER, LANG_AR, "ar", 10) == []
        conn.fetch.side_effect = asyncpg.exceptions.UndefinedColumnError("judged_at")
        assert await verdicts_repo.candidates(conn, cj.REGISTER, LANG_AR, "ar", 10) == []

    async def test_zero_limit_asks_nothing(self):
        conn = mock_conn()
        assert await verdicts_repo.candidates(conn, cj.REGISTER, LANG_AR, "ar", 0) == []
        conn.fetch.assert_not_awaited()


class TestCounts:
    async def test_scope_size_counts_the_question_scope(self):
        conn = mock_conn()
        conn.fetchval.side_effect = (
            lambda sql, *args: True if "information_schema.columns" in sql else 1234)
        assert await verdicts_repo.scope_size(conn, cj.GLOSS, LANG_AR) == 1234
        sql, *args = conn.fetchval.await_args.args
        assert sql.startswith("SELECT count(*) FROM (")
        assert "t.locale <> 'en'" in sql
        assert "AND v.retired_at IS NULL" in sql  # retired words are not in the denominator
        assert args == [LANG_AR]

    async def test_judged_count_is_distinct_entities_for_the_question(self):
        conn = mock_conn()
        conn.fetchval.return_value = 7
        assert await verdicts_repo.judged_count(conn, cj.SENSE, LANG_AR) == 7
        sql, *args = conn.fetchval.await_args.args
        assert "count(DISTINCT (entity_type, entity_id, field, COALESCE(locale, '')))" in sql
        assert "FROM content_verdicts" in sql
        assert args == [LANG_AR, "sense"]

    async def test_both_degrade_to_zero(self):
        conn = mock_conn()
        conn.fetchval.side_effect = _missing()
        assert await verdicts_repo.judged_count(conn, cj.SENSE, LANG_AR) == 0
        assert await verdicts_repo.scope_size(conn, cj.SENSE, LANG_AR) == 0


class TestRecordVerdicts:
    async def test_clamps_confidence_and_lists_evidence(self):
        conn = mock_conn()
        conn.fetchval.return_value = "id"
        items = _items(5)
        verdicts = [
            {"id": items[0]["id"], "verdict": "dialect", "confidence": 1.7, "evidence": "one"},
            {"id": items[1]["id"], "verdict": "msa", "confidence": -0.2, "evidence": None},
            {"id": items[2]["id"], "verdict": "msa", "confidence": "abc", "evidence": [1, None]},
            {"id": items[3]["id"], "verdict": None, "confidence": None},
            {"id": items[4]["id"], "verdict": "dialect", "confidence": 0.7, "evidence": []},
        ]
        n = await verdicts_repo.record_verdicts(conn, "run-9", LANG_AR, cj.REGISTER,
                                                items, verdicts, "fake")
        assert n == 5
        rows = _verdict_rows(conn)
        assert [r["confidence"] for r in rows] == [
            Decimal("1.0"), Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), Decimal("0.7")]
        assert all(isinstance(r["confidence"], Decimal) for r in rows)
        assert [r["evidence"] for r in rows] == [["one"], [], ["1"], [], []]
        assert rows[3]["verdict"] == "unsure"
        assert all(r["run_id"] == "run-9" for r in rows)
        assert "$11::numeric" in conn.fetchval.await_args.args[0]
        assert "ON CONFLICT DO NOTHING" in conn.fetchval.await_args.args[0]
        assert "RETURNING id" in conn.fetchval.await_args.args[0]

    def test_confidence_is_bound_as_the_short_decimal_the_threshold_reads(self):
        # asyncpg binds a float to numeric as Decimal(float), the binary
        # expansion: 0.7 reached a real Postgres 16 as
        # 0.6999999999999999555910790149937383830547332763671875, and
        # `WHERE confidence >= 0.7` found none of the rows the
        # flagged.register ledger row had counted at exactly the threshold.
        assert Decimal(0.7) < Decimal("0.7")  # the defect, stated
        stored = verdicts_repo.stored_confidence(0.7)
        assert stored == Decimal("0.7") and str(stored) == "0.7"
        assert stored >= js.FLAG_CONFIDENCE
        # Four places — what a question's rules ask a model to report, no
        # more — so the stored value and the flagged count move together.
        assert verdicts_repo.stored_confidence(0.69996) == Decimal("0.7")
        assert verdicts_repo.stored_confidence(0.69994) == Decimal("0.6999")
        assert verdicts_repo.stored_confidence("0.85") == Decimal("0.85")
        assert verdicts_repo.stored_confidence(float("nan")) == Decimal("0.0")
        assert verdicts_repo.stored_confidence(float("inf")) == Decimal("1.0")
        assert verdicts_repo.stored_confidence(None) == Decimal("0.0")

    async def test_a_conflict_is_not_counted_and_an_unmatched_item_is_skipped(self):
        conn = mock_conn()
        conn.fetchval.side_effect = ["id", None]
        items = _items(3)
        verdicts = [{"id": items[0]["id"], "verdict": "msa", "confidence": 0.5},
                    {"id": items[1]["id"], "verdict": "msa", "confidence": 0.5}]
        n = await verdicts_repo.record_verdicts(conn, "run-9", LANG_AR, cj.REGISTER,
                                                items, verdicts, "fake")
        assert n == 1
        assert conn.fetchval.await_count == 2

    async def test_absent_table_returns_none(self):
        conn = mock_conn()
        conn.fetchval.side_effect = _missing()
        items = _items(1)
        verdicts = [{"id": items[0]["id"], "verdict": "msa", "confidence": 0.5}]
        assert await verdicts_repo.record_verdicts(conn, "run-9", LANG_AR, cj.REGISTER,
                                                   items, verdicts, "fake") is None


# ---------------------------------------------------------------------------
# calibrated.json
# ---------------------------------------------------------------------------


class TestCalibratedPairs:
    def test_the_committed_file_names_register_for_arabic_only(self):
        assert cj.calibrated_pairs() == {("register", "ar")}

    def test_absent_or_malformed_reads_as_empty_with_a_warning(self, tmp_path, caplog):
        with caplog.at_level("WARNING", logger="content_judge"):
            assert cj.calibrated_pairs(tmp_path / "nope.json") == set()
            bad = tmp_path / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            assert cj.calibrated_pairs(bad) == set()
            listy = tmp_path / "list.json"
            listy.write_text("[]", encoding="utf-8")
            assert cj.calibrated_pairs(listy) == set()
        assert len([r for r in caplog.records if "calibrated" in r.getMessage()]) == 3

    def test_a_question_whose_value_is_not_a_map_is_ignored_not_fatal(self, tmp_path):
        path = tmp_path / "c.json"
        path.write_text(json.dumps({"register": {"ar": {}}, "sense": "yes"}), encoding="utf-8")
        assert cj.calibrated_pairs(path) == {("register", "ar")}


# ---------------------------------------------------------------------------
# Coverage rows, and the loop wiring
# ---------------------------------------------------------------------------


class TestCoverage:
    async def test_one_row_per_question_whether_or_not_the_judge_is_on(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {"id": "row"}

        async def counts(sql, *args):
            if "information_schema.columns" in sql:  # the retired_at probes
                return True
            return 3 if "FROM content_verdicts" in sql else 40

        conn.fetchval.side_effect = counts
        stats = quality_loop._new_stats()
        await quality_loop._judge_coverage_step(
            conn, stats, "ar", LANG_AR, "abc123", {("register", "ar")})
        rows = _runs(conn)
        assert [r["metric"] for r in rows] == [f"judge.{q}" for q in cj.QUESTIONS]
        assert all(r["kind"] == "coverage" and r["language_id"] == LANG_AR for r in rows)
        assert all(r["value"] == 3 and r["population"] == 40 for r in rows)
        by_metric = {r["metric"]: r["meta"] for r in rows}
        assert by_metric["judge.register"] == {"calibrated": True}
        assert by_metric["judge.gloss"] == {"calibrated": False}
        assert stats["rows"] == 5

    async def test_without_the_verdicts_table_coverage_reads_zero_of_scope(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {"id": "row"}

        async def counts(sql, *args):
            if "information_schema.columns" in sql:  # the retired_at probes
                return True
            if "FROM content_verdicts" in sql:
                raise _missing()
            return 40

        conn.fetchval.side_effect = counts
        stats = quality_loop._new_stats()
        await quality_loop._judge_coverage_step(conn, stats, "ru", LANG_RU, None, set())
        assert all(r["value"] == 0 and r["population"] == 40 for r in _runs(conn))


async def test_loop_survives_a_judge_failure_and_still_stamps_the_heartbeat(monkeypatch):
    monkeypatch.setattr(quality_loop, "FIRST_SWEEP_DELAY_SECONDS", 0)
    monkeypatch.setattr(quality_loop, "SWEEP_SECONDS", 3600)
    for key, value in (("started", False), ("cycles", 0), ("last_cycle_at", None),
                       ("last_error", None), ("last_stats", None)):
        monkeypatch.setitem(quality_loop.QUALITY_HEARTBEAT, key, value)

    @asynccontextmanager
    async def pool():
        yield mock_conn()

    with patch("backend.repositories.pool.privileged_connection", pool), \
         patch.object(quality_loop, "run_quality_cycle",
                      new=AsyncMock(return_value=quality_loop._new_stats())), \
         patch.object(quality_loop, "judge_step",
                      new=AsyncMock(side_effect=RuntimeError("judge exploded"))) as judge:
        task = asyncio.create_task(quality_loop.quality_loop())
        await asyncio.sleep(0.05)
        assert not task.done(), "the loop must survive a failed judge"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    judge.assert_awaited_once()
    hb = quality_loop.quality_heartbeat()
    assert hb["cycles"] == 1
    assert hb["last_error"] is None            # the CYCLE did not fail
    assert hb["last_cycle_at"] is not None
    assert hb["last_stats"]["judge"] is None
    assert hb["last_stats"]["failures"] == ["*.judge: RuntimeError: judge exploded"]


async def test_loop_keeps_the_judge_stats_beside_the_mechanical_ones(monkeypatch):
    monkeypatch.setattr(quality_loop, "FIRST_SWEEP_DELAY_SECONDS", 0)
    monkeypatch.setattr(quality_loop, "SWEEP_SECONDS", 3600)
    monkeypatch.setitem(quality_loop.QUALITY_HEARTBEAT, "last_stats", None)

    @asynccontextmanager
    async def pool():
        yield mock_conn()

    judge_stats = {**js.new_stats(), "enabled": True, "judged": 7, "flagged": 2, "tokens": 900}
    with patch("backend.repositories.pool.privileged_connection", pool), \
         patch.object(quality_loop, "run_quality_cycle",
                      new=AsyncMock(return_value=quality_loop._new_stats())), \
         patch.object(quality_loop, "judge_step", new=AsyncMock(return_value=judge_stats)):
        task = asyncio.create_task(quality_loop.quality_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert quality_loop.quality_heartbeat()["last_stats"]["judge"] == judge_stats


def test_summary_says_judged_flagged_and_tokens_when_present():
    base = quality_loop._new_stats()
    assert "judge" not in quality_loop._summary(base)
    assert quality_loop._summary({**base, "judge": js.new_stats()}).endswith("; judge off")
    on = {**js.new_stats(), "enabled": True, "judged": 40, "flagged": 3, "tokens": 2200,
          "calls": 2, "cap_reached": True}
    line = quality_loop._summary({**base, "judge": on})
    assert line.endswith("; judge: 40 judged, 3 flagged, 2200 tokens over 2 calls, cap reached")
