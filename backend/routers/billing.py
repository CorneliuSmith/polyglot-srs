"""Billing router — Stripe Checkout + webhook for the tutor add-on."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.billing import (
    deactivate_plan_by_subscription,
    get_custom_price,
    get_customer_id,
    grant_entitlement,
    grant_topup,
    revoke_by_subscription,
    save_customer_id,
    set_plan_subscription,
)
from backend.repositories.pool import privileged_connection
from backend.services import billing
from backend.services.flags import monetization_enabled

logger = logging.getLogger("billing")
router = APIRouter()


class CheckoutRequest(BaseModel):
    language_id: str


class PlanCheckoutRequest(BaseModel):
    plan_scope: str = Field(pattern="^(single|all)$")
    plan_language_id: str | None = None


async def _require_monetization() -> None:
    """Every purchase path checks the master switch (owner: money features
    stay OFF until the employer clearance lands). 503, not 403 — nothing is
    wrong with the account; the feature isn't turned on."""
    if not await monetization_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monetization is switched off",
        )


@router.post("/checkout")
async def checkout(
    body: CheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Start an AI add-on subscription for a language.

    Real mode returns a Stripe Checkout URL to redirect to. Dev-mock mode grants
    the entitlement directly and returns {granted: true} so the gated → unlocked
    flow is testable without Stripe.
    """
    await _require_monetization()
    if not billing.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured on this server",
        )
    settings = get_settings()

    if settings.stripe_dev_mock:
        async with privileged_connection() as conn:
            await grant_entitlement(
                conn, user["id"], body.language_id,
                subscription_id="mock", customer_id="mock",
            )
        return {"granted": True, "url": None}

    async with privileged_connection() as conn:
        customer_id = await get_customer_id(conn, user["id"])
        if not customer_id:
            customer_id = billing.create_customer(user.get("email"), user["id"])
            await save_customer_id(conn, user["id"], customer_id)

    base = settings.app_base_url.rstrip("/")
    session = billing.create_checkout_session(
        user_id=user["id"],
        language_id=body.language_id,
        customer_id=customer_id,
        success_url=f"{base}/tutor",
        cancel_url=f"{base}/tutor",
    )
    return {"granted": False, "url": session["url"]}


@router.get("/plan/prices")
async def plan_prices(user: dict = Depends(get_current_user)):
    """The plans' live prices for THIS account (WP16d — never hardcoded).

    Standard accounts see the two Stripe plan prices; unconfigured scopes
    come back null and the UI shows its free-beta copy. An account with an
    admin-set monthly charge sees THAT amount on both scopes (the charge is
    per account, whichever scope they pick) plus a `custom` field naming it.
    Fetched per request behind auth — pricing pages are low-traffic and
    stale prices are worse than a Stripe read.

    Also carries the monetization master switch: `monetization: false`
    means the UI shows no prices, upgrade buttons, top-ups, or the tip
    jar anywhere — one flag, every surface.
    """
    if not await monetization_enabled():
        return {"single": None, "all": None, "custom": None,
                "topup": None, "monetization": False}
    settings = get_settings()
    # The one-time top-up is priced from Settings (inline price_data), so
    # its price is known without a Stripe read.
    topup = (
        {"amount_cents": settings.topup_price_cents, "currency": "usd",
         "messages": settings.topup_messages}
        if billing.is_configured() else None
    )
    async with privileged_connection() as conn:
        custom = await get_custom_price(conn, user["id"])
    custom_price = (
        {"amount_cents": custom["monthly_cents"],
         "currency": custom["currency"], "interval": "month"}
        if custom else None
    )
    if custom_price:
        return {"single": custom_price, "all": custom_price,
                "custom": custom_price, "topup": topup, "monetization": True}
    if not settings.stripe_secret_key:
        return {"single": None, "all": None, "custom": None,
                "topup": topup, "monetization": True}
    return {**billing.list_plan_prices(), "custom": None,
            "topup": topup, "monetization": True}


@router.post("/plan/checkout")
async def plan_checkout(
    body: PlanCheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Start (or in dev-mock, immediately grant) a language-plan subscription.

    Also the upgrade path: checking out 'all' from a single plan replaces
    the recorded plan on webhook completion.
    """
    await _require_monetization()
    if body.plan_scope == "single" and not body.plan_language_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A single-language plan needs plan_language_id",
        )
    settings = get_settings()

    # An admin-set monthly charge outranks the fixed plan prices: it's the
    # generalized lane — any amount, no dashboard Price object.
    async with privileged_connection() as conn:
        custom = await get_custom_price(conn, user["id"])

    # Priced at zero by the admin = subscribed free of charge. No Stripe
    # round trip; the plan lands exactly as a paid webhook would land it.
    if custom and custom["monthly_cents"] == 0:
        async with privileged_connection() as conn:
            await set_plan_subscription(
                conn, user["id"], body.plan_scope, body.plan_language_id,
                subscription_id="admin-free", customer_id=None,
            )
        return {"granted": True, "url": None}

    # Custom pricing needs only the secret key (the price is inline);
    # standard pricing needs the configured Price ids too.
    configured = (
        bool(settings.stripe_secret_key) or settings.stripe_dev_mock
        if custom
        else billing.plans_configured()
    )
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plan billing is not configured on this server",
        )

    if settings.stripe_dev_mock:
        async with privileged_connection() as conn:
            await set_plan_subscription(
                conn, user["id"], body.plan_scope, body.plan_language_id,
                subscription_id="mock-plan", customer_id="mock",
            )
        return {"granted": True, "url": None}

    async with privileged_connection() as conn:
        customer_id = await get_customer_id(conn, user["id"])
        if not customer_id:
            customer_id = billing.create_customer(user.get("email"), user["id"])
            await save_customer_id(conn, user["id"], customer_id)

    base = settings.app_base_url.rstrip("/")
    if custom:
        session = billing.create_priced_plan_checkout_session(
            user_id=user["id"],
            plan_scope=body.plan_scope,
            plan_language_id=body.plan_language_id,
            monthly_cents=custom["monthly_cents"],
            currency=custom["currency"],
            customer_id=customer_id,
            success_url=f"{base}/settings",
            cancel_url=f"{base}/settings",
        )
    else:
        session = billing.create_plan_checkout_session(
            user_id=user["id"],
            plan_scope=body.plan_scope,
            plan_language_id=body.plan_language_id,
            customer_id=customer_id,
            success_url=f"{base}/settings",
            cancel_url=f"{base}/settings",
        )
    return {"granted": False, "url": session["url"]}


