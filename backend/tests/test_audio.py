"""Cached-TTS endpoint tests (WP7a) — DB, storage, and synth all mocked."""

from __future__ import annotations

import base64
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.tts import RATE, VOICES, cache_key, voice_for

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


def _conn(fetchval_results, cache_rows=None):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=list(fetchval_results))
    # The cache lookup reads (storage_path, audio) as one row now that a
    # clip can be held in the database when its upload failed. Derive the
    # rows from the same fixtures unless a test states them: a string is a
    # stored clip, anything else is a miss.
    if cache_rows is None:
        cache_rows = [
            {"storage_path": v, "audio": None} if isinstance(v, str) else None
            for v in fetchval_results
        ]
    conn.fetchrow = AsyncMock(side_effect=list(cache_rows))
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
        # 17 of 22 — yo/ha/xh/mi wait on the MMS phase (browser fallback);
        # jam has no neural voice anywhere and is deliberately voiceless.
        assert set(VOICES) == {
            "en", "es", "fr", "de", "it", "ca", "pt", "ro", "el",
            "ru", "tr", "ar", "sw", "hi", "nl", "th", "ko",
        }

    def test_cache_key_is_stable_and_voice_scoped(self):
        a = cache_key("pt-BR-FranciscaNeural", "você")
        assert a == cache_key("pt-BR-FranciscaNeural", "você")
        assert a != cache_key("es-ES-ElviraNeural", "você")


class TestProviderChain:
    """Prod lesson: edge-tts is rejected from datacenter IPs — with an
    Azure key set, synthesis must use the keyed API instead."""

    def test_azure_used_when_key_set(self):
        import asyncio

        from backend.services import tts as tts_mod

        class AzureSettings(FakeSettings):
            azure_speech_key = "azkey"
            azure_speech_region = "westeurope"

        resp = MagicMock(status_code=200, content=b"mp3bytes")
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=resp)

        with patch("backend.config.get_settings", return_value=AzureSettings()), \
             patch("httpx.AsyncClient", return_value=http_client):
            audio = asyncio.run(tts_mod.synthesize("Habari <b>", "sw"))

        assert audio == b"mp3bytes"
        call = http_client.post.await_args
        assert "westeurope.tts.speech.microsoft.com" in call.args[0]
        assert call.kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "azkey"
        ssml = call.kwargs["content"].decode()
        assert "sw-KE-ZuriNeural" in ssml
        assert "rate='-10%'" in ssml
        assert "&lt;b&gt;" in ssml  # text is XML-escaped

    def test_azure_gapped_text_becomes_a_break(self):
        # Listening-mode audio replaces the answer with '…' — voices read
        # that as nothing, so the SSML must turn it into real silence.
        import asyncio

        from backend.services import tts as tts_mod

        class AzureSettings(FakeSettings):
            azure_speech_key = "azkey"
            azure_speech_region = "eastus"

        resp = MagicMock(status_code=200, content=b"mp3bytes")
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=resp)

        with patch("backend.config.get_settings", return_value=AzureSettings()), \
             patch("httpx.AsyncClient", return_value=http_client):
            asyncio.run(tts_mod.synthesize("Он не станет меня … .", "ru"))

        ssml = http_client.post.await_args.kwargs["content"].decode()
        assert "<break time='900ms'/>" in ssml
        assert "…" not in ssml

    def test_azure_error_raises(self):
        import asyncio

        from backend.services import tts as tts_mod

        class AzureSettings(FakeSettings):
            azure_speech_key = "azkey"
            azure_speech_region = "eastus"

        resp = MagicMock(status_code=401, content=b"", text="unauthorized")
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=resp)

        with patch("backend.config.get_settings", return_value=AzureSettings()), \
             patch("httpx.AsyncClient", return_value=http_client), \
             pytest.raises(RuntimeError):
            asyncio.run(tts_mod.synthesize("hello", "en"))

    def test_edge_used_without_key(self):
        import asyncio

        from backend.services import tts as tts_mod

        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch.object(
                 tts_mod, "_synthesize_edge",
                 new=AsyncMock(return_value=b"edgebytes"),
             ) as mock_edge:
            audio = asyncio.run(tts_mod.synthesize("hola", "es"))
        assert audio == b"edgebytes"
        mock_edge.assert_awaited_once_with("hola", "es-ES-ElviraNeural", RATE)


