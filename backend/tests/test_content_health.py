"""The Content Health endpoints and the arithmetic behind them
(docs/plans/quality-guardrails-telemetry.md §6, phase B).

Three layers, each tested where it lives. The pure module
(`services/content_health.py`) gets the status rules one branch at a time
and the None arithmetic, because a `0 > 15` that reads as green for an
unmeasured course is the false comfort the panel exists to remove. The
repository (`repositories/content_health.py`) gets its SQL shape and its
degrade path on `mock_conn()`. The router gets the plan-limits treatment:
403 for every non-admin, 200 shapes with the repository patched, 200 with
`available: false` when every telemetry table is absent, and 503 naming
migration 20261029 from every writer — never a 500, never a silent save.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import asyncpg
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories import content_health as repo
from backend.repositories.quality import SETTINGS_OFF, TARGET_DEFAULTS
from backend.services import content_health as ch
from backend.services import quality_loop
from backend.services.quality.audit_content import FAIL_RULES
from backend.services.quality.content_judge import QUESTIONS
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG_AR = "11111111-1111-1111-1111-111111111111"
LANG_KO = "22222222-2222-2222-2222-222222222222"
VERDICT = "33333333-3333-3333-3333-333333333333"

T0 = datetime(2026, 9, 18, 3, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)

TARGETS = {"judge_enabled": True, "max_bad_card_pct": 15, "max_judge_flag_pct": 5}


def _m(kind, metric, value, population=None, run_at=T0, locale=None):
    return {"kind": kind, "metric": metric, "locale": locale, "value": value,
            "population": population, "run_at": run_at}


def _metrics(**overrides) -> dict:
    """A course the loop has measured once: 1,800 of the top 2,000 blankable,
    two audit rules with counts, a judge coverage row for `sense`, one
    queue, a reconcile survey, and one judge run."""
    base = {
        "blankable_top_band": _m("coverage", "blankable_top_band", 1800, 2000),
        "leak_hard": _m("audit", "leak_hard", 3, 120, run_at=T1),
        "empty": _m("audit", "empty", 1, 120),
        "gender_marking": _m("audit", "gender_marking", 40),
        "judge.sense": _m("coverage", "judge.sense", 200, 2000),
        "pending_drills": _m("queues", "pending_drills", 7),
        "gone": _m("reconcile", "gone", 2, 5000, run_at=T0),
        "new": _m("reconcile", "new", 4, 5000, run_at=T1),
        "flagged.sense": _m("judge", "flagged.sense", 10, 200, run_at=T1),
    }
    base.update(overrides)
    return base


def _missing(name: str) -> asyncpg.exceptions.UndefinedTableError:
    return asyncpg.exceptions.UndefinedTableError(f'relation "{name}" does not exist')


# ---------------------------------------------------------------------------
# The pure module
# ---------------------------------------------------------------------------


class TestArithmetic:
    def test_pct_is_none_without_a_population(self):
        assert ch.pct(3, 0) is None
        assert ch.pct(3, None) is None
        assert ch.pct(None, 10) is None
        assert ch.pct(0, 10) == 0.0
        assert ch.pct(1, 8) == 12.5

    def test_derive_reads_every_field_from_the_latest_rows(self):
        baseline = {rule: 0 for rule in FAIL_RULES}
        baseline["leak_hard"] = 2
        course = ch.derive_course(
            _metrics(), TARGETS, baseline, {"sense": 10}, QUESTIONS,
            "ar", {("register", "ar")},
        )
        assert course["bad_card_pct"] == 10.0
        assert course["top_band_covered_pct"] == 90.0
        # fail-level rules only: gender_marking (report) is not a fail
        assert course["audit_fails"] == 4
        assert course["audit_fail_delta"] == (3 - 2) + (1 - 0)
        assert set(course["judge"]) == set(QUESTIONS)
        assert course["judge"]["sense"] == {
            "judged": 200, "population": 2000, "judged_pct": 10.0,
            "flagged": 10, "flag_pct": 5.0, "calibrated": False,  # no sense gold set
        }
        # register/ar IS in data/eval/calibrated.json, and it is the one pair
        # the judge spends on — the panel must not label it "not calibrated".
        assert course["judge"]["register"] == {
            "judged": 0, "population": 0, "judged_pct": None,
            "flagged": 0, "flag_pct": None, "calibrated": True,
        }
        assert course["queues"] == {"pending_drills": 7}
        assert course["reconcile"] == {"gone": 2, "new": 4, "run_at": T1.isoformat()}
        assert course["last_audited"] == T1.isoformat()
        assert course["last_judged"] == T1.isoformat()
        assert course["targets"] == TARGETS

    def test_calibration_is_per_pair_not_per_question(self):
        """A gold set is labelled in ONE course. `register` clearing its
        gates on Arabic says nothing about Persian, so the flag is keyed on
        (question, course) — keying it on the question name alone was wrong
        in both directions."""
        pairs = {("register", "ar")}
        ar = ch.derive_course({}, TARGET_DEFAULTS, {}, {}, QUESTIONS, "ar", pairs)
        fa = ch.derive_course({}, TARGET_DEFAULTS, {}, {}, QUESTIONS, "fa", pairs)
        assert ar["judge"]["register"]["calibrated"] is True
        assert fa["judge"]["register"]["calibrated"] is False
        assert ar["judge"]["sense"]["calibrated"] is False

    def test_without_the_pair_set_every_question_reads_uncalibrated(self):
        """The safe direction for a label that says how much to trust a rate."""
        course = ch.derive_course({}, TARGET_DEFAULTS, {}, {}, QUESTIONS)
        assert not any(q["calibrated"] for q in course["judge"].values())

    def test_the_panel_and_the_ledger_share_one_flag_threshold(self):
        """Three documents call these the same number, and they are compared
        in two languages: the panel's SQL binds this constant to a numeric
        column, the ledger's Python compares judge_step's. A float bound to
        numeric encodes as Decimal(float), so the two must be the same
        Decimal or they can disagree about which rows are flagged."""
        from backend.services.quality import judge_step
        assert ch.FLAG_CONFIDENCE == judge_step.FLAG_CONFIDENCE
        assert isinstance(ch.FLAG_CONFIDENCE, Decimal)
        assert isinstance(judge_step.FLAG_CONFIDENCE, Decimal)

    def test_an_unmeasured_course_has_nulls_not_zeros(self):
        course = ch.derive_course({}, TARGET_DEFAULTS, {}, {}, QUESTIONS)
        assert course["bad_card_pct"] is None
        assert course["top_band_covered_pct"] is None
        assert course["audit_fails"] is None
        assert course["audit_fail_delta"] is None
        assert course["last_audited"] is None
        assert course["last_judged"] is None
        assert course["reconcile"] == {"run_at": None}
        assert course["queues"] == {}
        assert course["status"] == "grey"

    def test_a_zero_population_never_divides(self):
        metrics = {"blankable_top_band": _m("coverage", "blankable_top_band", 0, 0),
                   "judge.sense": _m("coverage", "judge.sense", 0, 0)}
        course = ch.derive_course(metrics, TARGETS, {}, {"sense": 3}, QUESTIONS)
        assert course["bad_card_pct"] is None
        assert course["judge"]["sense"]["judged_pct"] is None
        assert course["judge"]["sense"]["flag_pct"] is None
        assert course["judge"]["sense"]["flagged"] == 3

    def test_support_locale_rows_do_not_feed_the_course_row(self):
        # latest_metrics keys a locale row "<locale>:<metric>" and marks it;
        # the course row is the course's own content only (principle 6).
        metrics = {"ar:blankable_top_band": _m("coverage", "blankable_top_band", 100, 2000,
                                                locale="ar")}
        course = ch.derive_course(metrics, TARGETS, {}, {}, QUESTIONS)
        assert course["bad_card_pct"] is None
        assert course["status"] == "green"  # measured (a row exists), nothing wrong

    def test_baseline_for_is_one_entry_per_fail_rule(self):
        out = ch.baseline_for({"ar.leak_hard": 5, "ru.leak_hard": 9, "ar.structural": 4}, "ar")
        assert set(out) == set(FAIL_RULES)
        assert out["leak_hard"] == 5
        assert out["empty"] == 0

    def test_question_positives_come_from_the_registry(self):
        out = ch.question_positives(QUESTIONS)
        assert out["sense"] == frozenset({"rare", "wrong"})
        assert out["register"] == frozenset({"dialect"})

    def test_reconcile_fields_pin_what_the_loop_writes(self):
        loop_metrics = {m for m, _ in quality_loop.RECONCILE_METRICS} | {"gone_with_cards"}
        assert set(ch.RECONCILE_FIELDS) == loop_metrics


class TestStatus:
    def _course(self, **fields):
        course = {"targets": dict(TARGETS), "bad_card_pct": 10.0, "top_band_covered_pct": 96.0,
                  "audit_fail_delta": 0, "judge": {"sense": {"flag_pct": 2.0}}}
        course.update(fields)
        return course

    def test_grey_when_never_measured(self):
        assert ch.status_of(self._course(), measured=False) == "grey"

    def test_red_when_bad_cards_exceed_the_target(self):
        assert ch.status_of(self._course(bad_card_pct=15.1)) == "red"
        assert ch.status_of(self._course(bad_card_pct=15.0)) == "green"

    def test_red_when_any_judge_flag_rate_exceeds_the_target(self):
        judge = {"sense": {"flag_pct": 1.0}, "gloss": {"flag_pct": 5.5}}
        assert ch.status_of(self._course(judge=judge)) == "red"

    def test_red_when_audit_fails_rose_above_the_baseline(self):
        assert ch.status_of(self._course(audit_fail_delta=1)) == "red"
        assert ch.status_of(self._course(audit_fail_delta=-3)) == "green"

    def test_amber_when_the_top_band_is_under_95_covered(self):
        assert ch.status_of(self._course(top_band_covered_pct=94.9)) == "amber"
        assert ch.status_of(self._course(top_band_covered_pct=95.0)) == "green"

    def test_red_beats_amber(self):
        assert ch.status_of(self._course(top_band_covered_pct=50.0, audit_fail_delta=2)) == "red"

    def test_none_never_trips_a_rule(self):
        course = self._course(bad_card_pct=None, top_band_covered_pct=None,
                              audit_fail_delta=None, judge={"sense": {"flag_pct": None}})
        assert ch.status_of(course) == "green"

    def test_sort_is_worst_first_then_by_code(self):
        rows = [{"code": "ru", "status": "green"}, {"code": "ar", "status": "grey"},
                {"code": "ko", "status": "red"}, {"code": "xh", "status": "amber"},
                {"code": "de", "status": "red"}]
        assert [r["code"] for r in sorted(rows, key=ch.sort_key)] == \
            ["de", "ko", "xh", "ru", "ar"]


class TestDrillDown:
    def test_audit_rows_carry_a_baseline_only_for_fail_rules(self):
        rows = ch.audit_rows(_metrics(), {"leak_hard": 2, "empty": 0})
        by_rule = {r["rule"]: r for r in rows}
        assert by_rule["leak_hard"] == {"rule": "leak_hard", "value": 3, "baseline": 2,
                                        "delta": 1, "population": 120}
        assert by_rule["gender_marking"] == {"rule": "gender_marking", "value": 40,
                                             "baseline": None, "delta": None,
                                             "population": None}
        assert [r["rule"] for r in rows] == sorted(by_rule)

    def test_trends_transform_and_drop_unplottable_points(self):
        rows = [{"run_at": T0, "value": 1800, "population": 2000},
                {"run_at": T1, "value": 5, "population": 0},
                {"run_at": T1, "value": 1900, "population": 2000}]
        assert ch.bad_card_trend(rows) == [{"run_at": T0.isoformat(), "value": 10.0},
                                           {"run_at": T1.isoformat(), "value": 5.0}]
        flags = [{"run_at": T0, "value": 10, "population": 200},
                 {"run_at": T1, "value": 3, "population": None}]
        assert ch.flag_trend(flags) == [{"run_at": T0.isoformat(), "value": 5.0}]

    def test_deploy_row_has_every_field_zero_filled(self):
        row = ch.deploy_row(
            {"code": "ar", "name": "Arabic"},
            {"metrics": {"gone": 2, "gloss": 17}, "run_at": T0, "build_sha": "abc"},
        )
        assert row["code"] == "ar" and row["name"] == "Arabic"
        assert row["run_at"] == T0.isoformat() and row["build_sha"] == "abc"
        assert row["gone"] == 2 and row["gloss"] == 17
        assert all(row[f] == 0 for f in ch.RECONCILE_FIELDS if f not in ("gone", "gloss"))


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------


class TestRepository:
    async def test_table_flags_probe_every_table_in_one_statement(self):
        conn = mock_conn()
        conn.fetch.return_value = [{"name": "quality_runs", "present": True},
                                   {"name": "content_verdicts", "present": False},
                                   {"name": "quality_settings", "present": True},
                                   {"name": "language_quality_targets", "present": False}]
        flags = await repo.table_flags(conn)
        assert flags == {"quality_runs": True, "content_verdicts": False,
                         "quality_settings": True, "language_quality_targets": False}
        assert conn.fetch.await_count == 1
        sql, tables = conn.fetch.await_args.args
        assert "to_regclass" in sql
        assert tables == list(repo.TABLES)

    async def test_open_flag_counts_pairs_question_with_its_own_verdicts(self):
        conn = mock_conn()
        conn.fetch.return_value = [
            {"language_id": LANG_AR, "question": "sense", "flagged": 4},
            {"language_id": LANG_KO, "question": "register", "flagged": 1},
        ]
        out = await repo.open_flag_counts(
            conn, {"sense": frozenset({"rare", "wrong"}), "register": frozenset({"dialect"})},
            ch.FLAG_CONFIDENCE,   # the real constant, a Decimal — not a literal
        )
        assert out == {LANG_AR: {"sense": 4}, LANG_KO: {"register": 1}}
        sql, questions, verdicts, floor = conn.fetch.await_args.args
        assert "disposition = 'open'" in sql and "unnest" in sql
        # The numerator of a rate whose denominator counts distinct rows of
        # content, so it must count those and not verdict rows: a card judged
        # on two nights with both verdicts open is one flagged card.
        assert "count(DISTINCT (v.entity_type, v.entity_id, v.field," in sql
        assert list(zip(questions, verdicts, strict=True)) == [
            ("register", "dialect"), ("sense", "rare"), ("sense", "wrong")]
        assert floor == Decimal("0.7") and isinstance(floor, Decimal)

    async def test_open_flag_counts_degrade_to_empty(self):
        conn = mock_conn()
        conn.fetch.side_effect = _missing("content_verdicts")
        assert await repo.open_flag_counts(conn, {"sense": {"rare"}}, 0.7) == {}
        assert await repo.open_flag_counts(mock_conn(), {}, 0.7) == {}

    async def test_open_verdicts_normalises_the_row(self):
        conn = mock_conn()
        conn.fetch.return_value = [{
            "id": VERDICT, "judged_at": T0, "entity_type": "vocabulary", "entity_id": LANG_AR,
            "field": "definition", "question": "sense", "verdict": "rare",
            "category": "dated", "evidence": ["in an unfortunate way"],
            "confidence": Decimal("0.90"), "expected": "unhappily", "note": None,
            "judge": "claude-x", "disposition": "open", "locale": None,
        }]
        rows = await repo.open_verdicts(conn, LANG_AR)
        assert rows[0]["judged_at"] == T0.isoformat()
        assert rows[0]["confidence"] == 0.9
        assert rows[0]["evidence"] == ["in an unfortunate way"]
        assert set(rows[0]) == set(repo.VERDICT_COLUMNS)
        sql, lang, limit = conn.fetch.await_args.args
        assert "ORDER BY judged_at DESC" in sql and (lang, limit) == (LANG_AR, 200)

    async def test_open_verdicts_degrade_to_empty(self):
        conn = mock_conn()
        conn.fetch.side_effect = _missing("content_verdicts")
        assert await repo.open_verdicts(conn, LANG_AR) == []

    async def test_dispose_only_touches_an_open_row(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {"id": VERDICT, "disposition": "accepted", "disposed_at": T1}
        out = await repo.dispose_verdict(conn, VERDICT, "accepted", TEST_USER_ID)
        assert out == {"id": VERDICT, "disposition": "accepted", "disposed_at": T1.isoformat()}
        sql, *args = conn.fetchrow.await_args.args
        assert "disposition = 'open'" in sql and "RETURNING" in sql
        assert args == [VERDICT, "accepted", TEST_USER_ID]

    async def test_dispose_distinguishes_no_row_from_no_table(self):
        conn = mock_conn()
        conn.fetchrow.return_value = None
        assert await repo.dispose_verdict(conn, VERDICT, "rejected", TEST_USER_ID) is None
        conn.fetchrow.side_effect = _missing("content_verdicts")
        assert await repo.dispose_verdict(conn, VERDICT, "rejected", TEST_USER_ID) \
            is repo.TABLE_ABSENT

    async def test_latest_reconcile_groups_per_course_with_the_newest_stamp(self):
        conn = mock_conn()
        conn.fetch.return_value = [
            {"language_id": LANG_AR, "metric": "gone", "value": Decimal("2"),
             "run_at": T0, "build_sha": "old"},
            {"language_id": LANG_AR, "metric": "new", "value": Decimal("4"),
             "run_at": T1, "build_sha": "new"},
            {"language_id": LANG_KO, "metric": "gone", "value": Decimal("0"),
             "run_at": T0, "build_sha": None},
        ]
        out = await repo.latest_reconcile(conn)
        assert out[LANG_AR] == {"metrics": {"gone": 2, "new": 4}, "run_at": T1,
                                "build_sha": "new"}
        assert out[LANG_KO]["metrics"] == {"gone": 0}
        assert "kind = 'reconcile'" in conn.fetch.await_args.args[0]

    async def test_latest_reconcile_degrades_to_empty(self):
        conn = mock_conn()
        conn.fetch.side_effect = _missing("quality_runs")
        assert await repo.latest_reconcile(conn) == {}

    async def test_list_languages_is_by_code(self):
        conn = mock_conn()
        conn.fetch.return_value = [{"id": LANG_AR, "code": "ar", "name": "Arabic"}]
        assert await repo.list_languages(conn) == [{"id": LANG_AR, "code": "ar",
                                                    "name": "Arabic"}]
        assert "ORDER BY code" in conn.fetch.await_args.args[0]


# ---------------------------------------------------------------------------
# The endpoints (the plan-limits pattern from test_contributor.py)
# ---------------------------------------------------------------------------


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    tutor_model = "claude-sonnet-5"


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield mock_conn()


@asynccontextmanager
async def _fake_priv():
    yield mock_conn()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.contribute.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.privileged_connection", _fake_priv):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _roles(roles):
    return patch("backend.routers.contribute.get_roles", new=AsyncMock(return_value=roles))


def _admin():
    return _roles([{"language_id": None, "role": "admin"}])


LANGUAGES = [{"id": LANG_AR, "code": "ar", "name": "Arabic"},
             {"id": LANG_KO, "code": "ko", "name": "Korean"}]
PRESENT = {t: True for t in repo.TABLES}
ABSENT = {t: False for t in repo.TABLES}
SETTINGS_ON = {"judge_enabled": True, "judge_rows_per_cycle": 500,
               "judge_daily_token_cap": 1_500_000, "judge_model": None}


class _Repo:
    """Every repository call the routes make, patched at once, with the
    happy-path return values; a test overrides what it needs. Each patch is
    an AsyncMock so a test can assert the path ran (quality rule 14)."""

    def __init__(self, **overrides):
        values = {
            "table_flags": PRESENT,
            "list_languages": LANGUAGES,
            "get_language_targets": {LANG_AR: TARGETS, LANG_KO: dict(TARGET_DEFAULTS)},
            "latest_quality_metrics": {LANG_AR: _metrics()},
            "open_flag_counts": {LANG_AR: {"sense": 10}},
            "get_quality_settings": SETTINGS_ON,
            "judge_tokens_spent_today": 123,
            "quality_trend": [],
            "open_verdicts": [],
            "latest_reconcile": {LANG_AR: {"metrics": {"gone": 2}, "run_at": T0,
                                           "build_sha": "abc"}},
            "dispose_verdict": {"id": VERDICT, "disposition": "accepted",
                                "disposed_at": T1.isoformat()},
            "update_quality_settings": SETTINGS_ON,
            "set_language_target": TARGETS,
        }
        values.update(overrides)
        self.mocks = {name: AsyncMock(return_value=value) for name, value in values.items()}
        self._patches = [patch(f"backend.routers.contribute.{name}", new=mock)
                         for name, mock in self.mocks.items()]
        self._patches.append(patch("backend.routers.contribute.load_baseline",
                                   return_value={"ar.leak_hard": 2}))

    def __enter__(self):
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        return False


ROUTES = [
    ("get", "/api/contribute/admin/content-health", None),
    ("get", "/api/contribute/admin/content-health/ar", None),
    ("get", "/api/contribute/admin/content-health/deploy", None),
    ("post", f"/api/contribute/admin/content-health/verdicts/{VERDICT}",
     {"disposition": "accepted"}),
    ("get", "/api/contribute/admin/quality-settings", None),
    ("put", "/api/contribute/admin/quality-settings", {"judge_enabled": True}),
    ("put", "/api/contribute/admin/quality-targets/ar", {"judge_enabled": True}),
]


class TestAuth:
    @pytest.mark.parametrize("method,path,body", ROUTES)
    def test_every_route_is_admin_only(self, client, method, path, body):
        with _roles([{"language_id": None, "role": "reviewer"}]), _Repo() as r:
            resp = client.request(method.upper(), path, json=body, headers=_auth_headers())
        assert resp.status_code == 403
        assert not any(m.await_count for m in r.mocks.values())


class TestOverview:
    def test_shape_and_sort(self, client):
        with _admin(), _Repo() as r:
            resp = client.get("/api/contribute/admin/content-health", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] == PRESENT
        assert body["settings"] == SETTINGS_ON
        assert body["spent_today"] == 123
        assert datetime.fromisoformat(body["generated_at"]).tzinfo is not None
        assert [c["code"] for c in body["courses"]] == ["ar", "ko"]
        ar, ko = body["courses"]
        assert ar["language_id"] == LANG_AR and ar["name"] == "Arabic"
        # leak_hard 3 against a baseline of 2, plus empty 1: red, before amber
        assert ar["status"] == "red" and ar["audit_fail_delta"] == 2
        assert ar["bad_card_pct"] == 10.0 and ar["top_band_covered_pct"] == 90.0
        assert ar["judge"]["sense"]["flagged"] == 10 and ar["judge"]["sense"]["flag_pct"] == 5.0
        assert ar["targets"] == TARGETS
        assert ko["status"] == "grey" and ko["targets"] == TARGET_DEFAULTS
        r.mocks["open_flag_counts"].assert_awaited_once()
        _, positives, floor = r.mocks["open_flag_counts"].await_args.args
        assert positives == ch.question_positives(QUESTIONS)
        assert floor == Decimal("0.7") and isinstance(floor, Decimal)

    def test_every_table_absent_is_still_200(self, client):
        with _admin(), _Repo(table_flags=ABSENT, latest_quality_metrics={},
                             open_flag_counts={}, get_quality_settings=dict(SETTINGS_OFF),
                             judge_tokens_spent_today=0,
                             get_language_targets={LANG_AR: dict(TARGET_DEFAULTS),
                                                   LANG_KO: dict(TARGET_DEFAULTS)}) as r:
            resp = client.get("/api/contribute/admin/content-health", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] == ABSENT
        assert body["settings"] == SETTINGS_OFF and body["spent_today"] == 0
        assert [c["status"] for c in body["courses"]] == ["grey", "grey"]
        assert all(set(c["judge"]) == set(QUESTIONS) for c in body["courses"])
        r.mocks["latest_quality_metrics"].assert_awaited_once()


class TestCourse:
    def test_drill_down_shape(self, client):
        coverage = [{"run_at": T0, "value": 1800, "population": 2000}]
        flagged = [{"run_at": T1, "value": 10, "population": 200}]

        async def trend(conn, lang_id, metric, days=30, locale=None):
            assert lang_id == LANG_AR
            return coverage if metric == "blankable_top_band" else \
                flagged if metric == "flagged.sense" else []

        verdict = {"id": VERDICT, "judged_at": T0.isoformat(), "entity_type": "vocabulary",
                   "entity_id": LANG_KO, "field": "definition", "question": "sense",
                   "verdict": "rare", "category": None, "evidence": [], "confidence": 0.9,
                   "expected": None, "note": None, "judge": "m", "disposition": "open",
                   "locale": None}
        with _admin(), _Repo(open_verdicts=[verdict]) as r:
            r.mocks["quality_trend"].side_effect = trend
            resp = client.get("/api/contribute/admin/content-health/ar", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "ar" and body["status"] == "red"
        assert body["trends"]["bad_card_pct"] == [{"run_at": T0.isoformat(), "value": 10.0}]
        assert body["trends"]["judge_flag_pct"]["sense"] == [{"run_at": T1.isoformat(),
                                                              "value": 5.0}]
        assert set(body["trends"]["judge_flag_pct"]) == set(QUESTIONS)
        by_rule = {a["rule"]: a for a in body["audit"]}
        assert by_rule["leak_hard"]["baseline"] == 2 and by_rule["leak_hard"]["delta"] == 1
        assert body["verdicts"] == [verdict]
        # one trend read for coverage, one per question
        assert r.mocks["quality_trend"].await_count == 1 + len(QUESTIONS)
        assert r.mocks["open_verdicts"].await_args.args[1] == LANG_AR

    def test_unknown_code_is_404(self, client):
        with _admin(), _Repo() as r:
            resp = client.get("/api/contribute/admin/content-health/zz", headers=_auth_headers())
        assert resp.status_code == 404
        r.mocks["quality_trend"].assert_not_awaited()


class TestDeploy:
    def test_only_surveyed_courses_with_the_running_build(self, client):
        with _admin(), _Repo(), \
             patch("backend.routers.contribute.build_info", return_value={"sha": "run-sha"}):
            resp = client.get("/api/contribute/admin/content-health/deploy",
                              headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["build_sha"] == "run-sha" and body["available"] is True
        assert len(body["courses"]) == 1
        row = body["courses"][0]
        assert row["code"] == "ar" and row["build_sha"] == "abc"
        assert row["run_at"] == T0.isoformat()
        assert row["gone"] == 2 and row["gone_with_cards"] == 0 and row["no_translation"] == 0

    def test_absent_table_is_available_false(self, client):
        with _admin(), _Repo(table_flags=ABSENT, latest_reconcile={}):
            resp = client.get("/api/contribute/admin/content-health/deploy",
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"build_sha": resp.json()["build_sha"], "available": False,
                               "courses": []}


class TestVerdicts:
    def test_dispose_records_the_admin(self, client):
        with _admin(), _Repo() as r:
            resp = client.post(f"/api/contribute/admin/content-health/verdicts/{VERDICT}",
                               json={"disposition": "accepted"}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"id": VERDICT, "disposition": "accepted",
                               "disposed_at": T1.isoformat()}
        assert r.mocks["dispose_verdict"].await_args.args[1:] == \
            (VERDICT, "accepted", TEST_USER_ID)

    @pytest.mark.parametrize("body", [{"disposition": "fixed"}, {"disposition": "open"}, {}])
    def test_only_accepted_or_rejected(self, client, body):
        with _admin(), _Repo() as r:
            resp = client.post(f"/api/contribute/admin/content-health/verdicts/{VERDICT}",
                               json=body, headers=_auth_headers())
        assert resp.status_code == 422
        r.mocks["dispose_verdict"].assert_not_awaited()

    def test_a_malformed_id_is_422(self, client):
        with _admin(), _Repo() as r:
            resp = client.post("/api/contribute/admin/content-health/verdicts/not-a-uuid",
                               json={"disposition": "rejected"}, headers=_auth_headers())
        assert resp.status_code == 422
        r.mocks["dispose_verdict"].assert_not_awaited()

    def test_no_open_row_is_404(self, client):
        with _admin(), _Repo(dispose_verdict=None):
            resp = client.post(f"/api/contribute/admin/content-health/verdicts/{VERDICT}",
                               json={"disposition": "rejected"}, headers=_auth_headers())
        assert resp.status_code == 404

    def test_absent_table_is_503_naming_the_migration(self, client):
        with _admin(), _Repo(dispose_verdict=repo.TABLE_ABSENT):
            resp = client.post(f"/api/contribute/admin/content-health/verdicts/{VERDICT}",
                               json={"disposition": "rejected"}, headers=_auth_headers())
        assert resp.status_code == 503
        assert "20261029" in resp.json()["detail"]


class TestQualitySettings:
    def test_get_shape(self, client):
        with _admin(), _Repo():
            resp = client.get("/api/contribute/admin/quality-settings", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is True and body["settings"] == SETTINGS_ON
        assert body["spent_today"] == 123
        assert body["targets"] == {"ar": TARGETS, "ko": TARGET_DEFAULTS}

    def test_get_before_the_migration_reads_off(self, client):
        with _admin(), _Repo(table_flags=ABSENT, get_quality_settings=dict(SETTINGS_OFF),
                             judge_tokens_spent_today=0):
            resp = client.get("/api/contribute/admin/quality-settings", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["available"] is False
        assert resp.json()["settings"] == SETTINGS_OFF

    def test_put_sends_only_the_fields_given(self, client):
        with _admin(), _Repo() as r:
            resp = client.put("/api/contribute/admin/quality-settings",
                              json={"judge_rows_per_cycle": 300, "judge_model": None},
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["settings"] == SETTINGS_ON
        assert resp.json()["targets"]["ar"] == TARGETS
        call = r.mocks["update_quality_settings"].await_args
        assert call.kwargs == {"updated_by": TEST_USER_ID, "judge_rows_per_cycle": 300,
                               "judge_model": None}

    @pytest.mark.parametrize("body", [
        {"judge_rows_per_cycle": -1}, {"judge_rows_per_cycle": 10_001},
        {"judge_daily_token_cap": -5}, {"judge_daily_token_cap": 1_000_000_001},
        {"judge_model": "x" * 101}, {"judge_enabled": "sometimes"},
    ])
    def test_put_rejects_out_of_range_values(self, client, body):
        with _admin(), _Repo() as r:
            resp = client.put("/api/contribute/admin/quality-settings", json=body,
                              headers=_auth_headers())
        assert resp.status_code == 422
        r.mocks["update_quality_settings"].assert_not_awaited()

    def test_put_before_the_migration_is_503(self, client):
        with _admin(), _Repo(update_quality_settings=None) as r:
            resp = client.put("/api/contribute/admin/quality-settings",
                              json={"judge_enabled": True}, headers=_auth_headers())
        assert resp.status_code == 503
        assert "20261029" in resp.json()["detail"]
        r.mocks["update_quality_settings"].assert_awaited_once()


class TestQualityTargets:
    def test_put_one_course(self, client):
        with _admin(), _Repo() as r:
            resp = client.put("/api/contribute/admin/quality-targets/ar",
                              json={"max_bad_card_pct": 12.5}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"code": "ar", "targets": TARGETS}
        call = r.mocks["set_language_target"].await_args
        assert call.args[1] == LANG_AR
        assert call.kwargs == {"updated_by": TEST_USER_ID, "max_bad_card_pct": 12.5}

    def test_unknown_code_is_404(self, client):
        with _admin(), _Repo() as r:
            resp = client.put("/api/contribute/admin/quality-targets/zz",
                              json={"judge_enabled": True}, headers=_auth_headers())
        assert resp.status_code == 404
        r.mocks["set_language_target"].assert_not_awaited()

    @pytest.mark.parametrize("body", [
        {"max_bad_card_pct": -1}, {"max_bad_card_pct": 100.5},
        {"max_judge_flag_pct": 101}, {"judge_enabled": "yes please"},
    ])
    def test_out_of_range_is_422(self, client, body):
        with _admin(), _Repo() as r:
            resp = client.put("/api/contribute/admin/quality-targets/ar", json=body,
                              headers=_auth_headers())
        assert resp.status_code == 422
        r.mocks["set_language_target"].assert_not_awaited()

    def test_before_the_migration_is_503(self, client):
        with _admin(), _Repo(set_language_target=None) as r:
            resp = client.put("/api/contribute/admin/quality-targets/ar",
                              json={"judge_enabled": True}, headers=_auth_headers())
        assert resp.status_code == 503
        assert "20261029" in resp.json()["detail"]
        r.mocks["set_language_target"].assert_awaited_once()