@router.post("/topup")
async def topup(user: dict = Depends(get_current_user)):
    """Buy a one-time AI top-up — messages added to the CURRENT calendar
    month's pool (they don't roll over; the button says so before charging).

    Real mode returns a Stripe Checkout URL (mode='payment'); the completed
    webhook records the grant. Dev-mock grants directly so the exhausted →
    topped-up flow is testable without Stripe.
    """
    await _require_monetization()
    if not billing.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured on this server",
        )
    settings = get_settings()

    if settings.stripe_dev_mock:
        async with privileged_connection() as conn:
            ok = await grant_topup(
                conn, user["id"], settings.topup_messages, f"mock-{uuid4()}"
            )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Top-ups need migration 20261006 applied — "
                    "check /api/health/schema"
                ),
            )
        return {"granted": True, "url": None}

    async with privileged_connection() as conn:
        customer_id = await get_customer_id(conn, user["id"])
        if not customer_id:
            customer_id = billing.create_customer(user.get("email"), user["id"])
            await save_customer_id(conn, user["id"], customer_id)

    base = settings.app_base_url.rstrip("/")
    session = billing.create_topup_checkout_session(
        user_id=user["id"],
        customer_id=customer_id,
        success_url=f"{base}/tutor",
        cancel_url=f"{base}/tutor",
    )
    return {"granted": False, "url": session["url"]}


@router.post("/portal")
async def billing_portal(user: dict = Depends(get_current_user)):
    """A Stripe Billing Portal session — plan changes prorate there (WP16b)."""
    await _require_monetization()
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured on this server",
        )
    async with privileged_connection() as conn:
        customer_id = await get_customer_id(conn, user["id"])
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing account yet — start a subscription first",
        )
    url = billing.create_portal_session(
        customer_id=customer_id,
        return_url=f"{settings.app_base_url.rstrip('/')}/settings",
    )
    return {"url": url}


@router.post("/webhook")
async def webhook(request: Request):
    """Handle Stripe subscription lifecycle events (grant/revoke entitlements).

    Public endpoint: authenticated by Stripe's signature, not a user session.
    """
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = billing.construct_event(payload, sig)
    except Exception as exc:  # noqa: BLE001 — bad signature / malformed payload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature"
        ) from exc

    change = billing.extract_entitlement_change(event)
    if change:
        async with privileged_connection() as conn:
            if change["action"] == "grant":
                await grant_entitlement(
                    conn, change["user_id"], change["language_id"],
                    subscription_id=change.get("subscription_id"),
                    customer_id=change.get("customer_id"),
                )
            elif change["action"] == "revoke":
                await revoke_by_subscription(conn, change["subscription_id"])
        logger.info("billing webhook %s -> %s", event["type"], change["action"])

    # Language plans share the endpoint (WP16). Revokes are id-scoped, so
    # running both extractors never cross-fires: a tutor subscription id
    # can't match a plan_subscriptions row and vice versa.
    plan_change = billing.extract_plan_change(event)
    if plan_change:
        async with privileged_connection() as conn:
            if plan_change["action"] == "grant":
                await set_plan_subscription(
                    conn, plan_change["user_id"], plan_change["plan_scope"],
                    plan_change["plan_language_id"],
                    subscription_id=plan_change.get("subscription_id"),
                    customer_id=plan_change.get("customer_id"),
                )
            elif plan_change["action"] == "revoke":
                await deactivate_plan_by_subscription(
                    conn, plan_change["subscription_id"]
                )
        logger.info(
            "billing webhook %s -> plan %s", event["type"], plan_change["action"]
        )

    # One-time top-ups: kind='topup' sessions only ever complete. The
    # session id is the idempotency key, so a redelivered event is a no-op.
    topup_grant = billing.extract_topup(event)
    if topup_grant:
        async with privileged_connection() as conn:
            await grant_topup(
                conn, topup_grant["user_id"], topup_grant["messages"],
                topup_grant["session_id"],
            )
        logger.info("billing webhook %s -> topup grant", event["type"])

    return {"received": True}
