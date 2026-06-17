"""Endpoint tests for the onboarding router (DB + NLP mocked)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.nlp.base import AnswerResult

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"


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
        {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield AsyncMock()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.onboarding.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _items(n):
    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    return [
        {"id": f"id-{i}", "level": levels[i % len(levels)], "prompt": f"def {i}"}
        for i in range(n)
    ]


class TestOnboarding:
    def test_status_requires_auth(self, client):
        assert client.get("/api/onboarding/status").status_code == 401

    def test_status(self, client):
        with patch("backend.routers.onboarding.get_status",
                   new=AsyncMock(return_value={"onboarded": False,
                                               "active_language_id": None,
                                               "has_subscriptions": False})):
            resp = client.get("/api/onboarding/status", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["onboarded"] is False

    def test_placement_falls_back_when_thin(self, client):
        with patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=_items(2))):
            resp = client.get(f"/api/onboarding/placement/{LANG}", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["available"] is False

    def test_placement_returns_items(self, client):
        with patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=_items(6))):
            resp = client.get(f"/api/onboarding/placement/{LANG}", headers=_auth_headers())
        body = resp.json()
        assert body["available"] is True and len(body["items"]) == 6
        # The correct answer is never sent to the client.
        assert all("word" not in item for item in body["items"])

    def test_score_placement_estimates_level(self, client):
        answers = {
            "a1": {"word": "uno", "level": "A1"},
            "b1": {"word": "dos", "level": "B1"},
        }
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(AnswerResult.CORRECT, None))):
            resp = client.post(f"/api/onboarding/placement/{LANG}", json={
                "answers": [{"id": "a1", "input": "uno"}, {"id": "b1", "input": "dos"}],
            }, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["estimated_level"] == "B1"  # passed A1 and B1
        assert body["per_level"]["B1"] == {"correct": 1, "total": 1}

    def test_complete_subscribes(self, client):
        with patch("backend.routers.onboarding.complete_onboarding",
                   new=AsyncMock(return_value={"subscribed": 4,
                                               "active_language_id": LANG,
                                               "level": "A2"})) as mock_complete:
            resp = client.post("/api/onboarding/complete", json={
                "language_id": LANG, "level": "A2",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["subscribed"] == 4
        assert mock_complete.await_args.args[3] == "A2"

    def test_complete_rejects_bad_level(self, client):
        resp = client.post("/api/onboarding/complete", json={
            "language_id": LANG, "level": "Z9",
        }, headers=_auth_headers())
        assert resp.status_code == 422
