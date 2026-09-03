"""Tutor repository — entitlement checks and weak-area aggregation.

The weak-area query is what grounds the AI tutor: it pulls the user's worst
recent material (failed reviews, low-ease cards) so the tutor coaches on what
the learner is actually struggling with rather than generic content.
"""

from __future__ import annotations

import json

import asyncpg

from backend.repositories.pool import savepoint

PLAN_TIERS = ("free", "single", "all", "plus")


async def get_plan_message_limits(conn: asyncpg.Connection) -> dict[str, int] | None:
    """The admin-configurable monthly cap per plan tier, or None if migration
    20260907 hasn't been applied yet — the caller falls back to Settings."""
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                "SELECT plan, monthly_messages FROM plan_message_limits"
            )
    except asyncpg.exceptions.UndefinedTableError:
        return None
    limits = {r["plan"]: r["monthly_messages"] for r in rows}
    # A tier with no row (e.g. added to PLAN_TIERS after this table was last
    # seeded) is a caller concern, not this function's — it returns exactly
    # what's stored, and get_allowance's dict lookup is what falls back.
    return limits


async def set_plan_message_limit(
    conn: asyncpg.Connection, plan: str, monthly_messages: int, admin_id: str
) -> bool:
    """Admin-only (router enforces); UPSERT so a tier missing its seed row
    (a table created after launch, or a hand-added tier) still saves.
    Returns False (rather than raising) when migration 20260907 hasn't been
    applied yet — the router turns that into a clear 503."""
    try:
        async with savepoint(conn):
            await conn.execute(
                """
                INSERT INTO plan_message_limits (plan, monthly_messages, updated_by, updated_at)
                VALUES ($1, $2, $3, now())
                ON CONFLICT (plan) DO UPDATE
                SET monthly_messages = $2, updated_by = $3, updated_at = now()
                """,
                plan, monthly_messages, admin_id,
            )
    except asyncpg.exceptions.UndefinedTableError:
        return False
    return True


# Kinds that draw a learner's monthly allowance. Every learner-triggered
# AI turn belongs here; operator-side accounting rows ('summary', the
# auto-translate fills) never count.
#
# 'speak' and 'reader'/'reader_explain' used to be logged as 'chat', which
# both drew the allowance (correct) and made them invisible in the admin
# cost view (not correct — a Speak turn and a Reader text cost very
# different money from a tutor message). They now carry their own kind and
# are listed here, so what a learner spends is unchanged to the row.
ALLOWANCE_KINDS = (
    "chat",            # a tutor turn
    "speak",           # a Speak conversation turn (and its opener)
    "reader",          # a generated reading
    "reader_explain",  # "what does this word mean" inside a reading
    "gym_gen",         # a Gym on-demand generation (WP41)
    "gym_chart",       # a chart for a new word those drills exercise (WP45)
    "recs",            # a recommendations batch (~1/week ≈ 4 a month)
)


async def count_tutor_messages(
    conn: asyncpg.Connection, user_id: str, since
) -> int:
    """Messages this user has spent from their allowance since *since*.

    ALLOWANCE_KINDS draw the pool. 'summary' rows are the operator's cost
    accounting for the post-session summarizer — part of a message already
    spent — and never count.
    """
    n = await conn.fetchval(
        """
        SELECT count(*) FROM tutor_usage
        WHERE user_id = $1 AND created_at >= $2
          AND kind = ANY($3::text[])
        """,
        user_id, since, list(ALLOWANCE_KINDS),
    )
    return int(n or 0)


