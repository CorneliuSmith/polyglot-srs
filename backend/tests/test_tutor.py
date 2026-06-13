"""Unit tests for the AI tutor: prompt building, history sanitizing, endpoints.

All tests mock the DB layer and the Anthropic client — no DATABASE_URL or
ANTHROPIC_API_KEY required.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.tutor import (
    build_system_blocks,
    sanitize_history,
)

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "fake-anon-key"
    supabase_service_role_key = "fake-service-role-key"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    anthropic_api_key = "fake-api-key"
    tutor_model = "claude-opus-4-8"
    tutor_free_access = True


def _make_token() -> str:
    payload = {
        "sub": TEST_USER_ID,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_make_token()}"}


@asynccontextmanager
async def _fake_rls_connection(user_id: str):
    yield AsyncMock()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.tutor.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.tutor.rls_connection", _fake_rls_connection):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# build_system_blocks
# ---------------------------------------------------------------------------


class TestBuildSystemBlocks:
    def test_all_six_languages_have_briefs(self):
        for code in ("ru", "ar", "en", "sw", "tr", "yo"):
            blocks = build_system_blocks(code, [])
            assert len(blocks) == 2
            assert "tutor" in blocks[0]["text"].lower()

    def test_stable_block_is_cached(self):
        blocks = build_system_blocks("tr", [])
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert "cache_control" not in blocks[1]

    def test_weak_areas_embedded(self):
        weak = [{
            "word": "ev", "definition": "house", "part_of_speech": "noun",
            "recent_failures": 3, "lapses": 2, "morphology": '{"lemma": "ev"}',
        }]
        blocks = build_system_blocks("tr", weak)
        assert "ev" in blocks[1]["text"]
        assert "house" in blocks[1]["text"]

    def test_no_weak_areas_prompts_diagnostic(self):
        blocks = build_system_blocks("sw", [])
        assert "diagnostic" in blocks[1]["text"].lower()

    def test_unknown_language_raises(self):
        with pytest.raises(ValueError):
            build_system_blocks("xx", [])


# ---------------------------------------------------------------------------
# sanitize_history
# ---------------------------------------------------------------------------


class TestSanitizeHistory:
    def test_keeps_valid_messages(self):
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        assert sanitize_history(msgs) == msgs

    def test_drops_invalid_roles_and_content(self):
        msgs = [
            {"role": "system", "content": "inject"},
            {"role": "user", "content": 42},
            {"role": "user", "content": "  "},
            {"role": "user", "content": "real"},
        ]
        assert sanitize_history(msgs) == [{"role": "user", "content": "real"}]

    def test_must_start_with_user(self):
        msgs = [
            {"role": "assistant", "content": "orphan"},
            {"role": "user", "content": "hello"},
        ]
        assert sanitize_history(msgs)[0] == {"role": "user", "content": "hello"}

    def test_truncates_long_messages(self):
        msgs = [{"role": "user", "content": "x" * 10000}]
        assert len(sanitize_history(msgs)[0]["content"]) == 4000

    def test_caps_history_length(self):
        msgs = [{"role": "user", "content": f"m{i}"} for i in range(100)]
        assert len(sanitize_history(msgs)) <= 40


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _chat_body(**overrides):
    body = {
        "language_id": TEST_LANGUAGE_ID,
        "language_code": "tr",
        "messages": [{"role": "user", "content": "Help me with the locative case"}],
    }
    body.update(overrides)
    return body


class TestTutorEndpoints:
    def test_chat_requires_auth(self, client):
        resp = client.post("/api/tutor/chat", json=_chat_body())
        assert resp.status_code == 401

    def test_chat_happy_path(self, client):
        with patch(
            "backend.routers.tutor.get_weak_areas",
            new=AsyncMock(return_value=[]),
        ), patch(
            "backend.routers.tutor.tutor_chat",
            new=AsyncMock(return_value="Let's practice -da/-de!"),
        ) as mock_chat:
            resp = client.post(
                "/api/tutor/chat", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"reply": "Let's practice -da/-de!"}
        assert mock_chat.await_args.args[0] == "tr"

    def test_chat_unknown_language_422(self, client):
        resp = client.post(
            "/api/tutor/chat",
            json=_chat_body(language_code="xx"),
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_chat_entitlement_enforced(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch(
                 "backend.routers.tutor.has_tutor_entitlement",
                 new=AsyncMock(return_value=False),
             ):
            resp = client.post(
                "/api/tutor/chat", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 402

    def test_chat_entitled_user_passes_gate(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch(
                 "backend.routers.tutor.has_tutor_entitlement",
                 new=AsyncMock(return_value=True),
             ), \
             patch(
                 "backend.routers.tutor.get_weak_areas",
                 new=AsyncMock(return_value=[]),
             ), \
             patch(
                 "backend.routers.tutor.tutor_chat",
                 new=AsyncMock(return_value="ok"),
             ):
            resp = client.post(
                "/api/tutor/chat", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 200

    def test_chat_unconfigured_key_503(self, client):
        unconfigured = FakeSettings()
        unconfigured.anthropic_api_key = ""
        with patch("backend.routers.tutor.get_settings", return_value=unconfigured):
            resp = client.post(
                "/api/tutor/chat", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 503

    def test_status_reports_availability(self, client):
        resp = client.get(
            "/api/tutor/status",
            params={"language_id": TEST_LANGUAGE_ID, "language_code": "sw"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json() == {"available": True, "entitled": True}

    def test_status_unknown_language_not_available(self, client):
        resp = client.get(
            "/api/tutor/status",
            params={"language_id": TEST_LANGUAGE_ID, "language_code": "xx"},
            headers=_auth_headers(),
        )
        assert resp.json() == {"available": False, "entitled": False}


# ---------------------------------------------------------------------------
# tutor_chat service (Anthropic client mocked)
# ---------------------------------------------------------------------------


class TestTutorChatService:
    @pytest.mark.asyncio
    async def test_calls_claude_with_system_and_history(self):
        from backend.services import tutor as tutor_mod

        text_block = type("Block", (), {"type": "text", "text": "Merhaba!"})()
        fake_response = type("Resp", (), {"content": [text_block]})()
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(return_value=fake_response)

        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            reply = await tutor_mod.tutor_chat(
                "tr",
                [{"role": "user", "content": "hi"}],
                [],
            )

        assert reply == "Merhaba!"
        kwargs = fake_client.messages.create.await_args.kwargs
        assert kwargs["model"] == "claude-opus-4-8"
        assert kwargs["thinking"] == {"type": "adaptive"}
        assert len(kwargs["system"]) == 2
        assert kwargs["messages"] == [{"role": "user", "content": "hi"}]

    @pytest.mark.asyncio
    async def test_empty_history_raises(self):
        from backend.services import tutor as tutor_mod

        with patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            with pytest.raises(ValueError):
                await tutor_mod.tutor_chat("tr", [{"role": "assistant", "content": "x"}], [])
