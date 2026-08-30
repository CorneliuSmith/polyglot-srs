"""Contributor recordings — human audio for voiceless languages (jam).

Router-level with mocked repos: role gates, payload validation, the
review flow, and the audio endpoint serving an approved clip ahead of
(or instead of) a synthetic voice.
"""
from __future__ import annotations

import base64
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
CLIP = b"webm-bytes-of-wah-gwaan-" * 4
CLIP_B64 = base64.b64encode(CLIP).decode()


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
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _fake_conn(*args):
    yield AsyncMock()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.contribute.rls_connection", _fake_conn), \
         patch("backend.routers.contribute.privileged_connection", _fake_conn):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _roles(roles):
    return patch("backend.routers.contribute.get_roles",
                 new=AsyncMock(return_value=roles))


CONTRIBUTOR = [{"language_id": LANG, "role": "contributor"}]
REVIEWER = [{"language_id": LANG, "role": "reviewer"}]


def _submission(**over):
    body = {"language_id": LANG, "text": "Wah gwaan?",
            "audio_b64": CLIP_B64, "mime": "audio/webm"}
    body.update(over)
    return body


class TestSubmit:
    def test_requires_a_contributor_role_for_the_language(self, client):
        with _roles([]):
            resp = client.post("/api/contribute/recordings",
                               json=_submission(), headers=_auth_headers())
        assert resp.status_code == 403

    def test_contributor_submits_and_it_queues(self, client):
        with _roles(CONTRIBUTOR), \
             patch("backend.routers.contribute.submit_recording",
                   new=AsyncMock(return_value=True)) as mock_submit:
            resp = client.post("/api/contribute/recordings",
                               json=_submission(), headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"status": "pending"}
        args = mock_submit.await_args.args
        assert args[1:] == (LANG, TEST_USER_ID, "Wah gwaan?", CLIP, "audio/webm")

    def test_reviewers_can_also_submit(self, client):
        # can_contribute includes reviewers — a reviewer recording their own
        # clip must not need a second role grant.
        with _roles(REVIEWER), \
             patch("backend.routers.contribute.submit_recording",
                   new=AsyncMock(return_value=True)):
            resp = client.post("/api/contribute/recordings",
                               json=_submission(), headers=_auth_headers())
        assert resp.status_code == 200

    def test_rejects_unknown_mime(self, client):
        with _roles(CONTRIBUTOR):
            resp = client.post("/api/contribute/recordings",
                               json=_submission(mime="video/mp4"),
                               headers=_auth_headers())
        assert resp.status_code == 422

    def test_rejects_bad_base64(self, client):
        with _roles(CONTRIBUTOR):
            resp = client.post("/api/contribute/recordings",
                               json=_submission(audio_b64="?" * 100),
                               headers=_auth_headers())
        assert resp.status_code == 422

    def test_missing_migration_reports_503_not_500(self, client):
        with _roles(CONTRIBUTOR), \
             patch("backend.routers.contribute.submit_recording",
                   new=AsyncMock(return_value=False)):
            resp = client.post("/api/contribute/recordings",
                               json=_submission(), headers=_auth_headers())
        assert resp.status_code == 503
        assert "20261007" in resp.json()["detail"]


