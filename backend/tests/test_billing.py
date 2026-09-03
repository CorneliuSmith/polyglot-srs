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
from backend.tests.fakes import mock_conn

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
    topup_price_cents = 500
    topup_messages = 200


TOPUP_PRICE = {"amount_cents": 500, "currency": "usd", "messages": 200}
# What each option includes, as /plan/prices reports it (admin-editable).
POOLS = {"free": 20, "single": 0, "all": 300, "plus": 200}


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
    yield mock_conn()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.billing.get_settings", return_value=FakeSettings()), \
         patch("backend.services.billing.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.billing.privileged_connection", _fake_priv), \
         patch("backend.routers.billing.monetization_enabled",
               new=AsyncMock(return_value=True)), \
         patch("backend.routers.billing.get_custom_price",
               new=AsyncMock(return_value=None)):
        # Monetization ON so the purchase paths are exercisable; the
        # master-switch tests below patch it off. No admin-set price by
        # default; the custom-pricing tests override.
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
         patch("backend.routers.billing.monetization_enabled",
               new=AsyncMock(return_value=True)), \
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
            # Minted before the AI flag existed: None, so the repository
            # leaves plan_ai alone rather than switching it off.
            "ai": None,
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
        # Plan prices need Stripe Price ids; the top-up is priced inline
        # from Settings so dev-mock alone already quotes it. The pools ride
        # along either way — what an option includes is known before it
        # is priced.
        with patch("backend.routers.billing.get_plan_message_limits",
                   new=AsyncMock(return_value=None)), \
             patch("backend.routers.billing.effective_plan_limits",
                   return_value=POOLS):
            resp = client.get("/api/billing/plan/prices", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"single": None, "all": None, "ai_addon": None,
                               "custom": None, "topup": TOPUP_PRICE,
                               "pools": POOLS, "monetization": True}

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


# ── admin-set per-account pricing (the generalized charge) ───────────────────

