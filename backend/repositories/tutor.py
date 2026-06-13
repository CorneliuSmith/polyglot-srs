"""Tutor repository — entitlement checks and weak-area aggregation.

The weak-area query is what grounds the AI tutor: it pulls the user's worst
recent material (failed reviews, low-ease cards) so the tutor coaches on what
the learner is actually struggling with rather than generic content.
"""

from __future__ import annotations

import asyncpg


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
    """Return the user's weakest vocabulary cards for a language.

    Ranks cards by recent failures first (wrong / wrong_form answers in the
    last 30 days), then by lapse count and low ease. Each entry carries the
    word, its definition, morphology, and failure stats so the tutor can
    build targeted drills.
    """
    rows = await conn.fetch(
        """
        SELECT
            v.word,
            v.part_of_speech,
            v.morphology,
            t.definition          AS definition,
            uc.ease_factor,
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
                 uc.ease_factor, uc.lapses, uc.streak
        HAVING uc.lapses > 0
            OR uc.ease_factor < 2.3
            OR COUNT(rl.id) FILTER (
                   WHERE rl.answer_result IN ('wrong', 'wrong_form')
                     AND rl.created_at > now() - interval '30 days'
               ) > 0
        ORDER BY recent_failures DESC, uc.lapses DESC, uc.ease_factor ASC
        LIMIT $3
        """,
        user_id,
        language_id,
        limit,
    )
    return [dict(r) for r in rows]
