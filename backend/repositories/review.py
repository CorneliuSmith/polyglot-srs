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


async def add_card_feedback(
    conn: asyncpg.Connection, user_id: str, card_id: str, message: str
) -> bool:
    """Record a learner's feedback on a card, tied to its underlying content.

    *card_id* is the learner's user_cards id; RLS scopes it to them. The
    feedback is stored against the grammar point / vocabulary so contributors
    can act on it. Returns False if the card isn't the user's.
    """
    card = await conn.fetchrow(
        "SELECT card_type, card_id, language_id FROM user_cards WHERE id = $1",
        card_id,
    )
    if card is None:
        return False
    await conn.execute(
        """
        INSERT INTO card_feedback
            (user_id, language_id, card_type, content_id, message)
        VALUES ($1, $2, $3, $4, $5)
        """,
        user_id, card["language_id"], card["card_type"], card["card_id"], message,
    )
    return True
