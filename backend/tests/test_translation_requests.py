"""Asking for a support language to be filled on a course whose backlog
drain is switched off (migration 20261024)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.translation_requests import (
    add_request,
    fulfil_requests,
    my_request,
    open_request_counts,
)
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG_ID = "11111111-1111-1111-1111-111111111111"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "sk"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    anthropic_api_key = ""
    tutor_dev_mock = True


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _conn(*, tables: bool = True, auto_on: bool = False,
          locale: str | None = "es", existing: dict | None = None) -> AsyncMock:
    """A connection standing in for one learner on one course."""
    conn = mock_conn()

    async def fetchval(sql, *args):
        if "to_regclass" in sql:
            return tables
        if "SELECT name FROM languages WHERE code" in sql:
            return {"es": "Spanish", "fr": "French"}.get(args[0])
        if "count(*) FROM translation_requests" in sql:
            return 0
        return None

    async def fetchrow(sql, *args):
        if "support_locale, ui_language" in sql:
            return {"support_locale": locale, "ui_language": "en"}
        if "auto_translate_enabled FROM languages" in sql:
            return {"name": "Dutch", "auto_translate_enabled": auto_on}
        if "FROM translation_requests" in sql:
            return existing
        return None

    conn.fetchval = AsyncMock(side_effect=fetchval)
    conn.fetchrow = AsyncMock(side_effect=fetchrow)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    return conn


@pytest.fixture
def client_for():
    def _make(conn):
        @asynccontextmanager
        async def fake_conn(*args, **kwargs):
            yield conn

        ctx = [
            patch("backend.main.init_pool", new=AsyncMock()),
            patch("backend.main.close_pool", new=AsyncMock()),
            patch("backend.main.get_settings", return_value=FakeSettings()),
            patch("backend.dependencies.get_settings", return_value=FakeSettings()),
            patch("backend.routers.languages.rls_connection", fake_conn),
        ]
        for c in ctx:
            c.start()
        app = create_app()
        client = TestClient(app, raise_server_exceptions=True)
        client.__enter__()
        client._ctx = ctx
        client.fake_conn = conn
        return client

    made: list = []

    def make(conn):
        c = _make(conn)
        made.append(c)
        return c

    yield make
    for c in made:
        c.__exit__(None, None, None)
        for patcher in c._ctx:
            patcher.stop()


class TestTheRepository:
    @pytest.mark.asyncio
    async def test_asking_twice_is_asking_once(self):
        conn = _conn()
        assert await add_request(conn, TEST_USER_ID, LANG_ID, "es") == "created"
        conn.execute = AsyncMock(return_value="INSERT 0 0")
        assert await add_request(conn, TEST_USER_ID, LANG_ID, "es") == "already"

    @pytest.mark.asyncio
    async def test_everything_degrades_before_the_migration(self):
        conn = _conn(tables=False)
        assert await add_request(conn, TEST_USER_ID, LANG_ID, "es") == "unavailable"
        assert await my_request(conn, TEST_USER_ID, LANG_ID, "es") is None
        assert await open_request_counts(conn) == {}
        # The toggle must still work with no table behind the asks.
        assert await fulfil_requests(conn, LANG_ID) == 0

    @pytest.mark.asyncio
    async def test_counts_group_by_course_and_locale(self):
        conn = _conn()
        conn.fetch = AsyncMock(return_value=[
            {"language_id": LANG_ID, "locale": "es", "locale_name": "Spanish", "n": 3},
            {"language_id": LANG_ID, "locale": "tr", "locale_name": None, "n": 1},
        ])
        counts = await open_request_counts(conn)
        assert counts[LANG_ID] == [
            {"locale": "es", "locale_name": "Spanish", "learners": 3},
            # A locale that is only an interface language shows its code.
            {"locale": "tr", "locale_name": "tr", "learners": 1},
        ]

    @pytest.mark.asyncio
    async def test_switching_the_drain_on_closes_the_open_asks(self):
        conn = _conn()
        conn.execute = AsyncMock(return_value="UPDATE 4")
        assert await fulfil_requests(conn, LANG_ID) == 4


class TestTheEndpoint:
    def test_a_learner_on_a_switched_off_course_may_ask(self, client_for):
        c = client_for(_conn(auto_on=False))
        r = c.get(f"/api/languages/translation-request?language_id={LANG_ID}",
                  headers=_auth_headers())
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["can_ask"] is True
        assert body["locale"] == "es" and body["locale_name"] == "Spanish"
        assert body["auto_translate_enabled"] is False
        assert body["request"] is None

    def test_nothing_to_ask_for_when_the_drain_is_already_on(self, client_for):
        c = client_for(_conn(auto_on=True))
        body = c.get(f"/api/languages/translation-request?language_id={LANG_ID}",
                     headers=_auth_headers()).json()
        assert body["can_ask"] is False and body["auto_translate_enabled"] is True
        # Asking anyway is good news, not an error.
        r = c.post("/api/languages/translation-request",
                   headers=_auth_headers(), json={"language_id": LANG_ID})
        assert r.status_code == 200 and r.json()["result"] == "already_on"

    def test_english_help_needs_no_translation(self, client_for):
        c = client_for(_conn(locale=None))
        body = c.get(f"/api/languages/translation-request?language_id={LANG_ID}",
                     headers=_auth_headers()).json()
        assert body["can_ask"] is False and body["locale"] is None
        r = c.post("/api/languages/translation-request",
                   headers=_auth_headers(), json={"language_id": LANG_ID})
        assert r.status_code == 422

    def test_asking_records_the_ask_and_reports_it_back(self, client_for):
        conn = _conn(auto_on=False)
        c = client_for(conn)
        r = c.post("/api/languages/translation-request",
                   headers=_auth_headers(),
                   json={"language_id": LANG_ID, "note": "  most of it is English  "})
        assert r.status_code == 200, r.text
        assert r.json()["result"] == "created"
        inserts = [call.args for call in conn.execute.await_args_list
                   if "INSERT INTO translation_requests" in call.args[0]]
        assert len(inserts) == 1
        # args[0] is the SQL: user, language, locale, note follow it.
        # Trimmed, and the locale comes from the profile, never the client.
        assert inserts[0][4] == "most of it is English"
        assert inserts[0][3] == "es"

    def test_an_existing_ask_is_shown_instead_of_the_button(self, client_for):
        from datetime import UTC, datetime

        existing = {"status": "open", "requested_at": datetime.now(UTC),
                    "decided_at": None}
        c = client_for(_conn(auto_on=False, existing=existing))
        body = c.get(f"/api/languages/translation-request?language_id={LANG_ID}",
                     headers=_auth_headers()).json()
        assert body["can_ask"] is False
        assert body["request"]["status"] == "open"

    def test_before_the_migration_the_ask_is_unavailable_not_a_500(self, client_for):
        c = client_for(_conn(tables=False))
        body = c.get(f"/api/languages/translation-request?language_id={LANG_ID}",
                     headers=_auth_headers()).json()
        assert body["available"] is False and body["can_ask"] is False
        r = c.post("/api/languages/translation-request",
                   headers=_auth_headers(), json={"language_id": LANG_ID})
        assert r.status_code == 503 and "20261024" in r.json()["detail"]
