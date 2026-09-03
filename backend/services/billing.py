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

import logging

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
    """Checkout for the AI add-on on its own — "Add AI" to a plan bought
    without it.

    metadata.kind='ai' marks it as the plan-level pool (plan_ai on the
    profile), which is what the four options sell. Sessions minted before
    this carried only user_id + language_id and granted a per-language
    tutor_entitlements row; `extract_entitlement_change` still serves those
    subscriptions' lifecycle events, and skips these.
    """
    settings = get_settings()
    meta = {"kind": "ai", "user_id": user_id, "language_id": language_id}
    session = _stripe().checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        client_reference_id=user_id,
        metadata=meta,
        # Mirror onto the subscription so lifecycle webhooks can reconcile.
        subscription_data={"metadata": meta},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"url": session["url"], "session_id": session["id"]}


def _plan_meta(user_id: str, plan_scope: str, plan_language_id: str | None,
               ai: bool) -> dict:
    """The metadata every plan session and its subscription carry. `ai` is
    a string because Stripe metadata is strings: '1' or '0', never absent,
    so a webhook can tell "bought without AI" from "minted before AI
    existed"."""
    return {
        "kind": "plan",
        "user_id": user_id,
        "plan_scope": plan_scope,
        "plan_language_id": plan_language_id or "",
        "ai": "1" if ai else "0",
    }


def create_plan_checkout_session(
    *,
    user_id: str,
    plan_scope: str,
    plan_language_id: str | None,
    customer_id: str,
    success_url: str,
    cancel_url: str,
    ai: bool = False,
) -> dict:
    """Create a Stripe Checkout session for one of the four plan options.

    An option is a scope (single / all) with or without AI. With AI, the
    session carries TWO recurring line items — the plan's Price and the AI
    add-on's Price — and Stripe makes them one subscription with one
    charge, which is the whole point: "Single language + AI" is a thing a
    learner buys, not two things they assemble. Both Prices must bill on
    the same interval (monthly) or Stripe refuses the session.

    metadata.kind='plan' is what separates plan webhooks from add-on
    webhooks — every product shares the /webhook endpoint.
    """
    settings = get_settings()
    price = (
        settings.stripe_price_single
        if plan_scope == "single"
        else settings.stripe_price_all
    )
    line_items = [{"price": price, "quantity": 1}]
    if ai:
        line_items.append({"price": settings.stripe_price_id, "quantity": 1})
    meta = _plan_meta(user_id, plan_scope, plan_language_id, ai)
    session = _stripe().checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=line_items,
        client_reference_id=user_id,
        metadata=meta,
        subscription_data={"metadata": meta},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"url": session["url"], "session_id": session["id"]}


def create_priced_plan_checkout_session(
    *,
    user_id: str,
    plan_scope: str,
    plan_language_id: str | None,
    monthly_cents: int,
    currency: str,
    customer_id: str,
    success_url: str,
    cancel_url: str,
    ai: bool = False,
) -> dict:
    """Checkout for an ADMIN-PRICED subscription (the generalized charge).

    Same metadata — and therefore the exact same webhook grant/revoke path —
    as the fixed plans, but the amount comes from price_data: an inline
    price minted at checkout time. No dashboard Price object exists or is
    needed, which is what lets the admin set any monthly charge per account
    from the panel instead of managing Stripe products. The admin's amount
    is the whole price, AI included or not — `ai` only records which of
    the four options the charge is for.
    """
    meta = _plan_meta(user_id, plan_scope, plan_language_id, ai)
    session = _stripe().checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{
            "price_data": {
                "currency": currency,
                "unit_amount": monthly_cents,
                "recurring": {"interval": "month"},
                "product_data": {"name": "PolyglotSRS subscription"},
            },
            "quantity": 1,
        }],
        client_reference_id=user_id,
        metadata=meta,
        subscription_data={"metadata": meta},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"url": session["url"], "session_id": session["id"]}


def create_topup_checkout_session(
    *,
    user_id: str,
    customer_id: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """One-time Checkout for an AI top-up (mode='payment', no subscription).

    The price is inline from Settings — no dashboard Price object — and
    metadata.kind='topup' is what routes the completed-session webhook to
    the top-up grant instead of the subscription lanes.
    """
    settings = get_settings()
    session = _stripe().checkout.Session.create(
        mode="payment",
        customer=customer_id,
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": settings.topup_price_cents,
                "product_data": {
                    "name": f"AI top-up — {settings.topup_messages} messages this month",
                },
            },
            "quantity": 1,
        }],
        client_reference_id=user_id,
        metadata={
            "kind": "topup",
            "user_id": user_id,
            "messages": str(settings.topup_messages),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"url": session["url"], "session_id": session["id"]}


