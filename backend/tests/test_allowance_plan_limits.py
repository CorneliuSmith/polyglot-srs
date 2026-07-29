"""get_allowance honoring an admin's stored plan-limit override.

Before this, the four tiers' monthly caps were Settings/env constants — an
admin had no lever short of a redeploy. plan_message_limits (migration
20260907) makes them editable at runtime; these tests pin the fallback
chain: DB override wins, Settings/env is the default, and an unmigrated
deploy (get_plan_message_limits returns None) behaves exactly as before.
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.allowance import effective_plan_limits, get_allowance


class FakeSettings:
    tutor_free_access = False
    tutor_free_monthly_messages = 20
    tutor_single_monthly_messages = 100
    tutor_all_monthly_messages = 300
    tutor_plus_monthly_messages = 1000


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield AsyncMock()


DEFAULT_ACCESS = {"access": "default", "daily_cap": None, "plan_scope": None}


def _patches(plan_limits, access=DEFAULT_ACCESS, entitled=False, messages_used=0):
    return [
        patch("backend.services.allowance.get_settings", return_value=FakeSettings()),
        patch("backend.services.allowance.rls_connection", _fake_rls),
        patch("backend.services.allowance.get_tutor_access",
              new=AsyncMock(return_value=access)),
        patch("backend.services.allowance.get_plan_message_limits",
              new=AsyncMock(return_value=plan_limits)),
        patch("backend.services.allowance.has_tutor_entitlement",
              new=AsyncMock(return_value=entitled)),
        patch("backend.services.allowance.count_tutor_messages",
              new=AsyncMock(return_value=messages_used)),
    ]


async def _allowance(**kwargs):
    patches = _patches(**kwargs)
    for p in patches:
        p.start()
    try:
        return await get_allowance("user-1", "lang-1")
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_no_override_row_falls_back_to_settings_for_free_tier():
    # Unmigrated deploy, or a tier nobody has ever edited.
    allowance = await _allowance(plan_limits=None)
    assert allowance["tier"] == "free"
    assert allowance["limit"] == 20


@pytest.mark.asyncio
async def test_an_admin_edit_overrides_the_settings_default():
    allowance = await _allowance(plan_limits={"free": 50})
    assert allowance["limit"] == 50


@pytest.mark.asyncio
async def test_editing_one_tier_does_not_touch_the_others():
    allowance = await _allowance(
        plan_limits={"free": 50},
        access={"access": "default", "daily_cap": None, "plan_scope": "all"},
    )
    assert allowance["tier"] == "all"
    assert allowance["limit"] == 300  # untouched Settings default


@pytest.mark.asyncio
async def test_plus_tier_override_applies_to_a_tutor_entitlement():
    allowance = await _allowance(plan_limits={"plus": 2000}, entitled=True)
    assert allowance["tier"] == "plus"
    assert allowance["limit"] == 2000


@pytest.mark.asyncio
async def test_single_and_all_scopes_each_read_their_own_override():
    single = await _allowance(
        plan_limits={"single": 150},
        access={"access": "default", "daily_cap": None, "plan_scope": "single"},
    )
    assert single["limit"] == 150

    all_scope = await _allowance(
        plan_limits={"all": 400},
        access={"access": "default", "daily_cap": None, "plan_scope": "all"},
    )
    assert all_scope["limit"] == 400


@pytest.mark.asyncio
async def test_a_granted_override_with_no_explicit_cap_falls_back_to_plus_tier():
    allowance = await _allowance(
        plan_limits={"plus": 2500},
        access={"access": "enabled", "daily_cap": None, "plan_scope": None},
    )
    assert allowance["tier"] == "granted"
    assert allowance["limit"] == 2500


@pytest.mark.asyncio
async def test_an_explicit_per_account_cap_still_wins_over_the_plan_default():
    # The per-ACCOUNT override (an admin picked a number for this one
    # person) must not be shadowed by the per-TIER default.
    allowance = await _allowance(
        plan_limits={"plus": 2500},
        access={"access": "enabled", "daily_cap": 77, "plan_scope": None},
    )
    assert allowance["limit"] == 77


def test_effective_plan_limits_fills_in_every_tier():
    with patch("backend.services.allowance.get_settings", return_value=FakeSettings()):
        limits = effective_plan_limits({"free": 50})
    assert limits == {"free": 50, "single": 100, "all": 300, "plus": 1000}


def test_effective_plan_limits_with_no_overrides_is_pure_settings():
    with patch("backend.services.allowance.get_settings", return_value=FakeSettings()):
        limits = effective_plan_limits(None)
    assert limits == {"free": 20, "single": 100, "all": 300, "plus": 1000}
