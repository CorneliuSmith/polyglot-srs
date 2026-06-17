"""Tests for Stripe billing: event mapping, signature verification, endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services import billing

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"
WEBHOOK_SECRET = "whsec_test_secret"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    stripe_secret_key = ""
    stripe_webhook_secret = WEBHOOK_SECRET
    stripe_price_id = "price_tutor"
    stripe_dev_mock = True
    app_base_url = "https://app.example"


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "email": "u@x.co",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ── pure event → entitlement mapping ─────────────────────────────────────────

class TestExtractEntitlementChange:
    def test_checkout_completed_grants(self):
        event = {"type": "checkout.session.completed", "data": {"object": {
            "client_reference_id": TEST_USER_ID,
            "metadata": {"language_id": LANG},
            "subscription": "sub_1", "customer": "cus_1",
        }}}
        assert billing.extract_entitlement_change(event) == {
            "action": "grant", "user_id": TEST_USER_ID, "language_id": LANG,
            "subscription_id": "sub_1", "customer_id": "cus_1",
        }

    def test_subscription_deleted_revokes(self):
        event = {"type": "customer.subscription.deleted",
                 "data": {"object": {"id": "sub_9"}}}
        assert billing.extract_entitlement_change(event) == {
            "action": "revoke", "subscription_id": "sub_9",
        }

    def test_subscription_updated_canceled_revokes(self):
        event = {"type": "customer.subscription.updated",
                 "data": {"object": {"id": "sub_9", "status": "canceled"}}}
        assert billing.extract_entitlement_change(event)["action"] == "revoke"

    def test_subscription_updated_active_grants(self):
        event = {"type": "customer.subscription.updated", "data": {"object": {
            "id": "sub_2", "status": "active", "customer": "cus_2",
            "metadata": {"user_id": TEST_USER_ID, "language_id": LANG},
        }}}
        change = billing.extract_entitlement_change(event)
        assert change["action"] == "grant" and change["subscription_id"] == "sub_2"

    def test_unhandled_event_is_ignored(self):
        assert billing.extract_entitlement_change(
            {"type": "invoice.paid", "data": {"object": {}}}
        ) is None

    def test_grant_needs_user_and_language(self):
        event = {"type": "checkout.session.completed",
                 "data": {"object": {"subscription": "sub_1"}}}
        assert billing.extract_entitlement_change(event) is None


# ── webhook signature verification (offline, real Stripe verifier) ───────────

def _sign(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    signed = f"{ts}.{payload.decode()}".encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


class TestConstructEvent:
    def test_valid_signature_round_trips(self):
        payload = json.dumps({"type": "invoice.paid", "data": {"object": {}}}).encode()
        header = _sign(payload, WEBHOOK_SECRET)
        with patch("backend.services.billing.get_settings", return_value=FakeSettings()):
            event = billing.construct_event(payload, header)
        assert event["type"] == "invoice.paid"

    def test_bad_signature_raises(self):
        payload = b'{"type": "invoice.paid", "data": {"object": {}}}'
        with patch("backend.services.billing.get_settings", return_value=FakeSettings()):
            with pytest.raises(Exception):
                billing.construct_event(payload, _sign(payload, "wrong_secret"))


# ── endpoints ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _fake_priv():
    yield AsyncMock()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.billing.get_settings", return_value=FakeSettings()), \
         patch("backend.services.billing.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.billing.privileged_connection", _fake_priv):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


class TestEndpoints:
    def test_checkout_requires_auth(self, client):
        assert client.post("/api/billing/checkout", json={"language_id": LANG}).status_code == 401

    def test_checkout_dev_mock_grants_directly(self, client):
        with patch("backend.routers.billing.grant_entitlement",
                   new=AsyncMock()) as grant:
            resp = client.post("/api/billing/checkout", json={"language_id": LANG},
                               headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"granted": True, "url": None}
        assert grant.await_args.args[1:] == (TEST_USER_ID, LANG)

    def test_checkout_503_when_not_configured(self, client):
        with patch("backend.services.billing.is_configured", return_value=False):
            resp = client.post("/api/billing/checkout", json={"language_id": LANG},
                               headers=_auth_headers())
        assert resp.status_code == 503

    def test_webhook_grants_on_event(self, client):
        event = {"type": "checkout.session.completed", "data": {"object": {
            "client_reference_id": TEST_USER_ID, "metadata": {"language_id": LANG},
            "subscription": "sub_1", "customer": "cus_1",
        }}}
        with patch("backend.services.billing.construct_event", return_value=event), \
             patch("backend.routers.billing.grant_entitlement", new=AsyncMock()) as grant:
            resp = client.post("/api/billing/webhook", content=b"{}",
                               headers={"Stripe-Signature": "t=1,v1=x"})
        assert resp.status_code == 200 and resp.json() == {"received": True}
        assert grant.await_args.args[1:] == (TEST_USER_ID, LANG)

    def test_webhook_bad_signature_400(self, client):
        with patch("backend.services.billing.construct_event",
                   side_effect=ValueError("bad sig")):
            resp = client.post("/api/billing/webhook", content=b"{}",
                               headers={"Stripe-Signature": "bad"})
        assert resp.status_code == 400


def test_checkout_real_mode_returns_url():
    """With a Stripe key (not mock), checkout returns a Checkout URL."""
    class RealSettings(FakeSettings):
        stripe_secret_key = "sk_test_x"
        stripe_dev_mock = False

    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=RealSettings()), \
         patch("backend.dependencies.get_settings", return_value=RealSettings()), \
         patch("backend.routers.billing.get_settings", return_value=RealSettings()), \
         patch("backend.services.billing.get_settings", return_value=RealSettings()), \
         patch("backend.routers.billing.privileged_connection", _fake_priv), \
         patch("backend.routers.billing.get_customer_id", new=AsyncMock(return_value=None)), \
         patch("backend.routers.billing.save_customer_id", new=AsyncMock()), \
         patch("backend.services.billing.create_customer", return_value="cus_new"), \
         patch("backend.services.billing.create_checkout_session",
               return_value={"url": "https://checkout.stripe/x", "session_id": "cs_1"}) as mk:
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.post("/api/billing/checkout", json={"language_id": LANG},
                          headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json() == {"granted": False, "url": "https://checkout.stripe/x"}
    assert mk.call_args.kwargs["customer_id"] == "cus_new"
