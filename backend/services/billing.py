"""Stripe billing service for the tutor add-on.

Wraps the Stripe SDK behind small functions so the router stays thin and the
event→entitlement mapping is pure and testable. Stripe is imported lazily so
the package isn't required unless billing is actually configured.

Two modes:
* real — a Stripe secret key is set; checkout creates a Stripe session and
  webhooks (signature-verified) drive entitlement grant/revoke.
* dev-mock (stripe_dev_mock) — no key; the router grants directly so the
  gated → unlocked flow is demoable without Stripe.
"""
from __future__ import annotations

from backend.config import get_settings

# Subscription statuses that should keep the entitlement on / off.
_ACTIVE_STATUSES = {"active", "trialing"}
_INACTIVE_STATUSES = {"canceled", "unpaid", "incomplete_expired", "past_due"}


def is_configured() -> bool:
    """True when checkout can run — a real Stripe key, or dev-mock mode."""
    settings = get_settings()
    return bool(settings.stripe_secret_key) or settings.stripe_dev_mock


def _stripe():
    import stripe

    stripe.api_key = get_settings().stripe_secret_key
    return stripe


def create_customer(email: str | None, user_id: str) -> str:
    """Create a Stripe customer for a user and return its id."""
    customer = _stripe().Customer.create(
        email=email, metadata={"user_id": user_id}
    )
    return customer["id"]


def create_checkout_session(
    *,
    user_id: str,
    language_id: str,
    customer_id: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a Stripe Checkout session for the tutor subscription."""
    settings = get_settings()
    session = _stripe().checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        client_reference_id=user_id,
        metadata={"user_id": user_id, "language_id": language_id},
        # Mirror onto the subscription so lifecycle webhooks can reconcile.
        subscription_data={"metadata": {"user_id": user_id, "language_id": language_id}},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"url": session["url"], "session_id": session["id"]}


def create_plan_checkout_session(
    *,
    user_id: str,
    plan_scope: str,
    plan_language_id: str | None,
    customer_id: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a Stripe Checkout session for a language plan (WP16).

    metadata.kind='plan' is what separates plan webhooks from tutor
    webhooks — both products share the /webhook endpoint.
    """
    settings = get_settings()
    price = (
        settings.stripe_price_single
        if plan_scope == "single"
        else settings.stripe_price_all
    )
    meta = {
        "kind": "plan",
        "user_id": user_id,
        "plan_scope": plan_scope,
        "plan_language_id": plan_language_id or "",
    }
    session = _stripe().checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price, "quantity": 1}],
        client_reference_id=user_id,
        metadata=meta,
        subscription_data={"metadata": meta},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"url": session["url"], "session_id": session["id"]}


def create_portal_session(*, customer_id: str, return_url: str) -> str:
    """A Stripe Billing Portal URL — upgrades/downgrades prorate there."""
    session = _stripe().billing_portal.Session.create(
        customer=customer_id, return_url=return_url
    )
    return session["url"]


def plans_configured() -> bool:
    """True when plan checkout can run (both Prices set, or dev-mock)."""
    settings = get_settings()
    if settings.stripe_dev_mock:
        return True
    return bool(
        settings.stripe_secret_key
        and settings.stripe_price_single
        and settings.stripe_price_all
    )


def list_plan_prices() -> dict[str, dict | None]:
    """The two plans' live prices, from Stripe — never hardcoded (WP16d).

    Returns {"single": {...}|None, "all": {...}|None} where each price is
    {"amount_cents", "currency", "interval"}. Unconfigured (or dev-mock)
    scopes return None and the UI shows its free-beta copy instead.
    """
    settings = get_settings()
    out: dict[str, dict | None] = {"single": None, "all": None}
    if not settings.stripe_secret_key:
        return out
    stripe = _stripe()
    for scope, price_id in (
        ("single", settings.stripe_price_single),
        ("all", settings.stripe_price_all),
    ):
        if not price_id:
            continue
        price = stripe.Price.retrieve(price_id)
        out[scope] = {
            "amount_cents": price.get("unit_amount"),
            "currency": price.get("currency"),
            "interval": (price.get("recurring") or {}).get("interval"),
        }
    return out


def construct_event(payload: bytes, sig_header: str):
    """Verify a webhook payload's signature and return the Stripe event."""
    settings = get_settings()
    return _stripe().Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )


def extract_entitlement_change(event) -> dict | None:
    """Map a Stripe event to a normalized entitlement change, or None.

    Returns one of:
      {"action": "grant", "user_id", "language_id", "subscription_id", "customer_id"}
      {"action": "revoke", "subscription_id"}
    """
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        user_id = obj.get("client_reference_id") or meta.get("user_id")
        language_id = meta.get("language_id")
        if not (user_id and language_id):
            return None
        return {
            "action": "grant",
            "user_id": user_id,
            "language_id": language_id,
            "subscription_id": obj.get("subscription"),
            "customer_id": obj.get("customer"),
        }

    if event_type == "customer.subscription.deleted":
        return {"action": "revoke", "subscription_id": obj.get("id")}

    if event_type == "customer.subscription.updated":
        status = obj.get("status")
        if status in _INACTIVE_STATUSES:
            return {"action": "revoke", "subscription_id": obj.get("id")}
        if status in _ACTIVE_STATUSES:
            meta = obj.get("metadata") or {}
            user_id, language_id = meta.get("user_id"), meta.get("language_id")
            if not (user_id and language_id):
                return None
            return {
                "action": "grant",
                "user_id": user_id,
                "language_id": language_id,
                "subscription_id": obj.get("id"),
                "customer_id": obj.get("customer"),
            }

    return None


def extract_plan_change(event) -> dict | None:
    """Map a Stripe event to a language-plan change, or None (WP16).

    Grants require metadata.kind == 'plan' (so tutor events never set a
    plan); revokes are id-scoped, so passing a tutor subscription id to the
    plan deactivator is a harmless no-op — the webhook runs both extractors.

    Returns one of:
      {"action": "grant", "user_id", "plan_scope", "plan_language_id",
       "subscription_id", "customer_id"}
      {"action": "revoke", "subscription_id"}
    """
    event_type = event["type"]
    obj = event["data"]["object"]

    def _grant(meta, subscription_id):
        if meta.get("kind") != "plan":
            return None
        user_id = meta.get("user_id")
        scope = meta.get("plan_scope")
        if not user_id or scope not in ("single", "all"):
            return None
        language_id = meta.get("plan_language_id") or None
        if scope == "single" and not language_id:
            return None
        return {
            "action": "grant",
            "user_id": user_id,
            "plan_scope": scope,
            "plan_language_id": language_id,
            "subscription_id": subscription_id,
            "customer_id": obj.get("customer"),
        }

    if event_type == "checkout.session.completed":
        return _grant(obj.get("metadata") or {}, obj.get("subscription"))

    if event_type == "customer.subscription.deleted":
        return {"action": "revoke", "subscription_id": obj.get("id")}

    if event_type == "customer.subscription.updated":
        status = obj.get("status")
        if status in _INACTIVE_STATUSES:
            return {"action": "revoke", "subscription_id": obj.get("id")}
        if status in _ACTIVE_STATUSES:
            return _grant(obj.get("metadata") or {}, obj.get("id"))

    return None
