"""Billing repository — Stripe customer mapping + entitlement writes.

All writes here happen on the privileged (service-role) connection: webhooks
have no authenticated user, and entitlements are read-only to users by RLS.
"""
from __future__ import annotations

from datetime import datetime

import asyncpg


async def get_customer_id(conn: asyncpg.Connection, user_id: str) -> str | None:
    return await conn.fetchval(
        "SELECT stripe_customer_id FROM billing_customers WHERE user_id = $1", user_id
    )


async def save_customer_id(
    conn: asyncpg.Connection, user_id: str, customer_id: str
) -> None:
    await conn.execute(
        """
        INSERT INTO billing_customers (user_id, stripe_customer_id)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET stripe_customer_id = EXCLUDED.stripe_customer_id
        """,
        user_id,
        customer_id,
    )


async def grant_entitlement(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    *,
    subscription_id: str | None = None,
    customer_id: str | None = None,
    expires_at: datetime | None = None,
) -> None:
    """Activate the tutor entitlement for (user, language)."""
    await conn.execute(
        """
        INSERT INTO tutor_entitlements
            (user_id, language_id, is_active, expires_at,
             stripe_subscription_id, stripe_customer_id)
        VALUES ($1, $2, true, $3, $4, $5)
        ON CONFLICT (user_id, language_id) DO UPDATE SET
            is_active = true,
            expires_at = EXCLUDED.expires_at,
            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
            stripe_customer_id = EXCLUDED.stripe_customer_id
        """,
        user_id,
        language_id,
        expires_at,
        subscription_id,
        customer_id,
    )


async def revoke_by_subscription(
    conn: asyncpg.Connection, subscription_id: str
) -> int:
    """Deactivate entitlements tied to a subscription. Returns rows affected."""
    result = await conn.execute(
        "UPDATE tutor_entitlements SET is_active = false "
        "WHERE stripe_subscription_id = $1",
        subscription_id,
    )
    # asyncpg returns "UPDATE <n>"
    return int(result.split()[-1])
