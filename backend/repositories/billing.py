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


async def plan_ai_columns_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20261013 (plan_ai) has been applied.

    Probed, never caught: every pooled connection runs one transaction, and
    an UndefinedColumnError aborts it for every later statement — see
    docs/decisions/0001. A webhook that 500s on an unmigrated column would
    make Stripe retry a payment it has already taken.
    """
    n = await conn.fetchval(
        """
        SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'user_profiles'
           AND column_name IN ('plan_ai', 'plan_ai_subscription_id')
        """
    )
    return int(n or 0) == 2


async def previous_plan_subscription(
    conn: asyncpg.Connection, user_id: str
) -> str | None:
    """The Stripe subscription currently backing this user's plan, if any —
    what an upgrade has to cancel, since Checkout only ever creates."""
    return await conn.fetchval(
        "SELECT stripe_subscription_id FROM plan_subscriptions "
        "WHERE user_id = $1 AND is_active",
        user_id,
    )


async def set_plan_ai(
    conn: asyncpg.Connection, user_id: str, on: bool,
    subscription_id: str | None,
) -> bool:
    """Turn the plan's AI pool on or off, remembering which subscription
    pays for it. Returns False (and writes nothing) when the column has not
    been migrated yet, so the caller can say so instead of failing."""
    if not await plan_ai_columns_present(conn):
        return False
    await conn.execute(
        """
        INSERT INTO user_profiles (id, plan_ai, plan_ai_subscription_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET
            plan_ai = EXCLUDED.plan_ai,
            plan_ai_subscription_id = EXCLUDED.plan_ai_subscription_id
        """,
        user_id, on, subscription_id if on else None,
    )
    return True


async def clear_plan_ai_by_subscription(
    conn: asyncpg.Connection, subscription_id: str
) -> int:
    """The subscription that paid for the AI pool has ended: switch the pool
    off, and only the pool — the plan's scope is a separate decision."""
    if not await plan_ai_columns_present(conn):
        return 0
    result = await conn.execute(
        "UPDATE user_profiles SET plan_ai = false, plan_ai_subscription_id = NULL "
        "WHERE plan_ai_subscription_id = $1",
        subscription_id,
    )
    return int(result.split()[-1])


async def set_plan_subscription(
    conn: asyncpg.Connection,
    user_id: str,
    plan_scope: str,
    plan_language_id: str | None,
    *,
    subscription_id: str | None = None,
    customer_id: str | None = None,
    ai: bool | None = None,
) -> None:
    """Record the Stripe subscription behind a plan AND enforce it (WP16).

    The profile's plan_scope/plan_language_id are what the app checks, so
    the paid plan lands there in the same call. *ai* is the other half of
    the four options: True/False sets whether this plan includes the AI
    pool (paid for by the same subscription); None leaves it alone, for
    callers that only know the scope.
    """
    await conn.execute(
        """
        INSERT INTO plan_subscriptions
            (user_id, plan_scope, plan_language_id, stripe_subscription_id,
             stripe_customer_id, is_active, updated_at)
        VALUES ($1, $2, $3, $4, $5, true, now())
        ON CONFLICT (user_id) DO UPDATE SET
            plan_scope = EXCLUDED.plan_scope,
            plan_language_id = EXCLUDED.plan_language_id,
            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
            stripe_customer_id = EXCLUDED.stripe_customer_id,
            is_active = true,
            updated_at = now()
        """,
        user_id, plan_scope, plan_language_id, subscription_id, customer_id,
    )
    await conn.execute(
        """
        INSERT INTO user_profiles (id, plan_scope, plan_language_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET
            plan_scope = EXCLUDED.plan_scope,
            plan_language_id = EXCLUDED.plan_language_id
        """,
        user_id, plan_scope, plan_language_id,
    )
    if ai is not None:
        await set_plan_ai(conn, user_id, ai, subscription_id)


async def _custom_prices_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20260920 has landed. Probed with to_regclass (never
    raises) because a thrown UndefinedTableError aborts the whole pooled
    transaction — the checkout path must degrade to standard pricing, not
    take the endpoint down."""
    return bool(
        await conn.fetchval("SELECT to_regclass('custom_prices') IS NOT NULL")
    )


async def get_custom_price(
    conn: asyncpg.Connection, user_id: str
) -> dict | None:
    """The admin-set monthly charge for this account, or None (standard
    plan pricing applies). A missing migration reads as None on purpose —
    the learner-facing checkout must never 500 over an admin feature."""
    if not await _custom_prices_present(conn):
        return None
    row = await conn.fetchrow(
        "SELECT monthly_cents, currency, note FROM custom_prices "
        "WHERE user_id = $1",
        user_id,
    )
    return dict(row) if row else None


async def set_custom_price(
    conn: asyncpg.Connection,
    user_id: str,
    monthly_cents: int | None,
    *,
    currency: str = "usd",
    note: str | None = None,
) -> bool:
    """Upsert the account's monthly charge; None clears it back to standard
    pricing. Returns False when the migration hasn't landed so the admin
    endpoint can 503 naming it — an admin's write failing silently is worse
    than a learner's read degrading."""
    if not await _custom_prices_present(conn):
        return False
    if monthly_cents is None:
        await conn.execute(
            "DELETE FROM custom_prices WHERE user_id = $1", user_id
        )
        return True
    await conn.execute(
        """
        INSERT INTO custom_prices (user_id, monthly_cents, currency, note,
                                   updated_at)
        VALUES ($1, $2, $3, $4, now())
        ON CONFLICT (user_id) DO UPDATE SET
            monthly_cents = EXCLUDED.monthly_cents,
            currency = EXCLUDED.currency,
            note = EXCLUDED.note,
            updated_at = now()
        """,
        user_id, monthly_cents, currency, note,
    )
    return True


async def _topups_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20261006 has landed. to_regclass, never raises —
    a thrown UndefinedTableError would abort the pooled transaction."""
    return bool(
        await conn.fetchval("SELECT to_regclass('allowance_topups') IS NOT NULL")
    )


async def grant_topup(
    conn: asyncpg.Connection, user_id: str, messages: int, external_id: str
) -> bool:
    """Record a purchased top-up. external_id (the Stripe Checkout session
    id; 'mock-*' in dev-mock) is UNIQUE, so webhook retries and
    double-deliveries grant exactly once — the duplicate INSERT is a no-op.
    Returns False when migration 20261006 hasn't been applied."""
    if not await _topups_present(conn):
        return False
    await conn.execute(
        """
        INSERT INTO allowance_topups (user_id, messages, external_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (external_id) DO NOTHING
        """,
        user_id, messages, external_id,
    )
    return True


async def count_topup_messages(
    conn: asyncpg.Connection, user_id: str, window_start: datetime
) -> int:
    """Messages purchased in the current window. A top-up belongs to the
    calendar month it was bought in — one SUM over the window, no mutable
    credit ledger. Missing migration reads as 0 on purpose."""
    if not await _topups_present(conn):
        return 0
    return await conn.fetchval(
        """
        SELECT COALESCE(SUM(messages), 0) FROM allowance_topups
        WHERE user_id = $1 AND created_at >= $2
        """,
        user_id, window_start,
    )


async def deactivate_plan_by_subscription(
    conn: asyncpg.Connection, subscription_id: str
) -> int:
    """Mark a plan subscription inactive. Returns rows affected.

    Deliberately does NOT touch the profile's plan SCOPE: what a canceled
    account keeps of its content is the owner's free-tier decision (ROADMAP
    WP16e), and beta accounts were promised their access. The AI pool is
    different — it is what the subscription was paying for — so if this
    subscription carried it, it goes.
    """
    result = await conn.execute(
        "UPDATE plan_subscriptions SET is_active = false, updated_at = now() "
        "WHERE stripe_subscription_id = $1",
        subscription_id,
    )
    await clear_plan_ai_by_subscription(conn, subscription_id)
    return int(result.split()[-1])
