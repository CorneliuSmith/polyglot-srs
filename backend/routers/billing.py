"""Billing router — Stripe Checkout + webhook for the tutor add-on."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.billing import (
    deactivate_plan_by_subscription,
    get_customer_id,
    grant_entitlement,
    revoke_by_subscription,
    save_customer_id,
    set_plan_subscription,
)
from backend.repositories.pool import privileged_connection
from backend.services import billing

logger = logging.getLogger("billing")
router = APIRouter()


class CheckoutRequest(BaseModel):
    language_id: str


class PlanCheckoutRequest(BaseModel):
    plan_scope: str = Field(pattern="^(single|all)$")
    plan_language_id: str | None = None


@router.post("/checkout")
async def checkout(
    body: CheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Start a tutor subscription.

    Real mode returns a Stripe Checkout URL to redirect to. Dev-mock mode grants
    the entitlement directly and returns {granted: true} so the gated → unlocked
    flow is testable without Stripe.
    """
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
    """The two plans' live Stripe prices (WP16d — never hardcoded).

    Unconfigured scopes come back null; the UI shows its free-beta copy.
    Fetched per request behind auth — pricing pages are low-traffic and
    stale prices are worse than a Stripe read.
    """
    if not get_settings().stripe_secret_key:
        return {"single": None, "all": None}
    return billing.list_plan_prices()


@router.post("/plan/checkout")
async def plan_checkout(
    body: PlanCheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Start (or in dev-mock, immediately grant) a language-plan subscription.

    Also the upgrade path: checking out 'all' from a single plan replaces
    the recorded plan on webhook completion.
    """
    if body.plan_scope == "single" and not body.plan_language_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A single-language plan needs plan_language_id",
        )
    if not billing.plans_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plan billing is not configured on this server",
        )
    settings = get_settings()

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
    session = billing.create_plan_checkout_session(
        user_id=user["id"],
        plan_scope=body.plan_scope,
        plan_language_id=body.plan_language_id,
        customer_id=customer_id,
        success_url=f"{base}/settings",
        cancel_url=f"{base}/settings",
    )
    return {"granted": False, "url": session["url"]}


@router.post("/portal")
async def billing_portal(user: dict = Depends(get_current_user)):
    """A Stripe Billing Portal session — plan changes prorate there (WP16b)."""
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

    return {"received": True}