class TestTTSEndpoint:
    @pytest.fixture(autouse=True)
    def _reset_storage_breaker(self):
        import backend.routers.audio as audio_mod

        audio_mod._storage_down_until = 0.0
        yield
        audio_mod._storage_down_until = 0.0

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

    def test_verification_covers_titles_and_own_sentences(self):
        # Grammar point titles and the learner's own cloze sentences are
        # spoken in the UI — the guard must cover them (RLS scopes the
        # cloze rows to the caller), while staying a closed set.
        import asyncio

        from backend.routers.audio import _text_is_ours

        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=True)
        assert asyncio.run(_text_is_ours(conn, "sw", "Si ya maana."))
        sql = conn.fetchval.await_args.args[0]
        assert "gp.title = $2" in sql
        assert "user_cloze_cards" in sql

    def test_upload_failure_still_serves_the_clip_inline(self):
        # Storage is an optimization: a broken bucket/key must never
        # regress the learner to the browser voice.
        #
        # This used to assert "no cache row either", which is what made the
        # clip cost a fresh synthesis on every later play. The audio has
        # been paid for by the time we get here — whether the upload landed
        # decides HOW it is remembered, never WHETHER.
        priv = _conn([None])
        rls = _conn([True])
        upload = MagicMock(status_code=403, text="signature verification failed")
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=upload)

        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")), \
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
        body = resp.json()
        assert body["url"] is None
        import base64
        assert base64.b64decode(body["audio_b64"]) == b"mp3bytes"
        # Recorded with the bytes and no storage path — so the next play is
        # a cache hit that promotes it, not another call to the provider.
        priv.execute.assert_awaited_once()
        args = priv.execute.await_args.args
        assert "INSERT INTO tts_audio" in args[0]
        assert args[4] is None          # storage_path
        assert args[5] == b"mp3bytes"   # audio

    def test_upload_timeout_trips_cooldown_then_skips_storage(self):
        # Prod egress quirk: connections to Supabase's HTTP APIs hang.
        # A transport error must (a) still serve the clip inline and
        # (b) trip the cooldown so the NEXT miss skips storage entirely
        # instead of paying the connect timeout again.
        import backend.routers.audio as audio_mod

        priv = _conn([None, None])
        rls = _conn([True, True])
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(
            side_effect=__import__("httpx").ConnectTimeout("hang")
        )

        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")), \
             patch("backend.routers.audio.httpx.AsyncClient",
                   return_value=http_client) as mock_client:
            app = create_app()
            with TestClient(app) as client:
                first = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
                second = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        for resp in (first, second):
            assert resp.status_code == 200
            body = resp.json()
            assert body["url"] is None
            assert "audio_b64" in body
        # One attempted upload (the timeout), then the breaker held.
        assert mock_client.call_count == 1
        assert audio_mod._storage_down_until > 0

    def test_http_error_does_not_trip_cooldown(self):
        # A 403 answers fast — no latency cost, so keep trying storage.
        import backend.routers.audio as audio_mod

        priv = _conn([None])
        rls = _conn([True])
        upload = MagicMock(status_code=403, text="denied")
        http_client = AsyncMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)
        http_client.post = AsyncMock(return_value=upload)

        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")), \
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
        assert audio_mod._storage_down_until == 0.0

    def test_missing_service_key_serves_inline_without_storage(self):
        class KeylessSettings(FakeSettings):
            supabase_service_role_key = ""

        priv = _conn([None])
        rls = _conn([True])
        # ps[4] is the audio-router get_settings patch — swap in the
        # keyless settings there; everything else stays stock.
        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], \
             patch("backend.routers.audio.get_settings",
                   return_value=KeylessSettings()), \
             ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")), \
             patch("backend.routers.audio.httpx.AsyncClient") as mock_httpx:
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 200
        assert resp.json()["url"] is None
        assert "audio_b64" in resp.json()
        mock_httpx.assert_not_called()

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

    def test_a_synthesis_is_billed_but_a_cache_hit_is_not(self):
        """Characters reach the provider only on a miss. Counting plays
        instead of syntheses would bill the operator for a CDN file that
        cost nothing — and hide the one number that does cost money."""
        ledger = AsyncMock()
        # Miss: the provider is called, so the ledger is.
        priv = _conn([None])
        rls = _conn([True])
        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")), \
             patch("backend.routers.audio._upload_clip",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.audio.record_speech_event", ledger):
            app = create_app()
            with TestClient(app) as client:
                miss = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        assert miss.status_code == 200
        assert ledger.await_args.kwargs["chars"] == len("você")
        assert ledger.await_args.kwargs["feature"] == "content"

        # Hit: the clip already exists, nothing is synthesized, nothing is
        # billed.
        ledger.reset_mock()
        cached = _conn([f"pt/{cache_key(voice_for('pt'), 'você')}.mp3"])
        ps = _client(cached, _conn([True]))
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=b"mp3bytes")), \
             patch("backend.routers.audio.record_speech_event", ledger):
            app = create_app()
            with TestClient(app) as client:
                hit = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        assert hit.status_code == 200
        assert hit.json()["cached"] is True
        ledger.assert_not_awaited()


