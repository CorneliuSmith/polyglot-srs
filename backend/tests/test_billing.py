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
    stripe_price_single = "price_single"
    stripe_price_all = "price_all"
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
        # Real Stripe events carry a top-level "object": "event" — Stripe's
        # verifier reads it to tell v1 from v2 events.
        payload = json.dumps(
            {"object": "event", "type": "invoice.paid", "data": {"object": {}}}
        ).encode()
        header = _sign(payload, WEBHOOK_SECRET)
        with patch("backend.services.billing.get_settings", return_value=FakeSettings()):
            event = billing.construct_event(payload, header)
        assert event["type"] == "invoice.paid"

    def test_bad_signature_raises(self):
        payload = b'{"object": "event", "type": "invoice.paid", "data": {"object": {}}}'
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


# ── language plans (WP16) ────────────────────────────────────────────────────

class TestExtractPlanChange:
    def _completed(self, meta):
        return {"type": "checkout.session.completed", "data": {"object": {
            "metadata": meta, "subscription": "sub_p1", "customer": "cus_1",
        }}}

    def test_plan_checkout_grants(self):
        change = billing.extract_plan_change(self._completed({
            "kind": "plan", "user_id": TEST_USER_ID,
            "plan_scope": "single", "plan_language_id": LANG,
        }))
        assert change == {
            "action": "grant", "user_id": TEST_USER_ID, "plan_scope": "single",
            "plan_language_id": LANG, "subscription_id": "sub_p1",
            "customer_id": "cus_1",
        }

    def test_all_plan_needs_no_language(self):
        change = billing.extract_plan_change(self._completed({
            "kind": "plan", "user_id": TEST_USER_ID,
            "plan_scope": "all", "plan_language_id": "",
        }))
        assert change["plan_scope"] == "all"
        assert change["plan_language_id"] is None

    def test_tutor_event_never_sets_a_plan(self):
        # No kind=plan → the tutor's own checkout can't touch plans.
        assert billing.extract_plan_change(self._completed({
            "user_id": TEST_USER_ID, "language_id": LANG,
        })) is None

    def test_plan_event_never_grants_tutor(self):
        # The mirror image: plan metadata has no language_id.
        assert billing.extract_entitlement_change(self._completed({
            "kind": "plan", "user_id": TEST_USER_ID,
            "plan_scope": "all", "plan_language_id": "",
        })) is None

    def test_single_without_language_is_rejected(self):
        assert billing.extract_plan_change(self._completed({
            "kind": "plan", "user_id": TEST_USER_ID,
            "plan_scope": "single", "plan_language_id": "",
        })) is None

    def test_subscription_deleted_revokes(self):
        event = {"type": "customer.subscription.deleted",
                 "data": {"object": {"id": "sub_p1"}}}
        assert billing.extract_plan_change(event) == {
            "action": "revoke", "subscription_id": "sub_p1",
        }

    def test_past_due_revokes(self):
        event = {"type": "customer.subscription.updated",
                 "data": {"object": {"id": "sub_p1", "status": "past_due"}}}
        assert billing.extract_plan_change(event)["action"] == "revoke"


class TestPlanEndpoints:
    def test_plan_checkout_requires_auth(self, client):
        resp = client.post("/api/billing/plan/checkout",
                           json={"plan_scope": "all"})
        assert resp.status_code == 401

    def test_single_needs_language(self, client):
        resp = client.post(
            "/api/billing/plan/checkout",
            json={"plan_scope": "single"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_dev_mock_sets_plan_directly(self, client):
        with patch("backend.routers.billing.set_plan_subscription",
                   new=AsyncMock()) as mock_set:
            resp = client.post(
                "/api/billing/plan/checkout",
                json={"plan_scope": "single", "plan_language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"granted": True, "url": None}
        args = mock_set.await_args.args
        assert args[1:] == (TEST_USER_ID, "single", LANG)

    def test_plan_checkout_503_when_not_configured(self, client):
        paid = FakeSettings()
        paid.stripe_dev_mock = False  # no secret key either
        with patch("backend.routers.billing.get_settings", return_value=paid), \
             patch("backend.services.billing.get_settings", return_value=paid):
            resp = client.post(
                "/api/billing/plan/checkout",
                json={"plan_scope": "all"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 503

    def test_prices_null_until_configured(self, client):
        resp = client.get("/api/billing/plan/prices", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"single": None, "all": None}

    def test_portal_503_when_not_configured(self, client):
        resp = client.post("/api/billing/portal", headers=_auth_headers())
        assert resp.status_code == 503

    def test_webhook_sets_plan_on_event(self, client):
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {
                "metadata": {"kind": "plan", "user_id": TEST_USER_ID,
                             "plan_scope": "all", "plan_language_id": ""},
                "subscription": "sub_p9", "customer": "cus_9",
            }},
        }).encode()
        with patch("backend.services.billing.construct_event",
                   return_value=json.loads(payload)), \
             patch("backend.routers.billing.set_plan_subscription",
                   new=AsyncMock()) as mock_set:
            resp = client.post(
                "/api/billing/webhook", content=payload,
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200
        args = mock_set.await_args
        assert args.args[1:] == (TEST_USER_ID, "all", None)
        assert args.kwargs["subscription_id"] == "sub_p9"
