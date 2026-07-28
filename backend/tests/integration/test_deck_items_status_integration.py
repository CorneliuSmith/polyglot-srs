"""Deck browser per-card learner status + individual-card reset.

Owner: cards need to be resettable individually, not just by wiping a whole
deck — which first means the deck browser has to show which cards HAVE
progress. Runs against real Postgres so the user_cards LEFT JOIN and the
RLS-scoped reset are both exercised for real, not mocked.
"""
from __future__ import annotations

from backend.repositories.cards import get_deck_items, reset_card_progress

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


async def _deck(pool, lang: str, level: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'grammar', $2, $2) RETURNING id",
            lang, level,
        ))


async def _point(pool, lang: str, level: str, title: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed) "
            "VALUES ($1, $2, $3, true) RETURNING id",
            lang, title, level,
        ))


async def test_deck_items_report_learner_status(pool):
    lang = await _lang(pool, "dst")
    await _deck(pool, lang, "A1")
    new_point = await _point(pool, lang, "A1", "New point")
    learning_point = await _point(pool, lang, "A1", "Learning point")
    known_point = await _point(pool, lang, "A1", "Known point")
    active_point = await _point(pool, lang, "A1", "Active point")
    user = await _user(pool, "learner@dst")
    other_user = await _user(pool, "other@dst")

    async with pool.privileged_connection() as conn:
        # Pending teach-gate: is_suspended AND repetitions = 0.
        await conn.execute(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, true, 0)",
            user, lang, learning_point,
        )
        # Retired via mark_card_known: is_suspended, repetitions >= 1.
        await conn.execute(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, true, 1)",
            user, lang, known_point,
        )
        # Normal active review card.
        await conn.execute(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, false, 3)",
            user, lang, active_point,
        )
        # Another user's card on the SAME content must never leak into this
        # user's status — RLS should make it invisible to the join.
        await conn.execute(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, false, 5)",
            other_user, lang, new_point,
        )

    async with pool.rls_connection(user) as conn:
        cl_id = await conn.fetchval(
            "SELECT id FROM content_lists WHERE language_id = $1", lang
        )
        listing = await get_deck_items(conn, str(cl_id))

    by_title = {it["item"]: it for it in listing["items"]}
    assert by_title["New point"]["status"] == "new"
    assert by_title["New point"]["user_card_id"] is None
    assert by_title["Learning point"]["status"] == "learning"
    assert by_title["Known point"]["status"] == "known"
    assert by_title["Active point"]["status"] == "active"
    for title in ("Learning point", "Known point", "Active point"):
        assert by_title[title]["user_card_id"] is not None


async def test_reset_card_progress_deletes_only_that_row(pool):
    lang = await _lang(pool, "rst")
    point_a = await _point(pool, lang, "A1", "Point A")
    point_b = await _point(pool, lang, "A1", "Point B")
    user = await _user(pool, "reset@rst")

    async with pool.privileged_connection() as conn:
        card_a = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, true, 1) "
            "RETURNING id",
            user, lang, point_a,
        )
        card_b = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, true, 1) "
            "RETURNING id",
            user, lang, point_b,
        )

    async with pool.rls_connection(user) as conn:
        ok = await reset_card_progress(conn, str(card_a))
        assert ok is True

    async with pool.privileged_connection() as conn:
        remaining = await conn.fetch(
            "SELECT id FROM user_cards WHERE user_id = $1", user
        )
    remaining_ids = {str(r["id"]) for r in remaining}
    assert str(card_a) not in remaining_ids
    assert str(card_b) in remaining_ids


async def test_reset_card_progress_is_rls_scoped(pool):
    """One user's card id can't be reset by another user — RLS makes the
    delete affect zero rows, which the router turns into a 404."""
    lang = await _lang(pool, "rso")
    point = await _point(pool, lang, "A1", "Someone else's point")
    owner = await _user(pool, "owner@rso")
    attacker = await _user(pool, "attacker@rso")

    async with pool.privileged_connection() as conn:
        card_id = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "is_suspended, repetitions) VALUES ($1, $2, 'grammar', $3, true, 1) "
            "RETURNING id",
            owner, lang, point,
        )

    async with pool.rls_connection(attacker) as conn:
        ok = await reset_card_progress(conn, str(card_id))
        assert ok is False

    async with pool.privileged_connection() as conn:
        still_there = await conn.fetchval(
            "SELECT 1 FROM user_cards WHERE id = $1", card_id
        )
    assert still_there == 1
