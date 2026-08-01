"""Auth router — JWT-based user info and profile management."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection

router = APIRouter()

# Columns added by migration 20260908 (the weekly digest opt-in). The profile
# is fetched on EVERY page load, so a deploy that ships this code before the
# migration would take the whole app down rather than degrade one setting —
# the same failure the is_visible incident produced. Selected separately and
# defaulted when absent.
_DIGEST_DEFAULTS = {"weekly_digest_opt_in": False, "weekly_digest_dow": 0}

# Migration 20260910 (explicit content opt-in) is a SEPARATE migration, so
# either may be applied without the other. Each optional column group is
# therefore tried and dropped independently rather than as one bundle —
# assuming they land together is how a "degrades gracefully" fallback
# quietly stops degrading.
_EXPLICIT_DEFAULTS = {"allow_explicit_content": False}

#: Optional column groups, widest first. Each entry is
#: (select fragment, defaults to substitute when the columns are absent).
#: Tried in order, dropping one group at a time.
_OPTIONAL_PROFILE_COLUMNS = (
    (", weekly_digest_opt_in, weekly_digest_dow", _DIGEST_DEFAULTS),
    (", allow_explicit_content", _EXPLICIT_DEFAULTS),
)

_UPSERT_SQL = """
    INSERT INTO user_profiles
        (id, batch_size, ui_language, active_language_id, support_locale,
         reminder_opt_in, reminder_hour_utc{cols})
    VALUES ($1, COALESCE($2, 5), COALESCE($3, 'en'), $4,
            NULLIF($5, 'en'), COALESCE($6, false), COALESCE($7, 16){vals})
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
        {sets}
        updated_at = now()
    RETURNING id, batch_size, ui_language, active_language_id,
              support_locale, plan_scope, plan_language_id,
              reminder_opt_in, reminder_hour_utc,
              created_at, updated_at{ret}
"""


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
    # Independent second opt-in: a weekly round-up of the week's study WITH
    # that week's recommendations. Not a mode switch — a learner can have the
    # daily nudge, the weekly digest, both, or neither.
    weekly_digest_opt_in: bool | None = None
    weekly_digest_dow: int | None = Field(default=None, ge=0, le=6)
    # Explicit vocabulary and sentences (slurs, strong profanity) are hidden
    # unless this is on. Off by default — the frequency lists are built from
    # subtitle corpora and put Spanish *puta* at rank 505, so a beginner met
    # it without anyone choosing to teach it.
    allow_explicit_content: bool | None = None


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT (no DB call needed)."""
    return user


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Return user profile from DB."""
    base = (
        "SELECT id, batch_size, ui_language, active_language_id, "
        "support_locale, plan_scope, plan_language_id, "
        "reminder_opt_in, reminder_hour_utc, "
        "created_at, updated_at{extra} "
        "FROM user_profiles WHERE id = $1"
    )
    # Try every optional group, then each smaller combination, ending with
    # none. Whatever is missing comes back as its default, so a half-migrated
    # database serves a complete profile instead of a 500 on every page load.
    row = None
    missing: dict = {}
    async with rls_connection(user["id"]) as conn:
        for drop in range(len(_OPTIONAL_PROFILE_COLUMNS) + 1):
            groups = _OPTIONAL_PROFILE_COLUMNS[: len(_OPTIONAL_PROFILE_COLUMNS) - drop]
            extra = "".join(frag for frag, _ in groups)
            missing = {
                k: v
                for _, defaults in _OPTIONAL_PROFILE_COLUMNS[len(groups):]
                for k, v in defaults.items()
            }
            try:
                row = await conn.fetchrow(base.format(extra=extra), user["id"])
                break
            except asyncpg.exceptions.UndefinedColumnError:
                continue
    if row is not None and missing:
        row = {**dict(row), **missing}
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
    base_args = (
        user["id"],
        body.batch_size,
        body.ui_language,
        body.active_language_id,
        body.support_locale,
        body.reminder_opt_in,
        body.reminder_hour_utc,
    )
    digest_frag = {
        "cols": ", weekly_digest_opt_in, weekly_digest_dow",
        "vals": ", COALESCE($8, false), COALESCE($9, 0)",
        "sets": (
            "weekly_digest_opt_in = "
            "COALESCE($8, user_profiles.weekly_digest_opt_in), "
            "weekly_digest_dow = "
            "COALESCE($9, user_profiles.weekly_digest_dow),"
        ),
        "ret": ", weekly_digest_opt_in, weekly_digest_dow",
    }
    explicit_frag = {
        "cols": ", allow_explicit_content",
        "vals": ", COALESCE($10, false)",
        "sets": (
            "allow_explicit_content = "
            "COALESCE($10, user_profiles.allow_explicit_content),"
        ),
        "ret": ", allow_explicit_content",
    }

    def _merge(*parts: dict) -> dict:
        return {k: "".join(p.get(k, "") for p in parts) for k in
                ("cols", "vals", "sets", "ret")}

    # Widest first, then narrower, ending with the columns every deploy has.
    # Two independent migrations (20260908, 20260910) can be applied in
    # either order or neither, so a settings write must not fail wholesale
    # because one of them hasn't landed — the rest of the form still saves.
    attempts = (
        (_merge(digest_frag, explicit_frag),
         (*base_args, body.weekly_digest_opt_in, body.weekly_digest_dow,
          body.allow_explicit_content),
         {}),
        (_merge(digest_frag),
         (*base_args, body.weekly_digest_opt_in, body.weekly_digest_dow),
         _EXPLICIT_DEFAULTS),
        (_merge(),
         base_args,
         {**_DIGEST_DEFAULTS, **_EXPLICIT_DEFAULTS}),
    )
    async with rls_connection(user["id"]) as conn:
        for fragments, args, defaults in attempts:
            try:
                row = await conn.fetchrow(_UPSERT_SQL.format(**fragments), *args)
                return {**dict(row), **defaults}
            except asyncpg.exceptions.UndefinedColumnError:
                continue
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not save the profile",
    )
