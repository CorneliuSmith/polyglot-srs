"""Personal decks: learner-named folders over Tutor/Reader cards."""
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
DECK = "22222222-2222-2222-2222-222222222222"
CARD = "33333333-3333-3333-3333-333333333333"


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
         patch("backend.routers.personal_decks.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


class TestPersonalDecksEndpoints:
    def test_requires_auth(self, client):
        assert client.get(
            "/api/personal-decks", params={"language_id": LANG}
        ).status_code == 401

    def test_list_decks(self, client):
        decks = [{"id": DECK, "name": "K-dramas", "card_count": 3}]
        with patch(
            "backend.routers.personal_decks.list_decks",
            new=AsyncMock(return_value=decks),
        ):
            resp = client.get(
                "/api/personal-decks", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == decks

    def test_create_trims_and_returns_id(self, client):
        with patch(
            "backend.routers.personal_decks.create_deck",
            new=AsyncMock(return_value=DECK),
        ) as mock_create:
            resp = client.post(
                "/api/personal-decks",
                json={"language_id": LANG, "name": "  Songs  "},
                headers=_auth_headers(),
            )
        assert resp.status_code == 201
        assert resp.json() == {"id": DECK}
        assert mock_create.await_args.args[3] == "Songs"

    def test_create_rejects_empty_name(self, client):
        resp = client.post(
            "/api/personal-decks",
            json={"language_id": LANG, "name": ""},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_rename_404_when_not_owned(self, client):
        with patch(
            "backend.routers.personal_decks.rename_deck",
            new=AsyncMock(return_value=False),
        ):
            resp = client.patch(
                f"/api/personal-decks/{DECK}",
                json={"name": "New name"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_delete_ok(self, client):
        with patch(
            "backend.routers.personal_decks.delete_deck",
            new=AsyncMock(return_value=True),
        ):
            resp = client.delete(
                f"/api/personal-decks/{DECK}", headers=_auth_headers()
            )
        assert resp.status_code == 200

    def test_file_card_into_deck(self, client):
        with patch(
            "backend.routers.personal_decks.file_card",
            new=AsyncMock(return_value=True),
        ) as mock_file:
            resp = client.patch(
                f"/api/personal-decks/cards/{CARD}",
                json={"deck_id": DECK},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_file.await_args.args[1] == CARD
        assert mock_file.await_args.args[2] == DECK

    def test_unfile_card_with_null(self, client):
        with patch(
            "backend.routers.personal_decks.file_card",
            new=AsyncMock(return_value=True),
        ) as mock_file:
            resp = client.patch(
                f"/api/personal-decks/cards/{CARD}",
                json={"deck_id": None},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_file.await_args.args[2] is None
