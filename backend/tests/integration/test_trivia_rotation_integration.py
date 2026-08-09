"""The trivia bank's rotation, against a real Postgres.

The contract is "try to not show users the same stuff over and over":
unseen questions first, and when a learner has read the whole bank, the
repeats come back longest-ago-first and keep cycling — which only works if
re-serving a question refreshes its seen_at. That refresh is an ON CONFLICT
DO UPDATE, precisely the kind of SQL behaviour a mock can't vouch for.
"""
from __future__ import annotations

import pytest

from backend.repositories.trivia import (
    least_recently_seen,
    mark_seen,
    store_trivia,
    unseen_trivia,
)

from .conftest import requires_db

pytestmark = [pytest.mark.asyncio, requires_db]


async def _learner(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email))


def _q(n: int) -> dict:
    return {"question": f"rotation question {n}?",
            "options": ["a", "b", "c"], "answer_index": 0, "fact": f"fact {n}"}


async def test_seen_questions_stop_being_served_until_the_bank_runs_dry(pool):
    uid = await _learner(pool, "rot1@trivia.test")
    async with pool.privileged_connection() as conn:
        await store_trivia(conn, "es", [_q(i) for i in range(4)], source="seed")
        first = await unseen_trivia(conn, uid, "es", 2)
        await mark_seen(conn, uid, [q["id"] for q in first])
        second = await unseen_trivia(conn, uid, "es", 10)
    seen_ids = {q["id"] for q in first}
    assert seen_ids.isdisjoint({q["id"] for q in second}), (
        "a question came back while unseen ones were still available")


async def test_an_exhausted_bank_recycles_longest_ago_first(pool):
    uid = await _learner(pool, "rot2@trivia.test")
    async with pool.privileged_connection() as conn:
        await store_trivia(conn, "fr", [_q(i) for i in range(3)], source="seed")
        everything = await unseen_trivia(conn, uid, "fr", 10)
        ids = [q["id"] for q in everything]
        # Seen at three distinct moments, oldest first.
        for i, qid in enumerate(ids):
            await mark_seen(conn, uid, [qid])
            await conn.execute(
                "UPDATE user_trivia_seen SET seen_at = now() - ($2 || ' hours')::interval "
                "WHERE user_id = $1 AND trivia_id = $3",
                uid, str(10 - i), qid)
        assert await unseen_trivia(conn, uid, "fr", 10) == []
        recycled = await least_recently_seen(conn, uid, "fr", 2)
    assert [q["id"] for q in recycled] == ids[:2], (
        "the recycle order is not longest-ago-first")


async def test_reserving_refreshes_seen_at_so_the_cycle_moves_on(pool):
    """Without the DO UPDATE, the least-recent question stays least recent
    forever and every exhausted wait screen opens with the same question."""
    uid = await _learner(pool, "rot3@trivia.test")
    async with pool.privileged_connection() as conn:
        await store_trivia(conn, "pt", [_q(i) for i in range(3)], source="seed")
        everything = await unseen_trivia(conn, uid, "pt", 10)
        ids = [q["id"] for q in everything]
        for i, qid in enumerate(ids):
            await mark_seen(conn, uid, [qid])
            await conn.execute(
                "UPDATE user_trivia_seen SET seen_at = now() - ($2 || ' hours')::interval "
                "WHERE user_id = $1 AND trivia_id = $3",
                uid, str(10 - i), qid)
        first_pick = (await least_recently_seen(conn, uid, "pt", 1))[0]["id"]
        # The wait screen serves it again; the client posts it back as seen.
        await mark_seen(conn, uid, [first_pick])
        second_pick = (await least_recently_seen(conn, uid, "pt", 1))[0]["id"]
    assert first_pick != second_pick, (
        "re-serving did not refresh seen_at — the rotation is pinned to one question")
