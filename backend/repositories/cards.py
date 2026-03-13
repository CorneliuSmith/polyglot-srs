"""User cards repository — RLS-protected queries."""

from __future__ import annotations

import asyncpg


async def get_due_cards(
    conn: asyncpg.Connection, language_id: str, limit: int = 20
) -> list[dict]:
    """Return due cards for the authenticated user, sorted by next_review ASC.

    RLS automatically filters to the connection's user context.
    """
    rows = await conn.fetch(
        """
        SELECT id, user_id, language_id, card_type, card_id,
               ease_factor, interval, repetitions, streak, lapses,
               next_review, last_review, is_suspended, created_at
        FROM user_cards
        WHERE language_id = $1
          AND next_review <= now()
          AND is_suspended = false
        ORDER BY next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
    )
    return [dict(r) for r in rows]


async def update_card_srs(
    conn: asyncpg.Connection, card_id: str, srs_update: dict
) -> None:
    """Update a card's SRS fields after review."""
    await conn.execute(
        """
        UPDATE user_cards
        SET ease_factor = $1,
            interval = $2,
            repetitions = $3,
            streak = $4,
            lapses = $5,
            next_review = $6,
            last_review = now()
        WHERE id = $7
        """,
        srs_update["ease_factor"],
        srs_update["interval"],
        srs_update["repetitions"],
        srs_update["streak"],
        srs_update["lapses"],
        srs_update["next_review"],
        card_id,
    )