class TestQueueAndReview:
    def test_queue_requires_a_reviewer(self, client):
        with _roles(CONTRIBUTOR):
            resp = client.get(
                "/api/contribute/recordings",
                params={"language_id": LANG}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_queue_lists_pending(self, client):
        rows = [{"id": "r1", "text": "Wah gwaan?", "mime": "audio/webm",
                 "status": "pending", "created_at": "2026-08-30T00:00:00",
                 "contributor_email": "c@x.co"}]
        with _roles(REVIEWER), \
             patch("backend.routers.contribute.list_recordings",
                   new=AsyncMock(return_value=rows)):
            resp = client.get(
                "/api/contribute/recordings",
                params={"language_id": LANG}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["recordings"] == rows

    def test_review_checks_the_clips_own_language(self, client):
        # The role gate must come from the CLIP's language, not from any
        # language id the caller chooses to claim.
        clip = {"audio": CLIP, "mime": "audio/webm",
                "language_id": LANG, "status": "pending"}
        with _roles([{"language_id": "other-lang", "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_recording_audio",
                   new=AsyncMock(return_value=clip)):
            resp = client.post(
                "/api/contribute/recordings/r1/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_approve_flips_status(self, client):
        clip = {"audio": CLIP, "mime": "audio/webm",
                "language_id": LANG, "status": "pending"}
        with _roles(REVIEWER), \
             patch("backend.routers.contribute.get_recording_audio",
                   new=AsyncMock(return_value=clip)), \
             patch("backend.routers.contribute.review_recording",
                   new=AsyncMock(return_value="approved")) as mock_review:
            resp = client.post(
                "/api/contribute/recordings/r1/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"status": "approved"}
        assert mock_review.await_args.kwargs == {"approve": True}

    def test_audio_endpoint_serves_the_clip_to_reviewers(self, client):
        clip = {"audio": CLIP, "mime": "audio/webm",
                "language_id": LANG, "status": "pending"}
        with _roles(REVIEWER), \
             patch("backend.routers.contribute.get_recording_audio",
                   new=AsyncMock(return_value=clip)):
            resp = client.get("/api/contribute/recordings/r1/audio",
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"audio_b64": CLIP_B64, "mime": "audio/webm"}


class TestServingToLearners:
    """The whole point: an approved clip plays where TTS would have been."""

    def _client_patches(self):
        return (
            patch("backend.main.init_pool", new=AsyncMock()),
            patch("backend.main.close_pool", new=AsyncMock()),
            patch("backend.main.get_settings", return_value=FakeSettings()),
            patch("backend.dependencies.get_settings",
                  return_value=FakeSettings()),
            patch("backend.routers.audio.get_settings",
                  return_value=FakeSettings()),
            patch("backend.routers.audio.privileged_connection", _fake_conn),
            patch("backend.routers.audio.rls_connection", _fake_conn),
        )

    def test_voiceless_language_serves_an_approved_recording(self, client):
        ps = self._client_patches()
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.approved_recording",
                   new=AsyncMock(return_value={"audio": CLIP,
                                               "mime": "audio/webm"})), \
             patch("backend.routers.audio.synthesize",
                   new=AsyncMock()) as mock_synth:
            app = create_app()
            with TestClient(app) as c:
                resp = c.post(
                    "/api/audio/tts",
                    json={"language_code": "jam", "text": "Wah gwaan?"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["audio_b64"] == CLIP_B64
        assert body["mime"] == "audio/webm"
        assert body["cached"] is True
        mock_synth.assert_not_awaited()  # no provider call, nothing billed

    def test_voiceless_language_without_a_recording_still_404s(self, client):
        ps = self._client_patches()
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], ps[6], \
             patch("backend.routers.audio.approved_recording",
                   new=AsyncMock(return_value=None)):
            app = create_app()
            with TestClient(app) as c:
                resp = c.post(
                    "/api/audio/tts",
                    json={"language_code": "jam", "text": "Wah gwaan?"},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 404


def test_languages_carry_the_has_tts_flag(client):
    rows = [
        {"id": LANG, "code": "jam", "name": "Jamaican Patois", "rtl": False},
        {"id": "2", "code": "es", "name": "Spanish", "rtl": False},
    ]
    with patch("backend.routers.languages.get_all_languages",
               new=AsyncMock(return_value=rows)), \
         patch("backend.routers.languages.get_pool", return_value=None):
        resp = client.get("/api/languages/")
    assert resp.status_code == 200
    by_code = {r["code"]: r for r in resp.json()}
    assert by_code["jam"]["has_tts"] is False   # the disclaimer languages
    assert by_code["es"]["has_tts"] is True