class TestDurableCache:
    """Synthesize once, ever — even when the CDN upload fails.

    storage_path was NOT NULL, so a clip could only be recorded if it
    reached the bucket. Everything else was served inline and forgotten,
    and every later play paid the provider again. These cover the path that
    closes it.
    """

    def _http(self, *, ok: bool):
        resp = MagicMock(
            status_code=200 if ok else 403, text="" if ok else "denied"
        )
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.post = AsyncMock(return_value=resp)
        return client

    def _post(self, priv, rls, http_client, synth=b"mp3bytes"):
        ps = _client(priv, rls)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock(return_value=synth)) as mock_synth, \
             patch("backend.routers.audio.httpx.AsyncClient",
                   return_value=http_client):
            app = create_app()
            with TestClient(app) as client:
                resp = client.post(
                    "/api/audio/tts",
                    json={"language_code": "pt", "text": "você"},
                    headers=_auth_headers(),
                )
        return resp, mock_synth

    def test_a_database_held_clip_is_never_synthesized_again(self):
        # The cache hit that this whole change exists to produce.
        priv = _conn(
            [None], cache_rows=[{"storage_path": None, "audio": b"mp3bytes"}]
        )
        resp, synth = self._post(priv, _conn([True]), self._http(ok=False))

        assert resp.status_code == 200
        assert resp.json()["cached"] is True
        assert base64.b64decode(resp.json()["audio_b64"]) == b"mp3bytes"
        synth.assert_not_awaited()

    def test_a_database_held_clip_is_promoted_once_storage_recovers(self):
        # The bytes column is a safety net, not the destination: one bad
        # afternoon must not leave megabytes in Postgres forever.
        priv = _conn(
            [None], cache_rows=[{"storage_path": None, "audio": b"mp3bytes"}]
        )
        resp, synth = self._post(priv, _conn([True]), self._http(ok=True))

        assert resp.json()["url"].endswith(".mp3")
        assert "audio_b64" not in resp.json()
        synth.assert_not_awaited()
        # …and the row now points at the bucket with the bytes dropped.
        sql = priv.execute.await_args.args[0]
        assert "UPDATE tts_audio" in sql
        assert "audio = NULL" in sql

    def test_a_successful_upload_stores_no_bytes(self):
        priv = _conn([None])
        resp, _ = self._post(priv, _conn([True]), self._http(ok=True))

        assert resp.json()["url"].endswith(".mp3")
        args = priv.execute.await_args.args
        assert args[4] is not None   # storage_path
        assert args[5] is None       # audio — the CDN has it

    def test_an_unmigrated_database_still_serves_audio(self):
        # The audio column lands by hand. Until it does, a clip that could
        # not be uploaded goes back to costing a synthesis next time — but
        # the learner must still hear this one rather than meet a 500.
        priv = _conn([None])
        priv.execute = AsyncMock(
            side_effect=asyncpg.exceptions.UndefinedColumnError("no column")
        )
        resp, _ = self._post(priv, _conn([True]), self._http(ok=False))

        assert resp.status_code == 200
        assert base64.b64decode(resp.json()["audio_b64"]) == b"mp3bytes"
