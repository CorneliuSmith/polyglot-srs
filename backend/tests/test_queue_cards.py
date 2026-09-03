"""Every review queue that names a card carries it (docs/plans/
owner-notes-2026-09-03.md, item 7a). The change-request board and the
learner-feedback queue already did; review notes, suggestions and tester
recommendations now name their target the same way and get the same
`load_cards` pass — best-effort, so a lookup failure never empties a
queue."""
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
         patch("backend.routers.contribute.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.privileged_connection", _fake_priv):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _roles(roles):
    return patch("backend.routers.contribute.get_roles", new=AsyncMock(return_value=roles))


async def _attach(conn, rows):
    for r in rows:
        r["card"] = {"sentence": "pequeña", "answer": None, "hint": None,
                     "translation": "small", "context": "adj", "level": "A1"}


def test_review_notes_name_and_carry_their_card(client):
    notes = [{"id": "n1", "grammar_point_id": None, "vocabulary_id": CARD,
              "entity_type": "vocab", "entity_label": "pequeña",
              "point_title": "pequeña", "level": "A1", "note": "gloss is regional",
              "status": "open", "author_email": "r@x", "created_at": None}]
    with _roles([{"language_id": LANG, "role": "reviewer"}]), \
         patch("backend.routers.contribute.list_review_notes",
               new=AsyncMock(return_value=notes)), \
         patch("backend.routers.contribute.load_cards", new=_attach):
        resp = client.get("/api/contribute/notes", params={"language_id": LANG},
                          headers=_auth_headers())
    assert resp.status_code == 200
    row = resp.json()["notes"][0]
    assert row["target_type"] == "vocabulary" and row["target_id"] == CARD
    assert row["card"]["translation"] == "small"


def test_suggestions_map_their_kind_to_the_loaders(client):
    items = [{"id": "s1", "entity_type": "grammar", "entity_id": CARD,
              "card_title": "Ser vs estar", "current": {}, "proposed": {},
              "note": None, "status": "pending", "source": "contributor",
              "origin": None, "created_at": None}]
    with _roles([{"language_id": LANG, "role": "reviewer"}]), \
         patch("backend.routers.contribute.list_suggestions",
               new=AsyncMock(return_value=items)), \
         patch("backend.routers.contribute.load_cards", new=_attach):
        resp = client.get("/api/contribute/suggestions", params={"language_id": LANG},
                          headers=_auth_headers())
    assert resp.status_code == 200
    row = resp.json()["suggestions"][0]
    # 'grammar' is the suggestion's kind; 'grammar_point' is the loader's.
    assert row["target_type"] == "grammar_point" and row["card"] is not None


def test_a_failed_card_lookup_still_returns_the_notes(client):
    notes = [{"id": "n1", "grammar_point_id": CARD, "vocabulary_id": None,
              "entity_type": "grammar", "entity_label": "Ser", "point_title": "Ser",
              "level": None, "note": "x", "status": "open", "author_email": "r@x",
              "created_at": None}]
    with _roles([{"language_id": LANG, "role": "reviewer"}]), \
         patch("backend.routers.contribute.list_review_notes",
               new=AsyncMock(return_value=notes)), \
         patch("backend.routers.contribute.load_cards",
               new=AsyncMock(side_effect=asyncpg.PostgresError("boom"))):
        resp = client.get("/api/contribute/notes", params={"language_id": LANG},
                          headers=_auth_headers())
    assert resp.status_code == 200 and resp.json()["notes"][0]["note"] == "x"
