"""Auth router — JWT-based user info, profile management, trial requests."""

from __future__ import annotations

import logging
from html import escape

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.admins import admin_recipients
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

logger = logging.getLogger("auth")
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
    # admin's inbox ring on someone else's behalf). The request itself is
    # already safe in the queue — and the staff bell counts it — so mail is
    # a convenience, never the record.
    #
    # Recipients are the ACCOUNTS holding the admin role, plus
    # ADMIN_NOTIFY_EMAIL if it names an extra inbox. It used to be that env
    # var alone, which nobody had set (it wasn't in .env.example either), so
    # every request announced itself into the void. Roles are already in the
    # database and cannot drift out of date.
    if not added:
        return {"received": True}

    async with privileged_connection() as conn:
        recipients = [a["email"] for a in await admin_recipients(conn)]
    extra = get_settings().admin_notify_email
    if extra and extra not in recipients:
        recipients.append(extra)

    if not recipients:
        logger.warning(
            "trial request queued but NOT emailed: no account holds the admin "
            "role and ADMIN_NOTIFY_EMAIL is unset. The request is in the "
            "admin panel's Trial requests queue."
        )
        return {"received": True}

    who = escape(body.name or body.email)
    note = f"<p>{escape(body.note)}</p>" if body.note else ""
    for to in recipients:
        sent = await send_email(
            to,
            f"PolyglotSRS: trial access request from {body.email}",
            f"<p><strong>{who}</strong> ({escape(body.email)}) asked for "
            f"trial access.</p>{note}"
            "<p>Approve or reject it from the admin panel's "
            "Trial requests queue.</p>",
        )
        if not sent:
            # send_email already logged the reason (no key, transport, or a
            # rejection body — Resend's default onboarding@resend.dev sender
            # only delivers to the account owner's own verified address).
            logger.warning(
                "trial request queued but the announcement email to %s did "
                "not send. It is in the Trial requests queue either way.", to,
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

# Migration 20261012 (word-by-word glosses). OFF by default (owner): the
# Leipzig notation is unfamiliar enough that meeting it unasked is what
# learners reported as confusing. Anyone who wants it turns it on, where
# the Settings toggle also explains what it is.
_GLOSS_DEFAULTS = {"show_glosses": False}

#: Optional column groups, widest first. Each entry is
#: (select fragment, defaults to substitute when the columns are absent).
#: Which ones exist is ASKED, not discovered by failing — see
#: `_present_profile_columns` and docs/decisions/0001.
_OPTIONAL_PROFILE_COLUMNS = (
    (", weekly_digest_opt_in, weekly_digest_dow", _DIGEST_DEFAULTS),
    (", allow_explicit_content", _EXPLICIT_DEFAULTS),
    (", sentence_audio_on_correct", _AUDIO_DEFAULTS),
    (", show_glosses", _GLOSS_DEFAULTS),
)


#: Every optional column, with the SQL literal used when a save does not
#: name it. Order fixes the placeholder numbering in the upsert.
_OPTIONAL_PROFILE_FIELDS = (
    ("weekly_digest_opt_in", "false"),
    ("weekly_digest_dow", "0"),
    ("allow_explicit_content", "false"),
    ("sentence_audio_on_correct", "true"),
    ("show_glosses", "false"),
)

_ALL_OPTIONAL_DEFAULTS = {
    **_DIGEST_DEFAULTS, **_EXPLICIT_DEFAULTS, **_AUDIO_DEFAULTS,
    **_GLOSS_DEFAULTS,
}


async def _present_profile_columns(conn: asyncpg.Connection) -> set[str]:
    """Which `user_profiles` columns this database actually has.

    One question, asked up front, instead of finding out by failing —
    docs/decisions/0001-probe-tables-instead-of-catching-errors.md.

    Catching the error is not merely less tidy here, it does not WORK.
    `rls_connection` runs everything inside one explicit transaction (it has
    to: the RLS claims are transaction-scoped). A statement that raises
    `UndefinedColumnError` aborts that transaction, so the next attempt —
    the narrower SELECT that was supposed to be the graceful fallback —
    raises `InFailedSQLTransactionError` instead, which nothing catches and
    which reaches the client as a 500 on the endpoint that renders every
    page. The fallback ladder read as defensive and was decorative.

    Verified against a real Postgres rather than reasoned about; see
    backend/tests/integration/test_show_glosses_integration.py.
    """
    rows = await conn.fetch(
        """
        SELECT column_name FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'user_profiles'
        """
    )
    return {r["column_name"] for r in rows}


def _profile_column_plan(present: set[str]) -> tuple[str, dict]:
    """(select fragment, defaults) for the groups this database can serve.

    A group is included only when EVERY column in it exists, so a
    half-applied migration cannot produce a SELECT naming one column that
    landed and one that did not.
    """
    extra: list[str] = []
    defaults: dict = {}
    for frag, group_defaults in _OPTIONAL_PROFILE_COLUMNS:
        if all(col in present for col in group_defaults):
            extra.append(frag)
        else:
            defaults.update(group_defaults)
    return "".join(extra), defaults

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
    # Offer the word-by-word gloss (a Leipzig decomposition: bark.3SG) as a
    # hint layer. On by default; a learner who finds the notation more
    # confusing than useful turns it off and the layer stops being offered.
    show_glosses: bool | None = None


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
    # Ask which optional columns exist, then select exactly those. Whatever
    # is missing comes back as its default, so a half-migrated database
    # serves a complete profile instead of a 500 on every page load.
    async with rls_connection(user["id"]) as conn:
        extra, missing = _profile_column_plan(await _present_profile_columns(conn))
        row = await conn.fetchrow(base.format(extra=extra), user["id"])
    if row is not None and missing:
        row = {**dict(row), **missing}
    # Name the settings this database cannot store yet, so the UI can say
    # "not available on this server" instead of rendering a switch that
    # saves, reads back its default, and silently snaps off. Every
    # substituted default is a control that cannot work, and until now the
    # client had no way to tell one from a real stored value.
    if row is not None:
        row = {**dict(row), "unavailable_settings": sorted(missing)}
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
    """The rollouts this person should see in Settings.

    Two ways in, matching the two ways an experiment is run:
      - learner_choice on: the admin opened it to self-service, so it shows
        with switch buttons whether or not this account is on the default.
      - learner_choice off (the admin chooses for the account — the owner's
        stated mode): it shows ONLY when this account is actually on a
        non-default variant. They should know they're on a test version and
        have somewhere to say what they think of it, without being offered
        a switch the server would refuse — and an account on the default
        sees nothing, because there is nothing new to tell them about.

    Either way an experiment still being decided internally (enabled=false)
    is never revealed.
    """
    async with rls_connection(user["id"]) as conn:
        experiments = await list_experiments(conn)
        resolved = await resolve_variants(conn, user["id"])
    out = []
    for e in experiments:
        if not e.get("enabled"):
            continue
        current = resolved.get(e["key"], e["default_variant"])
        if not e.get("learner_choice") and current == e["default_variant"]:
            continue
        out.append({
            "key": e["key"],
            "name": e["name"],
            "description": e["description"],
            "variants": e["variants"],
            "current": current,
            "learner_choice": bool(e.get("learner_choice")),
        })
    return {"experiments": out}


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
    # Build the optional half of the upsert from the columns this database
    # actually HAS, one column at a time.
    #
    # Two faults in the ladder this replaces. It caught UndefinedColumnError
    # and retried on the same connection — inside rls_connection's single
    # transaction, where the first failure aborts everything after it, so
    # the retry raised InFailedSQLTransactionError and the "graceful"
    # degradation was decorative. And it only ever dropped groups from the
    # RIGHT, so a database with the newest migration but not a middle one
    # (migrations are owner-applied and independent — the comment above says
    # so) had no attempt that fitted it.
    #
    # Per column, numbered from $8 in the order they are appended, so any
    # subset produces a correct statement.
    async with rls_connection(user["id"]) as conn:
        present = await _present_profile_columns(conn)
        cols: list[str] = []
        vals: list[str] = []
        sets: list[str] = []
        args: list = []
        defaults: dict = {}
        for column, fallback in _OPTIONAL_PROFILE_FIELDS:
            if column not in present:
                defaults[column] = _ALL_OPTIONAL_DEFAULTS[column]
                continue
            n = len(base_args) + len(args) + 1
            cols.append(column)
            vals.append(f"COALESCE(${n}, {fallback})")
            sets.append(f"{column} = COALESCE(${n}, user_profiles.{column}),")
            args.append(getattr(body, column))

        joined = ", " + ", ".join(cols) if cols else ""
        fragments = {
            "cols": joined,
            "vals": ", " + ", ".join(vals) if vals else "",
            "sets": " ".join(sets),
            "ret": joined,
        }
        row = await conn.fetchrow(
            _UPSERT_SQL.format(**fragments), *base_args, *args
        )
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
        if row is not None:
            return {
                **dict(row), **defaults,
                "unavailable_settings": sorted(defaults),
            }
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not save the profile",
    )
