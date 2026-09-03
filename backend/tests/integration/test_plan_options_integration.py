"""The four plan options against a real database.

Owner: *"Make the 4 options … Single language with AI should be the default
but provide options to upgrade."* An option is a scope with or without AI;
the AI half lives on user_profiles.plan_ai (migration 20261013) and is
written only by billing. What is worth proving here is the round trip the
unit tests stub: the webhook's grant lands both halves, cancelling the
subscription that paid for the AI clears exactly that, `get_tutor_access`
reads it back — and that a plan counts as *backed* only when a
plan_subscriptions row stands behind it, which is what stops an unpaid
signup holding the all-languages pool.

Runs against a real Postgres (see conftest); skips without one.
"""
from __future__ import annotations

from backend.repositories.billing import (
    clear_plan_ai_by_subscription,
    deactivate_plan_by_subscription,
    plan_ai_columns_present,
    previous_plan_subscription,
    set_plan_ai,
    set_plan_subscription,
)
from backend.repositories.contributor import set_account_plan
from backend.repositories.tutor import get_tutor_access

from .conftest import requires_db

pytestmark = requires_db


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        uid = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        )
        await conn.execute(
            "INSERT INTO user_profiles (id) VALUES ($1) ON CONFLICT DO NOTHING", uid
        )
        return str(uid)


async def _lang(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def test_the_migration_is_applied_here(pool):
    async with pool.privileged_connection() as conn:
        assert await plan_ai_columns_present(conn) is True


async def test_an_option_with_ai_lands_both_halves_and_reads_back(pool):
    uid = await _user(pool, "opt-both@example.com")
    async with pool.privileged_connection() as conn:
        await set_plan_subscription(
            conn, uid, "all", None,
            subscription_id="sub_both", customer_id="cus_1", ai=True,
        )
        access = await get_tutor_access(conn, uid)
        row = await conn.fetchrow(
            "SELECT plan_scope, plan_ai, plan_ai_subscription_id "
            "FROM user_profiles WHERE id = $1", uid)
    assert access["plan_scope"] == "all"
    assert access["plan_ai"] is True
    assert access["plan_backed"] is True
    assert row["plan_ai_subscription_id"] == "sub_both"


async def test_cancelling_the_plan_that_paid_for_ai_clears_the_pool_only(pool):
    """The scope stays (owner-pending WP16e); the pool the subscription paid
    for goes."""
    uid = await _user(pool, "opt-cancel@example.com")
    async with pool.privileged_connection() as conn:
        await set_plan_subscription(
            conn, uid, "all", None, subscription_id="sub_c1", ai=True,
        )
        await deactivate_plan_by_subscription(conn, "sub_c1")
        access = await get_tutor_access(conn, uid)
    assert access["plan_scope"] == "all"
    assert access["plan_ai"] is False
    assert access["plan_backed"] is False


async def test_the_add_on_is_cleared_only_by_its_own_subscription(pool):
    uid = await _user(pool, "opt-addon@example.com")
    lang = await _lang(pool, "op1")
    async with pool.privileged_connection() as conn:
        await set_plan_subscription(
            conn, uid, "single", lang, subscription_id="sub_plan", ai=False,
        )
        await set_plan_ai(conn, uid, True, "sub_ai")
        # A stranger's id, and then the plan's own: neither pays for the AI.
        assert await clear_plan_ai_by_subscription(conn, "sub_other") == 0
        assert await clear_plan_ai_by_subscription(conn, "sub_plan") == 0
        assert (await get_tutor_access(conn, uid))["plan_ai"] is True
        assert await clear_plan_ai_by_subscription(conn, "sub_ai") == 1
        assert (await get_tutor_access(conn, uid))["plan_ai"] is False


async def test_a_scope_nobody_paid_for_is_not_backed(pool):
    """user_profiles.plan_scope defaults to 'all'. A fresh account has the
    column, and nothing behind it."""
    uid = await _user(pool, "opt-fresh@example.com")
    async with pool.privileged_connection() as conn:
        access = await get_tutor_access(conn, uid)
    assert access["plan_scope"] == "all"
    assert access["plan_backed"] is False


async def test_an_admin_override_backs_the_plan(pool):
    """The beta promise, and the reviewer case: an account an admin sets to
    a plan keeps its tier once money is on."""
    uid = await _user(pool, "opt-admin@example.com")
    async with pool.privileged_connection() as conn:
        assert await set_account_plan(conn, uid, "all", None) is True
        access = await get_tutor_access(conn, uid)
        assert access["plan_backed"] is True
        assert await previous_plan_subscription(conn, uid) == "admin-override"


async def test_a_grant_without_the_ai_flag_leaves_plan_ai_alone(pool):
    """A subscription minted before the flag existed carries no 'ai' key:
    ai=None must not switch a pool off that something else pays for."""
    uid = await _user(pool, "opt-legacy@example.com")
    async with pool.privileged_connection() as conn:
        await set_plan_ai(conn, uid, True, "sub_ai2")
        await set_plan_subscription(
            conn, uid, "all", None, subscription_id="sub_old", ai=None,
        )
        assert (await get_tutor_access(conn, uid))["plan_ai"] is True
