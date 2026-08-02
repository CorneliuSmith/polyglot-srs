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


async def _browse_setup(pool, code: str):
    """A language with one explicit and one clean word, plus its A1 deck."""
    lang = await _lang(pool, code)
    async with pool.privileged_connection() as conn:
        for word, rank, explicit, gloss in [
            ("puta", 1, True, "whore, slut, prostitute"),
            ("casa", 2, False, "house"),
        ]:
            vid = await conn.fetchval(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank, is_explicit) VALUES ($1,$2,'A1',$3,$4) "
                "RETURNING id",
                lang, word, rank, explicit,
            )
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1,'en',$2)", vid, gloss,
            )
        deck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1,'vocabulary','A1','A1 Vocabulary') "
            "ON CONFLICT (language_id, list_type, level) DO UPDATE "
            "SET title = EXCLUDED.title RETURNING id",
            lang,
        )
    return lang, str(deck)


class TestTheGateCoversBrowsingNotJustLearning:
    """The audit that prompted these: Learn was filtered while the deck
    browser and search were not, so a filtered learner could not be TAUGHT
    the word but could open the A1 deck — or type it into search — and read
    the gloss straight off the listing. A gate that only covers the front
    door is a claim, not a gate."""

    async def test_deck_preview_respects_the_preference(self, pool):
        from backend.repositories.cards import get_deck_preview

        lang, deck = await _browse_setup(pool, "exb1")
        strict = await _learner(pool, "s@exb1", lang, allow_explicit=False)
        open_ = await _learner(pool, "o@exb1", lang, allow_explicit=True)

        async with pool.rls_connection(strict) as conn:
            preview = await get_deck_preview(conn, deck)
        assert [i["item"] for i in preview["items"]] == ["casa"]

        async with pool.rls_connection(open_) as conn:
            preview = await get_deck_preview(conn, deck)
        assert [i["item"] for i in preview["items"]] == ["puta", "casa"]

    async def test_deck_items_respect_the_preference(self, pool):
        from backend.repositories.cards import get_deck_items

        lang, deck = await _browse_setup(pool, "exb2")
        strict = await _learner(pool, "s@exb2", lang, allow_explicit=False)

        async with pool.rls_connection(strict) as conn:
            listing = await get_deck_items(conn, deck)
        assert [i["item"] for i in listing["items"]] == ["casa"]

    async def test_search_cannot_be_used_as_a_bypass(self, pool):
        # Searching for the word BY NAME is the strongest version of the
        # hole: the learner is asking for it directly, and the answer for a
        # filtered account is still no.
        from backend.repositories.curriculum import search_content

        lang, _ = await _browse_setup(pool, "exb3")
        strict = await _learner(pool, "s@exb3", lang, allow_explicit=False)
        open_ = await _learner(pool, "o@exb3", lang, allow_explicit=True)

        async with pool.rls_connection(strict) as conn:
            hits = await search_content(conn, strict, lang, "puta")
        assert hits["vocabulary"] == []

        async with pool.rls_connection(open_) as conn:
            hits = await search_content(conn, open_, lang, "puta")
        assert [h["word"] for h in hits["vocabulary"]] == ["puta"]

    async def test_flipping_the_toggle_takes_effect_immediately(self, pool):
        """End to end through the same column the Settings toggle writes:
        no cache, no session state — the next query simply reads the new
        preference. This is the behaviour the Settings copy promises."""
        from backend.repositories.cards import get_deck_items

        lang, deck = await _browse_setup(pool, "exb4")
        learner = await _learner(pool, "flip@exb4", lang, allow_explicit=False)

        async with pool.rls_connection(learner) as conn:
            before = await get_deck_items(conn, deck)
        assert [i["item"] for i in before["items"]] == ["casa"]

        async with pool.privileged_connection() as conn:
            await conn.execute(
                "UPDATE user_profiles SET allow_explicit_content = true "
                "WHERE id = $1", learner,
            )
        async with pool.rls_connection(learner) as conn:
            after = await get_deck_items(conn, deck)
        assert [i["item"] for i in after["items"]] == ["puta", "casa"]
