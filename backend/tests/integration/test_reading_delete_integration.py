"""Deleting a story keeps the words it taught.

The owner asked for shelf housekeeping — "delete old stories if they would
like, but keep cards" — and the reassuring answer is structural rather than
careful: a word saved out of a reading becomes a user_cloze_cards row with
no reference back to the text, so no cascade can reach it.

"Structural" is exactly the kind of claim that quietly stops being true
when someone later adds a convenient foreign key, so it gets a real
Postgres test rather than a promise in a comment. Also pins the ownership
boundary: one learner cannot delete another's reading even though both rows
live in the same table.
"""
from __future__ import annotations

from backend.repositories.notes import create_personal_card
from backend.repositories.personal_decks import (
    get_or_create_deck,
    list_personal_cards,
)
from backend.repositories.reader import (
    delete_reading,
    get_reading,
    list_readings,
    save_reading,
)

from .conftest import requires_db

pytestmark = requires_db

_READING = {
    "sentences": [
        {
            "text": "Der Kater schläft am Fenster.",
            "translation": "The tomcat sleeps by the window.",
            "tokens": [{"t": "Kater", "gloss": "tomcat", "new": True}],
        }
    ],
    "new_words": [{"word": "Kater", "gloss": "tomcat", "sentence_index": 0}],
    "structures": ["Present tense"],
    "title": "Der Kater",
}


async def _lang(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _store(pool, user: str, lang: str, topic: str) -> str:
    async with pool.rls_connection(user) as conn:
        return await save_reading(
            conn, user, lang, topic, dict(_READING), "B1"
        )


async def test_deleting_a_story_keeps_the_words_it_taught(pool):
    lang = await _lang(pool, "delru")
    user = await _user(pool, "tidy@reader")
    reading_id = await _store(pool, user, lang, "cats")

    # The learner saves a word while reading, the way the Reader's
    # "add to reviews" button does.
    async with pool.rls_connection(user) as conn:
        deck_id = await get_or_create_deck(conn, user, lang, "From reading")
        await create_personal_card(
            conn, user, lang, "Der {{answer}} schläft.", "Kater",
            "tomcat", None, deck_id,
        )

    async with pool.rls_connection(user) as conn:
        assert await delete_reading(conn, user, reading_id) is True
        # The shelf is tidy…
        assert await list_readings(conn, user, lang) == []
        # …and the word is still theirs to review.
        cards = await list_personal_cards(conn, lang)

    # create_personal_card returns the SCHEDULING row's id while the listing
    # returns the cloze id, so identity is checked by the word itself.
    assert len(cards) == 1
    assert cards[0]["answer"] == "Kater"


async def test_a_second_delete_reports_nothing_to_delete(pool):
    lang = await _lang(pool, "delro")
    user = await _user(pool, "twice@reader")
    reading_id = await _store(pool, user, lang, "trains")

    async with pool.rls_connection(user) as conn:
        assert await delete_reading(conn, user, reading_id) is True
        # The router turns this False into a 404 — "already gone" and
        # "never yours" are deliberately the same answer.
        assert await delete_reading(conn, user, reading_id) is False


async def test_one_learner_cannot_delete_anothers_story(pool):
    lang = await _lang(pool, "delsw")
    owner = await _user(pool, "owner@reader")
    stranger = await _user(pool, "stranger@reader")
    reading_id = await _store(pool, owner, lang, "the harbour")

    async with pool.rls_connection(stranger) as conn:
        assert await delete_reading(conn, stranger, reading_id) is False

    # Still on the owner's shelf, untouched.
    async with pool.rls_connection(owner) as conn:
        shelf = await list_readings(conn, owner, lang)
    assert [r["id"] for r in shelf] == [reading_id]


async def test_deleting_one_story_leaves_the_rest_of_the_shelf(pool):
    lang = await _lang(pool, "delhe")
    user = await _user(pool, "shelf@reader")
    keep = await _store(pool, user, lang, "keep me")
    drop = await _store(pool, user, lang, "drop me")

    async with pool.rls_connection(user) as conn:
        assert await delete_reading(conn, user, drop) is True
        shelf = await list_readings(conn, user, lang)

    assert [r["id"] for r in shelf] == [keep]
    # And the survivor is readable in full, not merely listed: a delete that
    # scribbled on its neighbour's payload would still pass the line above.
    async with pool.rls_connection(user) as conn:
        survivor = await get_reading(conn, user, keep)
    assert survivor is not None
    assert survivor["sentences"][0]["text"] == "Der Kater schläft am Fenster."
    assert survivor["structures"] == ["Present tense"]
