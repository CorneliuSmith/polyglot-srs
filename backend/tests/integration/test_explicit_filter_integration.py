"""Explicit words stay out of a learner's deck unless they asked for them.

The unit tests pin the lexicon; these pin the thing the learner actually
experiences — that the word never reaches their cards. Real Postgres, because
the filter is a SQL predicate reading user_profiles from inside the candidate
query, and the interesting failure (it silently matches nobody, or everybody)
is invisible to a mock.
"""
from __future__ import annotations

from backend.repositories.cards import add_learn_batch

from .conftest import requires_db

pytestmark = requires_db


async def _lang(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _learner(pool, email: str, lang: str, *, allow_explicit: bool) -> str:
    async with pool.privileged_connection() as conn:
        uid = str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id, "
            "allow_explicit_content) VALUES ($1, $2, $3)",
            uid, lang, allow_explicit,
        )
        # Subscribe to the A1 vocabulary deck, or nothing is learnable.
        list_id = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') "
            "ON CONFLICT (language_id, list_type, level) DO UPDATE "
            "SET title = EXCLUDED.title RETURNING id",
            lang,
        )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2) ON CONFLICT DO NOTHING",
            uid, list_id,
        )
    return uid


async def _word(pool, lang: str, word: str, rank: int, *, explicit: bool) -> str:
    async with pool.privileged_connection() as conn:
        vid = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank, "
            "is_explicit) VALUES ($1, $2, 'A1', $3, $4) RETURNING id",
            lang, word, rank, explicit,
        ))
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', $2)",
            vid, f"gloss for {word}",
        )
    return vid


async def _learned_words(pool, user: str, lang: str) -> set[str]:
    async with pool.rls_connection(user) as conn:
        await add_learn_batch(conn, user, lang, batch_size=10)
        rows = await conn.fetch(
            "SELECT v.word FROM user_cards uc JOIN vocabulary v ON v.id = uc.card_id "
            "WHERE uc.user_id = $1 AND uc.card_type = 'vocabulary'",
            user,
        )
    return {r["word"] for r in rows}


async def test_an_explicit_word_never_reaches_a_default_learner(pool):
    lang = await _lang(pool, "ex1")
    # *puta* is rank 505 in the real Spanish list — a beginner meets it in
    # their first weeks purely on frequency. Ranked FIRST here so that if the
    # filter does nothing, it is certain to be picked.
    await _word(pool, lang, "puta", 1, explicit=True)
    await _word(pool, lang, "casa", 2, explicit=False)
    user = await _learner(pool, "clean@ex1", lang, allow_explicit=False)

    assert await _learned_words(pool, user, lang) == {"casa"}


async def test_a_learner_who_opted_in_gets_them(pool):
    """The point of a setting rather than a delete: these words are frequent
    for a reason and an adult who asks for them should be taught them."""
    lang = await _lang(pool, "ex2")
    await _word(pool, lang, "puta", 1, explicit=True)
    await _word(pool, lang, "casa", 2, explicit=False)
    user = await _learner(pool, "optin@ex2", lang, allow_explicit=True)

    assert await _learned_words(pool, user, lang) == {"puta", "casa"}


async def test_one_learner_s_choice_does_not_leak_to_another(pool):
    """The predicate reads user_profiles from inside the query. Scoped to the
    wrong row it would hide nothing for everyone (any opted-in account in the
    table satisfying the EXISTS) — which is the same as no filter at all, and
    would pass a single-user test."""
    lang = await _lang(pool, "ex3")
    await _word(pool, lang, "puta", 1, explicit=True)
    await _word(pool, lang, "casa", 2, explicit=False)
    permissive = await _learner(pool, "yes@ex3", lang, allow_explicit=True)
    strict = await _learner(pool, "no@ex3", lang, allow_explicit=False)

    assert await _learned_words(pool, permissive, lang) == {"puta", "casa"}
    assert await _learned_words(pool, strict, lang) == {"casa"}


async def test_nothing_explicit_means_nothing_hidden(pool):
    """The overwhelmingly common case: the filter must not cost a learner
    ordinary vocabulary."""
    lang = await _lang(pool, "ex4")
    for i, word in enumerate(["casa", "perro", "libro"], start=1):
        await _word(pool, lang, word, i, explicit=False)
    user = await _learner(pool, "plain@ex4", lang, allow_explicit=False)

    assert await _learned_words(pool, user, lang) == {"casa", "perro", "libro"}
