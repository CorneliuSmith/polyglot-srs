"""Tiered learner-assessment context (owner request): every AI surface
grounds itself in an assessment of the learner, sized to what that surface
actually needs.

    depth='forms'   → the Gym's generator: per-cell struggle rollup for the
                      chosen grammar points, so new drills target the forms
                      the learner actually gets wrong.
    depth='reading' → the Reader: level, known vocabulary, learned
                      structures, weak words, active focus — enough to
                      calibrate sentence complexity and coverage.
    depth='full'    → the Tutor: everything in 'reading' PLUS the detailed
                      weak-area rows and overall study stats.

Cards/reviews need no tier here: the SRS scheduler *is* the assessment —
FSRS state and the review log drive card selection directly.
"""

from __future__ import annotations

import asyncpg

from backend.repositories.reader import CEFR_ORDER, get_learner_model
from backend.repositories.tutor import (
    get_language_profile,
    get_study_stats,
    get_weak_areas,
)

# Weak-item breadth per tier: the Reader only re-exposes a handful; the
# Tutor coaches from the full list.
_READING_WEAK_LIMIT = 6
_FULL_WEAK_LIMIT = 12

# A cell only counts as a "struggle" once there's real evidence — a single
# slip on a form seen once is noise, not a pattern.
_MIN_CELL_MISSES = 2

# Below this many cards, the level derived from learned cards is mostly the
# cold-start default — a writing-sample baseline (onboarding) outranks it.
# Past it, earned card evidence wins.
_BASELINE_CARD_CUTOFF = 50


async def get_form_struggles(
    conn: asyncpg.Connection, user_id: str, point_ids: list[str]
) -> dict[str, list[dict]]:
    """The 'forms' tier: per-cell miss rollup from gym_progress, keyed by
    grammar point id. Cells are ordered worst-first; cells the learner has
    never missed are omitted entirely."""
    if not point_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT ds.grammar_point_id::text AS point_id,
               ds.cell,
               SUM(gp.seen)       AS seen,
               SUM(gp.misses)     AS misses,
               SUM(gp.wrong_form) AS wrong_form,
               SUM(gp.hint_used)  AS hint_used
        FROM gym_progress gp
        JOIN drill_sentences ds ON ds.id = gp.drill_id
        WHERE gp.user_id = $1
          AND ds.grammar_point_id = ANY($2::uuid[])
          AND ds.cell IS NOT NULL
        GROUP BY ds.grammar_point_id, ds.cell
        HAVING SUM(gp.misses) > 0
        ORDER BY SUM(gp.misses)::float / GREATEST(SUM(gp.seen), 1) DESC,
                 SUM(gp.misses) DESC
        """,
        user_id, point_ids,
    )
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["point_id"], []).append({
            "cell": r["cell"],
            "seen": int(r["seen"]),
            "misses": int(r["misses"]),
            "wrong_form": int(r["wrong_form"]),
            "hint_used": int(r["hint_used"]),
        })
    return out


def pick_struggling_cell(struggles: list[dict]) -> str | None:
    """The single cell generation should target, or None when the learner
    has no evidenced struggle (generation then stays cell-agnostic)."""
    for s in struggles:
        if s["misses"] >= _MIN_CELL_MISSES:
            return s["cell"]
    return None


async def get_assessment_summary(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    depth: str = "reading",
    language_profile: dict | None = None,
) -> dict:
    """The 'reading' and 'full' tiers (use get_form_struggles for 'forms').

    *language_profile*: callers that already fetched the tutor language
    profile (the tutor does, for its memory merge) pass it in to avoid a
    duplicate query.
    """
    if depth not in ("reading", "full"):
        raise ValueError(f"unknown assessment depth: {depth}")

    summary = await get_learner_model(conn, user_id, language_id)
    weak_limit = _FULL_WEAK_LIMIT if depth == "full" else _READING_WEAK_LIMIT
    weak = await get_weak_areas(conn, user_id, language_id, limit=weak_limit)
    if language_profile is None:
        language_profile = (
            await get_language_profile(conn, user_id, language_id)
        )["profile"]

    # Writing-sample priming (owner): a fresh account's card-derived level is
    # just the A1 cold start; until enough cards exist, the onboarding
    # writing baseline lifts it so the Tutor/Reader start at the learner's
    # real level instead of talking down to them.
    baseline = (language_profile.get("_writing_baseline") or {}).get("level")
    if (
        baseline in CEFR_ORDER
        and summary.get("known_count", 0) < _BASELINE_CARD_CUTOFF
        and CEFR_ORDER.index(baseline) > CEFR_ORDER.index(summary["level"])
    ):
        summary["level"] = baseline

    summary["weak_words"] = [w.get("word") for w in weak if w.get("word")]
    summary["focus"] = [
        f.get("structure")
        for f in (language_profile.get("_active_focus") or [])
        if isinstance(f, dict) and f.get("structure")
    ]
    if depth == "full":
        summary["weak_areas"] = weak
        summary["study_stats"] = await get_study_stats(
            conn, user_id, language_id
        )
    return summary
