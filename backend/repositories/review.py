"""Review log repository — append-only via RLS."""

from __future__ import annotations

import asyncpg


async def insert_review_log(
    conn: asyncpg.Connection,
    user_id: str,
    card_id: str,
    quality: int,
    ease_before: float,
    ease_after: float,
    interval_before: int,
    interval_after: int,
    time_taken_ms: int | None,
    answer_result: str | None,
) -> dict:
    """Insert a review log entry and return the created record."""
    row = await conn.fetchrow(
        """
        INSERT INTO review_log (
            user_id, card_id, quality,
            ease_factor_before, ease_factor_after,
            interval_before, interval_after,
            time_taken_ms, answer_result
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, created_at
        """,
        user_id,
        card_id,
        quality,
        ease_before,
        ease_after,
        interval_before,
        interval_after,
        time_taken_ms,
        answer_result,
    )
    return dict(row)
