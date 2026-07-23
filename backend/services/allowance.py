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
    get_tutor_access,
    has_tutor_entitlement,
)


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
        if override["access"] == "enabled":
            window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            resets_at = window_start + timedelta(days=1)
            limit = override["daily_cap"] or settings.tutor_plus_daily_messages
            tier = "granted"
        else:
            entitled = await has_tutor_entitlement(conn, user_id, language_id)
            if entitled:
                window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                resets_at = window_start + timedelta(days=1)
                limit = settings.tutor_plus_daily_messages
                tier = "plus"
            else:
                # A MONTHLY allowance included with the language plan
                # (all > single > no plan).
                window_start = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                resets_at = (window_start + timedelta(days=32)).replace(day=1)
                if override.get("plan_scope") == "all":
                    limit = settings.tutor_all_monthly_messages
                    tier = "all"
                elif override.get("plan_scope") == "single":
                    limit = settings.tutor_single_monthly_messages
                    tier = "single"
                else:
                    limit = settings.tutor_free_monthly_messages
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
