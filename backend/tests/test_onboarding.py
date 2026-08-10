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


NEVER_PLACED = {
    "attempts": 0, "has_placed": False,
    "last_level": None, "last_taken_at": None, "history": [],
}


@pytest.fixture()
def client():
    # Placement attempt bookkeeping is stubbed to "never placed" by default —
    # every endpoint here reads it, and the tests that care about it patch
    # over these inside the test body.
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.onboarding.placement_history",
               new=AsyncMock(return_value=dict(NEVER_PLACED))), \
         patch("backend.routers.onboarding.record_placement_attempt",
               new=AsyncMock()), \
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

    def test_set_level_reseats_decks(self, client):
        # Beta report (Kate): misplaced at A1, no way out. The level is
        # changeable any time via PUT /level with set semantics.
        with patch("backend.routers.onboarding.set_learner_level",
                   new=AsyncMock(return_value={"level": "B1",
                                               "subscribed": 4,
                                               "unsubscribed": 0})) as mock_set:
            resp = client.put("/api/onboarding/level", json={
                "language_id": LANG, "level": "B1",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"level": "B1", "subscribed": 4, "unsubscribed": 0}
        assert mock_set.await_args.args[3] == "B1"

    def test_set_level_rejects_bad_level(self, client):
        resp = client.put("/api/onboarding/level", json={
            "language_id": LANG, "level": "native",
        }, headers=_auth_headers())
        assert resp.status_code == 422

    def test_set_level_requires_auth(self, client):
        assert client.put("/api/onboarding/level", json={
            "language_id": LANG, "level": "B1",
        }).status_code == 401


class _WritingSettings:
    """Router-level settings for the writing endpoints."""
    def __init__(self, dev_mock=False, key=""):
        self.tutor_dev_mock = dev_mock
        self.anthropic_api_key = key


class TestWritingSample:
    """Owner token guard: the write-something baseline only spends a model
    call for entitled accounts (paid/granted) — or dev-mock testing."""

    def test_availability_true_in_dev_mock(self, client):
        with patch("backend.routers.onboarding.get_settings",
                   return_value=_WritingSettings(dev_mock=True)):
            resp = client.get(
                "/api/onboarding/writing-sample/availability",
                params={"language_id": LANG}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["available"] is True

    def test_availability_false_without_entitlement(self, client):
        with patch("backend.routers.onboarding.get_settings",
                   return_value=_WritingSettings(key="sk-real")), \
             patch("backend.routers.onboarding.has_tutor_entitlement",
                   new=AsyncMock(return_value=False)):
            resp = client.get(
                "/api/onboarding/writing-sample/availability",
                params={"language_id": LANG}, headers=_auth_headers(),
            )
        assert resp.json()["available"] is False

    def test_post_rejected_when_unavailable(self, client):
        with patch("backend.routers.onboarding.get_settings",
                   return_value=_WritingSettings(key="sk-real")), \
             patch("backend.routers.onboarding.has_tutor_entitlement",
                   new=AsyncMock(return_value=False)):
            resp = client.post("/api/onboarding/writing-sample", json={
                "language_id": LANG, "language_code": "es",
                "text": "Hola, me llamo Kate.",
            }, headers=_auth_headers())
        assert resp.status_code == 403

    def test_post_assesses_and_primes_the_profile(self, client):
        upserts = {}

        async def fake_upsert(conn, user_id, language_id, profile):
            upserts["profile"] = profile

        with patch("backend.routers.onboarding.get_settings",
                   return_value=_WritingSettings(dev_mock=True)), \
             patch("backend.services.writing_baseline.get_settings",
                   return_value=_WritingSettings(dev_mock=True)), \
             patch("backend.routers.onboarding.get_language_profile",
                   new=AsyncMock(return_value={"profile": {}, "session_summary": ""})), \
             patch("backend.routers.onboarding.upsert_language_profile",
                   new=fake_upsert), \
             patch("backend.routers.onboarding.log_tutor_usage",
                   new=AsyncMock()) as mock_usage:
            # DB conn is an AsyncMock: language-name lookup returns a Mock,
            # which is fine (only used in the judge prompt / not in dev-mock).
            resp = client.post("/api/onboarding/writing-sample", json={
                "language_id": LANG, "language_code": "es",
                "text": "Ayer fui al mercado y compré mucha fruta fresca",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["level"] == "A2"  # dev-mock band for a mid-length sample
        # The result primed the tutor language profile for the assessment
        # tiers: baseline level + seeded Active Focus.
        primed = upserts["profile"]
        assert primed["_writing_baseline"]["level"] == "A2"
        assert primed["_active_focus"][0]["structure"]
        mock_usage.assert_awaited_once()
        assert mock_usage.await_args.kwargs["kind"] == "writing_baseline"

    def test_post_never_overwrites_tutor_set_focus(self, client):
        existing = {"_active_focus": [{"structure": "ser vs estar"}]}
        upserts = {}

        async def fake_upsert(conn, user_id, language_id, profile):
            upserts["profile"] = profile

        with patch("backend.routers.onboarding.get_settings",
                   return_value=_WritingSettings(dev_mock=True)), \
             patch("backend.services.writing_baseline.get_settings",
                   return_value=_WritingSettings(dev_mock=True)), \
             patch("backend.routers.onboarding.get_language_profile",
                   new=AsyncMock(return_value={"profile": existing, "session_summary": ""})), \
             patch("backend.routers.onboarding.upsert_language_profile",
                   new=fake_upsert), \
             patch("backend.routers.onboarding.log_tutor_usage", new=AsyncMock()):
            resp = client.post("/api/onboarding/writing-sample", json={
                "language_id": LANG, "language_code": "es", "text": "Hola",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        assert upserts["profile"]["_active_focus"] == [{"structure": "ser vs estar"}]


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


class TestPlacementAttempts:
    """Owner: offer the test the FIRST time in a language, allow a retake any
    time, and vary the retake so it measures improvement rather than memory."""

    def test_history_endpoint_reports_never_placed(self, client):
        resp = client.get(
            f"/api/onboarding/placement/{LANG}/history", headers=_auth_headers()
        )
        assert resp.status_code == 200
        assert resp.json() == NEVER_PLACED

    def test_history_requires_auth(self, client):
        assert client.get(
            f"/api/onboarding/placement/{LANG}/history"
        ).status_code == 401

    def test_first_placement_samples_variant_zero(self, client):
        sampler = AsyncMock(return_value=_items(6))
        with patch("backend.routers.onboarding.sample_placement_items", new=sampler):
            resp = client.get(
                f"/api/onboarding/placement/{LANG}", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert sampler.await_args.kwargs["variant"] == 0
        assert resp.json()["attempt"] == 1

    def test_retake_asks_a_different_variant(self, client):
        placed = {**NEVER_PLACED, "attempts": 2, "has_placed": True,
                  "last_level": "A2", "last_taken_at": "2026-03-01T00:00:00+00:00"}
        sampler = AsyncMock(return_value=_items(6))
        with patch("backend.routers.onboarding.placement_history",
                   new=AsyncMock(return_value=placed)), \
             patch("backend.routers.onboarding.sample_placement_items", new=sampler):
            resp = client.get(
                f"/api/onboarding/placement/{LANG}", headers=_auth_headers()
            )
        body = resp.json()
        # Two attempts already done -> the third asks the third window.
        assert sampler.await_args.kwargs["variant"] == 2
        assert body["attempt"] == 3
        assert body["previous_level"] == "A2"

    def test_finishing_the_adaptive_test_records_an_attempt(self, client):
        recorder = AsyncMock()
        answers = {"a1": {"answer": "uno", "level": "A1"}}
        pool = [{"id": "a1", "kind": "vocabulary", "level": "A1",
                 "prompt": "one", "translation": None}] + _items(5)
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(AnswerResult.CORRECT, None))), \
             patch("backend.routers.onboarding.adaptive_next",
                   return_value=None), \
             patch("backend.routers.onboarding.record_placement_attempt",
                   new=recorder):
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [{"id": "a1", "input": "uno"}],
            }, headers=_auth_headers())
        assert resp.status_code == 200 and resp.json()["done"] is True
        recorder.assert_awaited_once()
        assert recorder.await_args.kwargs["items_asked"] == 1

    def test_mid_test_rounds_record_nothing(self, client):
        """Recording per ROUND would bump the variant mid-run and re-sample a
        different pool under the learner's feet."""
        recorder = AsyncMock()
        pool = _items(12)
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value={})), \
             patch("backend.routers.onboarding.record_placement_attempt",
                   new=recorder):
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [],
            }, headers=_auth_headers())
        assert resp.status_code == 200 and resp.json()["done"] is False
        recorder.assert_not_awaited()

    def test_scoring_the_batch_test_records_an_attempt(self, client):
        recorder = AsyncMock()
        answers = {"a1": {"answer": "uno", "level": "A1"}}
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(AnswerResult.CORRECT, None))), \
             patch("backend.routers.onboarding.record_placement_attempt",
                   new=recorder):
            resp = client.post(f"/api/onboarding/placement/{LANG}", json={
                "answers": [{"id": "a1", "input": "uno"}],
            }, headers=_auth_headers())
        assert resp.status_code == 200
        recorder.assert_awaited_once()
        assert recorder.await_args.kwargs["estimated_level"] == "A1"


