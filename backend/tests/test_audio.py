"""Cached-TTS endpoint tests (WP7a) — DB, storage, and synth all mocked."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.tts import VOICES, cache_key, voice_for

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "service-key"
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


def _conn(fetchval_results):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=fetchval_results)
    return conn


def _client(priv_conn, rls_conn):
    @asynccontextmanager
    async def fake_priv():
        yield priv_conn

    @asynccontextmanager
    async def fake_rls(user_id):
        yield rls_conn

    return (
        patch("backend.main.init_pool", new=AsyncMock()),
        patch("backend.main.close_pool", new=AsyncMock()),
        patch("backend.main.get_settings", return_value=FakeSettings()),
        patch("backend.dependencies.get_settings", return_value=FakeSettings()),
        patch("backend.routers.audio.get_settings", return_value=FakeSettings()),
        patch("backend.routers.audio.privileged_connection", fake_priv),
        patch("backend.routers.audio.rls_connection", fake_rls),
    )


class TestVoices:
    def test_covered_languages(self):
        # 13 of 17 — yo/ha/xh/mi wait on the MMS phase (browser fallback).
        assert set(VOICES) == {
            "en", "es", "fr", "de", "it", "ca", "pt", "ro", "el",
            "ru", "tr", "ar", "sw",
        }

    def test_cache_key_is_stable_and_voice_scoped(self):
        a = cache_key("pt-BR-FranciscaNeural", "você")
        assert a == cache_key("pt-BR-FranciscaNeural", "você")
        assert a != cache_key("es-ES-ElviraNeural", "você")


class TestTTSEndpoint:
    def test_requires_auth(self):
        ps = _client(_conn([None]), _conn([True]))
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6]:
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                )
        assert resp.status_code == 401

    def test_uncovered_language_404(self):
        ps = _client(_conn([None]), _conn([True]))
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6]:
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "yo", "text": "bawo"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 404

    def test_cache_hit_returns_public_url_without_synthesis(self):
        voice = voice_for("pt")
        key = cache_key(voice, "você")
        priv = _conn([f"pt/{key}.mp3"])
        ps = _client(priv, _conn([True]))
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock()) as mock_synth:
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["cached"] is True
        assert body["url"] == (
            f"https://fake.supabase.co/storage/v1/object/public/tts/pt/{key}.mp3"
        )
        mock_synth.assert_not_awaited()

    def test_unknown_text_404_never_an_open_proxy(self):
        priv = _conn([None])          # cache miss
        rls = _conn([False])          # text is NOT ours
        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock()) as mock_synth:
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "arbitrary spam text"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 404
        mock_synth.assert_not_awaited()

    def test_miss_synthesizes_uploads_and_records(self):
        priv = _conn([None])          # cache miss, then INSERT via execute
        rls = _conn([True])           # the text is ours
        upload = MagicMock(status_code=200, text="")
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=upload)

        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")) as mock_synth, \
             patch("backend.routers.audio.httpx.AsyncClient",
                   return_value=http_client):
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 200
        assert resp.json()["cached"] is False
        mock_synth.assert_awaited_once()
        # Uploaded with the service key to the tts bucket…
        upload_call = http_client.post.await_args
        assert "/storage/v1/object/tts/pt/" in upload_call.args[0]
        assert upload_call.kwargs["content"] == b"mp3bytes"
        # …and the cache row was written.
        priv.execute.assert_awaited_once()
