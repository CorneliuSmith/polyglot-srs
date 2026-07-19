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
        {"id": f"id-{i}", "kind": "vocabulary", "level": levels[i % len(levels)],
         "prompt": f"def {i}", "translation": None}
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
            "a1": {"answer": "uno", "level": "A1"},
            "b1": {"answer": "dos", "level": "B1"},
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


class TestPlainPromptFilter:
    """Placement prompts must read like flashcards, not a linguistics glossary
    (beta feedback: 'too much grammar vocab')."""

    def test_concrete_definitions_pass(self):
        from backend.repositories.onboarding import _plain_prompt

        assert _plain_prompt("house")
        assert _plain_prompt("to eat")
        assert _plain_prompt("water; rain")

    def test_grammarese_is_rejected(self):
        from backend.repositories.onboarding import _plain_prompt

        assert not _plain_prompt("initial interrogative particle")
        assert not _plain_prompt("inflection of होना (honā):")
        assert not _plain_prompt("feminine singular of o")
        assert not _plain_prompt("first/third-person plural present indicative")
        assert not _plain_prompt("dative of я")

    def test_overlong_definitions_are_rejected(self):
        from backend.repositories.onboarding import _plain_prompt

        assert not _plain_prompt(
            "sometimes after lhe, especially when referring to a body part, "
            "a family member, or a pet."
        )


class TestAdaptiveStopCalibration:
    """Beta fix: oscillation can't end the test before MIN_ADAPTIVE_ITEMS —
    with 1–3 samples per level, one unlucky item was deciding the placement."""

    def _pool(self):
        from backend.repositories.onboarding import CEFR_ORDER
        return [
            {"id": f"p{i}", "kind": "vocabulary" if i % 2 else "grammar",
             "level": CEFR_ORDER[i % len(CEFR_ORDER)]}
            for i in range(30)
        ]

    def test_oscillation_does_not_stop_before_min_items(self):
        from backend.repositories.onboarding import adaptive_next
        pool, hist = self._pool(), []
        for i in range(5):  # pass/miss alternation racks up 4 reversals by item 5
            item = adaptive_next(pool, hist)
            assert item is not None
            hist.append((item, i % 2 == 0))
        # 5 items with 4 reversals: the old code stopped here — now it must
        # keep probing until MIN_ADAPTIVE_ITEMS.
        assert adaptive_next(pool, hist) is not None

    def test_oscillation_stops_at_min_items(self):
        from backend.repositories.onboarding import MIN_ADAPTIVE_ITEMS, adaptive_next
        pool, hist = self._pool(), []
        for i in range(MIN_ADAPTIVE_ITEMS):
            item = adaptive_next(pool, hist)
            assert item is not None
            hist.append((item, i % 2 == 0))
        assert adaptive_next(pool, hist) is None

    def test_floor_stop_stays_immediate(self):
        from backend.repositories.onboarding import adaptive_next
        pool, hist = self._pool(), []
        for _ in range(3):  # A2 miss -> A1, then two misses AT the floor
            item = adaptive_next(pool, hist)
            assert item is not None
            hist.append((item, False))
        # an absolute beginner is obvious after 3 misses — no min-items delay
        assert adaptive_next(pool, hist) is None


class TestPlacementAlternatives:
    """Beta fix: a definition prompt has several right answers (делать /
    сделать) — the card's recorded alternatives must count as correct."""

    def test_adaptive_grading_passes_alternatives_to_validator(self, client):
        pool = [{"id": "a1", "kind": "vocabulary", "level": "A1",
                 "prompt": "to do, to make", "translation": None}] + _items(11)
        answers = {"a1": {"answer": "делать", "level": "A1",
                          "alternatives": ["сделать"]}}
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="ru")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(AnswerResult.CORRECT, None))) as mock_v:
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [{"id": "a1", "input": "сделать"}],
            }, headers=_auth_headers())
        assert resp.status_code == 200
        assert mock_v.await_args.args[3] == {"answer_alternatives": ["сделать"]}