class TestPlacementEvidenceCapture:
    """The verdict was never the useful half — what they got WRONG is what
    the Gym/Tutor/Reader can act on, so it has to survive scoring."""

    def test_adaptive_run_records_the_tally_and_the_misses(self, client):
        recorder = AsyncMock()
        pool = [
            {"id": "g1", "kind": "grammar", "level": "B1",
             "prompt": "___", "translation": None},
            {"id": "v1", "kind": "vocabulary", "level": "A1",
             "prompt": "one", "translation": None},
        ] + _items(4)
        answers = {
            "g1": {"answer": "haya", "level": "B1", "kind": "grammar"},
            "v1": {"answer": "uno", "level": "A1", "kind": "vocabulary"},
        }

        async def grade(code, given, expected, ctx):
            ok = given == expected
            return (AnswerResult.CORRECT if ok else AnswerResult.WRONG, None)

        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(side_effect=grade)), \
             patch("backend.routers.onboarding.adaptive_next", return_value=None), \
             patch("backend.routers.onboarding.record_placement_attempt",
                   new=recorder):
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [
                    {"id": "v1", "input": "uno"},      # right
                    {"id": "g1", "input": "hubiera"},  # wrong
                ],
            }, headers=_auth_headers())

        assert resp.status_code == 200
        kwargs = recorder.await_args.kwargs
        assert kwargs["per_level"] == {
            "A1": {"correct": 1, "total": 1},
            "B1": {"correct": 0, "total": 1},
        }
        # A missed DRILL and a missed WORD land in different buckets — they
        # feed different halves of the insight.
        assert kwargs["missed_grammar_ids"] == ["g1"]
        assert kwargs["missed_vocabulary_ids"] == []

    def test_batch_scoring_records_the_same_evidence(self, client):
        recorder = AsyncMock()
        answers = {
            "v1": {"answer": "uno", "level": "A1", "kind": "vocabulary"},
        }
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(AnswerResult.WRONG, None))), \
             patch("backend.routers.onboarding.record_placement_attempt",
                   new=recorder):
            resp = client.post(f"/api/onboarding/placement/{LANG}", json={
                "answers": [{"id": "v1", "input": "dos"}],
            }, headers=_auth_headers())
        assert resp.status_code == 200
        kwargs = recorder.await_args.kwargs
        assert kwargs["missed_vocabulary_ids"] == ["v1"]
        assert kwargs["per_level"] == {"A1": {"correct": 0, "total": 1}}


