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
