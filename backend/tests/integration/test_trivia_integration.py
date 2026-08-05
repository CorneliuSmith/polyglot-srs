"""The language-trivia bank: shared per locale, rotating per learner.

The wait screen's match game plays the words of the session being waited
for, which needs some of that session to exist. At 0% none of it does —
and 0% is exactly when someone is sitting there. Trivia has no such
dependency: the bank is shared per locale and stocked before any given
learner arrives.
"""
from __future__ import annotations

from backend.repositories.trivia import (
    count_unseen,
    existing_questions,
    mark_seen,
    store_trivia,
    unseen_trivia,
)

from .conftest import requires_db

pytestmark = requires_db


def _q(n: int) -> dict:
    return {
        "question": f"Question {n}?",
        "options": [f"A{n}", f"B{n}", f"C{n}"],
        "answer_index": n % 3,
        "fact": f"Fact {n}.",
    }


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email))


async def test_the_bank_is_shared_and_rotates_per_learner(pool):
    ann = await _user(pool, "trivia-ann@t")
    bob = await _user(pool, "trivia-bob@t")

    async with pool.privileged_connection() as conn:
        assert await store_trivia(conn, "tqa", [_q(i) for i in range(5)]) == 5

        # Shared: a question stocked for the locale serves every learner of
        # it, so the corpus is worth growing rather than per-session work.
        assert len(await unseen_trivia(conn, ann, "tqa", 10)) == 5
        assert len(await unseen_trivia(conn, bob, "tqa", 10)) == 5

        first = await unseen_trivia(conn, ann, "tqa", 2)
        await mark_seen(conn, ann, [x["id"] for x in first])

        # Ann has moved on; Bob's pool is untouched.
        assert await count_unseen(conn, ann, "tqa") == 3
        assert await count_unseen(conn, bob, "tqa") == 5
        seen_ids = {x["id"] for x in first}
        assert not seen_ids & {x["id"] for x in
                               await unseen_trivia(conn, ann, "tqa", 10)}

        # Questions come back whole — a half-formed one is unanswerable.
        for item in await unseen_trivia(conn, ann, "tqa", 10):
            assert item["question"] and item["fact"]
            assert 0 <= item["answer_index"] < len(item["options"])


async def test_storing_the_same_question_twice_is_free(pool):
    """The generator repeating itself must cost nothing, not raise — the
    bank grows by accumulating, so collisions are expected and routine."""
    async with pool.privileged_connection() as conn:
        assert await store_trivia(conn, "tqb", [_q(1), _q(2)]) == 2
        assert await store_trivia(conn, "tqb", [_q(1), _q(2), _q(3)]) == 1
        assert await conn.fetchval(
            "SELECT count(*) FROM language_trivia WHERE locale = 'tqb'") == 3


async def test_the_bank_tells_the_generator_what_it_already_has(pool):
    """Otherwise it circles the same handful of ideas and the corpus never
    actually widens."""
    async with pool.privileged_connection() as conn:
        await store_trivia(conn, "tqc", [_q(i) for i in range(3)])
        asked = await existing_questions(conn, "tqc")
        assert set(asked) == {f"Question {i}?" for i in range(3)}


async def test_a_locale_with_no_bank_yet_returns_nothing_rather_than_failing(pool):
    ann = await _user(pool, "trivia-empty@t")
    async with pool.privileged_connection() as conn:
        assert await unseen_trivia(conn, ann, "zzz", 10) == []
        assert await count_unseen(conn, ann, "zzz") == 0
        # No locale at all (a learner on English support) is not an error.
        assert await unseen_trivia(conn, ann, "", 10) == []


async def test_it_survives_the_migration_not_having_landed(pool):
    """This feeds a waiting-room game. It must never be what breaks the
    page it decorates — and a thrown UndefinedTableError would abort the
    whole pooled transaction, not just this query."""
    ann = await _user(pool, "trivia-nomig@t")
    async with pool.privileged_connection() as conn:
        await conn.execute("ALTER TABLE language_trivia RENAME TO lt_hidden")
        try:
            assert await unseen_trivia(conn, ann, "tqa", 5) == []
            assert await count_unseen(conn, ann, "tqa") == 0
            assert await existing_questions(conn, "tqa") == []
            assert await store_trivia(conn, "tqa", [_q(9)]) == 0
            # The transaction is still usable — the real tell.
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await conn.execute("ALTER TABLE lt_hidden RENAME TO language_trivia")
