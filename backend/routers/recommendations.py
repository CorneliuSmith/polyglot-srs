"""Personalized immersion recommendations (owner request).

Opt-in, paid-tutor-gated, generated about once a week. The learner keeps a
small interest profile; when a week has passed since their last batch, the
client asks to refresh and we draft a new one calibrated to their level and
interests. Every batch is kept so they can look back over the whole history.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.contributor import get_roles, is_admin
from backend.repositories.pool import rls_connection
from backend.repositories.recommendations import (
    get_reco_profile,
    insert_recommendation,
    latest_recommendation_at,
    list_recommendations,
    mark_recommendations_seen,
    rated_titles,
    recommended_titles,
    set_reco_feedback,
    unseen_batch,
    upsert_reco_profile,
)
from backend.repositories.tutor import get_study_stats, log_tutor_usage
from backend.services.allowance import get_allowance, reject_if_unavailable
from backend.services.models import resolve_model
from backend.services.rate_limit import reco_refresh_limiter
from backend.services.recommend import MEDIA_TYPES, generate_recommendations

router = APIRouter()
logger = logging.getLogger(__name__)

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


async def _is_admin_user(user_id: str) -> bool:
    """Admins are always entitled to recommendations — the owner runs the
    API key, so the Plus paywall gating their own testing surface meant
    the person building the feature could never see the generate button
    (reported twice). The allowance still logs usage; it just can't say no
    to an admin."""
    async with rls_connection(user_id) as conn:
        return is_admin(await get_roles(conn, user_id))


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


@router.get("/{language_id}/unseen")
async def unseen_recommendations(
    language_id: str, user: dict = Depends(get_current_user)
):
    """The newest batch the learner hasn't looked at yet, if any.

    Backs the once-a-week dashboard prompt: picks are generated weekly, but
    until now the only way to find them was to remember to open the page, so
    most batches were never seen at all.
    """
    _require_uuid(language_id)
    async with rls_connection(user["id"]) as conn:
        batch = await unseen_batch(conn, user["id"], language_id)
    return {"batch": batch}


@router.post("/seen")
async def mark_seen(user: dict = Depends(get_current_user)):
    """"I've seen my picks" — dismisses the prompt everywhere, not just on
    the device it was dismissed on."""
    async with rls_connection(user["id"]) as conn:
        await mark_recommendations_seen(conn, user["id"])
    return {"ok": True}


class FeedbackBody(BaseModel):
    item_index: int = Field(ge=0, le=15)
    done: bool = False
    rating: int | None = Field(default=None, ge=1, le=5)


@router.put("/batches/{batch_id}/feedback")
async def put_feedback(
    batch_id: str,
    body: FeedbackBody,
    user: dict = Depends(get_current_user),
):
    """Mark one pick finished and/or rate it 1–5 (owner: "users should be
    able to mark what they watched, read, listened to and give it a
    rating"). The engine reads this back — finished/rated titles are never
    re-recommended, and ratings steer the next batch."""
    try:
        UUID(batch_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid batch id",
        ) from exc
    async with rls_connection(user["id"]) as conn:
        ok = await set_reco_feedback(
            conn, user["id"], batch_id, body.item_index,
            done=body.done, rating=body.rating,
        )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Saving feedback needs migration 20260922 applied — "
                "run `supabase db push` (or the batch isn't yours)."
            ),
        )
    return {"saved": True}


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
        "entitled": bool(allowance["entitled"]) or await _is_admin_user(user["id"]),
        "stale": stale,
        "batches": batches,
    }


@router.post("/{language_id}/refresh")
async def refresh_recommendations(
    language_id: str,
    force: bool = False,
    user: dict = Depends(get_current_user),
):
    """Draft a new batch.

    Passively (force=False, what the client fires on every page load): only
    when the last batch is at least a week old. Idempotent — a batch made
    within the window is returned as-is, so loading the page never
    double-generates or double-charges.

    On demand (force=True, the "Get new recommendations now" button): drafts
    immediately regardless of staleness, calibrated to the learner's CURRENT
    progress/status the same way the weekly draft is — grounded in
    get_study_stats each time, not cached. Rate-limited on its own
    (reco_refresh_limiter) since staleness isn't there to cap the cost.
    """
    _require_uuid(language_id)

    async with rls_connection(user["id"]) as conn:
        profile = await get_reco_profile(conn, user["id"])
        if not profile["enabled"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recommendations are turned off.",
            )
        if force:
            if not await reco_refresh_limiter.allow(user["id"]):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="You've asked for a few fresh batches already — "
                           "try again a bit later.",
                )
        # Not due yet, and not explicitly asked for → return the current
        # batch untouched (no model call).
        elif not await _is_stale(conn, user["id"], language_id):
            batches = await list_recommendations(conn, user["id"], language_id, limit=1)
            return {"generated": False, "batch": batches[0] if batches else None}

        lang = await conn.fetchrow(
            "SELECT code, name, tutor_model FROM languages WHERE id = $1", language_id
        )
        if not lang:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown language"
            )
        stats = await get_study_stats(conn, user["id"], language_id)
        # What the engine must not repeat, and how earlier picks landed —
        # a batch that re-recommends last month's series reads as the
        # engine not paying attention.
        exclude = await recommended_titles(conn, user["id"], language_id)
        reactions = await rated_titles(conn, user["id"], language_id)

    # Paid-tutor gate: recommendations are a tutor+ perk (each batch is a model
    # call). Free/blocked accounts get a clear 402 the UI turns into an upsell.
    # Admins bypass both gates — the owner runs the key.
    allowance = await get_allowance(user["id"], language_id)
    admin = await _is_admin_user(user["id"])
    if not allowance["entitled"] and not admin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Recommendations need a tutor+ subscription for this language.",
        )
    # And each batch spends from the same monthly pool the tutor draws
    # (owner: "a plus feature that will use some of their monthly ai") —
    # an exhausted month means no more batches until it resets.
    if not admin:
        reject_if_unavailable(allowance)

    level = stats.get("highest_level_reached")
    # The admin's per-language model override (languages.tutor_model) —
    # previously only tutor chat and the Reader threaded this through.
    model = resolve_model("recommend", lang["code"], override=lang["tutor_model"])
    try:
        items = await generate_recommendations(
            language_name=lang["name"],
            language_code=lang["code"],
            level=level,
            learned_count=int(stats.get("learned_cards") or 0),
            about=profile["about"],
            genres=profile["genres"],
            media_types=profile["media_types"],
            model=model,
            exclude_titles=exclude,
            reactions=reactions,
        )
    except Exception as exc:  # noqa: BLE001 — a provider error is a 502, not a 500
        # The admin bypass made this path reachable for the first time and it
        # answered a bare 500 — the reason invisible to everyone. Log the full
        # traceback, and tell an ADMIN what actually failed (the owner reads
        # this in devtools; learners get the friendly line).
        logger.exception("recommendations draft failed (model=%s)", model)
        detail = "Couldn't draft recommendations just now — try again later."
        if admin:
            detail += f" [{type(exc).__name__}: {exc}]"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=detail
        ) from exc
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
