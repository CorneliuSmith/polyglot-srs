"""Tutor-style message allowance — shared by the tutor chat and any other
learner-triggered AI that should draw the same pool (e.g. Gym on-demand
generation, WP41). Message counts are the only unit exposed; the flat tier
price never depends on usage.

Counted kinds (count_tutor_messages) draw the allowance; 'summary' rows are
operator cost accounting and never count.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from backend.config import get_settings
from backend.repositories.pool import rls_connection
from backend.repositories.tutor import (
    count_tutor_messages,
    get_plan_message_limits,
    get_tutor_access,
    has_tutor_entitlement,
)

_SETTINGS_FALLBACK = {
    "free": "tutor_free_monthly_messages",
    "single": "tutor_single_monthly_messages",
    "all": "tutor_all_monthly_messages",
    "plus": "tutor_plus_monthly_messages",
}


def _plan_limit(plan_limits: dict[str, int] | None, settings, tier: str) -> int:
    """The monthly cap for *tier*: the admin's stored override if one
    exists, else the Settings/env default (unmigrated deploy, or a tier an
    admin has never touched)."""
    if plan_limits and tier in plan_limits:
        return plan_limits[tier]
    return getattr(settings, _SETTINGS_FALLBACK[tier])


def effective_plan_limits(plan_limits: dict[str, int] | None) -> dict[str, int]:
    """All four tiers' current caps, DB override or Settings default filled
    in either way — what the admin panel shows and edits."""
    settings = get_settings()
    return {tier: _plan_limit(plan_limits, settings, tier) for tier in _SETTINGS_FALLBACK}


async def get_allowance(user_id: str, language_id: str) -> dict:
    """The caller's allowance: tier, window usage, and reset time.

    The admin's per-account override is resolved first: 'blocked' zeroes
    everything (even in operator free-access mode); 'granted' gives a capped
    daily allowance without a billing entitlement.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    async with rls_connection(user_id) as conn:
        override = await get_tutor_access(conn, user_id)
        if override["access"] == "blocked":
            return {
                "tier": "blocked", "unlimited": False, "entitled": False,
                "limit": 0, "used": 0, "remaining": 0, "resets_at": None,
            }
        if settings.tutor_free_access and override["access"] != "enabled":
            return {
                "tier": "unlimited", "unlimited": True, "entitled": True,
                "limit": None, "used": 0, "remaining": None, "resets_at": None,
            }
        # Admin-configurable per plan (WP: "admins should be able to set
        # token allocations per account type"). None when migration 20260907
        # hasn't been applied — _plan_limit falls back to the Settings/env
        # default for every tier, so an unmigrated deploy behaves exactly as
        # it always has.
        plan_limits = await get_plan_message_limits(conn)
        # One window for everyone: the calendar month. No daily walls — a heavy
        # study day just draws down the month's pool.
        window_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        resets_at = (window_start + timedelta(days=32)).replace(day=1)
        if override["access"] == "enabled":
            # Admin per-account grant. `daily_cap` is the stored column name; it
            # now caps messages PER MONTH like every other tier.
            limit = override["daily_cap"] or _plan_limit(plan_limits, settings, "plus")
            tier = "granted"
        elif await has_tutor_entitlement(conn, user_id, language_id):
            # Tutor+ add-on — the heavy-use monthly pool.
            limit = _plan_limit(plan_limits, settings, "plus")
            tier = "plus"
        elif override.get("plan_scope") == "all":
            limit = _plan_limit(plan_limits, settings, "all")
            tier = "all"
        elif override.get("plan_scope") == "single":
            limit = _plan_limit(plan_limits, settings, "single")
            tier = "single"
        else:
            limit = _plan_limit(plan_limits, settings, "free")
            tier = "free"
        used = await count_tutor_messages(conn, user_id, window_start)
    return {
        "tier": tier, "unlimited": False, "entitled": tier in ("plus", "granted"),
        "limit": limit, "used": used, "remaining": max(0, limit - used),
        "resets_at": resets_at.isoformat(),
    }


def reject_if_unavailable(allowance: dict) -> None:
    """Turn a zeroed allowance into the right HTTP error."""
    if allowance["tier"] == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "tutor_blocked"},
        )
    if not allowance["unlimited"] and allowance["remaining"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "allowance_exhausted",
                "tier": allowance["tier"],
                "limit": allowance["limit"],
                "resets_at": allowance["resets_at"],
            },
        )
