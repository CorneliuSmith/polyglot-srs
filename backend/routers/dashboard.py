"""Dashboard router — per-language learning statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_current_user
from backend.repositories.dashboard import get_dashboard_stats
from backend.repositories.pool import rls_connection

router = APIRouter()


@router.get("/{language_id}")
async def get_dashboard(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Return dashboard stats for the user's given language.

    Response shape:
        {
            "due_count": int,
            "streak_days": int,
            "cefr_progress": {
                "A1": {"learned": int, "total": int},
                ...
                "C2": {"learned": int, "total": int},
            }
        }
    """
    async with rls_connection(user["id"]) as conn:
        stats = await get_dashboard_stats(conn, user["id"], language_id)
    return stats
