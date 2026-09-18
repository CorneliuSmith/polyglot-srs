"""The nightly quality cycle, and the judge switch that fails closed
(docs/plans/quality-guardrails-telemetry.md, phase A).

Nothing here touches a data file or a database. The real audit parses
every course's frequency file and sentence bank, the real survey needs
Postgres, and both are the point of the loop rather than of these tests —
so audit, survey, snapshot, inbox and build stamp are all faked, and the
connection is `mock_conn()` (its `transaction()` has to answer the
savepoint every step runs under). What is pinned is the wiring: which
rows a cycle writes, that a broken course costs one step and not the
cycle, that the audit never runs on the event loop, and that the judge
reads OFF whenever its switch is unreadable.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, contextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories import quality as repo
from backend.services import quality_loop
from backend.services.quality import audit_content, content_judge, db_snapshot
from backend.services.seeder import reconcile
from backend.tests.fakes import mock_conn

LANG_RU = "11111111-1111-1111-1111-111111111111"
LANG_AR = "22222222-2222-2222-2222-222222222222"
ADMIN = "550e8400-e29b-41d4-a716-446655440000"


def _missing(name: str = "quality_runs") -> asyncpg.exceptions.UndefinedTableError:
    return asyncpg.exceptions.UndefinedTableError(f'relation "{name}" does not exist')


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------


class TestRecordRun:
    async def test_inserts_every_column_and_returns_the_id(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {"id": "row-1"}
        row_id = await repo.record_run(
            conn, kind="audit", language_id=LANG_RU, metric="leak_hard", value=3,
            population=120, locale=None, build_sha="abc123", meta={"drills": 120},
        )
        assert row_id == "row-1"
        sql, *args = conn.fetchrow.await_args.args
        assert "INSERT INTO quality_runs" in sql
        for column in ("kind", "language_id", "locale", "metric", "value",
                       "population", "build_sha", "meta"):
            assert column in sql
        assert args == ["audit", LANG_RU, None, "leak_hard", 3, 120, "abc123",
                        json.dumps({"drills": 120})]

    async def test_absent_table_returns_none_not_an_error(self):
        conn = mock_conn()
        conn.fetchrow.side_effect = _missing()
        assert await repo.record_run(
            conn, kind="audit", language_id=LANG_RU, metric="leak_hard", value=3,
        ) is None

    async def test_record_runs_is_one_insert_per_row(self):
        conn = mock_conn()
        conn.fetchrow.side_effect = [{"id": "a"}, {"id": "b"}]
        ids = await repo.record_runs(conn, [
            {"kind": "audit", "language_id": LANG_RU, "metric": "leak_hard", "value": 1},
            {"kind": "audit", "language_id": LANG_RU, "metric": "empty", "value": 0},
        ])
        assert ids == ["a", "b"]
        assert conn.fetchrow.await_count == 2


class TestReads:
    async def test_latest_metrics_keys_support_locale_rows_apart(self):
        conn = mock_conn()
        conn.fetch.return_value = [
            {"language_id": LANG_RU, "locale": None, "metric": "leak_hard", "kind": "audit",
             "value": Decimal("3"), "population": 120, "run_at": "t1"},
            {"language_id": LANG_RU, "locale": "es", "metric": "judge.sense", "kind": "judge",
             "value": Decimal("2.5"), "population": 100, "run_at": "t2"},
        ]
        out = await repo.latest_metrics(conn, LANG_RU)
        assert out[LANG_RU]["leak_hard"]["value"] == 3
        assert isinstance(out[LANG_RU]["leak_hard"]["value"], int)
        assert out[LANG_RU]["es:judge.sense"]["value"] == 2.5
        assert "DISTINCT ON" in conn.fetch.await_args.args[0]

    async def test_reads_degrade_to_empty_without_the_table(self):
        conn = mock_conn()
        conn.fetch.side_effect = _missing()
        assert await repo.latest_metrics(conn) == {}
        assert await repo.trend(conn, LANG_RU, "leak_hard") == []

    async def test_trend_matches_a_null_locale(self):
        conn = mock_conn()
        conn.fetch.return_value = []
        await repo.trend(conn, LANG_RU, "leak_hard", days=7)
        sql, *args = conn.fetch.await_args.args
        # `locale = NULL` matches nothing; the course's own rows have NULL.
        assert "IS NOT DISTINCT FROM" in sql
        assert args == [LANG_RU, "leak_hard", None, 7]


class TestQualitySettings:
    OFF = {"judge_enabled": False, "judge_rows_per_cycle": 0,
           "judge_daily_token_cap": 0, "judge_model": None}

    async def test_fails_closed_without_the_table(self):
        conn = mock_conn()
        conn.fetchrow.side_effect = _missing("quality_settings")
        assert await repo.get_quality_settings(conn) == self.OFF

    async def test_fails_closed_without_the_row(self):
        conn = mock_conn()
        conn.fetchrow.return_value = None
        assert await repo.get_quality_settings(conn) == self.OFF

    async def test_fails_closed_on_any_database_error(self):
        # The one read where "I don't know" has to mean "spend nothing".
        conn = mock_conn()
        conn.fetchrow.side_effect = asyncpg.exceptions.InFailedSQLTransactionError("aborted")
        assert await repo.get_quality_settings(conn) == self.OFF

    async def test_reads_the_row(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {
            "judge_enabled": True, "judge_rows_per_cycle": 200,
            "judge_daily_token_cap": 1_500_000, "judge_model": "claude-opus-4-8",
        }
        assert await repo.get_quality_settings(conn) == {
            "judge_enabled": True, "judge_rows_per_cycle": 200,
            "judge_daily_token_cap": 1_500_000, "judge_model": "claude-opus-4-8",
        }

    async def test_update_clamps_to_the_check_ranges_and_ignores_stray_keys(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {
            "judge_enabled": True, "judge_rows_per_cycle": 10_000,
            "judge_daily_token_cap": 0, "judge_model": None,
        }
        out = await repo.update_quality_settings(
            conn, updated_by=ADMIN, judge_enabled=1, judge_rows_per_cycle=99_999,
            judge_daily_token_cap=-5, judge_model="   ", nonsense=1,
        )
        update = [c for c in conn.execute.await_args_list if "UPDATE" in c.args[0]]
        assert len(update) == 1
        sql, *args = update[0].args
        assert "nonsense" not in sql
        assert args == [True, 10_000, 0, None, ADMIN]
        assert out["judge_rows_per_cycle"] == 10_000

    async def test_update_returns_none_without_the_table(self):
        # A write failing silently is worse than a read degrading: the
        # router turns None into a 503 the admin can see.
        conn = mock_conn()
        conn.execute.side_effect = _missing("quality_settings")
        assert await repo.update_quality_settings(conn, updated_by=ADMIN, judge_enabled=True) is None


class TestLanguageTargets:
    async def test_defaults_fill_the_languages_with_no_row(self):
        conn = mock_conn()
        conn.fetch.return_value = [
            {"id": LANG_RU, "judge_enabled": None, "max_bad_card_pct": None,
             "max_judge_flag_pct": None},
            {"id": LANG_AR, "judge_enabled": True, "max_bad_card_pct": Decimal("10"),
             "max_judge_flag_pct": Decimal("2.5")},
        ]
        out = await repo.get_language_targets(conn)
        assert out[LANG_RU] == {"judge_enabled": False, "max_bad_card_pct": 15,
                                "max_judge_flag_pct": 5}
        assert out[LANG_AR] == {"judge_enabled": True, "max_bad_card_pct": 10,
                                "max_judge_flag_pct": 2.5}

    async def test_without_the_table_every_language_reads_as_not_judged(self):
        conn = mock_conn()
        conn.fetch.side_effect = [_missing("language_quality_targets"), [{"id": LANG_RU}]]
        out = await repo.get_language_targets(conn)
        assert out == {LANG_RU: {"judge_enabled": False, "max_bad_card_pct": 15,
                                 "max_judge_flag_pct": 5}}

    async def test_set_target_clamps_and_leaves_absent_fields_alone(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {"judge_enabled": False, "max_bad_card_pct": Decimal("100"),
                                      "max_judge_flag_pct": Decimal("5")}
        out = await repo.set_language_target(conn, LANG_RU, updated_by=ADMIN, max_bad_card_pct=150)
        sql, *args = conn.fetchrow.await_args.args
        assert "ON CONFLICT (language_id) DO UPDATE" in sql
        # NULL for the fields not given: COALESCE keeps the stored value.
        assert args == [LANG_RU, None, 100.0, None, ADMIN]
        assert out == {"judge_enabled": False, "max_bad_card_pct": 100, "max_judge_flag_pct": 5}

    async def test_set_target_returns_none_without_the_table(self):
        conn = mock_conn()
        conn.fetchrow.side_effect = _missing("language_quality_targets")
        assert await repo.set_language_target(conn, LANG_RU, updated_by=ADMIN,
                                              judge_enabled=True) is None


class TestJudgeTokens:
    async def test_sums_the_judge_ledger_rows_since_utc_midnight(self):
        # The ledger is quality_runs, not tutor_usage: that table's user_id
        # is NOT NULL against auth.users and the judge has no user until
        # owner decision #2 (the docstring says so).
        conn = mock_conn()
        conn.fetchval.return_value = Decimal("1234")
        assert await repo.judge_tokens_spent_today(conn) == 1234
        sql = conn.fetchval.await_args.args[0]
        assert "FROM quality_runs" in sql
        assert "kind = 'judge'" in sql and "metric = 'tokens'" in sql
        assert "SUM(value)" in sql
        assert "tutor_usage" not in sql
        # Both AT TIME ZONE casts: drop the zone to truncate, re-tag to compare.
        assert sql.count("AT TIME ZONE 'UTC'") == 2

    async def test_degrades_to_zero(self):
        conn = mock_conn()
        conn.fetchval.side_effect = _missing("quality_runs")
        assert await repo.judge_tokens_spent_today(conn) == 0
        conn.fetchval.side_effect = asyncpg.exceptions.UndefinedColumnError("metric")
        assert await repo.judge_tokens_spent_today(conn) == 0


# ---------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------


def _audit_report(code: str, unclozable: int = 5) -> dict:
    counts = dict.fromkeys(audit_content.ALL_RULES, 0)
    counts["leak_hard"] = 3
    counts["unclozable_rows"] = unclozable
    return {"code": code, "points": 10, "drills": 120,
            "findings": {rule: [] for rule in audit_content.ALL_RULES}, "counts": counts}


async def _survey(conn, code: str) -> dict:
    # reconcile.survey's own signature: the connection first, then the code.
    return _survey_report(code)


def _survey_report(code: str) -> dict:
    return {
        "code": code, "db_rows": 1500, "tsv_rows": 1500,
        "gloss_changes": [1, 2], "pos_changes": [1], "morphology_changes": [],
        "sentence_layers": [], "missing_translation": [1, 2, 3],
        "departed": [{"id": "a", "word": "x", "cards": 2}, {"id": "b", "word": "y", "cards": 0}],
        "owned_elsewhere": [], "absent_from_db": ["q"],
        "retire": [1], "unretire": [], "retire_skipped": None,
        "retire_points": [1, 1], "unretire_points": [], "point_retire_skipped": None,
    }


SNAPSHOT_COUNTS = {"vocabulary": 1500, "with_definition": 1400, "no_definition": 100,
                   "no_pos": 7, "learner_cards": 42}


async def _snapshot(conn, code: str, samples: int) -> dict:
    assert samples == 0, "the cycle must not store sample rows"
    return {"code": code, "present": True, "counts": dict(SNAPSHOT_COUNTS), "sample": []}


async def _inbox(conn, *, include_empty=False, exclude=None) -> list[dict]:
    assert include_empty, "a quiet language still gets a zero row"
    return [{"id": LANG_RU, "code": "ru", "name": "Russian", "is_visible": True, "total": 3,
             "counts": {"pending_drills": 2, "change_requests": 1}}]


# The judge-coverage step's two counts, answered by SQL shape: the numerator
# reads content_verdicts, the denominator counts the question's scope.
JUDGED, SCOPE = 3, 40
JUDGE_COVERAGE = {f"judge.{name}" for name in content_judge.QUESTIONS}


async def _counts(sql, *args):
    if "information_schema.columns" in sql:  # verdicts._scope's retired_at probes
        return True
    return JUDGED if "FROM content_verdicts" in sql else SCOPE


@contextmanager
def _faked(*, audit=None, survey=None, file_rows: int = 1500):
    """Every input to the cycle, faked. `audit` and `survey` are side_effects
    (a callable or an exception) for the two per-course steps."""
    with patch.object(audit_content, "audit_language",
                      side_effect=audit or _audit_report) as audit_mock, \
         patch.object(content_judge, "calibrated_pairs", return_value={("register", "ru")}), \
         patch.object(reconcile, "survey", new=AsyncMock(side_effect=survey or _survey)), \
         patch.object(reconcile, "expected_rows",
                      side_effect=lambda code: {f"w{i}": {} for i in range(file_rows)}), \
         patch.object(db_snapshot, "snapshot_language", new=AsyncMock(side_effect=_snapshot)), \
         patch("backend.services.quality_loop.review_inbox_by_language",
               new=AsyncMock(side_effect=_inbox)), \
         patch("backend.services.quality_loop.build_info", return_value={"sha": "abc123"}):
        yield audit_mock


def _conn(*languages: tuple[str, str]):
    conn = mock_conn()
    conn.fetch.return_value = [{"id": lang_id, "code": code} for code, lang_id in languages]
    conn.fetchrow.return_value = {"id": "row-id"}
    conn.fetchval.side_effect = _counts
    return conn


def _written(conn) -> list[dict]:
    rows = []
    for call in conn.fetchrow.await_args_list:
        if "INSERT INTO quality_runs" not in call.args[0]:
            continue
        kind, lang, locale, metric, value, population, sha, meta = call.args[1:]
        rows.append({"kind": kind, "language_id": lang, "locale": locale, "metric": metric,
                     "value": value, "population": population, "sha": sha,
                     "meta": json.loads(meta)})
    return rows


def _by_metric(rows: list[dict], kind: str, lang: str = LANG_RU) -> dict:
    return {r["metric"]: r for r in rows if r["kind"] == kind and r["language_id"] == lang}


class TestCycle:
    async def test_writes_audit_reconcile_snapshot_queues_and_coverage(self):
        conn = _conn(("ru", LANG_RU))
        with _faked():
            stats = await quality_loop.run_quality_cycle(conn)
        rows = _written(conn)

        audit = _by_metric(rows, "audit")
        assert set(audit) == set(audit_content.ALL_RULES)
        assert audit["leak_hard"]["value"] == 3
        assert audit["leak_hard"]["population"] == 120          # a drill rule
        assert audit["unclozable_rows"]["population"] is None   # not one
        assert audit["leak_hard"]["meta"] == {"drills": 120, "points": 10}

        drift = _by_metric(rows, "reconcile")
        assert {m: r["value"] for m, r in drift.items()} == {
            "gloss": 2, "pos": 1, "no_translation": 3, "gone": 2, "new": 1,
            "retire": 1, "unretire": 0, "gp_retire": 2, "gone_with_cards": 1,
        }
        assert all(r["population"] == 1500 for r in drift.values())

        snap = _by_metric(rows, "snapshot")
        assert {m: r["value"] for m, r in snap.items()} == SNAPSHOT_COUNTS

        queues = _by_metric(rows, "queues")
        assert {m: r["value"] for m, r in queues.items()} == {"pending_drills": 2,
                                                              "change_requests": 1}

        coverage = _by_metric(rows, "coverage")
        # Grew from one row to six per course when unit F added the judge
        # coverage step: one judge.<question> row per question, written
        # whether or not the judge is on, so the panel can show 0 of N.
        assert set(coverage) == {"blankable_top_band"} | JUDGE_COVERAGE
        # 1,500-row file: the band is the file, not CARD_RULE_BAND.
        assert coverage["blankable_top_band"]["value"] == 1500 - 5
        assert coverage["blankable_top_band"]["population"] == 1500
        for metric in JUDGE_COVERAGE:
            assert coverage[metric]["value"] == JUDGED
            assert coverage[metric]["population"] == SCOPE
        # calibrated.json (faked) has register/ru and nothing else.
        assert coverage["judge.register"]["meta"] == {"calibrated": True}
        assert coverage["judge.sense"]["meta"] == {"calibrated": False}

        assert all(r["sha"] == "abc123" for r in rows)
        assert all(r["language_id"] == LANG_RU for r in rows)
        assert stats["languages"] == 1
        assert stats["rows"] == len(rows)
        assert stats["dropped"] == 0
        assert stats["failures"] == []
        # The 26 courses the fake database does not have are skipped, named.
        assert len(stats["skipped"]) == len(db_snapshot.LANGUAGES) - 1

    async def test_coverage_band_is_capped_at_card_rule_band(self):
        conn = _conn(("ru", LANG_RU))
        with _faked(file_rows=30_000):
            await quality_loop.run_quality_cycle(conn)
        cov = _by_metric(_written(conn), "coverage")["blankable_top_band"]
        assert cov["population"] == audit_content.CARD_RULE_BAND
        assert cov["value"] == audit_content.CARD_RULE_BAND - 5

    async def test_the_audit_runs_in_a_worker_thread(self):
        conn = _conn(("ru", LANG_RU))
        threaded = AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))
        with _faked() as audit_mock, \
             patch("backend.services.quality_loop.asyncio.to_thread", new=threaded):
            await quality_loop.run_quality_cycle(conn)
        assert any(
            c.args[0] is audit_mock and c.args[1:] == ("ru",)
            for c in threaded.await_args_list
        )
        audit_mock.assert_called_once_with("ru")

    async def test_a_broken_course_costs_one_step_not_the_cycle(self):
        conn = _conn(("ru", LANG_RU), ("ar", LANG_AR))

        def audit(code):
            if code == "ar":
                raise FileNotFoundError("data/grammar/ar.json")
            return _audit_report(code)

        async def survey(conn, code):
            if code == "ar":
                return {"code": code, "skipped": "no frequency file"}
            return _survey_report(code)

        with _faked(audit=audit, survey=survey):
            stats = await quality_loop.run_quality_cycle(conn)
        rows = _written(conn)

        assert stats["languages"] == 2
        assert stats["failures"] == ["ar.audit: FileNotFoundError: data/grammar/ar.json"]
        assert "ar: no frequency file" in stats["skipped"]
        # Arabic lost its audit (and the blankable coverage row that needs
        # it) and nothing else; Russian is complete. The judge coverage rows
        # are their own step and need no audit, so Arabic keeps those five.
        assert _by_metric(rows, "audit", LANG_AR) == {}
        assert set(_by_metric(rows, "coverage", LANG_AR)) == JUDGE_COVERAGE
        assert _by_metric(rows, "reconcile", LANG_AR) == {}
        assert set(_by_metric(rows, "snapshot", LANG_AR)) == set(SNAPSHOT_COUNTS)
        assert set(_by_metric(rows, "audit", LANG_RU)) == set(audit_content.ALL_RULES)
        assert set(_by_metric(rows, "reconcile", LANG_RU)) == {
            m for m, _ in quality_loop.RECONCILE_METRICS} | {"gone_with_cards"}

    async def test_absent_table_is_counted_not_raised(self):
        conn = _conn(("ru", LANG_RU))
        conn.fetchrow.side_effect = _missing()
        with _faked():
            stats = await quality_loop.run_quality_cycle(conn)
        assert stats["rows"] == 0
        assert stats["dropped"] > 0
        assert stats["failures"] == []


# ---------------------------------------------------------------------------
# The loop and its wiring
# ---------------------------------------------------------------------------


def test_heartbeat_is_a_copy():
    hb = quality_loop.quality_heartbeat()
    assert hb == quality_loop.QUALITY_HEARTBEAT
    assert hb is not quality_loop.QUALITY_HEARTBEAT


async def test_loop_records_a_failed_cycle_and_keeps_going(monkeypatch):
    monkeypatch.setattr(quality_loop, "FIRST_SWEEP_DELAY_SECONDS", 0)
    monkeypatch.setattr(quality_loop, "SWEEP_SECONDS", 3600)
    for key, value in (("started", False), ("cycles", 0), ("last_cycle_at", None),
                       ("last_error", None), ("last_stats", None)):
        monkeypatch.setitem(quality_loop.QUALITY_HEARTBEAT, key, value)

    @asynccontextmanager
    async def no_pool():
        raise RuntimeError("pool not initialised")
        yield  # pragma: no cover — makes this a generator

    with patch("backend.repositories.pool.privileged_connection", no_pool):
        task = asyncio.create_task(quality_loop.quality_loop())
        await asyncio.sleep(0.05)
        assert not task.done(), "the loop must survive a failed cycle"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    hb = quality_loop.quality_heartbeat()
    assert hb["started"] is True
    assert hb["cycles"] == 1
    assert hb["last_error"] == "RuntimeError: pool not initialised"
    assert hb["last_cycle_at"] is not None


class FakeSettings:
    supabase_jwt_secret = "test-jwt-secret-for-unit-tests-32bytes"
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "fake-anon-key"
    supabase_service_role_key = "fake-service-role-key"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


@contextmanager
def _app(settings):
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=settings), \
         patch("backend.dependencies.get_settings", return_value=settings):
        yield create_app()


def test_lifespan_does_not_start_the_loop_without_the_flag():
    # Test settings objects lack the flag; getattr's default keeps every
    # TestClient in the suite from running a real audit at startup.
    with patch("backend.services.quality_loop.quality_loop") as loop, _app(FakeSettings()) as app:
        with TestClient(app):
            pass
    loop.assert_not_called()


def test_lifespan_starts_the_loop_when_the_flag_is_on():
    class On(FakeSettings):
        quality_loop_enabled = True

    started = []

    async def fake_loop():
        started.append(True)
        await asyncio.sleep(3600)

    with patch("backend.services.quality_loop.quality_loop", new=fake_loop), _app(On()) as app:
        with TestClient(app):
            pass
    assert started == [True]