class TestCustomPricing:
    """The owner's dial: each account's monthly charge is set from the admin
    panel and checkout charges exactly that — through price_data, so no
    per-person Price objects ever exist in the Stripe dashboard."""

    def test_prices_show_the_admin_set_charge(self, client):
        with patch("backend.routers.billing.get_custom_price",
                   new=AsyncMock(return_value={
                       "monthly_cents": 1234, "currency": "usd",
                       "note": None})), \
             patch("backend.routers.billing.get_plan_message_limits",
                   new=AsyncMock(return_value=None)), \
             patch("backend.routers.billing.effective_plan_limits",
                   return_value=POOLS):
            resp = client.get("/api/billing/plan/prices",
                              headers=_auth_headers())
        assert resp.status_code == 200
        priced = {"amount_cents": 1234, "currency": "usd",
                  "interval": "month"}
        # Mirrored onto both scopes: the charge is per ACCOUNT, whichever
        # plan shape they pick, so existing price displays need no changes.
        # No separate add-on amount: the charge is the whole price of
        # whichever of the four options the account picks.
        assert resp.json() == {"single": priced, "all": priced, "ai_addon": None,
                               "custom": priced, "topup": TOPUP_PRICE,
                               "pools": POOLS, "monetization": True}

    def test_zero_priced_account_subscribes_free_without_stripe(self):
        """0 cents = free. No key, no dev-mock, no Stripe round trip — the
        plan lands exactly as a paid webhook would land it."""
        unpaid = FakeSettings()
        unpaid.stripe_dev_mock = False  # and no secret key either
        with patch("backend.main.init_pool", new=AsyncMock()), \
             patch("backend.main.close_pool", new=AsyncMock()), \
             patch("backend.main.get_settings", return_value=unpaid), \
             patch("backend.dependencies.get_settings", return_value=unpaid), \
             patch("backend.routers.billing.get_settings", return_value=unpaid), \
             patch("backend.services.billing.get_settings", return_value=unpaid), \
             patch("backend.routers.billing.privileged_connection", _fake_priv), \
             patch("backend.routers.billing.monetization_enabled",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.billing.get_custom_price",
                   new=AsyncMock(return_value={
                       "monthly_cents": 0, "currency": "usd", "note": None})), \
             patch("backend.routers.billing.set_plan_subscription",
                   new=AsyncMock()) as mock_set:
            app = create_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.post("/api/billing/plan/checkout",
                              json={"plan_scope": "all"},
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"granted": True, "url": None}
        args = mock_set.await_args
        assert args.args[1:] == (TEST_USER_ID, "all", None)
        assert args.kwargs["subscription_id"] == "admin-free"

    def test_priced_checkout_charges_the_admin_amount(self):
        """A custom price checks out through price_data with THAT amount —
        and needs no configured plan Price ids at all."""
        class PricedSettings(FakeSettings):
            stripe_secret_key = "sk_test_x"
            stripe_dev_mock = False
            stripe_price_single = ""   # deliberately unconfigured:
            stripe_price_all = ""      # the custom lane must not need them

        with patch("backend.main.init_pool", new=AsyncMock()), \
             patch("backend.main.close_pool", new=AsyncMock()), \
             patch("backend.main.get_settings", return_value=PricedSettings()), \
             patch("backend.dependencies.get_settings", return_value=PricedSettings()), \
             patch("backend.routers.billing.get_settings", return_value=PricedSettings()), \
             patch("backend.services.billing.get_settings", return_value=PricedSettings()), \
             patch("backend.routers.billing.privileged_connection", _fake_priv), \
             patch("backend.routers.billing.monetization_enabled",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.billing.get_custom_price",
                   new=AsyncMock(return_value={
                       "monthly_cents": 750, "currency": "usd", "note": None})), \
             patch("backend.routers.billing.get_customer_id",
                   new=AsyncMock(return_value="cus_7")), \
             patch("backend.services.billing.create_priced_plan_checkout_session",
                   return_value={"url": "https://checkout.stripe/c",
                                 "session_id": "cs_c"}) as mk:
            app = create_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.post("/api/billing/plan/checkout",
                              json={"plan_scope": "all"},
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"granted": False,
                               "url": "https://checkout.stripe/c"}
        assert mk.call_args.kwargs["monthly_cents"] == 750
        assert mk.call_args.kwargs["currency"] == "usd"

    def test_priced_session_builds_inline_price_data(self):
        """The service builds a price_data line item (inline price) with the
        same plan metadata the webhook grant path already understands."""
        fake_stripe = type("S", (), {})()
        captured = {}

        class _Session:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                return {"url": "https://checkout/x", "id": "cs_9"}

        fake_stripe.checkout = type("C", (), {"Session": _Session})()
        with patch("backend.services.billing._stripe",
                   return_value=fake_stripe):
            out = billing.create_priced_plan_checkout_session(
                user_id=TEST_USER_ID, plan_scope="all",
                plan_language_id=None, monthly_cents=750, currency="usd",
                customer_id="cus_7", success_url="s", cancel_url="c",
            )
        assert out["url"] == "https://checkout/x"
        item = captured["line_items"][0]["price_data"]
        assert item["unit_amount"] == 750
        assert item["recurring"] == {"interval": "month"}
        assert captured["metadata"]["kind"] == "plan"
        assert captured["subscription_data"]["metadata"]["plan_scope"] == "all"


class TestCustomPriceRepo:
    """The repo degrades on a missing migration: reads say 'no custom
    price', writes say 'cannot' so the admin endpoint can name the fix."""

    @pytest.mark.asyncio
    async def test_reads_are_none_before_the_migration(self):
        from backend.repositories.billing import get_custom_price
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)  # to_regclass miss
        assert await get_custom_price(conn, TEST_USER_ID) is None
        conn.fetchrow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_writes_refuse_before_the_migration(self):
        from backend.repositories.billing import set_custom_price
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        assert await set_custom_price(conn, TEST_USER_ID, 500) is False
        conn.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_none_clears_back_to_standard_pricing(self):
        from backend.repositories.billing import set_custom_price
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=True)
        assert await set_custom_price(conn, TEST_USER_ID, None) is True
        assert "DELETE FROM custom_prices" in conn.execute.await_args.args[0]


