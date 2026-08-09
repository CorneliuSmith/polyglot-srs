"""The trial-access flow: public request → admin email → approval mints an
account with a TEMPORARY password that the app forces the applicant to
replace on first sign-in (user-metadata flag, enforced client-side by
ProtectedRoute and cleared by the same updateUser call that sets the new
password)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.routers.auth import trial_request_limiter
from backend.services.rate_limit import _MemoryBackend

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
ADMIN_ID = "550e8400-e29b-41d4-a716-446655440000"
REQ_ID = "22222222-2222-2222-2222-222222222222"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    admin_notify_email = "owner@example.com"
    app_base_url = "https://app.example"


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": ADMIN_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _fake_priv():
    yield AsyncMock()


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield AsyncMock()


@pytest.fixture()
def client():
    # A FRESH in-memory window per test, whatever REDIS_URL says: every
    # request in the suite arrives from the same "testclient" address, so a
    # shared Redis window bleeds state across tests (and across whole runs
    # — its entries outlive the process by an hour).
    with patch.object(trial_request_limiter, "_backend",
                      _MemoryBackend(max_calls=5, per_seconds=3600)), \
         patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.auth.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.auth.privileged_connection", _fake_priv), \
         patch("backend.routers.contribute.privileged_connection", _fake_priv), \
         patch("backend.routers.contribute.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _admin():
    return patch("backend.routers.contribute.get_roles",
                 new=AsyncMock(return_value=[{"language_id": None,
                                              "role": "admin"}]))


# ── the public request ───────────────────────────────────────────────────────

class TestTrialRequest:
    def test_a_new_request_is_queued_and_the_admin_is_emailed(self, client):
        with patch("backend.routers.auth.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.auth.add_trial_request",
                   new=AsyncMock(return_value=True)) as add, \
             patch("backend.routers.auth.send_email",
                   new=AsyncMock(return_value=True)) as mail:
            resp = client.post("/api/auth/trial-request", json={
                "email": "kate@example.com", "name": "Kate",
                "note": "Thai please",
            })
        assert resp.status_code == 200
        assert resp.json() == {"received": True}
        assert add.await_args.args[1:] == ("kate@example.com", "Kate",
                                           "Thai please")
        assert mail.await_args.args[0] == "owner@example.com"
        assert "kate@example.com" in mail.await_args.args[1]

    def test_a_duplicate_answers_identically_but_emails_nobody(self, client):
        """No enumeration, and no way to make the admin's inbox ring on
        someone else's behalf."""
        with patch("backend.routers.auth.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.auth.add_trial_request",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.auth.send_email",
                   new=AsyncMock()) as mail:
            resp = client.post("/api/auth/trial-request",
                               json={"email": "kate@example.com"})
        assert resp.status_code == 200
        assert resp.json() == {"received": True}
        mail.assert_not_awaited()

    def test_503_names_the_missing_migration(self, client):
        with patch("backend.routers.auth.trials_table_present",
                   new=AsyncMock(return_value=False)):
            resp = client.post("/api/auth/trial-request",
                               json={"email": "kate@example.com"})
        assert resp.status_code == 503
        assert "20260921" in resp.json()["detail"]

    def test_garbage_email_is_rejected(self, client):
        resp = client.post("/api/auth/trial-request",
                           json={"email": "not-an-email"})
        assert resp.status_code == 422

    def test_the_limiter_stops_a_hammering_client(self, client):
        with patch("backend.routers.auth.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.auth.add_trial_request",
                   new=AsyncMock(return_value=False)):
            codes = [
                client.post("/api/auth/trial-request",
                            json={"email": f"kate{i}@example.com"}).status_code
                for i in range(7)
            ]
        assert codes.count(429) >= 2  # 5/hour per IP


# ── the admin decision ───────────────────────────────────────────────────────

class TestTrialApproval:
    def _pending(self):
        return {"id": REQ_ID, "email": "kate@example.com", "name": "Kate",
                "note": None, "status": "pending"}

    def test_approve_mints_a_temp_password_account_and_emails_it(self, client):
        with _admin(), \
             patch("backend.routers.contribute.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.get_trial_request",
                   new=AsyncMock(return_value=self._pending())), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(return_value="new-uid")) as create, \
             patch("backend.routers.contribute.mark_trial_decided",
                   new=AsyncMock()) as decided, \
             patch("backend.routers.contribute.send_email",
                   new=AsyncMock(return_value=True)) as mail:
            resp = client.post(
                f"/api/contribute/trial-requests/{REQ_ID}/approve",
                headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        # The account was minted with the SAME temp password the panel gets,
        # and with the forced-reset flag in its user metadata.
        assert create.await_args.args[2] == body["temp_password"]
        assert len(body["temp_password"]) >= 10
        assert create.await_args.kwargs["user_meta"] == {
            "must_change_password": True}
        assert decided.await_args.args[2:] == ("approved", ADMIN_ID)
        # The applicant's email carries the temp password.
        assert mail.await_args.args[0] == "kate@example.com"
        assert body["temp_password"] in mail.await_args.args[2]
        assert body["emailed"] is True

    def test_approve_is_admin_only(self, client):
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[])):
            resp = client.post(
                f"/api/contribute/trial-requests/{REQ_ID}/approve",
                headers=_auth_headers())
        assert resp.status_code == 403

    def test_an_already_decided_request_409s(self, client):
        with _admin(), \
             patch("backend.routers.contribute.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.get_trial_request",
                   new=AsyncMock(return_value={**self._pending(),
                                               "status": "approved"})):
            resp = client.post(
                f"/api/contribute/trial-requests/{REQ_ID}/approve",
                headers=_auth_headers())
        assert resp.status_code == 409

    def test_an_existing_account_409s_cleanly(self, client):
        with _admin(), \
             patch("backend.routers.contribute.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.get_trial_request",
                   new=AsyncMock(return_value=self._pending())), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(side_effect=ValueError("dupe"))):
            resp = client.post(
                f"/api/contribute/trial-requests/{REQ_ID}/approve",
                headers=_auth_headers())
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_reject_records_and_emails_nothing(self, client):
        with _admin(), \
             patch("backend.routers.contribute.trials_table_present",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.get_trial_request",
                   new=AsyncMock(return_value=self._pending())), \
             patch("backend.routers.contribute.mark_trial_decided",
                   new=AsyncMock()) as decided, \
             patch("backend.routers.contribute.send_email",
                   new=AsyncMock()) as mail:
            resp = client.post(
                f"/api/contribute/trial-requests/{REQ_ID}/reject",
                headers=_auth_headers())
        assert resp.status_code == 200
        assert decided.await_args.args[2:] == ("rejected", ADMIN_ID)
        mail.assert_not_awaited()

    def test_the_queue_reports_unavailable_before_the_migration(self, client):
        with _admin(), \
             patch("backend.routers.contribute.trials_table_present",
                   new=AsyncMock(return_value=False)):
            resp = client.get("/api/contribute/trial-requests",
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"requests": [], "available": False}