async def log_tutor_usage(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str | None,
    model: str | None,
    usage: dict | None = None,
    kind: str = "chat",
) -> None:
    """Record one answered tutor message (the allowance + cost-tracking unit).

    *usage* carries the turn's Anthropic token counts (WP9b); token columns
    stay NULL when capture wasn't possible. kind='summary' rows track
    summarizer cost and never count against allowances.
    """
    usage = usage or {}
    await conn.execute(
        """
        INSERT INTO tutor_usage
            (user_id, language_id, model, kind,
             input_tokens, output_tokens, cache_write_tokens, cache_read_tokens)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        user_id, language_id, model, kind,
        usage.get("input_tokens"), usage.get("output_tokens"),
        usage.get("cache_write_tokens"), usage.get("cache_read_tokens"),
    )


async def aggregate_tutor_usage(conn: asyncpg.Connection, since) -> list[dict]:
    """Per-(language, model, kind) usage rollup since *since* (admin cost view).

    Must run on a privileged connection: tutor_usage RLS is select-own, and
    this intentionally spans all users. The caller enforces admin first.
    """
    rows = await conn.fetch(
        """
        SELECT
            tu.language_id,
            l.name                                          AS language_name,
            tu.model,
            tu.kind,
            count(*)::int                                   AS messages,
            COALESCE(sum(tu.input_tokens), 0)::bigint       AS input_tokens,
            COALESCE(sum(tu.output_tokens), 0)::bigint      AS output_tokens,
            COALESCE(sum(tu.cache_write_tokens), 0)::bigint AS cache_write_tokens,
            COALESCE(sum(tu.cache_read_tokens), 0)::bigint  AS cache_read_tokens
        FROM tutor_usage tu
        LEFT JOIN languages l ON l.id = tu.language_id
        WHERE tu.created_at >= $1
        GROUP BY tu.language_id, l.name, tu.model, tu.kind
        ORDER BY l.name NULLS LAST, tu.model, tu.kind
        """,
        since,
    )
    return [dict(r) for r in rows]


async def get_tutor_access(conn: asyncpg.Connection, user_id: str) -> dict:
    """The admin's per-account tutor override (WP15b).

    Returns {"access": 'default'|'blocked'|'enabled', "daily_cap": int|None,
    "plan_scope": 'single'|'all'|None, "plan_ai": bool, "plan_backed": bool}.
    The plan drives the monthly allowance tier; `plan_ai` is whether the
    plan includes the AI pool (the four options: scope × AI); `plan_backed`
    is whether an active plan_subscriptions row stands behind the scope —
    a paid, admin-granted or dev-mock subscription, as opposed to the
    column default or a choice recorded free during the beta.

    Anything unexpected (no profile row yet, unmigrated column) normalizes
    to 'default' / False so the tier system decides — the override only
    ever acts when an admin explicitly set it. Columns are probed, not
    caught: a raised UndefinedColumnError aborts the whole pooled
    transaction (docs/decisions/0001), and this runs on the tutor's hot
    path.
    """
    has_ai_col = await conn.fetchval(
        """
        SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'user_profiles'
           AND column_name = 'plan_ai'
        """
    )
    ai_col = ", plan_ai" if isinstance(has_ai_col, int) and has_ai_col > 0 else ""
    row = await conn.fetchrow(
        f"SELECT tutor_access, tutor_daily_cap, plan_scope{ai_col} "
        "FROM user_profiles WHERE id = $1",
        user_id,
    )
    access = row["tutor_access"] if row else None
    if access not in ("blocked", "enabled"):
        access = "default"
    cap = row["tutor_daily_cap"] if row else None
    plan = row["plan_scope"] if row else None
    if plan not in ("single", "all"):
        plan = None
    # Strict comparisons, like `isinstance(cap, int)` above: these feed a
    # money decision, and anything that is not literally what the column
    # holds (a missing row, a stub connection) must read as "no".
    plan_ai = (row["plan_ai"] is True) if (row and ai_col) else False
    backed = await conn.fetchval(
        "SELECT to_regclass('public.plan_subscriptions') IS NOT NULL"
    )
    plan_backed = False
    if backed is True and plan:
        plan_backed = await conn.fetchval(
            "SELECT 1 FROM plan_subscriptions WHERE user_id = $1 AND is_active",
            user_id,
        ) == 1
    return {
        "access": access,
        "daily_cap": cap if isinstance(cap, int) else None,
        "plan_scope": plan,
        "plan_ai": plan_ai,
        "plan_backed": plan_backed,
    }


async def set_tutor_access(
    conn: asyncpg.Connection,
    user_id: str,
    access: str,
    daily_cap: int | None,
) -> None:
    """Write the per-account override (privileged; router checks admin)."""
    await conn.execute(
        """
        INSERT INTO user_profiles (id, tutor_access, tutor_daily_cap)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET
            tutor_access = EXCLUDED.tutor_access,
            tutor_daily_cap = EXCLUDED.tutor_daily_cap
        """,
        user_id, access, daily_cap,
    )


async def log_tutor_session(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    summary: str,
    message_count: int,
) -> None:
    """Append one immutable row per ended session (WP18a — the practice
    log). Runs on the user's RLS connection; insert-own policy applies."""
    await conn.execute(
        """
        INSERT INTO tutor_sessions (user_id, language_id, summary, message_count)
        VALUES ($1, $2, $3, $4)
        """,
        user_id, language_id, summary, message_count,
    )


async def list_tutor_sessions(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    limit: int = 10,
) -> list[dict]:
    """Most-recent-first session history for the tutor UI and the
    summarizer's continuity context."""
    rows = await conn.fetch(
        """
        SELECT id, summary, message_count, created_at
        FROM tutor_sessions
        WHERE user_id = $1 AND language_id = $2
        ORDER BY created_at DESC
        LIMIT $3
        """,
        user_id, language_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "summary": r["summary"],
            "message_count": r["message_count"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def has_tutor_entitlement(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> bool:
    """Return True when the user has an active, unexpired tutor entitlement."""
    row = await conn.fetchrow(
        """
        SELECT 1
        FROM tutor_entitlements
        WHERE user_id = $1
          AND language_id = $2
          AND is_active = true
          AND (expires_at IS NULL OR expires_at > now())
        """,
        user_id,
        language_id,
    )
    return row is not None


async def get_weak_areas(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    limit: int = 12,
) -> list[dict]:
    """Return the user's weakest items — vocabulary AND grammar — for a language.

    Ranks by recent failures (wrong / wrong_form in the last 30 days), then
    lapse count and FSRS difficulty. Vocabulary entries carry the word,
    definition, and morphology; grammar entries carry the point's title (as
    `word`, so downstream prompt/mock formatting is uniform) and CEFR level.
    Both feed the tutor, so it coaches on failed grammar patterns too, not just
    missed words.
    """
    vocab_rows = await conn.fetch(
        """
        SELECT
            'vocabulary'          AS kind,
            v.word,
            v.part_of_speech,
            v.morphology,
            t.definition          AS definition,
            NULL::text            AS level,
            uc.difficulty,
            uc.lapses,
            uc.streak,
            COUNT(rl.id) FILTER (
                WHERE rl.answer_result IN ('wrong', 'wrong_form')
                  AND rl.created_at > now() - interval '30 days'
            ) AS recent_failures,
            MAX(rl.created_at) FILTER (
                WHERE rl.answer_result IN ('wrong', 'wrong_form')
            ) AS last_failed_at
        FROM user_cards uc
        JOIN vocabulary v ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
        LEFT JOIN translations t ON v.id = t.vocabulary_id AND t.locale = 'en'
        LEFT JOIN review_log rl ON rl.card_id = uc.id
        WHERE uc.user_id = $1
          AND uc.language_id = $2
        GROUP BY v.word, v.part_of_speech, v.morphology, t.definition,
                 uc.difficulty, uc.lapses, uc.streak
        HAVING uc.lapses > 0
            -- FSRS difficulty is 1 (easy) .. 10 (hard); >= 7 flags a hard card
            OR COALESCE(uc.difficulty, 0) >= 7
            OR COUNT(rl.id) FILTER (
                   WHERE rl.answer_result IN ('wrong', 'wrong_form')
                     AND rl.created_at > now() - interval '30 days'
               ) > 0
        ORDER BY recent_failures DESC, uc.lapses DESC,
                 COALESCE(uc.difficulty, 0) DESC
        LIMIT $3
        """,
        user_id,
        language_id,
        limit,
    )
    grammar_rows = await conn.fetch(
        """
        SELECT
            'grammar'             AS kind,
            gp.title              AS word,
            NULL::text            AS part_of_speech,
            NULL::jsonb           AS morphology,
            NULL::text            AS definition,
            gp.level              AS level,
            uc.difficulty,
            uc.lapses,
            uc.streak,
            COUNT(rl.id) FILTER (
                WHERE rl.answer_result IN ('wrong', 'wrong_form')
                  AND rl.created_at > now() - interval '30 days'
            ) AS recent_failures,
            MAX(rl.created_at) FILTER (
                WHERE rl.answer_result IN ('wrong', 'wrong_form')
            ) AS last_failed_at
        FROM user_cards uc
        JOIN grammar_points gp ON uc.card_id = gp.id AND uc.card_type = 'grammar'
        LEFT JOIN review_log rl ON rl.card_id = uc.id
        WHERE uc.user_id = $1
          AND uc.language_id = $2
        GROUP BY gp.title, gp.level, uc.difficulty, uc.lapses, uc.streak
        HAVING uc.lapses > 0
            OR COALESCE(uc.difficulty, 0) >= 7
            OR COUNT(rl.id) FILTER (
                   WHERE rl.answer_result IN ('wrong', 'wrong_form')
                     AND rl.created_at > now() - interval '30 days'
               ) > 0
        ORDER BY recent_failures DESC, uc.lapses DESC,
                 COALESCE(uc.difficulty, 0) DESC
        LIMIT $3
        """,
        user_id,
        language_id,
        limit,
    )
    merged = [dict(r) for r in vocab_rows] + [dict(r) for r in grammar_rows]
    merged.sort(
        key=lambda r: (
            -(r["recent_failures"] or 0),
            -(r["lapses"] or 0),
            -(r["difficulty"] or 0),
        )
    )
    return merged[:limit]


async def get_study_stats(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> dict:
    """Return overall study performance for a language (not just failures).

    Gives the tutor the bird's-eye view: how much has been studied, how
    accurate the learner is lately, how due they are, and how far up the
    CEFR ladder their learned cards reach — so it can set session ambition.
    """
    cards = await conn.fetchrow(
        """
        SELECT
            COUNT(*)                                        AS total_cards,
            COUNT(*) FILTER (WHERE repetitions > 0)         AS learned_cards,
            COUNT(*) FILTER (WHERE next_review <= now()
                               AND is_suspended = false)    AS due_now,
            ROUND(AVG(difficulty)::numeric, 2)             AS avg_difficulty
        FROM user_cards
        WHERE user_id = $1 AND language_id = $2
        """,
        user_id,
        language_id,
    )
    reviews = await conn.fetchrow(
        """
        SELECT
            COUNT(*)                                                       AS reviews_30d,
            COUNT(*) FILTER (
                WHERE rl.answer_result IN ('correct', 'correct_sloppy')
            )                                                              AS correct_30d
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        WHERE rl.user_id = $1
          AND uc.language_id = $2
          AND rl.created_at > now() - interval '30 days'
        """,
        user_id,
        language_id,
    )
    level = await conn.fetchval(
        """
        SELECT MAX(v.level)
        FROM user_cards uc
        JOIN vocabulary v ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
        WHERE uc.user_id = $1 AND uc.language_id = $2 AND uc.repetitions > 0
        """,
        user_id,
        language_id,
    )

    reviews_30d = int(reviews["reviews_30d"]) if reviews else 0
    correct_30d = int(reviews["correct_30d"]) if reviews else 0
    accuracy = round(correct_30d / reviews_30d, 2) if reviews_30d else None

    return {
        "total_cards": int(cards["total_cards"]) if cards else 0,
        "learned_cards": int(cards["learned_cards"]) if cards else 0,
        "due_now": int(cards["due_now"]) if cards else 0,
        "avg_difficulty": (
            float(cards["avg_difficulty"]) if cards and cards["avg_difficulty"] else None
        ),
        "reviews_last_30d": reviews_30d,
        "accuracy_last_30d": accuracy,
        "highest_level_reached": level,
    }


# ---------------------------------------------------------------------------
# Learner memory — global profile + per-language profile/summary
# ---------------------------------------------------------------------------

def _load_jsonb(value) -> dict:
    """asyncpg returns jsonb as a str by default — decode to a dict."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return dict(value)


async def get_user_profile(conn: asyncpg.Connection, user_id: str) -> dict:
    """Return the learner's global profile dict (empty if none yet)."""
    row = await conn.fetchrow(
        "SELECT profile FROM tutor_user_profile WHERE user_id = $1", user_id
    )
    return _load_jsonb(row["profile"]) if row else {}


async def get_language_profile(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> dict:
    """Return {"profile": dict, "session_summary": str} for a language."""
    row = await conn.fetchrow(
        """
        SELECT profile, session_summary
        FROM tutor_language_profile
        WHERE user_id = $1 AND language_id = $2
        """,
        user_id,
        language_id,
    )
    if not row:
        return {"profile": {}, "session_summary": ""}
    return {
        "profile": _load_jsonb(row["profile"]),
        "session_summary": row["session_summary"] or "",
    }


async def upsert_user_profile(
    conn: asyncpg.Connection, user_id: str, profile: dict
) -> None:
    """Replace the learner's global profile with *profile*."""
    await conn.execute(
        """
        INSERT INTO tutor_user_profile (user_id, profile, updated_at)
        VALUES ($1, $2::jsonb, now())
        ON CONFLICT (user_id) DO UPDATE
            SET profile = EXCLUDED.profile, updated_at = now()
        """,
        user_id,
        json.dumps(profile, ensure_ascii=False),
    )


async def upsert_language_profile(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    profile: dict,
    session_summary: str | None = None,
    touch_session: bool = False,
) -> None:
    """Upsert a per-language profile.

    session_summary is only overwritten when a non-None value is passed, so
    the `remember` tool (which updates `profile` mid-session) doesn't clobber
    the summary the post-session summarizer wrote.
    """
    await conn.execute(
        """
        INSERT INTO tutor_language_profile
            (user_id, language_id, profile, session_summary, last_session_at, updated_at)
        VALUES (
            $1, $2, $3::jsonb,
            COALESCE($4, ''),
            CASE WHEN $5 THEN now() ELSE NULL END,
            now()
        )
        ON CONFLICT (user_id, language_id) DO UPDATE SET
            profile = EXCLUDED.profile,
            session_summary = COALESCE($4, tutor_language_profile.session_summary),
            last_session_at = CASE WHEN $5 THEN now()
                                   ELSE tutor_language_profile.last_session_at END,
            updated_at = now()
        """,
        user_id,
        language_id,
        json.dumps(profile, ensure_ascii=False),
        session_summary,
        touch_session,
    )


def profile_facts(profile: dict) -> list[dict]:
    """The learner-visible facts in a profile dict.

    Underscore keys are the tutor's internal state (_active_focus, _sources)
    and never facts. Each fact carries its provenance from the _sources map;
    a key recorded before provenance tracking reads as "inferred" — the same
    cautious default the prompt uses.
    """
    sources = profile.get("_sources") or {}
    return [
        {"key": k, "value": v, "source": sources.get(k, "inferred")}
        for k, v in profile.items()
        if not k.startswith("_")
    ]


async def list_tutor_memory(conn: asyncpg.Connection, user_id: str) -> dict:
    """Everything the tutor remembers about a learner, for the Settings
    panel: global facts plus per-language facts (languages with none are
    omitted — an empty group is noise, not information)."""
    global_profile = await get_user_profile(conn, user_id)
    rows = await conn.fetch(
        """
        SELECT tlp.language_id, l.name, l.code, tlp.profile
        FROM tutor_language_profile tlp
        JOIN languages l ON l.id = tlp.language_id
        WHERE tlp.user_id = $1
        ORDER BY l.name
        """,
        user_id,
    )
    languages = []
    for r in rows:
        facts = profile_facts(_load_jsonb(r["profile"]))
        if facts:
            languages.append({
                "language_id": str(r["language_id"]),
                "name": r["name"],
                "code": r["code"],
                "facts": facts,
            })
    return {"global": profile_facts(global_profile), "languages": languages}


async def delete_tutor_memory_fact(
    conn: asyncpg.Connection,
    user_id: str,
    scope: str,
    key: str,
    language_id: str | None = None,
) -> bool:
    """Remove one remembered fact (and its provenance entry) at the
    learner's request. Returns False when there was no such fact.

    Underscore keys are refused: they are tutor plumbing, not facts, and
    the API must not offer a path to corrupt them.
    """
    if key.startswith("_"):
        return False
    if scope == "global":
        profile = await get_user_profile(conn, user_id)
    elif scope == "language" and language_id:
        lang = await get_language_profile(conn, user_id, language_id)
        profile = lang["profile"]
    else:
        return False
    if key not in profile:
        return False
    profile = dict(profile)
    del profile[key]
    sources = dict(profile.get("_sources") or {})
    sources.pop(key, None)
    if sources:
        profile["_sources"] = sources
    else:
        profile.pop("_sources", None)
    if scope == "global":
        await upsert_user_profile(conn, user_id, profile)
    else:
        # session_summary=None leaves the rolling summary untouched.
        await upsert_language_profile(conn, user_id, language_id, profile)
    return True


# ---------------------------------------------------------------------------
# WP19(e): mastery stars — tutor-suggested, learner-confirmed advancement
# ---------------------------------------------------------------------------


async def create_mastery_suggestions(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    stars: list[dict],
) -> int:
    """Record the tutor's `suggest_mastered` calls as pending suggestions.

    Each star is {"key": kind, "value": item, "evidence": ...} (the reserved
    "_mastery" scope of the remember accumulator). The item text is resolved
    to the learner's card by exact (case-insensitive) title/word match;
    unmatched items are dropped silently — the tutor was told to use the
    weak-items list verbatim. Cards already at seasoned stability (>= 30
    days) or still suspended are skipped: there is nothing to advance.

    Returns the number of suggestions actually recorded.
    """
    created = 0
    for star in stars:
        kind = star.get("key")
        item = (star.get("value") or "").strip()
        if kind not in ("vocabulary", "grammar") or not item:
            continue
        if kind == "grammar":
            card_id = await conn.fetchval(
                """
                SELECT uc.id
                FROM user_cards uc
                JOIN grammar_points gp
                  ON uc.card_id = gp.id AND uc.card_type = 'grammar'
                WHERE uc.user_id = $1
                  AND uc.language_id = $2
                  AND lower(gp.title) = lower($3)
                  AND uc.is_suspended = false
                  AND COALESCE(uc.stability, 0) < 30
                """,
                user_id, language_id, item,
            )
        else:
            card_id = await conn.fetchval(
                """
                SELECT uc.id
                FROM user_cards uc
                JOIN vocabulary v
                  ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
                WHERE uc.user_id = $1
                  AND uc.language_id = $2
                  AND lower(v.word) = lower($3)
                  AND uc.is_suspended = false
                  AND COALESCE(uc.stability, 0) < 30
                """,
                user_id, language_id, item,
            )
        if card_id is None:
            continue
        result = await conn.execute(
            """
            INSERT INTO tutor_card_suggestions
                (user_id, card_id, language_id, item_title, kind, evidence)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (card_id) WHERE status = 'pending' DO NOTHING
            """,
            user_id, card_id, language_id, item, kind, star.get("evidence"),
        )
        if result.endswith("1"):
            created += 1
    return created


async def list_mastery_suggestions(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> list[dict]:
    """Pending mastery stars for the tutor UI, newest first."""
    rows = await conn.fetch(
        """
        SELECT id, item_title, kind, evidence, created_at
        FROM tutor_card_suggestions
        WHERE user_id = $1 AND language_id = $2 AND status = 'pending'
        ORDER BY created_at DESC
        """,
        user_id, language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "item": r["item_title"],
            "kind": r["kind"],
            "evidence": r["evidence"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def resolve_mastery_suggestion(
    conn: asyncpg.Connection, user_id: str, suggestion_id: str, action: str
) -> dict | None:
    """Learner's verdict on a star: 'accept' advances the card, 'dismiss'
    just clears it. Returns {"action", "advanced"} or None if the suggestion
    isn't theirs / isn't pending.

    Accepting jumps the card to the seasoned floor — stability and interval
    at least 30 days, next review a month out — the concrete meaning of
    "mark it as farther along" without pretending it's fully mastered.
    """
    card_id = await conn.fetchval(
        """
        UPDATE tutor_card_suggestions
        SET status = CASE WHEN $3 = 'accept' THEN 'accepted' ELSE 'dismissed' END,
            resolved_at = now()
        WHERE id = $1 AND user_id = $2 AND status = 'pending'
        RETURNING card_id
        """,
        suggestion_id, user_id, action,
    )
    if card_id is None:
        return None
    advanced = False
    if action == "accept":
        result = await conn.execute(
            """
            UPDATE user_cards
            SET stability = GREATEST(COALESCE(stability, 0), 30),
                interval = GREATEST(interval, 30),
                next_review = now() + GREATEST(interval, 30) * interval '1 day',
                state = 'review'
            WHERE id = $1 AND user_id = $2
            """,
            card_id, user_id,
        )
        advanced = result.endswith("1")
    return {"action": action, "advanced": advanced}