# ── the monetization master switch ───────────────────────────────────────────

class TestMonetizationSwitch:
    """OFF (the default, and the state before migration 20261006 lands)
    means every purchase path 503s and /plan/prices tells the UI to show
    no money surface at all. The owner flips it from the admin panel."""

    def _off(self):
        return patch("backend.routers.billing.monetization_enabled",
                     new=AsyncMock(return_value=False))

    def test_prices_say_monetization_off(self, client):
        with self._off():
            resp = client.get("/api/billing/plan/prices",
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"single": None, "all": None, "ai_addon": None, "custom": None,
                               "topup": None, "monetization": False}

    def test_every_purchase_path_is_closed(self, client):
        with self._off():
            checkout = client.post("/api/billing/checkout",
                                   json={"language_id": LANG},
                                   headers=_auth_headers())
            plan = client.post("/api/billing/plan/checkout",
                               json={"plan_scope": "all"},
                               headers=_auth_headers())
            topup = client.post("/api/billing/topup", headers=_auth_headers())
            portal = client.post("/api/billing/portal", headers=_auth_headers())
        assert {r.status_code for r in (checkout, plan, topup, portal)} == {503}


# ── one-time AI top-ups ──────────────────────────────────────────────────────

class TestExtractTopup:
    def _completed(self, meta, session_id="cs_t1"):
        return {"type": "checkout.session.completed", "data": {"object": {
            "id": session_id, "metadata": meta,
            "client_reference_id": meta.get("user_id"),
        }}}

    def test_completed_topup_grants(self):
        grant = billing.extract_topup(self._completed({
            "kind": "topup", "user_id": TEST_USER_ID, "messages": "200",
        }))
        assert grant == {"user_id": TEST_USER_ID, "messages": 200,
                         "session_id": "cs_t1"}

    def test_other_kinds_never_grant_a_topup(self):
        # A plan or tutor checkout completing must not also add messages.
        assert billing.extract_topup(self._completed({
            "kind": "plan", "user_id": TEST_USER_ID,
            "plan_scope": "all", "plan_language_id": "",
        })) is None
        assert billing.extract_topup(self._completed({
            "user_id": TEST_USER_ID, "language_id": LANG,
        })) is None

    def test_topup_event_never_grants_plan_or_tutor(self):
        event = self._completed({
            "kind": "topup", "user_id": TEST_USER_ID, "messages": "200",
        })
        assert billing.extract_plan_change(event) is None
        assert billing.extract_entitlement_change(event) is None

    def test_bad_message_counts_are_rejected(self):
        for messages in ("", "0", "-5", "abc", None):
            assert billing.extract_topup(self._completed({
                "kind": "topup", "user_id": TEST_USER_ID,
                "messages": messages,
            })) is None

    def test_subscription_events_are_ignored(self):
        assert billing.extract_topup(
            {"type": "customer.subscription.deleted",
             "data": {"object": {"id": "sub_1"}}}
        ) is None


