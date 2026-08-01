"""Cards saved from the Reader and the Tutor land in a deck the learner can find.

The bug: create_personal_card never set personal_deck_id, so every word saved
from a reading was correctly stored and correctly scheduled — and invisible.
The Decks page groups by deck, so an unfiled card appeared nowhere, which is
indistinguishable from the save having failed. "Added to your reviews" was
literally true and completely unhelpful.

Real Postgres, because the whole point is the deck row and the foreign key.
"""
from __future__ import annotations

from backend.repositories.notes import create_personal_card
from backend.repositories.personal_decks import (
    get_or_create_deck,
    list_decks,
    list_personal_cards,
)

from .conftest import requires_db

pytestmark = requires_db


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


async def _save(pool, user: str, lang: str, answer: str, deck_name: str) -> str:
    """What the /notes/cards endpoint does: resolve the deck, then insert
    the card already filed into it."""
    async with pool.rls_connection(user) as conn:
        deck_id = await get_or_create_deck(conn, user, lang, deck_name)
        return await create_personal_card(
            conn, user, lang, "Ich sehe ein {{answer}}.", answer, "a word",
            None, deck_id,
        )


async def test_a_saved_word_is_filed_not_orphaned(pool):
    lang = await _lang(pool, "fil")
    user = await _user(pool, "reader@fil")

    await _save(pool, user, lang, "Buch", "From reading")

    async with pool.rls_connection(user) as conn:
        decks = await list_decks(conn, lang)
        cards = await list_personal_cards(conn, lang)

    assert [d["name"] for d in decks] == ["From reading"]
    assert decks[0]["card_count"] == 1
    # The regression this file exists for: deck_id was None for every card.
    assert cards[0]["deck_id"] == decks[0]["id"]


async def test_repeated_saves_reuse_one_deck(pool):
    """Otherwise a 30-word reading session mints 30 identical decks."""
    lang = await _lang(pool, "fil2")
    user = await _user(pool, "reader@fil2")

    for word in ("Buch", "Haus", "Baum"):
        await _save(pool, user, lang, word, "From reading")

    async with pool.rls_connection(user) as conn:
        decks = await list_decks(conn, lang)

    assert len(decks) == 1
    assert decks[0]["card_count"] == 3


async def test_different_sources_get_different_decks(pool):
    lang = await _lang(pool, "fil3")
    user = await _user(pool, "reader@fil3")

    await _save(pool, user, lang, "Buch", "From reading")
    await _save(pool, user, lang, "Haus", "From the tutor")

    async with pool.rls_connection(user) as conn:
        decks = {d["name"]: d["card_count"] for d in await list_decks(conn, lang)}

    assert decks == {"From reading": 1, "From the tutor": 1}


async def test_deck_lookup_is_case_insensitive(pool):
    """A learner who renamed the deck's casing shouldn't get a second one."""
    lang = await _lang(pool, "fil4")
    user = await _user(pool, "reader@fil4")

    async with pool.rls_connection(user) as conn:
        first = await get_or_create_deck(conn, user, lang, "From reading")
        second = await get_or_create_deck(conn, user, lang, "FROM READING")

    assert first == second


async def test_one_learners_deck_never_collects_anothers_cards(pool):
    """get_or_create matches on name — under RLS that must still be scoped
    to the owner, or two learners share a deck row."""
    lang = await _lang(pool, "fil5")
    alice = await _user(pool, "alice@fil5")
    bob = await _user(pool, "bob@fil5")

    await _save(pool, alice, lang, "Buch", "From reading")
    await _save(pool, bob, lang, "Haus", "From reading")

    async with pool.rls_connection(alice) as conn:
        alice_decks = await list_decks(conn, lang)
    async with pool.rls_connection(bob) as conn:
        bob_decks = await list_decks(conn, lang)

    assert len(alice_decks) == 1 and len(bob_decks) == 1
    assert alice_decks[0]["id"] != bob_decks[0]["id"]
    assert alice_decks[0]["card_count"] == 1
    assert bob_decks[0]["card_count"] == 1
