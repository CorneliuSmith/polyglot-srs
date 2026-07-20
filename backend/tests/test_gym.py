"""Unit tests for GET /api/gym/manifest (WP25 The Gym).

The manifest resolves curated form categories (data/gym/{code}.json) to
live grammar points; DB access is mocked.
"""
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
LANG_ID = "22222222-2222-2222-2222-222222222222"
POINT_ID = "33333333-3333-3333-3333-333333333333"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "sk"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


MANIFEST = {
    "language": "ru",
    "columns": [
        {"kind": "verbs", "label": "Verbs", "entries": [
            {"point": "Present tense", "label": "Present",
             "usage": "now and habits", "example": "Я читаю."},
            {"point": "Missing point", "label": "Ghost",
             "usage": "-", "example": "-"},
        ]},
        {"kind": "nouns", "label": "Nouns", "entries": [
            {"point": "Accusative case", "label": "Accusative (what)",
             "usage": "the object", "example": "Я читаю книгу.",
             "nonstandard": True},
        ]},
    ],
}


def _client(conn):
    @asynccontextmanager
    async def fake_rls(user_id):
        yield conn

    return (
        patch("backend.main.init_pool", new=AsyncMock()),
        patch("backend.main.close_pool", new=AsyncMock()),
        patch("backend.main.get_settings", return_value=FakeSettings()),
        patch("backend.dependencies.get_settings", return_value=FakeSettings()),
        patch("backend.routers.gym.rls_connection", fake_rls),
    )


def _conn(code="ru", rows=None):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=code)
    conn.fetch = AsyncMock(return_value=rows or [])
    return conn


class TestGymManifest:
    def test_requires_auth(self):
        ps = _client(_conn())
        with ps[0], ps[1], ps[2], ps[3], ps[4]:
            app = create_app()
            with TestClient(app) as client:
                resp = client.get(
                    "/api/gym/manifest", params={"language_id": LANG_ID}
                )
        assert resp.status_code == 401

    def test_invalid_language_id_422(self):
        ps = _client(_conn())
        with ps[0], ps[1], ps[2], ps[3], ps[4]:
            app = create_app()
            with TestClient(app) as client:
                resp = client.get(
                    "/api/gym/manifest",
                    params={"language_id": "not-a-uuid"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 422

    def test_unknown_language_404(self):
        ps = _client(_conn(code=None))
        with ps[0], ps[1], ps[2], ps[3], ps[4]:
            app = create_app()
            with TestClient(app) as client:
                resp = client.get(
                    "/api/gym/manifest",
                    params={"language_id": LANG_ID},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 404

    def test_no_manifest_means_no_gym(self):
        ps = _client(_conn(code="th"))
        with ps[0], ps[1], ps[2], ps[3], ps[4], \
             patch("backend.routers.gym._load_manifest", return_value=None):
            app = create_app()
            with TestClient(app) as client:
                resp = client.get(
                    "/api/gym/manifest",
                    params={"language_id": LANG_ID},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 200
        assert resp.json() == {"columns": []}

    def test_resolves_points_and_drops_missing_ones(self):
        rows = [
            {"id": POINT_ID, "title": "Present tense", "level": "A1",
             "drills": 12, "familiar": True},
            # "Accusative case" resolves too; "Missing point" does not.
            {"id": "44444444-4444-4444-4444-444444444444",
             "title": "Accusative case", "level": "A1",
             "drills": 18, "familiar": False},
        ]
        ps = _client(_conn(rows=rows))
        with ps[0], ps[1], ps[2], ps[3], ps[4], \
             patch("backend.routers.gym._load_manifest", return_value=MANIFEST):
            app = create_app()
            with TestClient(app) as client:
                resp = client.get(
                    "/api/gym/manifest",
                    params={"language_id": LANG_ID},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 200
        cols = resp.json()["columns"]
        assert [c["kind"] for c in cols] == ["verbs", "nouns"]
        verbs = cols[0]["entries"]
        # The unresolved "Missing point" entry is dropped silently.
        assert [e["label"] for e in verbs] == ["Present"]
        assert verbs[0]["point_id"] == POINT_ID
        assert verbs[0]["familiar"] is True
        assert verbs[0]["drills"] == 12
        assert verbs[0]["usage"] == "now and habits"
        nouns = cols[1]["entries"]
        assert nouns[0]["nonstandard"] is True
        assert nouns[0]["familiar"] is False

    def test_live_russian_manifest_parses(self):
        # The shipped data/gym/ru.json must load and declare the three
        # columns with non-empty entries — a broken manifest would 500.
        from backend.routers.gym import _load_manifest

        manifest = _load_manifest("ru")
        assert manifest is not None
        kinds = [c["kind"] for c in manifest["columns"]]
        assert kinds == ["verbs", "nouns", "adjectives"]
        for col in manifest["columns"]:
            assert col["entries"], f"empty column {col['kind']}"
            for e in col["entries"]:
                assert e["point"] and e["label"] and e["usage"] and e["example"]