class TestTopupEndpoint:
    def test_requires_auth(self, client):
        assert client.post("/api/billing/topup").status_code == 401

    def test_dev_mock_grants_directly(self, client):
        with patch("backend.routers.billing.grant_topup",
                   new=AsyncMock(return_value=True)) as grant:
            resp = client.post("/api/billing/topup", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"granted": True, "url": None}
        args = grant.await_args.args
        assert args[1:3] == (TEST_USER_ID, 200)
        # dev-mock still gets a unique idempotency key per purchase — two
        # mock top-ups are two rows, not one deduplicated one.
        assert args[3].startswith("mock-")

    def test_dev_mock_503_before_the_migration(self, client):
        with patch("backend.routers.billing.grant_topup",
                   new=AsyncMock(return_value=False)):
            resp = client.post("/api/billing/topup", headers=_auth_headers())
        assert resp.status_code == 503
        assert "20261006" in resp.json()["detail"]

    def test_webhook_records_the_grant_with_the_session_id(self, client):
        event = {"type": "checkout.session.completed", "data": {"object": {
            "id": "cs_t9", "client_reference_id": TEST_USER_ID,
            "metadata": {"kind": "topup", "user_id": TEST_USER_ID,
                         "messages": "200"},
        }}}
        with patch("backend.services.billing.construct_event",
                   return_value=event), \
             patch("backend.routers.billing.grant_topup",
                   new=AsyncMock(return_value=True)) as grant:
            resp = client.post("/api/billing/webhook", content=b"{}",
                               headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 200
        assert grant.await_args.args[1:] == (TEST_USER_ID, 200, "cs_t9")

    def test_session_builds_a_one_time_payment(self):
        fake_stripe = type("S", (), {})()
        captured = {}

        class _Session:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                return {"url": "https://checkout/t", "id": "cs_t2"}

        fake_stripe.checkout = type("C", (), {"Session": _Session})()
        with patch("backend.services.billing._stripe",
                   return_value=fake_stripe), \
             patch("backend.services.billing.get_settings",
                   return_value=FakeSettings()):
            out = billing.create_topup_checkout_session(
                user_id=TEST_USER_ID, customer_id="cus_7",
                success_url="s", cancel_url="c",
            )
        assert out["url"] == "https://checkout/t"
        assert captured["mode"] == "payment"          # one-time, never a sub
        item = captured["line_items"][0]["price_data"]
        assert item["unit_amount"] == 500
        assert "recurring" not in item
        assert captured["metadata"] == {
            "kind": "topup", "user_id": TEST_USER_ID, "messages": "200",
        }


class TestTopupRepo:
    """Degrades on a missing migration: counts read 0, grants say 'cannot'
    so the endpoint can name the fix instead of failing silently."""

    @pytest.mark.asyncio
    async def test_count_is_zero_before_the_migration(self):
        from backend.repositories.billing import count_topup_messages
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)  # to_regclass miss
        from datetime import UTC, datetime
        assert await count_topup_messages(
            conn, TEST_USER_ID, datetime.now(UTC)) == 0

    @pytest.mark.asyncio
    async def test_grant_refuses_before_the_migration(self):
        from backend.repositories.billing import grant_topup
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        assert await grant_topup(conn, TEST_USER_ID, 200, "cs_1") is False
        conn.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_grant_inserts_with_conflict_do_nothing(self):
        from backend.repositories.billing import grant_topup
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=True)
        assert await grant_topup(conn, TEST_USER_ID, 200, "cs_1") is True
        sql = conn.execute.await_args.args[0]
        assert "ON CONFLICT (external_id) DO NOTHING" in sql


class TestFlagsRepo:
    """app_flags reads default OFF — including before migration 20261006 —
    and writes refuse so the admin toggle can 503 naming the migration."""

    @pytest.mark.asyncio
    async def test_missing_table_reads_as_the_default(self):
        from backend.repositories.flags import get_flag
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        assert await get_flag(conn, "monetization") is False
        assert await get_flag(conn, "monetization", default=True) is True

    @pytest.mark.asyncio
    async def test_missing_row_reads_as_the_default(self):
        from backend.repositories.flags import get_flag
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[True, None])
        assert await get_flag(conn, "monetization") is False

    @pytest.mark.asyncio
    async def test_stored_value_wins(self):
        from backend.repositories.flags import get_flag
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=[True, True])
        assert await get_flag(conn, "monetization") is True

    @pytest.mark.asyncio
    async def test_write_refuses_before_the_migration(self):
        from backend.repositories.flags import set_flag
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)
        assert await set_flag(conn, "monetization", True, TEST_USER_ID) is False
        conn.execute.assert_not_awaited()


