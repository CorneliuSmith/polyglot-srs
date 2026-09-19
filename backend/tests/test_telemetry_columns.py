"""Migration 20261107000001's telemetry columns, written by code that deploys
before the migration lands (docs/plans/quality-guardrails-telemetry.md §5,
phase C).

Every writer here has two shapes: the wide INSERT that names the new
columns, run inside a savepoint, and the shape it falls back to on
UndefinedColumnError. The fallback is the half worth pinning. A deploy that
runs ahead of its migration is the ordinary case in this repository, and
what an unguarded statement produces then is not a missing column but a
poisoned transaction that 500s everything after it (repositories/pool.py).
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import asyncpg
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.change_requests import create_request
from backend.repositories.review import add_card_feedback
from backend.repositories.tutor import log_tutor_usage
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
USER = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"
CARD = "22222222-2222-2222-2222-222222222222"
CONTENT = "33333333-3333-3333-3333-333333333333"
DRILL = "44444444-4444-4444-4444-444444444444"
CR = "55555555-5555-5555-5555-555555555555"


def _absent(column: str) -> asyncpg.exceptions.UndefinedColumnError:
    """What Postgres raises on a deploy that ran ahead of 20261030."""
    return asyncpg.exceptions.UndefinedColumnError(f'column "{column}" does not exist')


# ---------------------------------------------------------------------------
# tutor_usage.outcome / latency_ms
# ---------------------------------------------------------------------------


class TestLogTutorUsage:
    async def test_writes_outcome_and_latency_when_given(self):
        conn = mock_conn()
        await log_tutor_usage(
            conn, USER, LANG, "claude-sonnet-5",
            usage={"input_tokens": 10, "output_tokens": 5},
            kind="chat", outcome="ok", latency_ms=812,
        )
        conn.execute.assert_awaited_once()
        sql, *args = conn.execute.await_args.args
        assert "outcome, latency_ms" in sql
        assert "$9, $10" in sql
        assert args[:4] == [USER, LANG, "claude-sonnet-5", "chat"]
        assert args[-2:] == ["ok", 812]

    async def test_falls_back_to_the_eight_columns_when_the_migration_is_absent(self):
        conn = mock_conn()
        conn.execute.side_effect = [_absent("outcome"), None]
        await log_tutor_usage(conn, USER, LANG, "m", outcome="ok", latency_ms=5)
        assert conn.execute.await_count == 2
        sql, *args = conn.execute.await_args_list[1].args
        assert "outcome" not in sql
        assert len(args) == 8

    async def test_callers_that_record_nothing_new_run_the_old_statement(self):
        # The sites that pass neither value must not pay a failed statement
        # and a rollback on every call against a database that has not
        # migrated — and there are eleven of them.
        conn = mock_conn()
        await log_tutor_usage(conn, USER, LANG, "m", kind="summary")
        conn.execute.assert_awaited_once()
        sql, *args = conn.execute.await_args.args
        assert "outcome" not in sql
        assert len(args) == 8

    async def test_a_clock_that_ran_backwards_is_clamped_not_refused(self):
        # The column's CHECK is >= 0. A negative wall-clock is a suspend or a
        # clock step, not a reason to 500 a turn the model already answered.
        conn = mock_conn()
        await log_tutor_usage(conn, USER, LANG, "m", outcome="ok", latency_ms=-7)
        assert conn.execute.await_args.args[-1] == 0

    async def test_an_outcome_the_column_would_refuse_is_dropped_with_a_warning(
        self, caplog,
    ):
        conn = mock_conn()
        await log_tutor_usage(conn, USER, LANG, "m", outcome="timeout", latency_ms=3)
        sql, *args = conn.execute.await_args.args
        assert args[-2:] == [None, 3]
        assert "timeout" in caplog.text


# ---------------------------------------------------------------------------
# card_feedback.field / drill_id / locale / support_locale
# ---------------------------------------------------------------------------


class TestAddCardFeedback:
    def _conn(self):
        conn = mock_conn()
        conn.fetchrow.return_value = {
            "card_type": "grammar", "card_id": CONTENT, "language_id": LANG,
        }
        return conn

    async def test_stores_field_drill_locale_and_support_locale(self):
        conn = self._conn()
        ok = await add_card_feedback(
            conn, USER, CARD, "the hint gives it away",
            field="hint", drill_id=DRILL, locale="fr", support_locale="fr",
        )
        assert ok is True
        sql, *args = conn.execute.await_args.args
        assert "field, drill_id, locale, support_locale" in sql
        assert "$7::uuid" in sql
        assert args == [
            USER, LANG, "grammar", CONTENT, "the hint gives it away",
            "hint", DRILL, "fr", "fr",
        ]

    async def test_falls_back_to_the_five_columns_when_the_migration_is_absent(self):
        # A report that reaches nobody is worse than a report with no label.
        conn = self._conn()
        conn.execute.side_effect = [_absent("field"), None]
        ok = await add_card_feedback(conn, USER, CARD, "msg", field="hint", locale="fr")
        assert ok is True
        assert conn.execute.await_count == 2
        sql, *args = conn.execute.await_args_list[1].args
        assert "field" not in sql
        assert args == [USER, LANG, "grammar", CONTENT, "msg"]

    async def test_a_card_that_is_not_the_users_is_still_refused_first(self):
        conn = mock_conn()
        conn.fetchrow.return_value = None
        assert await add_card_feedback(conn, USER, CARD, "msg", field="hint") is False
        conn.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# card_change_requests.locale
# ---------------------------------------------------------------------------


class TestCreateRequest:
    async def test_writes_the_locale_inside_a_savepoint(self):
        conn = mock_conn()
        conn.fetchval.return_value = CR
        req = await create_request(
            conn, USER, LANG, "drill", DRILL, "label", "hint",
            "the French hint leaks the answer", None, locale="fr",
        )
        assert req == CR
        sql, *args = conn.fetchval.await_args.args
        assert ", locale" in sql
        assert "$11" in sql
        assert len(args) == 11
        assert args[-1] == "fr"

    async def test_without_a_locale_the_old_statement_runs_untouched(self):
        conn = mock_conn()
        conn.fetchval.return_value = CR
        await create_request(conn, USER, LANG, "drill", DRILL, "label", "hint", "issue", None)
        conn.fetchval.assert_awaited_once()
        sql, *args = conn.fetchval.await_args.args
        assert "locale" not in sql
        assert len(args) == 10

    async def test_drops_the_locale_and_never_the_request_when_the_column_is_absent(self):
        conn = mock_conn()
        conn.fetchval.side_effect = [_absent("locale"), CR]
        req = await create_request(
            conn, USER, LANG, "drill", DRILL, "label", "hint", "issue", None, locale="fr",
        )
        assert req == CR
        assert conn.fetchval.await_count == 2
        sql, *args = conn.fetchval.await_args_list[1].args
        assert "locale" not in sql
        assert len(args) == 10


# ---------------------------------------------------------------------------
# The routers: what the client sends reaches the repository, and what the
# column would refuse is a 422 before any statement runs.
# ---------------------------------------------------------------------------


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": USER, "aud": "authenticated", "exp": int(time.time()) + 3600},
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
         patch("backend.routers.review.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.privileged_connection", _fake_priv):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _feedback(client, body: dict):
    return client.post(
        f"/api/review/card/{CARD}/feedback", json=body, headers=_auth_headers(),
    )


class TestFeedbackEndpointCarriesTheLayer:
    def test_passes_field_drill_locale_and_the_servers_support_locale(self, client):
        with patch("backend.routers.review.add_card_feedback",
                   new=AsyncMock(return_value=True)) as mock_add, \
             patch("backend.routers.review.effective_support_locale",
                   new=AsyncMock(return_value="ar")):
            resp = _feedback(client, {
                "message": "This is Egyptian, not MSA.", "field": "sentence",
                "drill_id": DRILL, "locale": "ar",
            })
        assert resp.status_code == 200
        assert mock_add.await_args.kwargs == {
            "field": "sentence", "drill_id": DRILL, "locale": "ar", "support_locale": "ar",
        }

    def test_an_english_support_learner_is_recorded_as_en_not_null(self, client):
        # effective_support_locale answers None for English, the convention
        # every overlay reader speaks. In this column NULL has to mean "not
        # recorded", or a pre-migration row and an English-support learner's
        # row would be the same row in every per-locale breakdown.
        with patch("backend.routers.review.add_card_feedback",
                   new=AsyncMock(return_value=True)) as mock_add, \
             patch("backend.routers.review.effective_support_locale",
                   new=AsyncMock(return_value=None)):
            resp = _feedback(client, {"message": "hi"})
        assert resp.status_code == 200
        kwargs = mock_add.await_args.kwargs
        assert kwargs["support_locale"] == "en"
        assert (kwargs["field"], kwargs["drill_id"], kwargs["locale"]) == (None, None, None)

    def test_a_field_the_column_would_refuse_is_a_422_not_a_500(self, client):
        with patch("backend.routers.review.add_card_feedback",
                   new=AsyncMock(return_value=True)) as mock_add:
            resp = _feedback(client, {"message": "hi", "field": "romanisation"})
        assert resp.status_code == 422
        mock_add.assert_not_awaited()

    def test_a_drill_id_that_is_not_a_uuid_is_a_422(self, client):
        with patch("backend.routers.review.add_card_feedback",
                   new=AsyncMock(return_value=True)) as mock_add:
            resp = _feedback(client, {"message": "hi", "drill_id": "drill-1"})
        assert resp.status_code == 422
        mock_add.assert_not_awaited()


class TestChangeRequestCarriesTheLocale:
    def _roles(self):
        return patch(
            "backend.routers.contribute.get_roles",
            new=AsyncMock(return_value=[{"language_id": LANG, "role": "reviewer"}]),
        )

    def test_the_locale_reaches_the_repository(self, client):
        with self._roles(), \
             patch("backend.routers.contribute.create_request",
                   new=AsyncMock(return_value=CR)) as mock_create:
            resp = client.post(
                "/api/contribute/change-requests",
                json={
                    "language_id": LANG, "target_type": "drill", "target_id": DRILL,
                    "field": "hint", "issue": "the French hint is wrong", "locale": "fr",
                },
                headers=_auth_headers(),
            )
        assert resp.status_code == 201
        assert mock_create.await_args.kwargs["locale"] == "fr"

    def test_an_older_client_that_sends_no_locale_still_raises_the_request(self, client):
        with self._roles(), \
             patch("backend.routers.contribute.create_request",
                   new=AsyncMock(return_value=CR)) as mock_create:
            resp = client.post(
                "/api/contribute/change-requests",
                json={"language_id": LANG, "field": "hint", "issue": "hint leaks"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 201
        assert mock_create.await_args.kwargs["locale"] is None


# ---------------------------------------------------------------------------
# The reader's background write: the one high-traffic site that is a plain
# function, so the wall-clock can be pinned without the router scaffolding.
# The tutor's /chat site is pinned in test_tutor.py beside its allowance
# tests; the Speak opener shares the repository path and has no router test
# for an opener today.
# ---------------------------------------------------------------------------


class TestReaderRecordsOutcomeAndLatency:
    async def test_the_background_write_logs_ok_with_the_learners_wait(self):
        from backend.routers import reader as reader_mod

        body = reader_mod.GenerateRequest(
            language_id=LANG, language_code="es", topic="los mercados",
        )

        async def slow_generate(*_a, **_k):
            # The whole generation step — the grader and a rewrite would sit
            # inside this await too — is what the learner's poll covers.
            await asyncio.sleep(0.02)
            return {"sentences": [], "structures": []}, {
                "input_tokens": 1, "output_tokens": 1,
                "cache_write_tokens": 0, "cache_read_tokens": 0,
            }

        with patch.object(reader_mod, "generate_reading", new=slow_generate), \
             patch.object(reader_mod, "rls_connection", _fake_rls), \
             patch.object(reader_mod, "privileged_connection", _fake_priv), \
             patch.object(reader_mod, "log_tutor_usage", new=AsyncMock()) as mock_log, \
             patch.object(reader_mod, "save_reading", new=AsyncMock(return_value="r-1")), \
             patch.object(reader_mod, "log_grammar_gaps", new=AsyncMock(return_value=0)):
            await reader_mod._write_reading(
                USER, body, learner={"level": "B1"}, gloss_locale="en", model="m",
                allowance={"unlimited": True, "used": 0, "limit": 0}, admin=False,
            )
        try:
            # _write_reading swallows every exception into the poll's error
            # slot; an empty slot is the proof the happy path ran.
            assert reader_mod._WRITE_ERRORS.get(USER) is None
            kwargs = mock_log.await_args.kwargs
            assert kwargs["kind"] == "reader"
            assert kwargs["outcome"] == "ok"
            assert isinstance(kwargs["latency_ms"], int)
            assert kwargs["latency_ms"] >= 15
        finally:
            reader_mod._RESULTS.pop(USER, None)
            reader_mod._WRITE_ERRORS.pop(USER, None)
