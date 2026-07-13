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
    tutor_free_monthly_messages = 20
    tutor_plus_daily_messages = 100


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


class _Usage:
    def __init__(self, input_tokens=0, output_tokens=0,
                 cache_creation_input_tokens=0, cache_read_input_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens
        self.cache_read_input_tokens = cache_read_input_tokens


class _Resp:
    def __init__(self, content, usage=None):
        self.content = content
        self.usage = usage


# A plausible per-call usage for tests that just need SOME token counts.
_SOME_USAGE = {
    "input_tokens": 120, "output_tokens": 45,
    "cache_write_tokens": 0, "cache_read_tokens": 900,
}


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
    LANGS = ("ru", "ar", "en", "sw", "tr", "yo", "ha", "xh",
             "es", "it", "fr", "de", "ca", "mi", "pt", "el", "ro")

    def test_all_languages_have_briefs(self):
        for code in self.LANGS:
            blocks = build_system_blocks(code, [])
            assert len(blocks) == 2
            assert "tutor" in blocks[0]["text"].lower()

    def test_briefs_mention_register(self):
        for code in self.LANGS:
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


class TestTutorSkills:
    """WP15b: per-language skill bundles (SKILL.md core + on-demand
    REFERENCE.md/ERRORS.md) replace the inline briefs dict."""

    def test_every_language_with_grammar_has_a_tutor(self):
        # The tutor roster must track the curriculum: a language we teach
        # is a language we tutor. pt/el/ro once had paths but no tutor.
        from pathlib import Path

        from backend.services.tutor import available_tutors

        grammar_langs = {
            p.name.removesuffix("_grammar.json")
            for p in Path("data/grammar").glob("*_grammar.json")
        }
        assert grammar_langs <= available_tutors(), (
            grammar_langs - available_tutors()
        )

    def test_bundles_are_complete_and_bounded(self):
        from backend.services.tutor import (
            SKILLS_DIR,
            available_tutors,
            load_reference,
        )

        for code in sorted(available_tutors()):
            for name in ("SKILL.md", "REFERENCE.md", "ERRORS.md"):
                assert (SKILLS_DIR / code / name).is_file(), f"{code}/{name}"
            # SKILL.md rides in EVERY prompt — keep it small (context rot
            # control); the deep files load on demand and stay bounded too.
            skill = (SKILLS_DIR / code / "SKILL.md").read_text(encoding="utf-8")
            assert len(skill) < 2500, f"{code}: SKILL.md too large"
            for topic in ("reference", "errors"):
                text = load_reference(code, topic)
                assert text and len(text) < 12000, f"{code}/{topic}"

    def test_reference_uses_curriculum_point_titles(self):
        import json

        from backend.services.tutor import load_reference

        ref = load_reference("ru", "reference")
        data = json.load(open("data/grammar/ru_grammar.json"))
        for point in data["points"][:5]:
            assert point["title"] in ref

    def test_charter_teaches_the_consult_tool(self):
        blocks = build_system_blocks("pt", [])
        assert "consult_reference" in blocks[0]["text"]

    def test_unknown_topic_returns_none(self):
        from backend.services.tutor import load_reference

        assert load_reference("ru", "everything") is None
        assert load_reference("zz", "reference") is None


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
            new=AsyncMock(return_value=("Let's drill -da/-de!", [], _SOME_USAGE)),
        ) as mock_chat:
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"] == "Let's drill -da/-de!"
        assert body["remembered"] == 0
        assert body["allowance"]["unlimited"] is True  # operator free-access mode
        assert mock_chat.await_args.args[0] == "tr"

    def test_persists_remembered_notes(self, client):
        p1, p2, p3, p4 = _patch_chat_repos()
        remembered = [{"scope": "global", "key": "native_language", "value": "English"}]
        with p1, p2, p3, p4, patch(
            "backend.routers.tutor.tutor_chat",
            new=AsyncMock(return_value=("ok", remembered, _SOME_USAGE)),
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

    def test_free_tier_chats_within_monthly_allowance(self, client):
        """No subscription needed to TRY the tutor — free accounts get a
        monthly message allowance, and the reply reports the meter."""
        paid = FakeSettings()
        paid.tutor_free_access = False
        p1, p2, p3, p4 = _patch_chat_repos()
        with p1, p2, p3, p4, \
             patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.has_tutor_entitlement",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=5)), \
             patch("backend.routers.tutor.log_tutor_usage",
                   new=AsyncMock()) as mock_log, \
             patch("backend.routers.tutor.tutor_chat",
                   new=AsyncMock(return_value=("hi", [], _SOME_USAGE))):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 200
        allowance = resp.json()["allowance"]
        assert allowance["tier"] == "free"
        assert allowance["limit"] == 20
        assert allowance["used"] == 6          # the 5 before + this one
        assert allowance["remaining"] == 14
        mock_log.assert_awaited_once()         # the message was recorded
        # WP9b: the turn's token counts reached the usage log
        assert mock_log.await_args.kwargs["usage"] == _SOME_USAGE

    def test_free_tier_blocked_at_monthly_limit(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.has_tutor_entitlement",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=20)):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert detail["code"] == "allowance_exhausted"
        assert detail["tier"] == "free"
        assert detail["limit"] == 20
        assert detail["resets_at"]  # the UI can say exactly when

    def test_plus_tier_blocked_at_daily_fair_use_cap(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.has_tutor_entitlement",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=100)):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert detail["code"] == "allowance_exhausted"
        assert detail["tier"] == "plus"        # not an upsell — resets tomorrow

    def test_blocked_account_403_even_in_free_access_mode(self, client):
        # The admin block wins over EVERYTHING, including the operator's
        # TUTOR_FREE_ACCESS demo bypass (FakeSettings has it on).
        with patch("backend.routers.tutor.get_tutor_access",
                   new=AsyncMock(return_value={"access": "blocked", "daily_cap": None})):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "tutor_blocked"

    def test_granted_account_chats_under_its_cap(self, client):
        # "Let a friend try the tutor, 10 messages a day": no entitlement,
        # free-access off, but the admin grant carries its own allowance.
        paid = FakeSettings()
        paid.tutor_free_access = False
        p1, p2, p3, p4 = _patch_chat_repos()
        with p1, p2, p3, p4, \
             patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.get_tutor_access",
                   new=AsyncMock(return_value={"access": "enabled", "daily_cap": 10})), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=4)), \
             patch("backend.routers.tutor.log_tutor_usage", new=AsyncMock()), \
             patch("backend.routers.tutor.tutor_chat",
                   new=AsyncMock(return_value=("hi", [], _SOME_USAGE))):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 200
        allowance = resp.json()["allowance"]
        assert allowance["tier"] == "granted"
        assert allowance["limit"] == 10
        assert allowance["remaining"] == 5     # 4 before + this one

    def test_granted_account_blocked_at_its_cap(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.get_tutor_access",
                   new=AsyncMock(return_value={"access": "enabled", "daily_cap": 10})), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=10)):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert detail["code"] == "allowance_exhausted"
        assert detail["tier"] == "granted"
        assert detail["limit"] == 10

    def test_unconfigured_key_503(self, client):
        unconfigured = FakeSettings()
        unconfigured.anthropic_api_key = ""
        with patch("backend.routers.tutor.get_settings", return_value=unconfigured):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 503

    def test_rate_limited_429(self, client):
        from backend.services.rate_limit import tutor_chat_limiter
        with patch.object(tutor_chat_limiter, "allow", new=AsyncMock(return_value=False)):
            resp = client.post("/api/tutor/chat", json=_chat_body(), headers=_auth_headers())
        assert resp.status_code == 429


