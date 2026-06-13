"""Unit tests for the AI tutor: prompt building, memory, tools, endpoints.

All tests mock the DB layer and the Anthropic client — no DATABASE_URL or
ANTHROPIC_API_KEY required.
"""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.tutor import (
    build_system_blocks,
    merge_remembered,
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
    tutor_summary_model = "claude-sonnet-4-6"
    tutor_free_access = True
    tutor_dev_mock = False


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


# Fake Anthropic content blocks ------------------------------------------------

class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _ToolUseBlock:
    type = "tool_use"

    def __init__(self, id, name, input):
        self.id = id
        self.name = name
        self.input = input


class _Resp:
    def __init__(self, content):
        self.content = content


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
    def test_all_eight_languages_have_briefs(self):
        for code in ("ru", "ar", "en", "sw", "tr", "yo", "ha", "xh"):
            blocks = build_system_blocks(code, [])
            assert len(blocks) == 2
            assert "tutor" in blocks[0]["text"].lower()

    def test_briefs_mention_register(self):
        for code in ("ru", "ar", "en", "sw", "tr", "yo", "ha", "xh"):
            assert "register" in build_system_blocks(code, [])[0]["text"].lower()

    def test_stable_block_is_cached(self):
        blocks = build_system_blocks("tr", [])
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert "cache_control" not in blocks[1]

    def test_weak_areas_embedded(self):
        weak = [{
            "word": "ev", "definition": "house", "part_of_speech": "noun",
            "recent_failures": 3, "lapses": 2, "morphology": '{"lemma": "ev"}',
        }]
        text = build_system_blocks("tr", weak)[1]["text"]
        assert "ev" in text and "house" in text

    def test_study_stats_embedded(self):
        stats = {"accuracy_last_30d": 0.62, "due_now": 14, "highest_level_reached": "A2"}
        text = build_system_blocks("tr", [], study_stats=stats)[1]["text"]
        assert "accuracy_last_30d" in text and "0.62" in text

    def test_memory_embedded(self):
        text = build_system_blocks(
            "tr", [],
            user_profile={"native_language": "English", "motivation": "trip to Istanbul"},
            language_profile={"error_pattern": "forgets vowel harmony"},
            session_summary="Worked on the locative case; struggled with -de/-da.",
        )[1]["text"]
        assert "trip to Istanbul" in text
        assert "vowel harmony" in text
        assert "locative" in text

    def test_no_data_prompts_diagnostic(self):
        assert "diagnostic" in build_system_blocks("sw", [])[1]["text"].lower()

    def test_unknown_language_raises(self):
        with pytest.raises(ValueError):
            build_system_blocks("zz", [])


# ---------------------------------------------------------------------------
# merge_remembered (pure)
# ---------------------------------------------------------------------------


class TestMergeRemembered:
    def test_global_and_language_routing(self):
        user, lang = merge_remembered(
            {}, {},
            [
                {"scope": "global", "key": "native_language", "value": "English"},
                {"scope": "language", "key": "level", "value": "A2"},
            ],
        )
        assert user == {"native_language": "English"}
        assert lang == {"level": "A2"}

    def test_repeated_key_becomes_list(self):
        _, lang = merge_remembered(
            {}, {"error_pattern": "drops articles"},
            [{"scope": "language", "key": "error_pattern", "value": "wrong case"}],
        )
        assert lang["error_pattern"] == ["drops articles", "wrong case"]

    def test_duplicate_value_not_duplicated(self):
        _, lang = merge_remembered(
            {}, {"interest": ["food", "music"]},
            [{"scope": "language", "key": "interest", "value": "food"}],
        )
        assert lang["interest"] == ["food", "music"]

    def test_does_not_mutate_inputs(self):
        original_user = {"a": "1"}
        merge_remembered(
            original_user, {},
            [{"scope": "global", "key": "b", "value": "2"}],
        )
        assert original_user == {"a": "1"}

    def test_ignores_incomplete_notes(self):
        user, lang = merge_remembered(
            {}, {}, [{"scope": "global", "key": None, "value": "x"}]
        )
        assert user == {} and lang == {}


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
        assert len(sanitize_history([{"role": "user", "content": "x" * 10000}])[0]["content"]) == 4000

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


def _patch_chat_repos():
    """Patch the DB reads the chat endpoint performs."""
    lang = {"profile": {}, "session_summary": ""}
    return (
        patch("backend.routers.tutor.get_weak_areas", new=AsyncMock(return_value=[])),
        patch("backend.routers.tutor.get_study_stats", new=AsyncMock(return_value={})),
        patch("backend.routers.tutor.get_user_profile", new=AsyncMock(return_value={})),
        patch("backend.routers.tutor.get_language_profile", new=AsyncMock(return_value=lang)),
    )


class TestTutorChatEndpoint:
    def test_requires_auth(self, client):
        assert client.post("/api/tutor/chat", json=_chat_body()).status_code == 401

    def test_happy_path(self, client):
        p1, p2, p3, p4 = _patch_chat_repos()
        with p1, p2, p3, p4, patch(
            "backend.routers.tutor.tutor_chat",
            new=AsyncMock(return_value=("Let's drill -da/-de!", [])),
        ) as mock_chat:
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"reply": "Let's drill -da/-de!", "remembered": 0}
        assert mock_chat.await_args.args[0] == "tr"

    def test_persists_remembered_notes(self, client):
        p1, p2, p3, p4 = _patch_chat_repos()
        remembered = [{"scope": "global", "key": "native_language", "value": "English"}]
        with p1, p2, p3, p4, patch(
            "backend.routers.tutor.tutor_chat",
            new=AsyncMock(return_value=("ok", remembered)),
        ), patch(
            "backend.routers.tutor.upsert_user_profile", new=AsyncMock(),
        ) as mock_user, patch(
            "backend.routers.tutor.upsert_language_profile", new=AsyncMock(),
        ):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.json()["remembered"] == 1
        mock_user.assert_awaited_once()

    def test_unknown_language_422(self, client):
        resp = client.post(
            "/api/tutor/chat", json=_chat_body(language_code="zz"), headers=_auth_headers()
        )
        assert resp.status_code == 422

    def test_entitlement_enforced(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.has_tutor_entitlement", new=AsyncMock(return_value=False)):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 402

    def test_unconfigured_key_503(self, client):
        unconfigured = FakeSettings()
        unconfigured.anthropic_api_key = ""
        with patch("backend.routers.tutor.get_settings", return_value=unconfigured):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 503


class TestSessionEndEndpoint:
    def test_summarizes_and_persists(self, client):
        result = {
            "user_profile_updates": {"motivation": "moving to Istanbul"},
            "language_profile_updates": {"level": "A2"},
            "session_summary": "Practiced locative; shaky on harmony.",
        }
        with patch(
            "backend.routers.tutor.get_user_profile", new=AsyncMock(return_value={}),
        ), patch(
            "backend.routers.tutor.get_language_profile",
            new=AsyncMock(return_value={"profile": {}, "session_summary": ""}),
        ), patch(
            "backend.routers.tutor.summarize_session", new=AsyncMock(return_value=result),
        ), patch(
            "backend.routers.tutor.upsert_user_profile", new=AsyncMock(),
        ) as mock_user, patch(
            "backend.routers.tutor.upsert_language_profile", new=AsyncMock(),
        ) as mock_lang:
            resp = client.post(
                "/api/tutor/session/end", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"summarized": True}
        mock_user.assert_awaited_once()
        # session_summary + touch_session passed through to the language upsert
        assert mock_lang.await_args.kwargs["session_summary"].startswith("Practiced")
        assert mock_lang.await_args.kwargs["touch_session"] is True

    def test_requires_auth(self, client):
        assert client.post("/api/tutor/session/end", json=_chat_body()).status_code == 401


class TestTutorStatus:
    def test_reports_availability(self, client):
        resp = client.get(
            "/api/tutor/status",
            params={"language_id": TEST_LANGUAGE_ID, "language_code": "xh"},
            headers=_auth_headers(),
        )
        assert resp.json() == {"available": True, "entitled": True}

    def test_unknown_language_not_available(self, client):
        resp = client.get(
            "/api/tutor/status",
            params={"language_id": TEST_LANGUAGE_ID, "language_code": "zz"},
            headers=_auth_headers(),
        )
        assert resp.json() == {"available": False, "entitled": False}


# ---------------------------------------------------------------------------
# tutor_chat / summarize_session services (Anthropic client mocked)
# ---------------------------------------------------------------------------


class TestTutorChatService:
    @pytest.mark.asyncio
    async def test_no_tool_returns_reply_and_empty_remembered(self):
        from backend.services import tutor as tutor_mod

        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(
            return_value=_Resp([_TextBlock("Merhaba!")])
        )
        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            reply, remembered = await tutor_mod.tutor_chat(
                "tr", [{"role": "user", "content": "hi"}], []
            )
        assert reply == "Merhaba!"
        assert remembered == []
        kwargs = fake_client.messages.create.await_args.kwargs
        assert kwargs["model"] == "claude-opus-4-8"
        assert kwargs["thinking"] == {"type": "adaptive"}
        assert len(kwargs["system"]) == 2

    @pytest.mark.asyncio
    async def test_remember_tool_loop_collects_notes(self):
        from backend.services import tutor as tutor_mod

        first = _Resp([
            _ToolUseBlock("t1", "remember",
                          {"scope": "global", "key": "native_language", "value": "English"}),
        ])
        second = _Resp([_TextBlock("Got it — let's practice.")])
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(side_effect=[first, second])

        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            reply, remembered = await tutor_mod.tutor_chat(
                "tr", [{"role": "user", "content": "I'm a native English speaker"}], []
            )
        assert reply == "Got it — let's practice."
        assert remembered == [
            {"scope": "global", "key": "native_language", "value": "English"}
        ]
        assert fake_client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_empty_history_raises(self):
        from backend.services import tutor as tutor_mod

        with patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            with pytest.raises(ValueError):
                await tutor_mod.tutor_chat("tr", [{"role": "assistant", "content": "x"}], [])


class TestSummarizeSession:
    @pytest.mark.asyncio
    async def test_parses_structured_output(self):
        from backend.services import tutor as tutor_mod

        payload = {
            "user_profile_updates": {"motivation": "heritage"},
            "language_profile_updates": {"level": "B1"},
            "session_summary": "Reviewed noun classes.",
        }
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(
            return_value=_Resp([_TextBlock(json.dumps(payload))])
        )
        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            result = await tutor_mod.summarize_session(
                "sw",
                [{"role": "user", "content": "teach me noun classes"},
                 {"role": "assistant", "content": "ki-/vi-..."}],
            )
        assert result == payload
        assert fake_client.messages.create.await_args.kwargs["model"] == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_empty_history_returns_prior_summary(self):
        from backend.services import tutor as tutor_mod

        with patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            result = await tutor_mod.summarize_session(
                "sw", [], prior_summary="earlier summary"
            )
        assert result["session_summary"] == "earlier summary"

    @pytest.mark.asyncio
    async def test_bad_json_falls_back(self):
        from backend.services import tutor as tutor_mod

        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(
            return_value=_Resp([_TextBlock("not json")])
        )
        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            result = await tutor_mod.summarize_session(
                "sw", [{"role": "user", "content": "hi"}], prior_summary="keep me"
            )
        assert result["session_summary"] == "keep me"
        assert result["user_profile_updates"] == {}


# ---------------------------------------------------------------------------
# Dev mock mode — no API key, no Claude API calls
# ---------------------------------------------------------------------------


class _MockSettings(FakeSettings):
    anthropic_api_key = ""
    tutor_dev_mock = True


class TestDevMock:
    @pytest.mark.asyncio
    async def test_chat_makes_no_api_call(self):
        from backend.services import tutor as tutor_mod

        def boom(*a, **k):
            raise AssertionError("Anthropic client must not be built in mock mode")

        with patch.object(tutor_mod, "get_settings", return_value=_MockSettings()), \
             patch.object(tutor_mod, "AsyncAnthropic", side_effect=boom):
            reply, remembered = await tutor_mod.tutor_chat(
                "tr",
                [{"role": "user", "content": "hello"}],
                [{"word": "ev", "definition": "house"}],
            )
        assert "dev mock" in reply.lower()
        assert "ev" in reply  # drills the weak item
        assert remembered == []

    @pytest.mark.asyncio
    async def test_remember_command_parsed(self):
        from backend.services import tutor as tutor_mod

        with patch.object(tutor_mod, "get_settings", return_value=_MockSettings()), \
             patch.object(tutor_mod, "AsyncAnthropic", side_effect=AssertionError):
            _, remembered = await tutor_mod.tutor_chat(
                "tr",
                [{"role": "user", "content": "/remember global native_language English"}],
                [],
            )
        assert remembered == [
            {"scope": "global", "key": "native_language", "value": "English"}
        ]

    @pytest.mark.asyncio
    async def test_summary_is_deterministic(self):
        from backend.services import tutor as tutor_mod

        with patch.object(tutor_mod, "get_settings", return_value=_MockSettings()), \
             patch.object(tutor_mod, "AsyncAnthropic", side_effect=AssertionError):
            result = await tutor_mod.summarize_session(
                "tr",
                [{"role": "user", "content": "teach me the locative"},
                 {"role": "assistant", "content": "..."}],
            )
        assert "dev mock" in result["session_summary"]
        assert result["language_profile_updates"]["last_session_topics"]

    def test_endpoint_works_without_api_key(self, client):
        # Router + service both see mock settings; no key, real (mock) tutor runs.
        from backend.services import tutor as tutor_mod

        with patch("backend.routers.tutor.get_settings", return_value=_MockSettings()), \
             patch.object(tutor_mod, "get_settings", return_value=_MockSettings()), \
             patch.object(tutor_mod, "AsyncAnthropic", side_effect=AssertionError), \
             patch("backend.routers.tutor.get_weak_areas", new=AsyncMock(return_value=[])), \
             patch("backend.routers.tutor.get_study_stats", new=AsyncMock(return_value={})), \
             patch("backend.routers.tutor.get_user_profile", new=AsyncMock(return_value={})), \
             patch("backend.routers.tutor.get_language_profile",
                   new=AsyncMock(return_value={"profile": {}, "session_summary": ""})):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 200
        assert "dev mock" in resp.json()["reply"].lower()
