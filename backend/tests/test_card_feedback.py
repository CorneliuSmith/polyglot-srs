"""Tests for learner card feedback: submission and the contributor queue."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import asyncpg
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"
CARD = "22222222-2222-2222-2222-222222222222"
FB = "33333333-3333-3333-3333-333333333333"


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
    yield mock_conn()


@asynccontextmanager
async def _fake_priv():
    yield mock_conn()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.review.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.privileged_connection", _fake_priv):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _roles(roles):
    return patch("backend.routers.contribute.get_roles", new=AsyncMock(return_value=roles))


class TestSubmitFeedback:
    def test_requires_auth(self, client):
        resp = client.post(f"/api/review/card/{CARD}/feedback", json={"message": "x"})
        assert resp.status_code == 401

    def test_submits(self, client):
        with patch("backend.routers.review.add_card_feedback",
                   new=AsyncMock(return_value=True)) as mock_add:
            resp = client.post(
                f"/api/review/card/{CARD}/feedback",
                json={"message": "This sentence looks wrong."},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"submitted": True}
        mock_add.assert_awaited_once()

    def test_empty_message_422(self, client):
        resp = client.post(
            f"/api/review/card/{CARD}/feedback", json={"message": ""},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_unknown_card_404(self, client):
        with patch("backend.routers.review.add_card_feedback",
                   new=AsyncMock(return_value=False)):
            resp = client.post(
                f"/api/review/card/{CARD}/feedback", json={"message": "hi"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404


class TestFeedbackQueue:
    def test_list_requires_role(self, client):
        with _roles([]):
            resp = client.get(
                "/api/contribute/feedback", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_list_with_role(self, client):
        items = [{"id": FB, "card_type": "grammar", "card_title": "Locative",
                  "message": "wrong answer", "status": "open"}]
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.list_feedback",
                   new=AsyncMock(return_value=items)):
            resp = client.get(
                "/api/contribute/feedback", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["feedback"][0]["card_title"] == "Locative"

    def test_resolve_role_gated(self, client):
        with _roles([{"language_id": "other", "role": "contributor"}]), \
             patch("backend.routers.contribute.get_feedback_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post(
                f"/api/contribute/feedback/{FB}/resolve", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_resolve_succeeds(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_feedback_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.resolve_feedback",
                   new=AsyncMock(return_value=True)) as mock_res:
            resp = client.post(
                f"/api/contribute/feedback/{FB}/resolve", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"resolved": True}
        mock_res.assert_awaited_once()


class TestQueueCarriesTheCard:
    """The queue used to hand a reviewer a complaint and a word.

    "Too much info" and "the definition doesn't match the sentence" are
    judgements about text that was nowhere on the screen — deciding either
    one meant leaving for the content editor and finding the card by search.
    """

    def test_the_queue_carries_the_card_the_report_is_about(self, client):
        items = [{"id": FB, "card_type": "vocabulary", "card_title": "pequeña",
                  "message": "Too much info", "status": "open",
                  "target_type": "vocabulary", "target_id": CARD}]

        async def _load(conn, rows):
            for r in rows:
                r["card"] = {"sentence": "pequeña", "answer": None,
                             "hint": "peh-KEH-nya", "translation": "small",
                             "context": "adj", "level": "A1"}

        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.list_feedback",
                   new=AsyncMock(return_value=items)), \
             patch("backend.routers.contribute.load_cards", new=_load):
            resp = client.get(
                "/api/contribute/feedback", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        row = resp.json()["feedback"][0]
        assert row["card"]["translation"] == "small"
        # Named as the change-request board names it, so one component in
        # the frontend renders (and edits) the card in either queue.
        assert row["target_type"] == "vocabulary"

    def test_a_failed_card_lookup_still_returns_the_queue(self, client):
        """A queue that 500s is strictly worse than one without context —
        the same rule the change-request board already follows."""
        items = [{"id": FB, "card_type": "vocabulary", "card_title": "ya",
                  "message": "Confusion", "status": "open",
                  "target_type": "vocabulary", "target_id": CARD}]
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.list_feedback",
                   new=AsyncMock(return_value=items)), \
             patch("backend.routers.contribute.load_cards",
                   new=AsyncMock(side_effect=asyncpg.PostgresError("boom"))):
            resp = client.get(
                "/api/contribute/feedback", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["feedback"][0]["message"] == "Confusion"


class TestEditCardUnderReview:
    """The write side of the queues' card view."""

    def test_requires_a_contributor_role_for_that_language(self, client):
        with _roles([{"language_id": "other-language", "role": "contributor"}]), \
             patch("backend.routers.contribute.card_language_id",
                   new=AsyncMock(return_value=LANG)):
            resp = client.put(
                f"/api/contribute/review/card/vocabulary/{CARD}",
                json={"translation": "small"}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_sends_only_the_fields_the_editor_offered(self, client):
        """exclude_unset, not exclude_none: a box the reviewer cleared means
        null, a box their editor never drew must not be written at all."""
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.card_language_id",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.edit_reviewed_card",
                   new=AsyncMock(return_value="ok")) as mock_edit:
            resp = client.put(
                f"/api/contribute/review/card/vocabulary/{CARD}",
                json={"translation": "small"}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_edit.await_args.args[3] == {"translation": "small"}

    def test_a_deleted_card_is_a_404(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.card_language_id",
                   new=AsyncMock(return_value=None)):
            resp = client.put(
                f"/api/contribute/review/card/vocabulary/{CARD}",
                json={"translation": "x"}, headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_a_kind_with_no_card_is_refused_before_any_lookup(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.put(
                f"/api/contribute/review/card/tutor_message/{CARD}",
                json={"translation": "x"}, headers=_auth_headers(),
            )
        assert resp.status_code == 422
