"""Personalized immersion recommendations (owner request).

Opt-in, paid-tutor-gated, generated about once a week. The learner keeps a
small interest profile; when a week has passed since their last batch, the
client asks to refresh and we draft a new one calibrated to their level and
interests. Every batch is kept so they can look back over the whole history.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection
from backend.repositories.recommendations import (
    get_reco_profile,
    insert_recommendation,
    latest_recommendation_at,
    list_recommendations,
    upsert_reco_profile,
)
from backend.repositories.tutor import get_study_stats, log_tutor_usage
from backend.services.allowance import get_allowance
from backend.services.models import resolve_model
from backend.services.recommend import MEDIA_TYPES, generate_recommendations

router = APIRouter()

# Once a week: a new batch is only drafted when the last one is at least this
# old, so opening the app repeatedly never regenerates (or re-charges).
_FRESH_WINDOW = timedelta(days=7)
_MAX_ABOUT = 1000
_MAX_TAGS = 24


class RecoProfileBody(BaseModel):
    enabled: bool = False
    about: str = Field(default="", max_length=_MAX_ABOUT)
    genres: list[str] = Field(default_factory=list, max_length=_MAX_TAGS)
    media_types: list[str] = Field(default_factory=list, max_length=8)


def _clean_types(types: list[str]) -> list[str]:
    # Keep only the media types we know how to recommend, in a stable order.
    return [t for t in MEDIA_TYPES if t in set(types)]


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    async with rls_connection(user["id"]) as conn:
        return await get_reco_profile(conn, user["id"])


@router.put("/profile")
async def put_profile(
    body: RecoProfileBody, user: dict = Depends(get_current_user)
):
    genres = [g.strip() for g in body.genres if g.strip()][:_MAX_TAGS]
    async with rls_connection(user["id"]) as conn:
        await upsert_reco_profile(
            conn, user["id"],
            enabled=body.enabled,
            about=body.about.strip(),
            genres=genres,
            media_types=_clean_types(body.media_types),
        )
        return await get_reco_profile(conn, user["id"])


def _require_uuid(language_id: str) -> None:
    try:
        UUID(language_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid language id",
        ) from exc


async def _is_stale(conn, user_id: str, language_id: str) -> bool:
    last = await latest_recommendation_at(conn, user_id, language_id)
    return last is None or (datetime.now(UTC) - last) >= _FRESH_WINDOW


@router.get("/{language_id}")
async def get_recommendations(
    language_id: str, user: dict = Depends(get_current_user)
):
    """The learner's recommendation state for one language: whether the feature
    is on, whether they're entitled (tutor+), whether a fresh batch is due, and
    the full history newest-first."""
    _require_uuid(language_id)
    allowance = await get_allowance(user["id"], language_id)
    async with rls_connection(user["id"]) as conn:
        profile = await get_reco_profile(conn, user["id"])
        batches = await list_recommendations(conn, user["id"], language_id)
        stale = await _is_stale(conn, user["id"], language_id)
    return {
        "enabled": profile["enabled"],
        "entitled": bool(allowance["entitled"]),
        "stale": stale,
        "batches": batches,
    }


@router.post("/{language_id}/refresh")
async def refresh_recommendations(
    language_id: str, user: dict = Depends(get_current_user)
):
    """Draft this week's batch — but only when it's actually due. Idempotent:
    if a batch was made within the last week it's returned as-is, so a client
    that fires this on load never double-generates or double-charges."""
    _require_uuid(language_id)

    async with rls_connection(user["id"]) as conn:
        profile = await get_reco_profile(conn, user["id"])
        if not profile["enabled"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recommendations are turned off.",
            )
        # Not due yet → return the current batch untouched (no model call).
        if not await _is_stale(conn, user["id"], language_id):
            batches = await list_recommendations(conn, user["id"], language_id, limit=1)
            return {"generated": False, "batch": batches[0] if batches else None}

        lang = await conn.fetchrow(
            "SELECT code, name FROM languages WHERE id = $1", language_id
        )
        if not lang:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown language"
            )
        stats = await get_study_stats(conn, user["id"], language_id)

    # Paid-tutor gate: recommendations are a tutor+ perk (each batch is a model
    # call). Free/blocked accounts get a clear 402 the UI turns into an upsell.
    allowance = await get_allowance(user["id"], language_id)
    if not allowance["entitled"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Recommendations need a tutor+ subscription for this language.",
        )

    level = stats.get("highest_level_reached")
    model = resolve_model("recommend", lang["code"])
    items = await generate_recommendations(
        language_name=lang["name"],
        language_code=lang["code"],
        level=level,
        learned_count=int(stats.get("learned_cards") or 0),
        about=profile["about"],
        genres=profile["genres"],
        media_types=profile["media_types"],
        model=model,
    )
    if not items:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't draft recommendations just now — try again later.",
        )

    async with rls_connection(user["id"]) as conn:
        batch = await insert_recommendation(
            conn, user["id"], language_id, items, level
        )
        # Accounting only — kind='recs' is NOT counted against the daily tutor
        # allowance (it's a weekly plan perk, not a chat message).
        await log_tutor_usage(
            conn, user["id"], language_id, model, kind="recs"
        )
    return {"generated": True, "batch": batch}