def cancel_subscription(subscription_id: str) -> bool:
    """End a subscription now, crediting the unused part of the period.

    Checkout only ever CREATES subscriptions, so an upgrade (single → all,
    or adding AI by re-buying the plan) leaves the old one billing beside
    the new one unless something ends it. This is that something, run from
    the webhook once the new plan has landed — never before, so a failed
    payment cannot leave the learner with nothing. Best-effort: a Stripe
    error is logged and returns False; the admin panel shows the customer's
    subscriptions for the manual fix.
    """
    if not subscription_id or not subscription_id.startswith("sub_"):
        return False  # 'mock-plan', 'admin-free': nothing at Stripe to end
    try:
        _stripe().Subscription.cancel(subscription_id, prorate=True)
        return True
    except Exception:  # noqa: BLE001 — logged; never fails the webhook
        logging.getLogger("billing").exception(
            "could not cancel superseded subscription %s", subscription_id
        )
        return False


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


def ai_configured() -> bool:
    """True when an option WITH AI can be sold: the add-on Price is set (or
    dev-mock). Separate from plans_configured so a deploy that has priced
    the plans but not the add-on still sells the two no-AI options."""
    settings = get_settings()
    if settings.stripe_dev_mock:
        return True
    return bool(settings.stripe_secret_key and settings.stripe_price_id)


def list_plan_prices() -> dict[str, dict | None]:
    """The plans' and the AI add-on's live prices, from Stripe — never
    hardcoded (WP16d).

    Returns {"single", "all", "ai_addon"} → {"amount_cents", "currency",
    "interval"} | None. The four options are priced from these three: an
    option with AI costs its scope's price plus the add-on's. Unconfigured
    (or dev-mock) ids return None and the UI shows its unpriced copy.
    """
    settings = get_settings()
    out: dict[str, dict | None] = {"single": None, "all": None, "ai_addon": None}
    if not settings.stripe_secret_key:
        return out
    stripe = _stripe()
    for scope, price_id in (
        ("single", settings.stripe_price_single),
        ("all", settings.stripe_price_all),
        ("ai_addon", settings.stripe_price_id),
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
        # kind='ai' sessions are the plan-level pool (extract_ai_change);
        # this path is for subscriptions minted before that existed.
        if meta.get("kind"):
            return None
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
            if meta.get("kind"):
                return None
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


def extract_ai_change(event) -> dict | None:
    """Map a Stripe event to a change of the plan-level AI pool, or None.

    The stand-alone add-on ("Add AI" on a plan bought without it) is its own
    subscription with metadata.kind='ai'. Grants set plan_ai on the profile
    and remember this subscription as what pays for it; revokes are keyed on
    the subscription id, so the deletion of a plan or a legacy per-language
    subscription cannot switch off a pool it never paid for.

    Returns one of:
      {"action": "grant", "user_id", "subscription_id", "customer_id"}
      {"action": "revoke", "subscription_id"}
    """
    event_type = event["type"]
    obj = event["data"]["object"]

    def _grant(meta, subscription_id):
        if meta.get("kind") != "ai":
            return None
        user_id = obj.get("client_reference_id") or meta.get("user_id")
        if not user_id:
            return None
        return {
            "action": "grant",
            "user_id": user_id,
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
        # 'ai' is one of the four options' halves. A subscription minted
        # before the flag existed carries no 'ai' key at all: None, so the
        # repository leaves plan_ai as it is rather than switching it off.
        ai_flag = meta.get("ai")
        return {
            "action": "grant",
            "user_id": user_id,
            "plan_scope": scope,
            "plan_language_id": language_id,
            "subscription_id": subscription_id,
            "customer_id": obj.get("customer"),
            "ai": None if ai_flag is None else ai_flag == "1",
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


def extract_topup(event) -> dict | None:
    """Map a Stripe event to a top-up grant, or None.

    One-time payments only complete — there is no lifecycle to track — so
    the only event that matters is checkout.session.completed with
    metadata.kind='topup'. The session id rides along as the idempotency
    key: grant_topup's UNIQUE external_id makes a redelivered event a no-op.

    Returns {"user_id", "messages", "session_id"} or None.
    """
    if event["type"] != "checkout.session.completed":
        return None
    obj = event["data"]["object"]
    meta = obj.get("metadata") or {}
    if meta.get("kind") != "topup":
        return None
    user_id = obj.get("client_reference_id") or meta.get("user_id")
    try:
        messages = int(meta.get("messages") or 0)
    except (TypeError, ValueError):
        return None
    if not user_id or messages <= 0:
        return None
    return {
        "user_id": user_id,
        "messages": messages,
        "session_id": obj.get("id"),
    }
