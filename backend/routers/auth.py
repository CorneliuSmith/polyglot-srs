"""Auth router — JWT-based user info, profile management, trial requests."""

from __future__ import annotations

from html import escape

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.cards import pretranslate_upcoming
from backend.repositories.experiments import (
    assign_variant,
    clear_assignment,
    get_experiment,
    list_experiments,
)
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.trials import add_trial_request, trials_table_present
from backend.services.email import send_email
from backend.services.experiments import resolve_variants
from backend.services.rate_limit import RateLimiter

router = APIRouter()

# The one unauthenticated write in the app. Generous for humans, useless
# for scripts: a handful of requests per IP per hour.
trial_request_limiter = RateLimiter("trial_request", max_calls=5,
                                    per_seconds=3600)


class TrialRequestBody(BaseModel):
    email: str = Field(min_length=5, max_length=200,
                       pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=500)


@router.post("/trial-request")
async def request_trial(body: TrialRequestBody, request: Request):
    """Ask for trial access (public — the login page's front door).

    Signup stays disabled; this queues the request for the admin, who
    approves it from the panel (which mints the account with a temporary
    password). The response is identical whether the email is new, already
    queued, or already an account — the form must not enumerate anything.
    """
    # Behind the platform's proxy every request shares the LB's address, so
    # key on the forwarded client when present — spoofable, but this is a
    # soft nuisance cap, and the alternative is one global 5/hour budget
    # for every visitor at once.
    forwarded = request.headers.get("x-forwarded-for", "")
    client_key = (
        forwarded.split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if not await trial_request_limiter.allow(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — try again later.",
        )
    async with privileged_connection() as conn:
        if not await trials_table_present(conn):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Trial signup isn't available on this server yet "
                    "(migration 20260921 pending)."
                ),
            )
        added = await add_trial_request(conn, body.email, body.name, body.note)

    # Announce NEW requests only (a duplicate would let a stranger make the
    # admin's inbox ring on someone else's behalf). Log-only when no
    # ADMIN_NOTIFY_EMAIL / Resend key — the panel's queue shows it anyway.
    admin_to = get_settings().admin_notify_email
    if added and admin_to:
        who = escape(body.name or body.email)
        note = f"<p>{escape(body.note)}</p>" if body.note else ""
        await send_email(
            admin_to,
            f"PolyglotSRS: trial access request from {body.email}",
            f"<p><strong>{who}</strong> ({escape(body.email)}) asked for "
            f"trial access.</p>{note}"
            "<p>Approve or reject it from the admin panel's "
            "Trial requests queue.</p>",
        )
    return {"received": True}

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

# Migration 20261001 (sentence audio on a correct answer). ON by default —
# the feature is the default, the toggle is the escape.
_AUDIO_DEFAULTS = {"sentence_audio_on_correct": True}

#: Optional column groups, widest first. Each entry is
#: (select fragment, defaults to substitute when the columns are absent).
#: Tried in order, dropping one group at a time.
_OPTIONAL_PROFILE_COLUMNS = (
    (", weekly_digest_opt_in, weekly_digest_dow", _DIGEST_DEFAULTS),
    (", allow_explicit_content", _EXPLICIT_DEFAULTS),
    (", sentence_audio_on_correct", _AUDIO_DEFAULTS),
)