class TestPlacementSynonyms:
    """Owner: "I am worrying that you are just using vocab with synonyms
    being blocked." The shipped seeds populate vocabulary.alternatives for
    almost nothing, so a definition prompt accepted exactly one headword —
    and since the staircase steps DOWN on a miss, one blocked synonym could
    cost a whole band. A failed vocabulary answer is now looked up in the
    course's own word list and counts when its gloss shares a sense."""

    def _run(self, client, glosses, typed="andar"):
        pool = [{"id": "a1", "kind": "vocabulary", "level": "B1",
                 "prompt": "to walk", "translation": None}] + _items(11)
        answers = {"a1": {"answer": "caminar", "level": "B1",
                          "kind": "vocabulary", "alternatives": [],
                          "prompt": "to walk"}}
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.lookup_word_glosses",
                   new=AsyncMock(return_value=glosses)), \
             patch("backend.routers.onboarding.adaptive_next",
                   return_value=None), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(AnswerResult.WRONG, None))):
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [{"id": "a1", "input": typed}],
            }, headers=_auth_headers())
        assert resp.status_code == 200
        return resp.json()

    def test_synonym_is_accepted_and_labelled(self, client):
        # andar is a real Spanish word meaning "to walk" — the seeds just
        # never recorded it as an alternative of caminar.
        body = self._run(client, {"andar": "to walk; to go about"})
        item = next(b for b in body["breakdown"] if b["prompt"] == "to walk")
        assert item["correct"] is True
        assert item["verdict"] == "synonym"
        assert item["accepted_as"] == "to walk; to go about"

    def test_a_merely_related_word_is_still_wrong(self, client):
        # ir ("to go") is not an answer to "to walk" — the rescue must not
        # turn the test into a participation trophy.
        body = self._run(client, {"ir": "to go"}, typed="ir")
        item = next(b for b in body["breakdown"] if b["prompt"] == "to walk")
        assert item["correct"] is False
        assert item["verdict"] == "wrong"

    def test_a_word_that_is_not_in_the_course_is_still_wrong(self, client):
        body = self._run(client, {}, typed="qwerty")
        item = next(b for b in body["breakdown"] if b["prompt"] == "to walk")
        assert item["correct"] is False


