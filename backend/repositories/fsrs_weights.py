"""FSRS weight storage + resolution.

The scheduler resolves the most specific weights available for a (user,
language): a per-user-per-language fit if one exists, else the per-language fit
(pooled across all users of that language), else the built-in FSRS defaults.

Reads run on the normal RLS connection (per-language rows are world-readable;
per-user rows are owner-only). The optimizer job writes on the privileged
connection, so the authenticated role never needs write access.
"""
from __future__ import annotations

import asyncpg

from backend.services.fsrs import DEFAULT_PARAMS
from backend.services.fsrs_optimizer import ReviewSequence

# Map review_log.answer_result to an FSRS grade (1=Again .. 4=Easy).
_ANSWER_TO_GRADE: dict[str, int] = {
    "correct": 3,
    "correct_sloppy": 2,
    "wrong_form": 1,
    "wrong": 1,
}


def _grade_from_row(row: asyncpg.Record) -> int | None:
    answer = row["answer_result"]
    if answer in _ANSWER_TO_GRADE:
        return _ANSWER_TO_GRADE[answer]
    # Fall back to the numeric quality (4=Good .. 1=Again) when text is missing.
    q = row["quality"]
    if q is None:
        return None
    return 3 if q >= 3 else (2 if q == 2 else 1)


async def get_effective_params(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> tuple[float, ...]:
    """Resolve the FSRS weights for this user+language (user → language → default)."""
    rows = await conn.fetch(
        """
        SELECT scope, params FROM fsrs_weights
        WHERE language_id = $1
          AND (scope = 'language' OR (scope = 'user_language' AND user_id = $2))
        """,
        language_id,
        user_id,
    )
    by_scope = {r["scope"]: r["params"] for r in rows}
    if "user_language" in by_scope:
        return tuple(by_scope["user_language"])
    if "language" in by_scope:
        return tuple(by_scope["language"])
    return DEFAULT_PARAMS


async def fetch_review_sequences(
    conn: asyncpg.Connection, language_id: str, user_id: str | None = None
) -> list[ReviewSequence]:
    """Build per-card review sequences for fitting (ordered by card, then time)."""
    rows = await conn.fetch(
        """
        SELECT rl.card_id, rl.created_at, rl.answer_result, rl.quality
        FROM review_log rl
        JOIN user_cards uc ON rl.card_id = uc.id
        WHERE uc.language_id = $1
          AND ($2::uuid IS NULL OR rl.user_id = $2)
        ORDER BY rl.card_id, rl.created_at
        """,
        language_id,
        user_id,
    )
    sequences: list[ReviewSequence] = []
    current_card = None
    seq: ReviewSequence = []
    prev_time = None
    for r in rows:
        if r["card_id"] != current_card:
            if seq:
                sequences.append(seq)
            current_card, seq, prev_time = r["card_id"], [], None
        grade = _grade_from_row(r)
        if grade is None:
            continue
        elapsed = 0.0 if prev_time is None else (
            (r["created_at"] - prev_time).total_seconds() / 86400.0
        )
        seq.append((elapsed, grade))
        prev_time = r["created_at"]
    if seq:
        sequences.append(seq)
    return sequences


async def upsert_language_weights(
    conn: asyncpg.Connection,
    language_id: str,
    params: list[float],
    review_count: int,
    log_loss: float,
) -> None:
    """Store (or refresh) the per-language weights."""
    await conn.execute(
        """
        INSERT INTO fsrs_weights (scope, language_id, user_id, params, review_count, log_loss, fit_at)
        VALUES ('language', $1, NULL, $2, $3, $4, now())
        ON CONFLICT (language_id) WHERE scope = 'language'
        DO UPDATE SET params = EXCLUDED.params,
                      review_count = EXCLUDED.review_count,
                      log_loss = EXCLUDED.log_loss,
                      fit_at = now()
        """,
        language_id,
        params,
        review_count,
        log_loss,
    )


async def upsert_user_weights(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    params: list[float],
    review_count: int,
    log_loss: float,
) -> None:
    """Store (or refresh) one user's per-language weights."""
    await conn.execute(
        """
        INSERT INTO fsrs_weights (scope, language_id, user_id, params, review_count, log_loss, fit_at)
        VALUES ('user_language', $1, $2, $3, $4, $5, now())
        ON CONFLICT (user_id, language_id) WHERE scope = 'user_language'
        DO UPDATE SET params = EXCLUDED.params,
                      review_count = EXCLUDED.review_count,
                      log_loss = EXCLUDED.log_loss,
                      fit_at = now()
        """,
        language_id,
        user_id,
        params,
        review_count,
        log_loss,
    )
