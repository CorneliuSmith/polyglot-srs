"""Real-Postgres integration tests: RLS tenant isolation + key SQL queries.

These prove the things mocked unit tests can't: that one user cannot read or
write another user's rows, that the privileged connection bypasses RLS as
intended, and that the actual repository SQL runs against the real schema.
"""
from __future__ import annotations

import uuid

import asyncpg
import pytest

from backend.repositories.cards import (
    add_grammar_learn_batch,
    add_learn_batch,
    get_card_detail,
    get_due_cards,
)
from backend.repositories.tutor import get_user_profile, upsert_user_profile

from .conftest import requires_db

pytestmark = requires_db


# ── helpers ──────────────────────────────────────────────────────────────────

async def _new_user(pool_mod, email: str) -> str:
    async with pool_mod.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _language(pool_mod, code: str) -> str:
    async with pool_mod.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _insert_card(pool_mod, user_id: str, language_id: str) -> str:
    async with pool_mod.privileged_connection() as conn:
        return str(await conn.fetchval(
            """
            INSERT INTO user_cards (user_id, language_id, card_type, card_id)
            VALUES ($1, $2, 'vocabulary', gen_random_uuid()) RETURNING id
            """,
            user_id, language_id,
        ))


# ── schema sanity ────────────────────────────────────────────────────────────

async def test_all_migrations_applied(pool):
    async with pool.privileged_connection() as conn:
        n = await conn.fetchval(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        )
    assert n >= 12  # vocabulary, user_cards, tutor_*, contributor_roles, ...


# ── RLS isolation: the #1 risk ───────────────────────────────────────────────

async def test_user_cards_are_isolated(pool):
    lang = await _language(pool, "rls1")
    a = await _new_user(pool, "a@isolation")
    b = await _new_user(pool, "b@isolation")
    a_card = await _insert_card(pool, a, lang)
    await _insert_card(pool, b, lang)

    async with pool.rls_connection(a) as conn:
        rows = await conn.fetch("SELECT id, user_id FROM user_cards")
    ids = {str(r["id"]) for r in rows}
    assert a_card in ids
    assert all(str(r["user_id"]) == a for r in rows)  # never sees B's rows


async def test_cannot_insert_card_for_another_user(pool):
    lang = await _language(pool, "rls2")
    a = await _new_user(pool, "a@check")
    b = await _new_user(pool, "b@check")
    # A, acting as themselves, must not be able to create a card owned by B.
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with pool.rls_connection(a) as conn:
            await conn.execute(
                "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
                "VALUES ($1, $2, 'vocabulary', gen_random_uuid())",
                b, lang,
            )


async def test_tutor_profile_isolated(pool):
    a = await _new_user(pool, "a@mem")
    b = await _new_user(pool, "b@mem")
    async with pool.rls_connection(a) as conn:
        await upsert_user_profile(conn, a, {"native_language": "English"})
    async with pool.rls_connection(b) as conn:
        await upsert_user_profile(conn, b, {"native_language": "Spanish"})
        b_view = await get_user_profile(conn, b)
        # B cannot read A's profile even by id.
        a_view_from_b = await get_user_profile(conn, a)
    assert b_view == {"native_language": "Spanish"}
    assert a_view_from_b == {}  # RLS hides A's row from B


async def test_card_feedback_isolated(pool):
    lang = await _language(pool, "rls3")
    a = await _new_user(pool, "a@fb")
    b = await _new_user(pool, "b@fb")
    content = uuid.uuid4()
    async with pool.privileged_connection() as conn:
        for uid in (a, b):
            await conn.execute(
                "INSERT INTO card_feedback (user_id, language_id, card_type, content_id, message) "
                "VALUES ($1, $2, 'grammar', $3, 'issue')",
                uid, lang, content,
            )
    async with pool.rls_connection(a) as conn:
        rows = await conn.fetch("SELECT user_id FROM card_feedback")
    assert rows and all(str(r["user_id"]) == a for r in rows)


async def test_contributor_role_read_own_only(pool):
    a = await _new_user(pool, "a@role")
    b = await _new_user(pool, "b@role")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, role) VALUES ($1, 'admin')", a
        )
    async with pool.rls_connection(b) as conn:
        rows = await conn.fetch("SELECT user_id FROM contributor_roles")
    assert rows == []  # B sees none of A's roles


# ── privileged connection bypasses RLS (the contributor write path) ───────────

async def test_privileged_write_grammar_point(pool):
    lang = await _language(pool, "rls4")
    async with pool.privileged_connection() as conn:
        pid = await conn.fetchval(
            """
            INSERT INTO grammar_points (language_id, title, explanation_source, reviewed)
            VALUES ($1, 'Test point', 'contributor', false) RETURNING id
            """,
            lang,
        )
    assert pid is not None


async def test_authenticated_cannot_write_grammar_content(pool):
    """Defense-in-depth: even with a role, the DB blocks content writes via RLS."""
    lang = await _language(pool, "rls5")
    user = await _new_user(pool, "contrib@hardening")
    # Reads are allowed (world-readable)...
    async with pool.rls_connection(user) as conn:
        await conn.fetch("SELECT id FROM grammar_points LIMIT 1")
    # ...but a direct write as the authenticated role is denied by RLS.
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with pool.rls_connection(user) as conn:
            await conn.execute(
                "INSERT INTO grammar_points (language_id, title) VALUES ($1, 'sneaky')",
                lang,
            )


# ── functional: real repository SQL against real data ────────────────────────

async def test_vocab_learn_and_due_flow(pool):
    lang = await _language(pool, "func1")
    user = await _new_user(pool, "learner@func")
    async with pool.privileged_connection() as conn:
        vocab_id = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'casa', 1, 'A1') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'house')", vocab_id,
        )
        list_id = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 vocab') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", user, list_id,
        )

    async with pool.rls_connection(user) as conn:
        result = await add_learn_batch(conn, user, lang, 5)
        assert result["added"] == 1
        due = await get_due_cards(conn, lang)
        assert any(c["correct_answer"] == "casa" for c in due)
        detail = await get_card_detail(conn, due[0]["id"])
    assert detail["definition"] == "house"


async def test_grammar_learn_respects_review_policy(pool):
    lang = await _language(pool, "func2")
    user = await _new_user(pool, "learner@grammar")
    async with pool.privileged_connection() as conn:
        # one human-reviewed point, one only AI-passed (unreviewed)
        reviewed = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Reviewed pt', 'A1', true, 1) RETURNING id", lang,
        )
        await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, ai_check_status, display_order) "
            "VALUES ($1, 'AI-only pt', 'A1', false, 'pass', 2) RETURNING id", lang,
        )
        list_id = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'grammar', 'A1', 'A1 grammar') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", user, list_id,
        )

    # strict (default): only the reviewed point is learnable
    async with pool.rls_connection(user) as conn:
        res = await add_grammar_learn_batch(conn, user, lang, 10)
        learned = {r async for r in _card_ids(conn, user)}
    assert res["added"] == 1
    assert str(reviewed) in learned

    # switch to ai_ok: the AI-passed point becomes learnable too
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE languages SET grammar_review_policy = 'ai_ok' WHERE id = $1", lang
        )
    async with pool.rls_connection(user) as conn:
        res2 = await add_grammar_learn_batch(conn, user, lang, 10)
    assert res2["added"] == 1  # the previously-hidden AI-passed point


async def _card_ids(conn, user_id):
    rows = await conn.fetch(
        "SELECT card_id FROM user_cards WHERE user_id = $1 AND card_type = 'grammar'",
        user_id,
    )
    for r in rows:
        yield str(r["card_id"])
