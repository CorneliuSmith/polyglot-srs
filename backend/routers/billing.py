"""Billing router — Stripe Checkout + webhook for the tutor add-on."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.billing import (
    get_customer_id,
    grant_entitlement,
    revoke_by_subscription,
    save_customer_id,
)
from backend.repositories.pool import privileged_connection
from backend.services import billing

logger = logging.getLogger("billing")
router = APIRouter()


class CheckoutRequest(BaseModel):
    language_id: str


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

    return {"received": True}
