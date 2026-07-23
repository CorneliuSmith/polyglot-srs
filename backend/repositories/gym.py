"""Adaptive Gym progress: persist and read a learner's per-drill practice
history (WP). Runs under the learner's RLS connection — the policies scope every
row to auth.uid()."""

from __future__ import annotations

import asyncpg

# Results that count as a miss / specifically a form error (the target skill).
_MISS = {"wrong", "wrong_form"}


async def record_gym_attempt(
    conn: asyncpg.Connection,
    user_id: str,
    drill_id: str,
    answer_result: str,
    used_hint: bool,
) -> None:
    """Fold one Gym answer into the learner's history for *drill_id*.

    A "clean correct" (correct AND no hint used) extends the mastery streak;
    anything else resets it. Misses and hint-leans accumulate so selection can
    bring shaky forms back. Ungraded: this never touches the SRS schedule.
    """
    is_miss = 1 if answer_result in _MISS else 0
    is_wrong_form = 1 if answer_result == "wrong_form" else 0
    hinted = 1 if used_hint else 0
    clean = answer_result == "correct" and not used_hint
    await conn.execute(
        """
        INSERT INTO gym_progress
            (user_id, drill_id, seen, misses, wrong_form, hint_used, streak,
             last_seen_at)
        VALUES ($1, $2, 1, $3, $4, $5, $6, now())
        ON CONFLICT (user_id, drill_id) DO UPDATE SET
            seen         = gym_progress.seen + 1,
            misses       = gym_progress.misses + $3,
            wrong_form   = gym_progress.wrong_form + $4,
            hint_used    = gym_progress.hint_used + $5,
            streak       = CASE WHEN $7 THEN gym_progress.streak + 1 ELSE 0 END,
            last_seen_at = now()
        """,
        user_id, drill_id, is_miss, is_wrong_form, hinted,
        1 if clean else 0, clean,
    )


async def get_gym_progress(
    conn: asyncpg.Connection, user_id: str, drill_ids: list[str]
) -> dict[str, dict]:
    """The learner's stats for the given drills, keyed by drill_id. Drills with
    no history are simply absent (selection treats them as unseen)."""
    if not drill_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT drill_id, seen, misses, wrong_form, hint_used, streak,
               EXTRACT(EPOCH FROM (now() - last_seen_at)) AS age_seconds
        FROM gym_progress
        WHERE user_id = $1 AND drill_id = ANY($2::uuid[])
        """,
        user_id, drill_ids,
    )
    return {
        str(r["drill_id"]): {
            "seen": r["seen"],
            "misses": r["misses"],
            "wrong_form": r["wrong_form"],
            "hint_used": r["hint_used"],
            "streak": r["streak"],
            "age_seconds": float(r["age_seconds"]),
        }
        for r in rows
    }
