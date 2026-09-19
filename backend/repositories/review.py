"""Review log repository — append-only via RLS."""

from __future__ import annotations

import asyncpg

from backend.repositories.pool import savepoint


async def insert_review_log(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    card_id: str,
    quality: int,
    answer_result: str | None,
    interval_before: int,
    interval_after: int,
    stability_before: float | None,
    stability_after: float,
    difficulty_before: float | None,
    difficulty_after: float,
    time_taken_ms: int | None,
    prompt_sentence: str | None = None,
) -> dict:
    """Insert a review log entry (FSRS variables) and return the record."""
    row = await conn.fetchrow(
        """
        INSERT INTO review_log (
            user_id, card_id, quality, answer_result,
            interval_before, interval_after,
            stability_before, stability_after,
            difficulty_before, difficulty_after,
            time_taken_ms, prompt_sentence
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id, created_at
        """,
        user_id,
        card_id,
        quality,
        answer_result,
        interval_before,
        interval_after,
        stability_before,
        stability_after,
        difficulty_before,
        difficulty_after,
        time_taken_ms,
        prompt_sentence,
    )
    return dict(row)


# One statement, two shapes — the app_feedback.variants writer's pattern:
# the five columns every deployment has are spelled once, so the migrated
# and the not-yet-migrated write cannot drift.
_INSERT_FEEDBACK = """
    INSERT INTO card_feedback
        (user_id, language_id, card_type, content_id, message{extra_cols})
    VALUES ($1, $2, $3, $4, $5{extra_vals})
"""


async def add_card_feedback(
    conn: asyncpg.Connection,
    user_id: str,
    card_id: str,
    message: str,
    *,
    field: str | None = None,
    drill_id: str | None = None,
    locale: str | None = None,
    support_locale: str | None = None,
) -> bool:
    """Record a learner's feedback on a card, tied to its underlying content.

    *card_id* is the learner's user_cards id; RLS scopes it to them. The
    feedback is stored against the grammar point / vocabulary so contributors
    can act on it. Returns False if the card isn't the user's.

    *field*, *drill_id*, *locale* and *support_locale* are migration
    20261030's columns (docs/plans/quality-guardrails-telemetry.md §5, A6):
    a report on a grammar card recorded the POINT and not the drill the
    learner saw, so the sentence was unrecoverable, and no learner channel
    recorded the locale they were reading in. The migration is owner-applied
    and the code deploys first, so the wide INSERT runs inside a savepoint
    and falls back to the five-column shape on UndefinedColumnError — a
    report that reaches nobody is worse than a report with no label.
    """
    card = await conn.fetchrow(
        "SELECT card_type, card_id, language_id FROM user_cards WHERE id = $1",
        card_id,
    )
    if card is None:
        return False
    base = (user_id, card["language_id"], card["card_type"], card["card_id"], message)
    try:
        async with savepoint(conn):
            await conn.execute(
                _INSERT_FEEDBACK.format(
                    extra_cols=", field, drill_id, locale, support_locale",
                    extra_vals=", $6, $7::uuid, $8, $9",
                ),
                *base, field, drill_id, locale, support_locale,
            )
    except asyncpg.exceptions.UndefinedColumnError:
        await conn.execute(_INSERT_FEEDBACK.format(extra_cols="", extra_vals=""), *base)
    return True
