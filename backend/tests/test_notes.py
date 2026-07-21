"""Endpoint tests for the personal notes/cloze-card router (DB + NLP mocked)."""

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
         patch("backend.routers.notes.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


class TestNotes:
    def test_requires_auth(self, client):
        assert client.post("/api/notes/extract", json={
            "language_id": LANG, "language_code": "es", "text": "x"
        }).status_code == 401

    def test_extract_flags_known_and_new(self, client):
        with patch("backend.routers.notes.known_vocab",
                   new=AsyncMock(return_value={"gato": "cat"})):
            resp = client.post("/api/notes/extract", json={
                "language_id": LANG, "language_code": "es",
                "text": "El gato xyzzy.",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        words = resp.json()["sentences"][0]["words"]
        by = {w["normalized"]: w for w in words}
        assert by["gato"]["known"] is True and by["gato"]["definition"] == "cat"
        assert by["xyzzy"]["known"] is False

    def test_extract_unknown_language_422(self, client):
        resp = client.post("/api/notes/extract", json={
            "language_id": LANG, "language_code": "zz", "text": "hi",
        }, headers=_auth_headers())
        assert resp.status_code == 422

    def test_create_card_happy_path(self, client):
        with patch("backend.routers.notes.validate_drill",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.notes.create_personal_card",
                   new=AsyncMock(return_value="card-1")) as mock_create:
            resp = client.post("/api/notes/cards", json={
                "language_id": LANG, "language_code": "es",
                "sentence": "El gato duerme.", "answer": "gato",
                "translation": "The cat sleeps.",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == "card-1"
        # The stored sentence has the blank inserted at the answer's position.
        assert mock_create.await_args.args[3] == "El {{answer}} duerme."

    def test_create_card_word_not_in_sentence_422(self, client):
        resp = client.post("/api/notes/cards", json={
            "language_id": LANG, "language_code": "es",
            "sentence": "El gato duerme.", "answer": "perro",
        }, headers=_auth_headers())
        assert resp.status_code == 422

    def test_create_card_unanswerable_422(self, client):
        with patch("backend.routers.notes.validate_drill",
                   new=AsyncMock(return_value=False)):
            resp = client.post("/api/notes/cards", json={
                "language_id": LANG, "language_code": "es",
                "sentence": "El gato duerme.", "answer": "gato",
            }, headers=_auth_headers())
        assert resp.status_code == 422

    def test_inflected_word_falls_back_to_gloss_prompt(self, client):
        # Reader lists dictionary forms; the sentence inflects them (başkent →
        # başkenti). No cloze is possible, so the gloss becomes a type-the-word
        # prompt instead of a silent 422.
        with patch("backend.routers.notes.create_personal_card",
                   new=AsyncMock(return_value="card-2")) as mock_create:
            resp = client.post("/api/notes/cards", json={
                "language_id": LANG, "language_code": "tr",
                "sentence": "Ankara Türkiye'nin başkentidir.",
                "answer": "başkent", "gloss": "capital city",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        # Stored sentence is the gloss (no {{answer}} marker → type-the-word).
        assert mock_create.await_args.args[3] == "capital city"
        assert mock_create.await_args.args[4] == "başkent"

    def test_prefers_cloze_over_gloss_when_word_is_verbatim(self, client):
        with patch("backend.routers.notes.validate_drill",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.notes.create_personal_card",
                   new=AsyncMock(return_value="card-3")) as mock_create:
            resp = client.post("/api/notes/cards", json={
                "language_id": LANG, "language_code": "es",
                "sentence": "El gato duerme.", "answer": "gato",
                "gloss": "cat",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        # Cloze wins — the gloss is only a fallback.
        assert mock_create.await_args.args[3] == "El {{answer}} duerme."