_UPSERT_SQL = """
    INSERT INTO user_profiles
        (id, batch_size, ui_language, active_language_id, support_locale,
         reminder_opt_in, reminder_hour_utc{cols})
    VALUES ($1, COALESCE($2, 5), COALESCE($3, 'en'), $4,
            NULLIF($5, 'auto'), COALESCE($6, false), COALESCE($7, 16){vals})
    ON CONFLICT (id) DO UPDATE SET
        batch_size = COALESCE($2, user_profiles.batch_size),
        ui_language = COALESCE($3, user_profiles.ui_language),
        active_language_id = COALESCE($4, user_profiles.active_language_id),
        -- Tri-state: absent keeps the stored value; 'auto' resets to NULL
        -- (automatic — help follows the interface language, resolved at
        -- read time by repositories/profile.py); any language code,
        -- INCLUDING 'en', is stored as an explicit choice. 'en' used to be
        -- the reset value, which made "I want English help" inexpressible
        -- once automatic meant "follow the interface": a French-interface
        -- learner asking for English glosses would have been snapped back
        -- to French.
        support_locale = CASE
            WHEN $5 IS NULL THEN user_profiles.support_locale
            ELSE NULLIF($5, 'auto')
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
    # Play the full sentence out loud when an answer grades correct — the
    # moment the learner can listen without still hunting for the answer.
    # Account-level on purpose: settings that live on the account behave
    # the same everywhere the account is opened.
    sentence_audio_on_correct: bool | None = None


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
    # Which rollouts this account is in, resolved fresh on every load so an
    # admin flipping a switch reaches everyone on their next page rather
    # than whenever a cache happens to expire. resolve_variants swallows
    # everything it can hit, including the table not existing yet — this
    # endpoint renders the whole app and must not be the thing an
    # experiment can break.
    async with rls_connection(user["id"]) as conn:
        variants = await resolve_variants(conn, user["id"])
    return {**dict(row), "experiments": variants}


@router.get("/experiments")
async def my_experiments(user: dict = Depends(get_current_user)):
    """The rollouts this person is allowed to switch themselves between.

    Only running experiments an admin has opened to learner choice, so the
    Settings page never offers a switch the server would refuse — and never
    reveals an experiment that is still being decided internally.
    """
    async with rls_connection(user["id"]) as conn:
        experiments = await list_experiments(conn)
        resolved = await resolve_variants(conn, user["id"])
    return {
        "experiments": [
            {
                "key": e["key"],
                "name": e["name"],
                "description": e["description"],
                "variants": e["variants"],
                "current": resolved.get(e["key"], e["default_variant"]),
            }
            for e in experiments
            if e.get("enabled") and e.get("learner_choice")
        ]
    }


class ExperimentChoice(BaseModel):
    key: str
    # None puts them back under whatever the rollout says — "give me
    # whatever everyone else is getting" is a real answer, and without it
    # a learner who tried the new look could never stop overriding.
    variant: str | None = None


@router.post("/experiment")
async def choose_experiment_variant(
    body: ExperimentChoice,
    user: dict = Depends(get_current_user),
):
    """A learner switching themselves between variants.

    Only for experiments an admin has marked as the learner's to choose, and
    only while the experiment is running: a switch that outlived its kill
    switch would leave people on a look that had been withdrawn, which is
    the one state a rollout must never produce.

    Someone who can leave gives better feedback than someone who is stuck.
    That is the whole reason this endpoint exists rather than admin
    assignment alone.
    """
    async with rls_connection(user["id"]) as conn:
        experiment = await get_experiment(conn, body.key)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Unknown experiment")
    if not experiment.get("learner_choice") or not experiment.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That isn't yours to switch",
        )
    async with privileged_connection() as conn:
        if body.variant is None:
            await clear_assignment(conn, user["id"], body.key)
            resolved = None
        else:
            known = {v["key"] for v in experiment["variants"]}
            if body.variant not in known:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown variant: {body.variant}",
                )
            await assign_variant(
                conn, user["id"], body.key, body.variant, source="self",
            )
            resolved = body.variant
    return {"key": body.key, "variant": resolved}


@router.post("/profile")
async def upsert_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Create or update user profile (upsert)."""
    # 'auto' is the reset sentinel, not a language: it stores NULL, which
    # means "follow the interface language" (repositories/profile.py).
    if body.support_locale is not None and body.support_locale != "auto":
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
    audio_frag = {
        "cols": ", sentence_audio_on_correct",
        "vals": ", COALESCE($11, true)",
        "sets": (
            "sentence_audio_on_correct = "
            "COALESCE($11, user_profiles.sentence_audio_on_correct),"
        ),
        "ret": ", sentence_audio_on_correct",
    }

    def _merge(*parts: dict) -> dict:
        return {k: "".join(p.get(k, "") for p in parts) for k in
                ("cols", "vals", "sets", "ret")}

    # Widest first, then narrower, ending with the columns every deploy has.
    # Two independent migrations (20260908, 20260910) can be applied in
    # either order or neither, so a settings write must not fail wholesale
    # because one of them hasn't landed — the rest of the form still saves.
    attempts = (
        (_merge(digest_frag, explicit_frag, audio_frag),
         (*base_args, body.weekly_digest_opt_in, body.weekly_digest_dow,
          body.allow_explicit_content, body.sentence_audio_on_correct),
         {}),
        (_merge(digest_frag, explicit_frag),
         (*base_args, body.weekly_digest_opt_in, body.weekly_digest_dow,
          body.allow_explicit_content),
         _AUDIO_DEFAULTS),
        (_merge(digest_frag),
         (*base_args, body.weekly_digest_opt_in, body.weekly_digest_dow),
         {**_EXPLICIT_DEFAULTS, **_AUDIO_DEFAULTS}),
        (_merge(),
         base_args,
         {**_DIGEST_DEFAULTS, **_EXPLICIT_DEFAULTS, **_AUDIO_DEFAULTS}),
    )
    async with rls_connection(user["id"]) as conn:
        for fragments, args, defaults in attempts:
            try:
                row = await conn.fetchrow(_UPSERT_SQL.format(**fragments), *args)
            except asyncpg.exceptions.UndefinedColumnError:
                continue
            # A saved course + support locale is the earliest possible signal
            # of what this learner will meet — queue their upcoming content
            # for translation NOW, so even the first learn session (and every
            # review after it) opens already localized. Never blocks the save.
            if (body.active_language_id and body.support_locale
                    and body.support_locale not in ("auto", "en")):
                await pretranslate_upcoming(
                    conn, user["id"], body.active_language_id,
                    body.batch_size or 10,
                )
            return {**dict(row), **defaults}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not save the profile",
    )