# ── the four options: scope × AI, one subscription ──────────────────────────
#
# Owner: "Make the 4 options … Single language with AI should be the default
# but provide options to upgrade." An option with AI is the plan's Price plus
# the add-on's Price in ONE Checkout session, so Stripe makes one
# subscription with one charge; the webhook records both halves.


class _FakeStripe:
    """Records the Checkout session Stripe would have been asked for."""
    created: list[dict] = []
    cancelled: list[tuple] = []

    class checkout:  # noqa: N801 — mirrors stripe.checkout
        class Session:
            @staticmethod
            def create(**kw):
                _FakeStripe.created.append(kw)
                return {"url": "https://checkout.stripe/opt", "id": "cs_opt"}

    class Subscription:
        @staticmethod
        def cancel(sub_id, **kw):
            _FakeStripe.cancelled.append((sub_id, kw))
            return {"id": sub_id, "status": "canceled"}

    class Price:
        @staticmethod
        def retrieve(price_id):
            return {"unit_amount": {"price_single": 700, "price_all": 1200,
                                    "price_tutor": 500}[price_id],
                    "currency": "usd", "recurring": {"interval": "month"}}


class TestFourOptions:
    def setup_method(self):
        _FakeStripe.created.clear()
        _FakeStripe.cancelled.clear()

    def test_an_option_with_ai_is_one_session_with_two_line_items(self):
        class RealSettings(FakeSettings):
            stripe_secret_key = "sk_test_x"
            stripe_dev_mock = False
        with patch("backend.services.billing.get_settings", return_value=RealSettings()), \
             patch("backend.services.billing._stripe", return_value=_FakeStripe):
            billing.create_plan_checkout_session(
                user_id=TEST_USER_ID, plan_scope="single", plan_language_id=LANG,
                customer_id="cus_1", success_url="s", cancel_url="c", ai=True,
            )
        [kw] = _FakeStripe.created
        assert [li["price"] for li in kw["line_items"]] == ["price_single", "price_tutor"]
        assert kw["mode"] == "subscription"
        # Both the session and the subscription say which option this is,
        # so lifecycle events months later can still tell.
        assert kw["metadata"]["ai"] == "1"
        assert kw["subscription_data"]["metadata"]["ai"] == "1"
        assert kw["metadata"]["plan_scope"] == "single"

    def test_an_option_without_ai_says_so_rather_than_saying_nothing(self):
        class RealSettings(FakeSettings):
            stripe_secret_key = "sk_test_x"
            stripe_dev_mock = False
        with patch("backend.services.billing.get_settings", return_value=RealSettings()), \
             patch("backend.services.billing._stripe", return_value=_FakeStripe):
            billing.create_plan_checkout_session(
                user_id=TEST_USER_ID, plan_scope="all", plan_language_id=None,
                customer_id="cus_1", success_url="s", cancel_url="c",
            )
        [kw] = _FakeStripe.created
        assert [li["price"] for li in kw["line_items"]] == ["price_all"]
        assert kw["metadata"]["ai"] == "0"

    def test_the_webhook_reads_the_ai_half_of_the_option(self):
        ev = {"type": "checkout.session.completed", "data": {"object": {
            "metadata": {"kind": "plan", "user_id": TEST_USER_ID,
                         "plan_scope": "all", "plan_language_id": "", "ai": "1"},
            "subscription": "sub_p2", "customer": "cus_1",
        }}}
        assert billing.extract_plan_change(ev)["ai"] is True
        ev["data"]["object"]["metadata"]["ai"] = "0"
        assert billing.extract_plan_change(ev)["ai"] is False

    def test_prices_carry_the_add_on_so_the_ui_can_add_the_two_up(self):
        class RealSettings(FakeSettings):
            stripe_secret_key = "sk_test_x"
            stripe_dev_mock = False
        with patch("backend.services.billing.get_settings", return_value=RealSettings()), \
             patch("backend.services.billing._stripe", return_value=_FakeStripe):
            prices = billing.list_plan_prices()
        assert prices["single"]["amount_cents"] == 700
        assert prices["ai_addon"]["amount_cents"] == 500
        assert prices["ai_addon"]["interval"] == "month"

    def test_an_option_with_ai_is_refused_until_the_add_on_is_priced(self):
        """A deploy that priced the plans but not the add-on still sells the
        two no-AI options; the two with AI say why they cannot be bought."""
        class HalfConfigured(FakeSettings):
            stripe_secret_key = "sk_test_x"
            stripe_dev_mock = False
            stripe_price_id = ""
        with patch("backend.main.init_pool", new=AsyncMock()), \
             patch("backend.main.close_pool", new=AsyncMock()), \
             patch("backend.main.get_settings", return_value=HalfConfigured()), \
             patch("backend.dependencies.get_settings", return_value=HalfConfigured()), \
             patch("backend.routers.billing.get_settings", return_value=HalfConfigured()), \
             patch("backend.services.billing.get_settings", return_value=HalfConfigured()), \
             patch("backend.routers.billing.privileged_connection", _fake_priv), \
             patch("backend.routers.billing.monetization_enabled",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.billing.get_custom_price",
                   new=AsyncMock(return_value=None)):
            app = create_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.post(
                    "/api/billing/plan/checkout",
                    json={"plan_scope": "all", "ai": True},
                    headers=_auth_headers(),
                )
        assert resp.status_code == 503
        assert "add-on" in resp.json()["detail"]

    def test_dev_mock_records_both_halves(self, client):
        with patch("backend.routers.billing.monetization_enabled",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.billing.get_custom_price",
                   new=AsyncMock(return_value=None)), \
             patch("backend.routers.billing.set_plan_subscription",
                   new=AsyncMock()) as mock_set:
            resp = client.post(
                "/api/billing/plan/checkout",
                json={"plan_scope": "single", "plan_language_id": LANG, "ai": True},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200 and resp.json()["granted"] is True
        assert mock_set.await_args.kwargs["ai"] is True

    def test_an_upgrade_cancels_the_subscription_it_replaces(self, client):
        """Checkout only creates. Without this, single → all left the single
        plan billing beside the new one, every month, until someone noticed."""
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {
                "metadata": {"kind": "plan", "user_id": TEST_USER_ID,
                             "plan_scope": "all", "plan_language_id": "", "ai": "1"},
                "subscription": "sub_new", "customer": "cus_9",
            }},
        }).encode()
        with patch("backend.services.billing.construct_event",
                   return_value=json.loads(payload)), \
             patch("backend.routers.billing.previous_plan_subscription",
                   new=AsyncMock(return_value="sub_old")), \
             patch("backend.routers.billing.set_plan_subscription",
                   new=AsyncMock()) as mock_set, \
             patch("backend.services.billing.cancel_subscription") as mock_cancel:
            resp = client.post(
                "/api/billing/webhook", content=payload,
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200
        assert mock_set.await_args.kwargs["ai"] is True
        # The old plan is ended AFTER the new one has landed, and only when
        # it is a different subscription — a redelivered event for the same
        # one must not cancel it.
        mock_cancel.assert_called_once_with("sub_old")

    def test_a_redelivered_grant_does_not_cancel_the_new_plan(self, client):
        payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {
                "metadata": {"kind": "plan", "user_id": TEST_USER_ID,
                             "plan_scope": "all", "plan_language_id": "", "ai": "0"},
                "subscription": "sub_new", "customer": "cus_9",
            }},
        }).encode()
        with patch("backend.services.billing.construct_event",
                   return_value=json.loads(payload)), \
             patch("backend.routers.billing.previous_plan_subscription",
                   new=AsyncMock(return_value="sub_new")), \
             patch("backend.routers.billing.set_plan_subscription", new=AsyncMock()), \
             patch("backend.services.billing.cancel_subscription") as mock_cancel:
            client.post("/api/billing/webhook", content=payload,
                        headers={"Stripe-Signature": "sig"})
        mock_cancel.assert_not_called()

    def test_cancel_credits_the_unused_period_and_skips_pretend_ids(self):
        class RealSettings(FakeSettings):
            stripe_secret_key = "sk_test_x"
        with patch("backend.services.billing.get_settings", return_value=RealSettings()), \
             patch("backend.services.billing._stripe", return_value=_FakeStripe):
            assert billing.cancel_subscription("sub_old") is True
            assert billing.cancel_subscription("mock-plan") is False
            assert billing.cancel_subscription("admin-free") is False
        assert _FakeStripe.cancelled == [("sub_old", {"prorate": True})]


