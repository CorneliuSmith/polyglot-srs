"""WP21 Reader tests — service shape, gap matching, endpoint flow.

The dev-mock path (tutor_dev_mock=True) exercises generation end-to-end
with no API key, same pattern as the tutor tests.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.reader import log_grammar_gaps
from backend.services.reader import _mock_reading, _validate_reading

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"
TEST_READING_ID = "22222222-2222-2222-2222-222222222222"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "sk"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    anthropic_api_key = ""
    tutor_model = "claude-sonnet-5"
    tutor_model_low_resource = "claude-opus-4-8"
    tutor_dev_mock = True
    tutor_free_access = True
    tutor_free_monthly_messages = 20
    tutor_single_monthly_messages = 100
    tutor_all_monthly_messages = 300
    tutor_plus_daily_messages = 50


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TestReadingShape:
    def test_mock_reading_passes_validation(self):
        reading = _validate_reading(_mock_reading("cats"))
        assert reading["sentences"]
        assert reading["new_words"]
        # Every token glossed; seeded words marked.
        seeded = [
            t for s in reading["sentences"] for t in s["tokens"] if t.get("new")
        ]
        assert seeded
        for s in reading["sentences"]:
            assert all(t.get("gloss") for t in s["tokens"])

    def test_validation_rejects_empty(self):
        with pytest.raises(ValueError):
            _validate_reading({"sentences": []})
        with pytest.raises(ValueError):
            _validate_reading(
                {"sentences": [{"text": "x", "tokens": []}]}
            )


class TestGapMatching:
    def _run(self, titles: list[str], structures: list[str]) -> int:
        conn = AsyncMock()
        conn.fetch = AsyncMock(
            return_value=[{"t": t.lower()} for t in titles]
        )
        conn.execute = AsyncMock()
        return asyncio.run(
            log_grammar_gaps(conn, "lang-1", structures, "example")
        ), conn

    def test_covered_structures_are_not_logged(self):
        logged, conn = self._run(
            ["Present tense of -ar verbs", "Gustar and similar verbs"],
            # exact-insensitive and containment both count as covered
            ["gustar and similar verbs", "present tense"],
        )
        assert logged == 0
        conn.execute.assert_not_awaited()

    def test_uncovered_structures_are_upserted(self):
        logged, conn = self._run(
            ["Present tense of -ar verbs"],
            ["Diminutives (-ito/-ita)", "present tense"],
        )
        assert logged == 1
        sql = conn.execute.await_args.args[0]
        assert "ON CONFLICT (language_id, structure)" in sql
        assert conn.execute.await_args.args[2] == "Diminutives (-ito/-ita)"


# ---------------------------------------------------------------------------
# Endpoints (dev-mock generation, DB mocked)
# ---------------------------------------------------------------------------


def _conn_for_generate():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])          # learner model queries
    conn.fetchrow = AsyncMock(return_value=None)     # profile row
    conn.fetchval = AsyncMock(return_value=None)     # model override
    conn.execute = AsyncMock()
    return conn


@pytest.fixture()
def client():
    from contextlib import asynccontextmanager

    conn = _conn_for_generate()

    @asynccontextmanager
    async def fake_conn(*args):
        yield conn

    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.tutor.get_settings", return_value=FakeSettings()), \
         patch("backend.services.reader.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.reader.rls_connection", fake_conn), \
         patch("backend.routers.reader.privileged_connection", fake_conn), \
         patch("backend.services.allowance.get_settings", return_value=FakeSettings()), \
         patch("backend.services.allowance.rls_connection", fake_conn), \
         patch("backend.routers.tutor.rls_connection", fake_conn):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            c.fake_conn = conn
            yield c


class TestGenerateEndpoint:
    def test_requires_auth(self, client):
        resp = client.post(
            "/api/reader/generate",
            json={"language_id": TEST_LANGUAGE_ID,
                  "language_code": "es", "topic": "cats"},
        )
        assert resp.status_code == 401

    def test_generates_saves_and_reports_allowance(self, client):
        with patch(
            "backend.routers.reader.save_reading",
            new=AsyncMock(return_value=TEST_READING_ID),
        ) as mock_save, patch(
            "backend.routers.reader.log_grammar_gaps",
            new=AsyncMock(return_value=1),
        ) as mock_gaps, patch(
            "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
        ) as mock_usage:
            resp = client.post(
                "/api/reader/generate",
                json={"language_id": TEST_LANGUAGE_ID,
                      "language_code": "es", "topic": "cats"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == TEST_READING_ID
        assert body["reading"]["sentences"]
        assert body["reading"]["new_words"]
        assert body["allowance"]["unlimited"] is True
        mock_save.assert_awaited_once()
        mock_usage.assert_awaited_once()
        # The dev-mock reading contains an uncovered structure — the gap
        # collector must have been fed the structure list.
        structures = mock_gaps.await_args.args[2]
        assert "[dev mock] an uncovered structure" in structures

    def test_topic_length_limited(self, client):
        resp = client.post(
            "/api/reader/generate",
            json={"language_id": TEST_LANGUAGE_ID,
                  "language_code": "es", "topic": "x" * 500},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422


class TestShelfEndpoints:
    def test_reading_404_when_not_owned(self, client):
        with patch(
            "backend.routers.reader.get_reading", new=AsyncMock(return_value=None),
        ):
            resp = client.get(
                f"/api/reader/readings/{TEST_READING_ID}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_explain_uses_dev_mock(self, client):
        reading = {
            "id": TEST_READING_ID, "topic": "cats", "title": "t",
            "level": "A1", "created_at": "2026-07-16T00:00:00",
            "sentences": [{"text": "El gato duerme.",
                           "translation": "The cat sleeps.", "tokens": []}],
            "new_words": [], "structures": [],
        }
        lang_row = {"language_id": TEST_LANGUAGE_ID, "code": "es",
                    "tutor_model": None}

        async def fetchrow_side(sql, *args):
            # The same fake conn serves the language lookup AND the
            # allowance's tutor-access lookup — answer each by its SQL.
            if "FROM readings r JOIN languages" in sql:
                return lang_row
            return None  # no tutor_account_access row → default access

        client.fake_conn.fetchrow = AsyncMock(side_effect=fetchrow_side)
        with patch(
            "backend.routers.reader.get_reading",
            new=AsyncMock(return_value=reading),
        ), patch(
            "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
        ):
            resp = client.post(
                f"/api/reader/readings/{TEST_READING_ID}/explain",
                json={"sentence_index": 0},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert "dev mock" in resp.json()["explanation"]

    def test_explain_rejects_bad_index(self, client):
        reading = {
            "id": TEST_READING_ID, "topic": "cats", "title": "t",
            "level": "A1", "created_at": "2026-07-16T00:00:00",
            "sentences": [{"text": "x", "translation": "", "tokens": []}],
            "new_words": [], "structures": [],
        }
        with patch(
            "backend.routers.reader.get_reading",
            new=AsyncMock(return_value=reading),
        ):
            resp = client.post(
                f"/api/reader/readings/{TEST_READING_ID}/explain",
                json={"sentence_index": 5},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422