class TestTutorChatStream:
    def test_streams_deltas_then_done_with_allowance(self, client):
        """Dev-mock mode drives the REAL streaming generator end to end:
        SSE delta chunks reassemble into the reply, and the final done
        event carries the updated allowance after persistence."""
        import json as _json

        mock_settings = FakeSettings()
        mock_settings.tutor_dev_mock = True
        p1, p2, p3, p4 = _patch_chat_repos()
        with p1, p2, p3, p4, \
             patch("backend.routers.tutor.get_settings", return_value=mock_settings), \
             patch("backend.services.tutor.get_settings", return_value=mock_settings), \
             patch("backend.routers.tutor.log_tutor_usage", new=AsyncMock()) as mock_log:
            resp = client.post(
                "/api/tutor/chat/stream", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = [
            _json.loads(line[len("data: "):])
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        deltas = [e for e in events if e["type"] == "delta"]
        done = [e for e in events if e["type"] == "done"]
        assert len(deltas) >= 2          # the reply arrived in chunks
        assert len(done) == 1
        assert "".join(d["text"] for d in deltas) == done[0]["reply"]
        assert done[0]["allowance"]["unlimited"] is True
        assert "usage" not in done[0]    # operator data never reaches clients
        mock_log.assert_awaited_once()   # the message was recorded
        # WP9b: dev-mock produces deterministic non-zero token counts
        logged_usage = mock_log.await_args.kwargs["usage"]
        assert logged_usage["input_tokens"] > 0
        assert logged_usage["output_tokens"] > 0

    def test_stream_blocked_when_allowance_exhausted(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.has_tutor_entitlement",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=20)):
            resp = client.post(
                "/api/tutor/chat/stream", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 402
        assert resp.json()["detail"]["code"] == "allowance_exhausted"


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

    def test_summarizer_cost_logged_as_summary_kind(self, client):
        """WP9b: the summarizer's tokens land in tutor_usage as kind='summary'
        (cost-only — the allowance counter filters those rows out)."""
        result = {
            "user_profile_updates": {},
            "language_profile_updates": {},
            "session_summary": "Practiced locative.",
            "usage": _SOME_USAGE,
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
        ), patch(
            "backend.routers.tutor.upsert_language_profile", new=AsyncMock(),
        ), patch(
            "backend.routers.tutor.log_tutor_usage", new=AsyncMock(),
        ) as mock_log:
            resp = client.post(
                "/api/tutor/session/end", json=_chat_body(), headers=_auth_headers()
            )
        assert resp.status_code == 200
        mock_log.assert_awaited_once()
        assert mock_log.await_args.kwargs["kind"] == "summary"
        assert mock_log.await_args.kwargs["usage"] == _SOME_USAGE
        # billed to the summarizer model, not the chat model
        assert mock_log.await_args.args[3] == "claude-sonnet-4-6"


class TestTutorStatus:
    def test_reports_availability_with_allowance(self, client):
        resp = client.get(
            "/api/tutor/status",
            params={"language_id": TEST_LANGUAGE_ID, "language_code": "xh"},
            headers=_auth_headers(),
        )
        body = resp.json()
        assert body["available"] is True
        assert body["entitled"] is True
        assert body["allowance"]["unlimited"] is True  # operator mode

    def test_free_tier_status_shows_meter(self, client):
        paid = FakeSettings()
        paid.tutor_free_access = False
        with patch("backend.routers.tutor.get_settings", return_value=paid), \
             patch("backend.routers.tutor.has_tutor_entitlement",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.tutor.count_tutor_messages",
                   new=AsyncMock(return_value=7)):
            resp = client.get(
                "/api/tutor/status",
                params={"language_id": TEST_LANGUAGE_ID, "language_code": "xh"},
                headers=_auth_headers(),
            )
        body = resp.json()
        assert body["entitled"] is False
        assert body["allowance"] == {
            "tier": "free", "unlimited": False, "entitled": False,
            "limit": 20, "used": 7, "remaining": 13,
            "resets_at": body["allowance"]["resets_at"],
        }

    def test_unknown_language_not_available(self, client):
        resp = client.get(
            "/api/tutor/status",
            params={"language_id": TEST_LANGUAGE_ID, "language_code": "zz"},
            headers=_auth_headers(),
        )
        assert resp.json() == {"available": False, "entitled": False, "allowance": None}


# ---------------------------------------------------------------------------
# tutor_chat / summarize_session services (Anthropic client mocked)
# ---------------------------------------------------------------------------


class TestTutorChatService:
    @pytest.mark.asyncio
    async def test_no_tool_returns_reply_and_empty_remembered(self):
        from backend.services import tutor as tutor_mod

        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(
            return_value=_Resp(
                [_TextBlock("Merhaba!")],
                usage=_Usage(input_tokens=100, output_tokens=20,
                             cache_read_input_tokens=800),
            )
        )
        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            reply, remembered, usage = await tutor_mod.tutor_chat(
                "tr", [{"role": "user", "content": "hi"}], []
            )
        assert reply == "Merhaba!"
        assert remembered == []
        assert usage == {
            "input_tokens": 100, "output_tokens": 20,
            "cache_write_tokens": 0, "cache_read_tokens": 800,
        }
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
        ], usage=_Usage(input_tokens=100, output_tokens=30))
        second = _Resp(
            [_TextBlock("Got it — let's practice.")],
            usage=_Usage(input_tokens=150, output_tokens=40),
        )
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(side_effect=[first, second])

        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            reply, remembered, usage = await tutor_mod.tutor_chat(
                "tr", [{"role": "user", "content": "I'm a native English speaker"}], []
            )
        assert reply == "Got it — let's practice."
        assert remembered == [
            {"scope": "global", "key": "native_language", "value": "English"}
        ]
        assert fake_client.messages.create.await_count == 2
        # WP9b: the turn total sums BOTH tool-loop calls
        assert usage["input_tokens"] == 250
        assert usage["output_tokens"] == 70

    @pytest.mark.asyncio
    async def test_consult_reference_tool_loop(self):
        # The tutor asks for the curriculum reference mid-turn; the loop
        # answers from the skill bundle on disk and the model continues.
        from backend.services import tutor as tutor_mod

        first = _Resp([
            _ToolUseBlock("t1", "consult_reference", {"topic": "reference"}),
        ], usage=_Usage(input_tokens=100, output_tokens=10))
        second = _Resp(
            [_TextBlock("Next up in your path: the locative case.")],
            usage=_Usage(input_tokens=200, output_tokens=40),
        )
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(side_effect=[first, second])

        with patch.object(tutor_mod, "AsyncAnthropic", return_value=fake_client), \
             patch.object(tutor_mod, "get_settings", return_value=FakeSettings()):
            reply, remembered, usage = await tutor_mod.tutor_chat(
                "tr", [{"role": "user", "content": "what should I learn next?"}], []
            )
        assert reply == "Next up in your path: the locative case."
        assert remembered == []  # consulting is not a memory write
        # The second call carried the reference text as the tool result.
        second_msgs = fake_client.messages.create.await_args_list[1].kwargs["messages"]
        tool_result = second_msgs[-1]["content"][0]
        assert tool_result["tool_use_id"] == "t1"
        assert "Curriculum reference" in tool_result["content"]
        # Both tools offered on tool-loop calls.
        tools = fake_client.messages.create.await_args_list[0].kwargs["tools"]
        assert {t["name"] for t in tools} == {"remember", "consult_reference"}

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
        usage = result.pop("usage")  # WP9b: summarizer cost rides along
        assert set(usage) == {"input_tokens", "output_tokens",
                              "cache_write_tokens", "cache_read_tokens"}
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
        assert "usage" not in result  # no model call happened — nothing to bill

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
            reply, remembered, usage = await tutor_mod.tutor_chat(
                "tr",
                [{"role": "user", "content": "hello"}],
                [{"word": "ev", "definition": "house"}],
            )
        assert "dev mock" in reply.lower()
        assert "ev" in reply  # drills the weak item
        assert remembered == []
        assert usage["output_tokens"] > 0  # deterministic pseudo-usage

    @pytest.mark.asyncio
    async def test_remember_command_parsed(self):
        from backend.services import tutor as tutor_mod

        with patch.object(tutor_mod, "get_settings", return_value=_MockSettings()), \
             patch.object(tutor_mod, "AsyncAnthropic", side_effect=AssertionError):
            _, remembered, _ = await tutor_mod.tutor_chat(
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
