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

    # -- Review forecast (next 7 days, from user_cards.next_review) ----------
    forecast_rows = await conn.fetch(
        """
        SELECT DATE(next_review AT TIME ZONE 'UTC') AS due_date, COUNT(*) AS n
        FROM user_cards
        WHERE user_id = $1
          AND language_id = $2
          AND is_suspended = false
          AND next_review > now()
          AND next_review < now() + interval '7 days'
        GROUP BY due_date
        ORDER BY due_date
        """,
        user_id,
        language_id,
    )
    today = datetime.now(UTC).date()
    forecast_by_date = {r["due_date"]: int(r["n"]) for r in forecast_rows}
    forecast = [
        {
            "date": (today + timedelta(days=i)).isoformat(),
            "count": forecast_by_date.get(today + timedelta(days=i), 0),
        }
        for i in range(7)
    ]

    # -- Activity (last 14 days, reviews/day split vocab vs grammar) ---------
    activity_rows = await conn.fetch(
        """
        SELECT
            DATE(rl.created_at AT TIME ZONE 'UTC') AS day,
            COUNT(*) FILTER (WHERE uc.card_type = 'vocabulary') AS vocab,
            COUNT(*) FILTER (WHERE uc.card_type <> 'vocabulary') AS grammar
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        WHERE rl.user_id = $1
          AND uc.language_id = $2
          AND rl.created_at > now() - interval '14 days'
        GROUP BY day
        """,
        user_id,
        language_id,
    )
    activity_by_day = {
        r["day"]: {"vocab": int(r["vocab"]), "grammar": int(r["grammar"])}
        for r in activity_rows
    }
    activity = [
        {
            "date": (today - timedelta(days=13 - i)).isoformat(),
            **activity_by_day.get(
                today - timedelta(days=13 - i), {"vocab": 0, "grammar": 0}
            ),
        }
        for i in range(14)
    ]

    # -- Named SRS stages (FSRS stability bands) ------------------------------
    # Bunpro-style tiles: how deep in memory each started card sits. Ghosts
    # are relearning cards (recently failed, still haunting the queue).
    stage_rows = await conn.fetch(
        """
        SELECT
            CASE WHEN card_type = 'personal' THEN 'vocab' ELSE
                 CASE WHEN card_type = 'vocabulary' THEN 'vocab' ELSE 'grammar' END
            END AS kind,
            CASE
                WHEN state = 'relearning' THEN 'ghost'
                WHEN card_type = 'personal' THEN 'self_study'
                WHEN COALESCE(stability, 0) < 7   THEN 'beginner'
                WHEN stability < 30  THEN 'adept'
                WHEN stability < 90  THEN 'seasoned'
                WHEN stability < 180 THEN 'expert'
                ELSE 'master'
            END AS stage,
            COUNT(*) AS n
        FROM user_cards
        WHERE user_id = $1
          AND language_id = $2
          AND NOT (is_suspended AND repetitions = 0)  -- unconfirmed walkthroughs
        GROUP BY kind, stage
        """,
        user_id,
        language_id,
    )
    stage_names = ["beginner", "adept", "seasoned", "expert", "master",
                   "self_study", "ghost"]
    stages = {
        kind: {s: 0 for s in stage_names} for kind in ("vocab", "grammar")
    }
    for r in stage_rows:
        stages[r["kind"]][r["stage"]] = int(r["n"])

    # -- Profile card ----------------------------------------------------------
    profile_row = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT DATE(rl.created_at AT TIME ZONE 'UTC')) AS days_studied,
            COUNT(DISTINCT rl.card_id)                             AS items_studied
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        WHERE rl.user_id = $1 AND uc.language_id = $2
        """,
        user_id,
        language_id,
    )
    # Last session = the most recent UTC day with reviews.
    last_session_row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (
                WHERE rl.answer_result IN ('correct', 'correct_sloppy')
            ) AS correct
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        WHERE rl.user_id = $1
          AND uc.language_id = $2
          AND DATE(rl.created_at AT TIME ZONE 'UTC') = (
              SELECT MAX(DATE(rl2.created_at AT TIME ZONE 'UTC'))
              FROM review_log rl2
              JOIN user_cards uc2 ON rl2.card_id = uc2.id
              WHERE rl2.user_id = $1 AND uc2.language_id = $2
          )
        """,
        user_id,
        language_id,
    )
    last_total = int(last_session_row["total"]) if last_session_row else 0
    last_correct = int(last_session_row["correct"]) if last_session_row else 0
    # Streak flame week: which of the last 7 days (oldest→today) had reviews.
    week = [
        {
            "date": (today - timedelta(days=6 - i)).isoformat(),
            "studied": (today - timedelta(days=6 - i)) in review_dates,
        }
        for i in range(7)
    ]

    return {
        "due_count": due_count,
        "streak_days": streak_days,
        "cefr_progress": cefr_progress,
        "forecast": forecast,
        "activity": activity,
        "stages": stages,
        "profile": {
            "days_studied": int(profile_row["days_studied"]) if profile_row else 0,
            "items_studied": int(profile_row["items_studied"]) if profile_row else 0,
            "last_session_accuracy": (
                round(last_correct / last_total, 2) if last_total else None
            ),
            "week": week,
        },
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
