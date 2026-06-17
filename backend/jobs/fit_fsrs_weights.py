"""Periodic job: fit FSRS weights from accumulated review history.

Fits one set of weights per language (pooled across all users), and a
per-user-per-language set for any learner who has reviewed enough in a language
to support their own fit. Writes to fsrs_weights via the privileged connection.

Run with the DB pool already initialized (see `main` for the CLI entrypoint):

    python -m backend.jobs.fit_fsrs_weights --db-url postgresql://...

A language/user is only fit once it clears the minimum-review threshold; below
that, the scheduler keeps using the next tier up (language, then defaults), so
small languages and new users are never fit on noise.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os

import asyncpg

from backend.repositories.fsrs_weights import (
    fetch_review_sequences,
    upsert_language_weights,
    upsert_user_weights,
)
from backend.services.fsrs_optimizer import fit_weights

logger = logging.getLogger("fsrs.fit")

# Minimum scorable reviews before a fit is trusted over the tier above it.
LANGUAGE_MIN_REVIEWS = 1000
USER_MIN_REVIEWS = 1000


async def fit_languages(
    conn: asyncpg.Connection, *, min_reviews: int = LANGUAGE_MIN_REVIEWS
) -> int:
    """Fit and store per-language weights. Returns how many languages were fit."""
    language_ids = [
        str(r["id"]) for r in await conn.fetch("SELECT id FROM languages ORDER BY code")
    ]
    fitted = 0
    for language_id in language_ids:
        sequences = await fetch_review_sequences(conn, language_id)
        result = fit_weights(sequences)
        if result is None or result.n_reviews < min_reviews:
            continue
        await upsert_language_weights(
            conn, language_id, result.params, result.n_reviews, result.log_loss
        )
        fitted += 1
        logger.info(
            "language %s fit on %d reviews (log_loss=%.4f)",
            language_id, result.n_reviews, result.log_loss,
        )
    return fitted


async def fit_users(
    conn: asyncpg.Connection, *, min_reviews: int = USER_MIN_REVIEWS
) -> int:
    """Fit and store per-user-per-language weights for heavy reviewers."""
    # Only consider (user, language) pairs that could clear the threshold.
    pairs = await conn.fetch(
        """
        SELECT rl.user_id, uc.language_id
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        GROUP BY rl.user_id, uc.language_id
        HAVING count(*) >= $1
        """,
        min_reviews,
    )
    fitted = 0
    for pair in pairs:
        user_id, language_id = str(pair["user_id"]), str(pair["language_id"])
        sequences = await fetch_review_sequences(conn, language_id, user_id)
        result = fit_weights(sequences)
        if result is None or result.n_reviews < min_reviews:
            continue
        await upsert_user_weights(
            conn, user_id, language_id, result.params, result.n_reviews, result.log_loss
        )
        fitted += 1
        logger.info(
            "user %s / language %s fit on %d reviews (log_loss=%.4f)",
            user_id, language_id, result.n_reviews, result.log_loss,
        )
    return fitted


async def run(
    conn: asyncpg.Connection,
    *,
    language_min_reviews: int = LANGUAGE_MIN_REVIEWS,
    user_min_reviews: int = USER_MIN_REVIEWS,
) -> dict[str, int]:
    """Fit both tiers. Returns counts of languages and users fit."""
    languages = await fit_languages(conn, min_reviews=language_min_reviews)
    users = await fit_users(conn, min_reviews=user_min_reviews)
    return {"languages": languages, "users": users}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fit FSRS weights from review history")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set. Pass --db-url or set DATABASE_URL.")
        return

    from backend.repositories import pool as pool_mod

    await pool_mod.init_pool(args.db_url)
    try:
        async with pool_mod.privileged_connection() as conn:
            counts = await run(conn)
        logger.info("done: fit %(languages)d languages, %(users)d users", counts)
    finally:
        await pool_mod.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
