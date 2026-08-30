"""Top-ups and the monetization flag on the real schema (migration 20261006).

The unit tests pin the arithmetic with mocks; these prove the SQL: the
UNIQUE(external_id) dedupe that makes webhook redeliveries grant once, the
window SUM the allowance reads, and the app_flags round-trip the admin
toggle drives — all against the actual tables.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.repositories.billing import count_topup_messages, grant_topup
from backend.repositories.flags import MONETIZATION, get_flag, set_flag
from backend.services.allowance import get_allowance

from .conftest import requires_db

pytestmark = requires_db


async def _seed_account(pool, email: str) -> tuple[str, str]:
    async with pool.privileged_connection() as conn:
        lang = str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ('qq', 'Quenya', false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        ))
        uid = str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id) VALUES ($1, $2) "
            "ON CONFLICT (id) DO NOTHING",
            uid, lang,
        )
    return lang, uid


async def test_duplicate_external_id_grants_exactly_once(pool):
    """A redelivered checkout.session.completed must not double-grant: the
    session id is UNIQUE and the second INSERT is a no-op."""
    _, uid = await _seed_account(pool, "topup-dedupe@example.com")
    window = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0,
                                       microsecond=0)
    async with pool.privileged_connection() as conn:
        assert await grant_topup(conn, uid, 200, "cs_dup_1") is True
        assert await grant_topup(conn, uid, 200, "cs_dup_1") is True  # retry
        assert await count_topup_messages(conn, uid, window) == 200

        # A genuinely new purchase stacks.
        assert await grant_topup(conn, uid, 200, "cs_dup_2") is True
        assert await count_topup_messages(conn, uid, window) == 400

        # The SUM is windowed: next month's pool starts clean.
        next_month = (window + timedelta(days=32)).replace(day=1)
        assert await count_topup_messages(conn, uid, next_month) == 0


async def test_a_topup_raises_this_months_allowance(pool):
    """The whole seam the tutor draws: get_allowance over the real tables,
    with a purchased top-up landing in the current month's limit — on the
    plan that ships with NO AI, where the top-up IS the à-la-carte path."""
    lang, uid = await _seed_account(pool, "topup-allowance@example.com")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE user_profiles SET plan_scope = 'single', "
            "plan_language_id = $2 WHERE id = $1",
            uid, lang,
        )

    class PaidSettings:
        tutor_free_access = False
        tutor_free_monthly_messages = 20
        tutor_single_monthly_messages = 0
        tutor_all_monthly_messages = 300
        tutor_plus_monthly_messages = 200

    with patch("backend.services.allowance.get_settings",
               return_value=PaidSettings()):
        before = await get_allowance(uid, lang)
        async with pool.privileged_connection() as conn:
            await grant_topup(conn, uid, 200, "cs_allow_1")
        after = await get_allowance(uid, lang)

    assert before["tier"] == "single"
    assert before["limit"] == 0            # $7 plan: no AI included
    assert after["limit"] == 200           # the top-up IS the AI
    assert after["remaining"] == 200


async def test_monetization_flag_round_trip(pool):
    """Seeded OFF by the migration; the admin toggle flips it and a
    re-applied seed must not stomp the choice (ON CONFLICT DO NOTHING)."""
    _, uid = await _seed_account(pool, "flag-admin@example.com")
    async with pool.privileged_connection() as conn:
        assert await get_flag(conn, MONETIZATION) is False  # the seed row

        assert await set_flag(conn, MONETIZATION, True, uid) is True
        assert await get_flag(conn, MONETIZATION) is True

        # What `supabase db push` re-running the seed would execute.
        await conn.execute(
            "INSERT INTO app_flags (key, enabled) VALUES ('monetization', false) "
            "ON CONFLICT (key) DO NOTHING"
        )
        assert await get_flag(conn, MONETIZATION) is True  # choice survives

        assert await set_flag(conn, MONETIZATION, False, uid) is True
        assert await get_flag(conn, MONETIZATION) is False
