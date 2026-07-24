"""AI vocab leveling: estimate → provisional level → gate → reviewer confirm."""
from __future__ import annotations

from backend.repositories.cards import get_deck_preview
from backend.repositories.contributor import (
    confirm_vocab_level,
    ensure_vocab_content_list,
    list_ai_leveled_vocab,
    set_vocab_ai_level,
    vocab_needing_level,
)

from .conftest import requires_db

pytestmark = requires_db


async def _language(pool, code: str, policy: str = "strict") -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, grammar_review_policy) "
            "VALUES ($1, $2, false, $3) "
            "ON CONFLICT (code) DO UPDATE SET grammar_review_policy = EXCLUDED.grammar_review_policy "
            "RETURNING id",
            code, code.upper(), policy,
        ))


async def _word(pool, language_id: str, word: str, level=None) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level) VALUES ($1, $2, $3) "
            "RETURNING id",
            language_id, word, level,
        ))


async def _deck_id(pool, language_id: str, level: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "SELECT id FROM content_lists WHERE language_id = $1 "
            "AND list_type = 'vocabulary' AND level = $2",
            language_id, level,
        ))


async def test_leveling_flow_and_gate(pool):
    lang = await _language(pool, "lvl", "strict")
    wid = await _word(pool, lang, "kupanga", level=None)  # no level yet

    async with pool.privileged_connection() as conn:
        # It shows up as needing a level.
        need = await vocab_needing_level(conn, lang)
        assert any(w["vocabulary_id"] == wid for w in need)

        # Assign a provisional AI level + ensure the deck exists.
        assert await set_vocab_ai_level(conn, wid, "B1") is True
        await ensure_vocab_content_list(conn, lang, "B1", "lvl")

        # It's now listed for review, provisional.
        ai = await list_ai_leveled_vocab(conn, lang)
        assert [w["word"] for w in ai] == ["kupanga"]
        assert ai[0]["level"] == "B1"

        # set_vocab_ai_level never overwrites a real level.
        assert await set_vocab_ai_level(conn, wid, "A1") is False

    deck = await _deck_id(pool, lang, "B1")

    # Strict policy: the provisional word is hidden from the deck preview.
    async with pool.rls_connection("00000000-0000-0000-0000-000000000000") as conn:
        preview = await get_deck_preview(conn, deck)
    assert preview is not None
    assert "kupanga" not in [i["item"] for i in preview["items"]]

    # Flip to ai_ok → it shows.
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE languages SET grammar_review_policy = 'ai_ok' WHERE id = $1", lang
        )
    async with pool.rls_connection("00000000-0000-0000-0000-000000000000") as conn:
        preview = await get_deck_preview(conn, deck)
    assert "kupanga" in [i["item"] for i in preview["items"]]

    # A reviewer confirms the level → curated, no longer provisional.
    async with pool.privileged_connection() as conn:
        assert await confirm_vocab_level(conn, wid, "A2") is True
        assert await list_ai_leveled_vocab(conn, lang) == []
        row = await conn.fetchrow(
            "SELECT level, level_source FROM vocabulary WHERE id = $1", wid
        )
    assert row["level"] == "A2"
    assert row["level_source"] == "curated"
