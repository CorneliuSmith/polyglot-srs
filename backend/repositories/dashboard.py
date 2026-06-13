"""Dashboard repository — aggregation queries for the dashboard endpoint."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import asyncpg


async def get_dashboard_stats(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
) -> dict:
    """Return dashboard statistics for the given user and language.

    Returns:
        {
            "due_count": int,
            "streak_days": int,
            "cefr_progress": {
                "A1": {"learned": int, "total": int},
                ...
                "C2": {"learned": int, "total": int},
            }
        }
    """
    # -- Due count -----------------------------------------------------------
    due_row = await conn.fetchrow(
        """
        SELECT COUNT(*) AS due_count
        FROM user_cards
        WHERE user_id = $1
          AND language_id = $2
          AND next_review <= now()
          AND is_suspended = false
        """,
        user_id,
        language_id,
    )
    due_count = int(due_row["due_count"])

    # -- Streak --------------------------------------------------------------
    # Fetch distinct review dates descending to count consecutive days
    date_rows = await conn.fetch(
        """
        SELECT DISTINCT DATE(rl.created_at AT TIME ZONE 'UTC') AS review_date
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        WHERE rl.user_id = $1
          AND uc.language_id = $2
        ORDER BY review_date DESC
        """,
        user_id,
        language_id,
    )
    review_dates = {r["review_date"] for r in date_rows}
    streak_days = _compute_streak(review_dates)

    # -- CEFR progress -------------------------------------------------------
    cefr_rows = await conn.fetch(
        """
        SELECT
            v.level,
            COUNT(uc.id)  AS learned,
            COUNT(v.id)   AS total
        FROM vocabulary v
        LEFT JOIN user_cards uc
               ON v.id = uc.card_id
              AND uc.card_type = 'vocabulary'
              AND uc.user_id = $1
        WHERE v.language_id = $2
          AND v.level IS NOT NULL
        GROUP BY v.level
        """,
        user_id,
        language_id,
    )

    cefr_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    cefr_progress: dict[str, dict] = {
        lvl: {"learned": 0, "total": 0} for lvl in cefr_levels
    }
    for row in cefr_rows:
        lvl = row["level"]
        if lvl in cefr_progress:
            cefr_progress[lvl] = {
                "learned": int(row["learned"]),
                "total": int(row["total"]),
            }

    return {
        "due_count": due_count,
        "streak_days": streak_days,
        "cefr_progress": cefr_progress,
    }


def _compute_streak(review_dates: set[date]) -> int:
    """Count consecutive days ending today (or yesterday) with a review.

    A streak of 1 means the user reviewed today only.  If no review today
    but a review yesterday, the streak is still counted from yesterday.

    "Today" is the current UTC date, matching the UTC day boundaries used
    when extracting review dates in SQL.
    """
    if not review_dates:
        return 0

    today = datetime.now(UTC).date()
    # Allow streak to start from today or yesterday (grace period)
    start = today if today in review_dates else today - timedelta(days=1)
    if start not in review_dates:
        return 0

    streak = 0
    current = start
    while current in review_dates:
        streak += 1
        current -= timedelta(days=1)

    return streak