class TestAiAddOn:
    """'Add AI' on a plan bought without it: its own subscription, the
    plan-level pool, revoked only by its own id."""

    def _completed(self, meta):
        return {"type": "checkout.session.completed", "data": {"object": {
            "metadata": meta, "subscription": "sub_ai", "customer": "cus_1",
        }}}

    def test_add_on_checkout_grants_the_plan_pool(self):
        change = billing.extract_ai_change(self._completed(
            {"kind": "ai", "user_id": TEST_USER_ID, "language_id": LANG}))
        assert change == {"action": "grant", "user_id": TEST_USER_ID,
                          "subscription_id": "sub_ai", "customer_id": "cus_1"}

    def test_the_legacy_per_language_extractor_leaves_it_alone(self):
        # Both extractors run on every event. A kind='ai' session must not
        # ALSO write a per-language row — one purchase, one record.
        assert billing.extract_entitlement_change(self._completed(
            {"kind": "ai", "user_id": TEST_USER_ID, "language_id": LANG})) is None
        # …while a session minted before 'kind' existed still does.
        assert billing.extract_entitlement_change(self._completed(
            {"user_id": TEST_USER_ID, "language_id": LANG}))["action"] == "grant"

    def test_plan_events_never_touch_the_add_on(self):
        assert billing.extract_ai_change(self._completed(
            {"kind": "plan", "user_id": TEST_USER_ID, "plan_scope": "all",
             "plan_language_id": "", "ai": "1"})) is None

    def test_cancelling_the_add_on_revokes_by_its_id(self):
        ev = {"type": "customer.subscription.deleted",
              "data": {"object": {"id": "sub_ai"}}}
        assert billing.extract_ai_change(ev) == {"action": "revoke",
                                                 "subscription_id": "sub_ai"}

    def test_webhook_switches_the_pool_on_and_off(self, client):
        on = json.dumps(self._completed(
            {"kind": "ai", "user_id": TEST_USER_ID, "language_id": LANG})).encode()
        with patch("backend.services.billing.construct_event",
                   return_value=json.loads(on)), \
             patch("backend.routers.billing.set_plan_ai", new=AsyncMock()) as mock_on:
            client.post("/api/billing/webhook", content=on,
                        headers={"Stripe-Signature": "sig"})
        assert mock_on.await_args.args[1:] == (TEST_USER_ID, True, "sub_ai")
        off = json.dumps({"type": "customer.subscription.deleted",
                          "data": {"object": {"id": "sub_ai"}}}).encode()
        # A deletion is id-scoped and every extractor sees it; the plan and
        # legacy revokes run too and must find nothing — stubbed here.
        with patch("backend.services.billing.construct_event",
                   return_value=json.loads(off)), \
             patch("backend.routers.billing.deactivate_plan_by_subscription",
                   new=AsyncMock(return_value=0)), \
             patch("backend.routers.billing.revoke_by_subscription",
                   new=AsyncMock(return_value=0)), \
             patch("backend.routers.billing.clear_plan_ai_by_subscription",
                   new=AsyncMock()) as mock_off:
            client.post("/api/billing/webhook", content=off,
                        headers={"Stripe-Signature": "sig"})
        assert mock_off.await_args.args[1] == "sub_ai"
