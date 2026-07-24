"""Vocab AI semantic check: the word + its definition and examples load for
review, and the stored verdict surfaces in the review list. Real Postgres."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_example_sentence,
    get_vocab_for_check,
    list_vocab_items,
    save_vocab_ai_check,
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


async def test_vocab_ai_check_loads_and_persists(pool):
    lang = await _lang(pool, "vck")
    async with pool.privileged_connection() as conn:
        vocab = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level) "
            "VALUES ($1, 'mchana', 'A1') RETURNING id", lang,
        ))
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'daytime; afternoon')", vocab,
        )
        await add_example_sentence(
            conn, vocab, lang, "Habari za mchana.", "Good afternoon.", source="human"
        )

        # The review loads the word, its gloss, and its examples.
        payload = await get_vocab_for_check(conn, vocab)
        assert payload["word"] == "mchana"
        assert payload["definition"] == "daytime; afternoon"
        assert payload["language_code"] == "vck"
        assert any("mchana" in e["sentence"] for e in payload["examples"])

        # Storing a verdict surfaces it in the review list.
        await save_vocab_ai_check(conn, vocab, "concerns", "Gloss is fine; example is natural but formal.")
        items = {i["id"]: i for i in await list_vocab_items(conn, lang)}
        assert items[vocab]["ai_check_status"] == "concerns"
        assert "formal" in items[vocab]["ai_check_notes"]

        # A 'pass' with empty notes stores NULL notes, not "".
        await save_vocab_ai_check(conn, vocab, "pass", "")
        items = {i["id"]: i for i in await list_vocab_items(conn, lang)}
        assert items[vocab]["ai_check_status"] == "pass"
        assert items[vocab]["ai_check_notes"] is None
