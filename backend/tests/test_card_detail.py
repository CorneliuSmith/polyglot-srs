"""Tests for the review card-detail endpoint and grammar-content pipeline."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
CARD_ID = "22222222-2222-2222-2222-222222222222"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    tutor_dev_mock = True
    anthropic_api_key = ""
    tutor_model = "claude-opus-4-8"
    tutor_summary_model = "claude-sonnet-4-6"
    tutor_free_access = True


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
         patch("backend.routers.review.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


class TestCardDetailEndpoint:
    def test_requires_auth(self, client):
        assert client.get(f"/api/review/card/{CARD_ID}/detail").status_code == 401

    def test_grammar_detail(self, client):
        detail = {
            "card_type": "grammar",
            "title": "Locative case",
            "explanation": "Used to express location...",
            "culture_note": "Common in directions.",
            "examples": [{"sentence": "evde", "translation": "at home", "hint": None}],
        }
        with patch("backend.routers.review.get_card_detail", new=AsyncMock(return_value=detail)):
            resp = client.get(f"/api/review/card/{CARD_ID}/detail", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["explanation"].startswith("Used to express")

    def test_vocab_detail(self, client):
        detail = {
            "card_type": "vocabulary",
            "title": "ev",
            "definition": "house",
            "usage_note": None,
            "examples": [{"sentence": "Ev güzel.", "translation": "The house is nice.", "hint": None}],
        }
        with patch("backend.routers.review.get_card_detail", new=AsyncMock(return_value=detail)):
            resp = client.get(f"/api/review/card/{CARD_ID}/detail", headers=_auth_headers())
        assert resp.json()["card_type"] == "vocabulary"
        assert resp.json()["examples"][0]["translation"] == "The house is nice."

    def test_not_found(self, client):
        with patch("backend.routers.review.get_card_detail", new=AsyncMock(return_value=None)):
            resp = client.get(f"/api/review/card/{CARD_ID}/detail", headers=_auth_headers())
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Grammar content generation pipeline
# ---------------------------------------------------------------------------


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, content):
        self.content = content


class TestGenerateGrammarContent:
    @pytest.mark.asyncio
    async def test_mock_mode_no_api_call(self):
        from backend.services.seeder import generate_grammar as gg

        with patch.object(gg, "get_settings", return_value=FakeSettings()), \
             patch.object(gg, "AsyncAnthropic", side_effect=AssertionError("no call in mock")):
            content = await gg.generate_grammar_content("ru", "Genitive case")
        assert "dev mock" in content["explanation"].lower()
        assert content["culture_note"] == ""

    @pytest.mark.asyncio
    async def test_real_mode_parses_structured_output(self):
        from backend.services.seeder import generate_grammar as gg

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "fake"
        payload = '{"explanation": "The genitive marks possession.", "culture_note": ""}'
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(return_value=_Resp([_TextBlock(payload)]))
        with patch.object(gg, "get_settings", return_value=settings), \
             patch.object(gg, "AsyncAnthropic", return_value=fake_client):
            content = await gg.generate_grammar_content(
                "ru", "Genitive case", ["dom -> doma"], "A2"
            )
        assert content["explanation"] == "The genitive marks possession."
        assert fake_client.messages.create.await_args.kwargs["model"] == "claude-sonnet-4-6"


class TestParseGrammarNotesFile:
    def test_parses_and_skips_incomplete(self, tmp_path):
        import json

        from backend.services.seeder.generate_grammar import parse_grammar_notes_file

        p = tmp_path / "notes.json"
        p.write_text(json.dumps([
            {"title": "Locative", "explanation": "Location.", "culture_note": "x"},
            {"title": "NoExplanation"},
            {"explanation": "orphan"},
        ]), encoding="utf-8")
        notes = parse_grammar_notes_file(str(p))
        assert len(notes) == 1
        assert notes[0]["title"] == "Locative"
