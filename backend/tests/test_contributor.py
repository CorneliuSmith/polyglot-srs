"""Tests for contributor roles and the grammar authoring/approval API."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.contributor import can_contribute, is_admin

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"
OTHER_LANG = "99999999-9999-9999-9999-999999999999"
POINT = "22222222-2222-2222-2222-222222222222"


# ── pure role logic ────────────────────────────────────────────────────────

class TestRoleLogic:
    def test_admin_can_contribute_any_language(self):
        roles = [{"language_id": None, "role": "admin"}]
        assert is_admin(roles)
        assert can_contribute(roles, LANG)

    def test_contributor_scoped_to_language(self):
        roles = [{"language_id": LANG, "role": "contributor"}]
        assert not is_admin(roles)
        assert can_contribute(roles, LANG)
        assert not can_contribute(roles, OTHER_LANG)

    def test_global_contributor(self):
        roles = [{"language_id": None, "role": "contributor"}]
        assert can_contribute(roles, OTHER_LANG)

    def test_no_roles(self):
        assert not can_contribute([], LANG)


# ── endpoint gating ─────────────────────────────────────────────────────────

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


@asynccontextmanager
async def _fake_priv():
    yield AsyncMock()


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


class TestContributeEndpoints:
    def test_roles_endpoint(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.get("/api/contribute/roles", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is False
        assert len(resp.json()["roles"]) == 1

    def test_list_grammar_requires_role(self, client):
        with _roles([]):
            resp = client.get(
                "/api/contribute/grammar", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_list_grammar_with_role(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.list_grammar_points",
                   new=AsyncMock(return_value=[{"id": POINT, "title": "Locative"}])):
            resp = client.get(
                "/api/contribute/grammar", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["points"][0]["title"] == "Locative"

    def test_update_grammar_gated_by_point_language(self, client):
        # contributor for OTHER_LANG editing a LANG point -> 403
        with _roles([{"language_id": OTHER_LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.put(
                f"/api/contribute/grammar/{POINT}",
                json={"explanation": "X"}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_update_grammar_saves_pending(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.save_explanation",
                   new=AsyncMock(return_value=True)) as mock_save:
            resp = client.put(
                f"/api/contribute/grammar/{POINT}",
                json={
                    "explanation": "The locative marks location.",
                    "references": [{"title": "Wiktionary", "url": "https://en.wiktionary.org/wiki/-de"}],
                },
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"saved": True, "reviewed": False}
        mock_save.assert_awaited_once()
        # references flow through to the repository layer
        assert mock_save.await_args.kwargs["references"][0]["url"].startswith("https://")

    def test_update_missing_point_404(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=None)):
            resp = client.put(
                f"/api/contribute/grammar/{POINT}",
                json={"explanation": "X"}, headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_approve_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_approve_as_admin(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.approve_explanation",
                   new=AsyncMock(return_value=True)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"approved": True}

    def test_grant_role_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.post(
                "/api/contribute/roles",
                json={"user_id": "u", "role": "contributor"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_grant_role_as_admin(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.grant_role", new=AsyncMock()) as mock_grant:
            resp = client.post(
                "/api/contribute/roles",
                json={"user_id": "u", "language_id": LANG, "role": "contributor"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_grant.assert_awaited_once()


class TestCreatePoint:
    def test_create_requires_role(self, client):
        with _roles([]):
            resp = client.post(
                "/api/contribute/grammar",
                json={"language_id": LANG, "title": "New point"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_create_succeeds(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.create_grammar_point",
                   new=AsyncMock(return_value=POINT)):
            resp = client.post(
                "/api/contribute/grammar",
                json={"language_id": LANG, "title": "New point", "level": "A1"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"id": POINT}

    def test_duplicate_title_409(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.create_grammar_point",
                   new=AsyncMock(return_value=None)):
            resp = client.post(
                "/api/contribute/grammar",
                json={"language_id": LANG, "title": "Dup"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 409


class TestDrills:
    def test_list_drills_role_gated(self, client):
        with _roles([]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))):
            resp = client.get(
                f"/api/contribute/grammar/{POINT}/drills", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_add_drill_validates_answerability(self, client):
        # validate_drill returns False -> 422, no write
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.validate_drill",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.contribute.add_drill", new=AsyncMock()) as mock_add:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/drills",
                json={"sentence": "no blank", "answer": "x"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422
        mock_add.assert_not_awaited()

    def test_add_drill_succeeds_when_answerable(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.validate_drill",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.add_drill",
                   new=AsyncMock(return_value="drill-1")) as mock_add:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/drills",
                json={"sentence": "Kitap {{answer}}.", "answer": "masada",
                      "translation": "The book is on the table."},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"id": "drill-1"}
        mock_add.assert_awaited_once()

    def test_add_drill_unknown_point_404(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=None)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/drills",
                json={"sentence": "Kitap {{answer}}.", "answer": "masada"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_delete_drill(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.delete_drill",
                   new=AsyncMock(return_value=True)) as mock_del:
            resp = client.delete(
                f"/api/contribute/grammar/{POINT}/drills/drill-1",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_del.assert_awaited_once()
