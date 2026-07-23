"""Tutor repository — entitlement checks and weak-area aggregation.

The weak-area query is what grounds the AI tutor: it pulls the user's worst
recent material (failed reviews, low-ease cards) so the tutor coaches on what
the learner is actually struggling with rather than generic content.
"""

from __future__ import annotations

import json

import asyncpg


async def count_tutor_messages(
    conn: asyncpg.Connection, user_id: str, since
) -> int:
    """Messages this user has spent from their allowance since *since*.

    Counted kinds draw the pool: 'chat' (a tutor turn) and 'gym_gen' (a Gym
    on-demand generation, WP41). 'summary' rows are the operator's cost
    accounting for the post-session summarizer — part of a message already
    spent — and never count.
    """
    n = await conn.fetchval(
        """
        SELECT count(*) FROM tutor_usage
        WHERE user_id = $1 AND created_at >= $2 AND kind IN ('chat', 'gym_gen')
        """,
        user_id, since,
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
    "plan_scope": 'single'|'all'|None} (the plan drives the monthly
    allowance tier).
    Anything unexpected (no profile row yet, unmigrated column) normalizes
    to 'default' so the tier system decides — the override only ever acts
    when an admin explicitly set it.
    """
    row = await conn.fetchrow(
        "SELECT tutor_access, tutor_daily_cap, plan_scope "
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
    return {
        "access": access,
        "daily_cap": cap if isinstance(cap, int) else None,
        "plan_scope": plan,
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
