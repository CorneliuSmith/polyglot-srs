"""The wait screen's matching game only plays real glosses.

A Russian speaker learning English was shown "it" against «И что?», "be"
against «У тебя это есть?» and "dogs" against a SPANISH sentence, while a
text was being written. The query was doing what it was told — those are the
definitions those rows hold — but a word paired with a sentence is unplayable
whatever the sentence says, and a matching game is the wrong place to
discover that the content needs work.

So the pairs are filtered where they are chosen. What is pinned here is the
shape of the filter, not the wording of any one bad row: short, gloss-like
text plays; sentences and empties do not.
"""
from __future__ import annotations

from backend.repositories.cards import session_readiness

from .conftest import requires_db

pytestmark = requires_db


async def _course(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper()))


async def _learner(pool, email: str, course: str, locale: str) -> str:
    async with pool.privileged_connection() as conn:
        uid = str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email))
        await conn.execute(
            "INSERT INTO user_profiles (id, support_locale) VALUES ($1, $2) "
            "ON CONFLICT (id) DO UPDATE SET support_locale = EXCLUDED.support_locale",
            uid, locale)
        deck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') RETURNING id",
            course)
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", uid, deck)
        return uid


async def _word(pool, course: str, word: str, gloss: str, rank: int) -> None:
    async with pool.privileged_connection() as conn:
        vid = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
            "VALUES ($1, $2, 'A1', $3) RETURNING id", course, word, rank)
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', $2)", vid, f"en meaning of {word}")
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'ru', $2)", vid, gloss)


async def test_a_sentence_is_never_offered_as_a_gloss(pool):
    course = await _course(pool, "wgen")
    uid = await _learner(pool, "match@wait", course, "ru")
    # Two real glosses and three of the rows from the owner's screenshot.
    await _word(pool, course, "dog", "собака", 1)
    await _word(pool, course, "house", "дом", 2)
    await _word(pool, course, "it", "И что?", 3)
    await _word(pool, course, "be", "У тебя это есть?", 4)
    await _word(pool, course, "dogs",
                "La mayoría de los perros son marrones y buenos.", 5)

    async with pool.rls_connection(uid) as conn:
        state = await session_readiness(conn, uid, course)

    glosses = {p["gloss"] for p in state["pairs"]}
    assert glosses == {"собака", "дом"}
    # And the words they belong to travel with them.
    assert {p["word"] for p in state["pairs"]} == {"dog", "house"}


async def test_a_short_phrase_still_plays(pool):
    # The filter must not be so eager that it empties the game: multi-word
    # glosses are normal ("to be able to"), and only sentence-shaped ones go.
    course = await _course(pool, "wgph")
    uid = await _learner(pool, "phrase@wait", course, "ru")
    await _word(pool, course, "can", "мочь, быть в состоянии", 1)
    await _word(pool, course, "run", "бежать", 2)

    async with pool.rls_connection(uid) as conn:
        state = await session_readiness(conn, uid, course)

    assert {p["gloss"] for p in state["pairs"]} == {
        "мочь, быть в состоянии", "бежать",
    }
