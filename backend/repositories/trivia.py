"""The language-trivia bank: shared questions, per-learner rotation.

Not keyed to a course. A question about why some scripts run right-to-left
is as good for a Turkish learner as a Greek one, so the bank is per LOCALE
and every learner who reads that locale draws from the same pool. That is
what lets it grow into something large instead of being regenerated per
session.

Every read is probed rather than wrapped in try/except: the pooled
connection runs one transaction, so a query naming a missing table aborts
it and takes the rest of the request down (see services/auto_translate
.table_present). This feeds a waiting-room game — it must never be what
breaks the page it decorates.
"""
from __future__ import annotations

import asyncpg

from backend.services.auto_translate import table_present

# Keep enough unseen questions ahead of each learner that a wait never runs
# dry, without generating a corpus nobody reads.
LOW_WATER = 30
TOP_UP_BATCH = 15


async def unseen_trivia(
    conn: asyncpg.Connection, user_id: str, locale: str, limit: int = 10,
) -> list[dict]:
    """Questions in *locale* this learner hasn't been asked yet."""
    if not locale or not await table_present(conn, "language_trivia"):
        return []
    rows = await conn.fetch(
        """
        SELECT t.id, t.question, t.options, t.answer_index, t.fact
        FROM language_trivia t
        WHERE t.locale = $1
          AND NOT EXISTS (
            SELECT 1 FROM user_trivia_seen s
             WHERE s.trivia_id = t.id AND s.user_id = $2)
        ORDER BY random()
        LIMIT $3
        """,
        locale, user_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "question": r["question"],
            "options": list(r["options"]),
            "answer_index": r["answer_index"],
            "fact": r["fact"],
        }
        for r in rows
    ]


async def count_unseen(
    conn: asyncpg.Connection, user_id: str, locale: str
) -> int:
    """How many questions this learner has left — the top-up trigger."""
    if not locale or not await table_present(conn, "language_trivia"):
        return 0
    return int(await conn.fetchval(
        """
        SELECT count(*) FROM language_trivia t
        WHERE t.locale = $1
          AND NOT EXISTS (
            SELECT 1 FROM user_trivia_seen s
             WHERE s.trivia_id = t.id AND s.user_id = $2)
        """,
        locale, user_id,
    ) or 0)


async def existing_questions(
    conn: asyncpg.Connection, locale: str, limit: int = 80
) -> list[str]:
    """Question text already in the bank, to hand the generator so it writes
    something new rather than circling the same few ideas."""
    if not await table_present(conn, "language_trivia"):
        return []
    rows = await conn.fetch(
        "SELECT question FROM language_trivia WHERE locale = $1 "
        "ORDER BY created_at DESC LIMIT $2",
        locale, limit,
    )
    return [r["question"] for r in rows]


async def store_trivia(
    conn: asyncpg.Connection, locale: str, items: list[dict],
    source: str = "ai",
) -> int:
    """Add questions to the bank. The (locale, question) unique constraint
    absorbs a generator that repeats itself, so a duplicate costs nothing
    and never raises.

    *source* separates the written baseline ("seed") from what the model
    wrote ("ai") — worth being able to tell apart when reviewing the bank,
    since one has been read by a person and the other has not.
    """
    if not items or not await table_present(conn, "language_trivia"):
        return 0
    stored = 0
    for it in items:
        added = await conn.fetchval(
            """
            INSERT INTO language_trivia
                (locale, question, options, answer_index, fact, source)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (locale, question) DO NOTHING
            RETURNING id
            """,
            locale, it["question"], it["options"], it["answer_index"],
            it["fact"], source,
        )
        if added:
            stored += 1
    return stored


async def mark_seen(
    conn: asyncpg.Connection, user_id: str, trivia_ids: list[str]
) -> None:
    """Record what was asked, so the bank rotates. Best-effort: failing to
    record is a repeated question later, not an error now.

    The SELECT filters to ids the bank actually holds. Questions served
    from the in-memory baseline (trivia_corpus.offline_questions, used when
    the table can't be read) carry ids that were never stored, and the
    foreign key would reject the whole statement — losing the real ids
    alongside them.
    """
    if not trivia_ids or not await table_present(conn, "user_trivia_seen"):
        return
    await conn.execute(
        """INSERT INTO user_trivia_seen (user_id, trivia_id)
           SELECT $1, t.id FROM language_trivia t
            WHERE t.id = ANY($2::uuid[])
           ON CONFLICT DO NOTHING""",
        user_id, trivia_ids,
    )