class TestPlacementTransparency:
    """Owner: "I want users to be able to understand why they received a
    rating" — the verdict now ships with the evidence behind it."""

    def _finish(self, client, result):
        answers = {"a1": {"answer": "uno", "level": "A1",
                          "kind": "vocabulary", "alternatives": [],
                          "prompt": "one"}}
        pool = [{"id": "a1", "kind": "vocabulary", "level": "A1",
                 "prompt": "one", "translation": None}]
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool * 4)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.adaptive_next",
                   return_value=None), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=AsyncMock(return_value=(result, None))):
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [{"id": "a1", "input": "uno"}],
            }, headers=_auth_headers())
        assert resp.status_code == 200
        return resp.json()

    def test_the_result_carries_every_question_and_the_pass_mark(self, client):
        body = self._finish(client, AnswerResult.CORRECT)
        assert body["done"] is True
        assert body["threshold"] == 0.6
        item = body["breakdown"][0]
        assert item == {
            "kind": "vocabulary", "level": "A1", "prompt": "one",
            "typed": "uno", "expected": "uno", "correct": True,
            "verdict": "correct", "accepted_as": None,
        }

    def test_an_accent_slip_reads_as_a_typo_not_a_failure(self, client):
        body = self._finish(client, AnswerResult.CORRECT_SLOPPY)
        assert body["breakdown"][0]["verdict"] == "typo"
        assert body["breakdown"][0]["correct"] is True

    def test_a_skipped_question_is_not_shown_as_a_wrong_answer(self, client):
        answers = {"a1": {"answer": "uno", "level": "A1",
                          "kind": "vocabulary", "alternatives": [],
                          "prompt": "one"}}
        pool = [{"id": "a1", "kind": "vocabulary", "level": "A1",
                 "prompt": "one", "translation": None}]
        validator = AsyncMock(return_value=(AnswerResult.WRONG, None))
        with patch("backend.routers.onboarding._language_code",
                   new=AsyncMock(return_value="es")), \
             patch("backend.routers.onboarding.sample_placement_items",
                   new=AsyncMock(return_value=pool * 4)), \
             patch("backend.routers.onboarding.get_placement_answers",
                   new=AsyncMock(return_value=answers)), \
             patch("backend.routers.onboarding.adaptive_next",
                   return_value=None), \
             patch("backend.routers.onboarding.validate_answer_async",
                   new=validator):
            resp = client.post(f"/api/onboarding/placement/{LANG}/next", json={
                "history": [{"id": "a1", "input": "   "}],
            }, headers=_auth_headers())
        item = resp.json()["breakdown"][0]
        assert item["verdict"] == "skipped" and item["correct"] is False
        # "I don't know" costs nothing to grade — no validator call at all.
        validator.assert_not_called()


class TestWritingBlend:
    """Owner: the writing sample "is the best way to determine placement" —
    taken as the final question it decides the level, within one band."""

    def _post(self, client, verdict_level, quiz_level=None):
        body = {"language_id": LANG, "language_code": "es",
                "text": "Ayer fui al mercado porque quería cocinar."}
        if quiz_level:
            body["quiz_level"] = quiz_level
        limiter = AsyncMock()
        limiter.allow = AsyncMock(return_value=True)
        # The real limiter is Redis-backed in a full-suite run and its
        # connection belongs to whichever event loop reached it first, so
        # sharing it across test loops fails only in the full run.
        with patch("backend.routers.onboarding.get_settings",
                   return_value=_WritingSettings(dev_mock=True)), \
             patch("backend.routers.onboarding.tutor_chat_limiter", limiter), \
             patch("backend.routers.onboarding.assess_writing",
                   new=AsyncMock(return_value=(
                       {"level": verdict_level, "notes": "n", "focus": []},
                       {"input_tokens": 1, "output_tokens": 1},
                   ))):
            resp = client.post(
                "/api/onboarding/writing-sample", json=body,
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        return resp.json()

    def test_the_sample_outranks_the_quiz(self, client):
        body = self._post(client, "B2", quiz_level="B1")
        assert body["quiz_level"] == "B1"
        assert body["blended_level"] == "B2"

    def test_a_single_paragraph_cannot_jump_two_bands(self, client):
        # A generous judge on one paragraph must not move an A2 to C1.
        assert self._post(client, "C1", quiz_level="A2")["blended_level"] == "B1"

    def test_it_still_works_as_a_standalone_assessment(self, client):
        body = self._post(client, "B1")
        assert body["quiz_level"] is None
        assert body["blended_level"] == "B1" == body["level"]
