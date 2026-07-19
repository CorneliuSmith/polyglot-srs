"""Auth router — JWT-based user info and profile management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection

router = APIRouter()


class ProfileUpdate(BaseModel):
    batch_size: int | None = None
    ui_language: str | None = None
    active_language_id: str | None = None
    # "I'm learning English FROM this language": hints/definitions/sentence
    # translations for ENGLISH cards render in this locale. 'en' resets to
    # the default (English definitions).
    support_locale: str | None = None
    # Opt-in daily email when reviews are due; the hour is UTC (the client
    # converts from the learner's local time).
    reminder_opt_in: bool | None = None
    reminder_hour_utc: int | None = Field(default=None, ge=0, le=23)


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT (no DB call needed)."""
    return user


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Return user profile from DB."""
    async with rls_connection(user["id"]) as conn:
        row = await conn.fetchrow(
            "SELECT id, batch_size, ui_language, active_language_id, "
            "support_locale, plan_scope, plan_language_id, "
            "reminder_opt_in, reminder_hour_utc, "
            "created_at, updated_at "
            "FROM user_profiles WHERE id = $1",
            user["id"],
        )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return dict(row)


@router.post("/profile")
async def upsert_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Create or update user profile (upsert)."""
    if body.support_locale is not None:
        async with rls_connection(user["id"]) as conn:
            known = await conn.fetchval(
                "SELECT count(*) FROM languages WHERE code = $1",
                body.support_locale,
            )
        if body.support_locale != "en" and not known:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown support locale: {body.support_locale}",
            )
    if body.active_language_id is not None:
        # A Single-language plan studies exactly its licensed language.
        async with rls_connection(user["id"]) as conn:
            plan = await conn.fetchrow(
                "SELECT plan_scope, plan_language_id FROM user_profiles "
                "WHERE id = $1",
                user["id"],
            )
        if (
            plan is not None
            and plan["plan_scope"] == "single"
            and plan["plan_language_id"] is not None
            and str(plan["plan_language_id"]) != body.active_language_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your plan covers one language. Upgrade to All "
                       "Languages to switch.",
            )
    async with rls_connection(user["id"]) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_profiles
                (id, batch_size, ui_language, active_language_id, support_locale,
                 reminder_opt_in, reminder_hour_utc)
            VALUES ($1, COALESCE($2, 5), COALESCE($3, 'en'), $4,
                    NULLIF($5, 'en'), COALESCE($6, false), COALESCE($7, 16))
            ON CONFLICT (id) DO UPDATE SET
                batch_size = COALESCE($2, user_profiles.batch_size),
                ui_language = COALESCE($3, user_profiles.ui_language),
                active_language_id = COALESCE($4, user_profiles.active_language_id),
                -- 'en' explicitly RESETS the support locale to the default
                support_locale = CASE
                    WHEN $5 IS NULL THEN user_profiles.support_locale
                    ELSE NULLIF($5, 'en')
                END,
                reminder_opt_in = COALESCE($6, user_profiles.reminder_opt_in),
                reminder_hour_utc = COALESCE($7, user_profiles.reminder_hour_utc),
                updated_at = now()
            RETURNING id, batch_size, ui_language, active_language_id,
                      support_locale, plan_scope, plan_language_id,
                      reminder_opt_in, reminder_hour_utc,
                      created_at, updated_at
            """,
            user["id"],
            body.batch_size,
            body.ui_language,
            body.active_language_id,
            body.support_locale,
            body.reminder_opt_in,
            body.reminder_hour_utc,
        )
    return dict(row)
