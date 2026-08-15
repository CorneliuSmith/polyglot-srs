"""Speak tests — the partner turn, the breakdown, and the endpoint flow.

The dev-mock path (tutor_dev_mock=True) runs a whole conversation with no
API key, same pattern as the tutor and reader tests.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.speak import (
    _fallback_groups,
    _mock_turn,
    _system_prompt,
    _usable_card,
    speak_turn,
    summarize_speak_session,
)

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"
TEST_SESSION_ID = "33333333-3333-3333-3333-333333333333"


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
    tutor_summary_model = "claude-haiku-4-5-20251001"
    tutor_model_low_resource = "claude-opus-4-8"
    tutor_dev_mock = True
    tutor_free_access = True
    tutor_free_monthly_messages = 20
    tutor_single_monthly_messages = 100
    tutor_all_monthly_messages = 300
    tutor_plus_monthly_messages = 1000


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _errors(*types: str) -> list[dict]:
    return [
        {"type": t, "learner_said": f"said {i}", "should_be": f"fix {i}",
         "note": "because"}
        for i, t in enumerate(types)
    ]


# ---------------------------------------------------------------------------
# The partner's brief
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_caps_the_partner_at_the_learners_level(self):
        prompt = _system_prompt("Spanish", "A2", None, None)
        # Without an explicit ceiling the model writes B2 prose at an A2
        # learner and the conversation becomes a listening test they fail.
        assert "A2" in prompt
        assert "short sentences" in prompt

    def test_replies_only_in_the_target_language(self):
        prompt = _system_prompt("Spanish", "B1", None, None)
        assert "Reply ONLY in Spanish" in prompt
        assert "Never translate yourself" in prompt

    def test_notes_are_written_in_the_support_language(self):
        prompt = _system_prompt("Spanish", "B1", None, "Russian")
        assert "Write the notes in Russian" in prompt

    def test_notes_default_to_english_with_no_support_language(self):
        assert "Write the notes in English" in _system_prompt(
            "Spanish", "B1", None, None
        )

    def test_a_topic_is_stated_and_its_absence_is_handled(self):
        assert "Ordering a coffee" in _system_prompt(
            "Spanish", "A2", "Ordering a coffee", None
        )
        assert "No topic was chosen" in _system_prompt(
            "Spanish", "A2", None, None
        )


# ---------------------------------------------------------------------------
# One turn
# ---------------------------------------------------------------------------


class TestSpeakTurn:
    async def test_dev_mock_returns_a_reply_and_errors(self):
        with patch("backend.services.speak.get_settings",
                   return_value=FakeSettings()):
            result, usage = await speak_turn(
                "Spanish", "A2", [], "Yo quiero un café",
            )
        assert result["reply"]
        assert result["errors"][0]["type"] == "pronoun"
        assert usage["input_tokens"] > 0

    async def test_a_clean_sentence_produces_no_errors(self):
        assert _mock_turn("Quiero un café")["errors"] == []

    async def test_history_becomes_alternating_messages(self):
        """The partner has to see the conversation, not just the last line."""
        captured = {}

        class FakeResponse:
            content = [type("B", (), {
                "type": "tool_use",
                "input": {"reply": "Vale.", "errors": []},
            })()]
            usage = None

        async def fake_create(**kwargs):
            captured.update(kwargs)
            return FakeResponse()

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.speak.get_settings", return_value=settings), \
             patch("backend.services.speak.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = fake_create
            await speak_turn(
                "Spanish", "A2",
                [{"learner_text": "Hola", "partner_text": "¡Hola!"}],
                "¿Qué tal?",
            )
        assert [m["role"] for m in captured["messages"]] == [
            "user", "assistant", "user"
        ]
        assert captured["messages"][-1]["content"] == "¿Qué tal?"

    async def test_an_empty_reply_is_rejected(self):
        """A blank reply would leave the learner staring at nothing with no
        way to tell whether the app broke or the partner had nothing to say."""

        class FakeResponse:
            content = [type("B", (), {
                "type": "tool_use", "input": {"reply": "   ", "errors": []},
            })()]
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.speak.get_settings", return_value=settings), \
             patch("backend.services.speak.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(
                return_value=FakeResponse()
            )
            with pytest.raises(ValueError, match="empty reply"):
                await speak_turn("Spanish", "A2", [], "Hola")

    async def test_half_formed_errors_are_dropped(self):
        """An error with no correction is not showable — it would arrive in
        the summary as an accusation with no answer."""

        class FakeResponse:
            content = [type("B", (), {
                "type": "tool_use",
                "input": {"reply": "Vale.", "errors": [
                    {"type": "gender", "learner_said": "el casa",
                     "should_be": "la casa", "note": "casa is feminine"},
                    {"type": "gender", "learner_said": "algo"},
                    {"type": "gender", "should_be": "otra cosa"},
                ]},
            })()]
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.speak.get_settings", return_value=settings), \
             patch("backend.services.speak.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(
                return_value=FakeResponse()
            )
            result, _ = await speak_turn("Spanish", "A2", [], "el casa")
        assert len(result["errors"]) == 1
        assert result["errors"][0]["should_be"] == "la casa"


# ---------------------------------------------------------------------------
# The breakdown
# ---------------------------------------------------------------------------


class TestSummary:
    async def test_a_clean_session_costs_nothing(self):
        """No errors means nothing to group — and so no model call at all.
        The None usage is what tells the router not to log a cost row."""
        with patch("backend.services.speak.get_settings",
                   return_value=FakeSettings()):
            summary, usage = await summarize_speak_session(
                "Spanish", [{"learner_text": "Hola", "partner_text": "¡Hola!"}],
                [],
            )
        assert usage is None
        assert summary["groups"] == []
        assert summary["stats"]["turns"] == 1

    def test_fallback_groups_by_type_most_frequent_first(self):
        groups = _fallback_groups(_errors("gender", "verb_form", "gender"))
        assert [g["label"] for g in groups] == ["Gender", "Verb form"]
        assert groups[0]["count"] == 2

    def test_fallback_groups_offer_no_card(self):
        """A per-turn error records the phrase that was wrong, not the
        sentence around it — there is nothing to blank out. Offering a
        broken card is worse than offering none."""
        assert all(
            g["card"] is None for g in _fallback_groups(_errors("gender"))
        )

    def test_a_card_whose_answer_is_missing_from_its_sentence_is_dropped(self):
        """The card endpoint blanks the answer out of the sentence and 422s
        when it isn't there. Checking here means the learner never sees an
        Add button that fails when they press it."""
        assert _usable_card({
            "sentence": "Quiero un café.", "answer": "hablo",
            "translation": "x",
        }) is None

    def test_a_usable_card_survives_and_is_trimmed(self):
        assert _usable_card({
            "sentence": "  Quiero un café.  ", "answer": " Quiero ",
            "translation": " I want a coffee. ",
        }) == {
            "sentence": "Quiero un café.", "answer": "Quiero",
            "translation": "I want a coffee.",
        }

    def test_a_card_missing_a_field_is_dropped(self):
        assert _usable_card({"sentence": "Quiero un café."}) is None
        assert _usable_card({"answer": "Quiero"}) is None
        assert _usable_card(None) is None

    async def test_an_unusable_card_from_the_model_becomes_none(self):
        """End to end: a model that returns a card the endpoint would reject
        must not put an Add button in front of the learner."""
        payload = {
            "groups": [{
                "label": "Pronouns", "note": "drop it", "examples": ["yo"],
                "count": 1,
                "card": {"sentence": "Quiero café.", "answer": "hablo",
                         "translation": "I want coffee."},
            }],
            "vocabulary": [],
        }

        class FakeResponse:
            content = [type("B", (), {
                "type": "text", "text": json.dumps(payload),
            })()]
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.speak.get_settings",
                   return_value=settings), \
             patch("backend.services.speak.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(
                return_value=FakeResponse()
            )
            summary, _ = await summarize_speak_session(
                "Spanish", [], _errors("pronoun"),
            )
        assert summary["groups"][0]["card"] is None
        assert summary["groups"][0]["label"] == "Pronouns"

    async def test_a_failed_summary_call_still_returns_a_breakdown(self):
        """Losing the summary is the one failure this feature cannot afford:
        it is the entire payoff for the conversation they just had."""
        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.speak.get_settings", return_value=settings), \
             patch("backend.services.speak.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(
                side_effect=RuntimeError("provider down")
            )
            summary, usage = await summarize_speak_session(
                "Spanish", [], _errors("gender", "gender"),
            )
        assert usage is None
        assert summary["groups"][0]["count"] == 2

    async def test_unparseable_json_falls_back_too(self):
        class FakeResponse:
            content = [type("B", (), {"type": "text", "text": "not json"})()]
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.speak.get_settings", return_value=settings), \
             patch("backend.services.speak.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(
                return_value=FakeResponse()
            )
            summary, _ = await summarize_speak_session(
                "Spanish", [], _errors("word_order"),
            )
        assert summary["groups"][0]["label"] == "Word order"

    async def test_stats_count_turns_and_errors_not_a_score(self):
        """The plan is explicit that there is no score — the moment there is
        a number, flow mode becomes a thing to game."""
        with patch("backend.services.speak.get_settings",
                   return_value=FakeSettings()):
            summary, _ = await summarize_speak_session(
                "Spanish",
                [{"learner_text": "a", "partner_text": "b"}] * 3,
                _errors("gender"),
            )
        assert summary["stats"] == {
            "turns": 3, "error_count": 1, "types": {"gender": 1}
        }
        assert "score" not in summary


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _conn() -> AsyncMock:
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock()

    async def fetchrow(sql, *args):
        # Only the course lookup gets a row; everything else (the tutor
        # override, the profile) answers None so the defaults apply.
        if "FROM languages" in sql:
            return {"name": "Spanish", "code": "es", "tutor_model": None}
        return None

    conn.fetchrow = AsyncMock(side_effect=fetchrow)
    return conn


@pytest.fixture()
def client():
    from contextlib import asynccontextmanager

    conn = _conn()

    @asynccontextmanager
    async def fake_conn(*args):
        yield conn

    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.tutor.get_settings", return_value=FakeSettings()), \
         patch("backend.services.generate.get_settings",
               return_value=FakeSettings()), \
         patch("backend.services.speak.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.speak.rls_connection", fake_conn), \
         patch("backend.services.allowance.get_settings",
               return_value=FakeSettings()), \
         patch("backend.services.allowance.rls_connection", fake_conn), \
         patch("backend.routers.tutor.rls_connection", fake_conn):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            c.fake_conn = conn
            yield c


def _live_session(**over) -> dict:
    return {
        "id": TEST_SESSION_ID, "language_id": TEST_LANGUAGE_ID,
        "mode": "flow", "topic": None, "started_at": None,
        "ended_at": None, "turn_count": 0, "summary": None, **over,
    }


class TestSpeakEndpoints:
    def test_requires_auth(self, client):
        assert client.post("/api/speak/start", json={
            "language_id": TEST_LANGUAGE_ID, "language_code": "es",
        }).status_code == 401

    def test_start_opens_a_session(self, client):
        with patch("backend.routers.speak.start_session",
                   new=AsyncMock(return_value=TEST_SESSION_ID)):
            resp = client.post("/api/speak/start", headers=_auth_headers(), json={
                "language_id": TEST_LANGUAGE_ID, "language_code": "es",
                "topic": "  Ordering a coffee  ",
            })
        assert resp.status_code == 200
        assert resp.json()["session_id"] == TEST_SESSION_ID
        assert resp.json()["topic"] == "Ordering a coffee"

    def test_an_unknown_mode_is_rejected(self, client):
        """Only the two real modes. A typo must not open a session that
        silently behaves like flow."""
        resp = client.post("/api/speak/start", headers=_auth_headers(), json={
            "language_id": TEST_LANGUAGE_ID, "language_code": "es",
            "mode": "gentle",
        })
        assert resp.status_code == 422

    def test_a_turn_never_returns_the_errors(self, client):
        """Flow mode's whole promise: feedback that does not interrupt. The
        client cannot leak what it is never sent."""
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=_live_session())), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=[])), \
             patch("backend.routers.speak.append_turn",
                   new=AsyncMock()) as appended:
            resp = client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Yo quiero un café",
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["reply"]
        assert "errors" not in body
        # …but they were recorded.
        assert appended.await_args.args[5][0]["type"] == "pronoun"

    def test_a_turn_on_an_unknown_session_is_404(self, client):
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=None)):
            resp = client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Hola",
            })
        assert resp.status_code == 404

    def test_a_turn_on_a_finished_session_is_rejected(self, client):
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=_live_session(ended_at="now"))):
            resp = client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Hola",
            })
        assert resp.status_code == 409

    def test_end_returns_the_breakdown(self, client):
        turns = [{
            "idx": 0, "learner_text": "Yo quiero café",
            "partner_text": "Claro.", "audio_ms": None,
            "errors": _errors("pronoun"),
        }]
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=_live_session())), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=turns)), \
             patch("backend.routers.speak.end_session", new=AsyncMock()):
            resp = client.post("/api/speak/end", headers=_auth_headers(),
                               json={"session_id": TEST_SESSION_ID})
        assert resp.status_code == 200
        assert resp.json()["summary"]["groups"]
        assert resp.json()["already_ended"] is False

    def test_ending_twice_returns_the_stored_breakdown(self, client):
        """A double tap on Done must not pay for a second pass over the same
        transcript — or, worse, show a different answer the second time."""
        stored = {"groups": [{"label": "Gender", "note": "", "examples": [],
                              "count": 1}], "vocabulary": [], "stats": {}}
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=_live_session(
                       ended_at="then", summary=stored))), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock()) as listed, \
             patch("backend.routers.speak.end_session", new=AsyncMock()) as ended:
            resp = client.post("/api/speak/end", headers=_auth_headers(),
                               json={"session_id": TEST_SESSION_ID})
        assert resp.json() == {"summary": stored, "already_ended": True}
        listed.assert_not_awaited()
        ended.assert_not_awaited()

    def test_an_interrupted_session_can_still_be_summarised(self, client):
        """People get interrupted. The summary is computed from whatever
        happened, including a session that never reached a natural end."""
        turns = [{"idx": 0, "learner_text": "Hola", "partner_text": "¡Hola!",
                  "audio_ms": None, "errors": []}]
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=_live_session())), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=turns)), \
             patch("backend.routers.speak.end_session", new=AsyncMock()):
            resp = client.post("/api/speak/end", headers=_auth_headers(),
                               json={"session_id": TEST_SESSION_ID})
        assert resp.status_code == 200
        assert resp.json()["summary"]["stats"]["turns"] == 1

    def test_status_hides_speak_when_the_migration_is_missing(self, client):
        """The tables land by hand, so the code ships first. An unapplied
        migration must cost the learner a tile, not a 500."""
        with patch("backend.routers.speak.tables_ready",
                   new=AsyncMock(return_value=False)):
            resp = client.get(
                f"/api/speak/status?language_id={TEST_LANGUAGE_ID}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {
            "available": False, "allowance": None, "sessions": []
        }

    def test_start_is_503_when_the_migration_is_missing(self, client):
        from backend.repositories.speak import SpeakUnavailableError

        with patch("backend.routers.speak.start_session",
                   new=AsyncMock(side_effect=SpeakUnavailableError)):
            resp = client.post("/api/speak/start", headers=_auth_headers(), json={
                "language_id": TEST_LANGUAGE_ID, "language_code": "es",
            })
        assert resp.status_code == 503


class TestCoachMode:
    """One correction per turn, then the conversation moves on.

    The plan is emphatic that this is never a list: a learner corrected
    three times in a turn stops talking. The other errors are not lost —
    every one is stored and they all reach the summary.
    """

    def _live(self, **over):
        return _live_session(mode="coach", **over)

    def test_coach_returns_exactly_one_correction(self, client):
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=self._live())), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=[])), \
             patch("backend.routers.speak.append_turn", new=AsyncMock()):
            resp = client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Yo quiero un café",
            })
        body = resp.json()
        assert body["correction"]["type"] == "pronoun"
        assert not isinstance(body["correction"], list)

    def test_every_error_is_still_stored_for_the_summary(self, client):
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=self._live())), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=[])), \
             patch("backend.routers.speak.append_turn",
                   new=AsyncMock()) as appended:
            client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Yo quiero un café",
            })
        assert appended.await_args.args[5]  # the full list, not just the one

    def test_a_clean_turn_says_so_rather_than_omitting_the_key(self, client):
        # The key is present-but-null so the client can tell "nothing wrong"
        # apart from "this mode doesn't correct".
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=self._live())), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=[])), \
             patch("backend.routers.speak.append_turn", new=AsyncMock()):
            resp = client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Quiero un café",
            })
        assert "correction" in resp.json()
        assert resp.json()["correction"] is None

    def test_flow_sends_no_correction_key_at_all(self, client):
        with patch("backend.routers.speak.get_session",
                   new=AsyncMock(return_value=_live_session(mode="flow"))), \
             patch("backend.routers.speak.list_turns",
                   new=AsyncMock(return_value=[])), \
             patch("backend.routers.speak.append_turn", new=AsyncMock()):
            resp = client.post("/api/speak/turn", headers=_auth_headers(), json={
                "session_id": TEST_SESSION_ID, "text": "Yo quiero un café",
            })
        assert "correction" not in resp.json()

    def test_coach_can_be_started(self, client):
        with patch("backend.routers.speak.start_session",
                   new=AsyncMock(return_value=TEST_SESSION_ID)):
            resp = client.post("/api/speak/start", headers=_auth_headers(), json={
                "language_id": TEST_LANGUAGE_ID, "language_code": "es",
                "mode": "coach",
            })
        assert resp.status_code == 200
        assert resp.json()["mode"] == "coach"
