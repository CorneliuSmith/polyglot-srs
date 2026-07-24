"""Reviewer editing of vocab example sentences: list / edit / delete against a
real Postgres."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_example_sentence,
    delete_example_sentence,
    edit_example_sentence,
    list_vocab_examples,
)

from .conftest import requires_db

pytestmark = requires_db


async def _language(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _vocab(pool, language_id: str, word: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word) VALUES ($1, $2) RETURNING id",
            language_id, word,
        ))


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def test_list_edit_delete_example(pool):
    lang = await _language(pool, "exl")
    vocab = await _vocab(pool, lang, "hond")
    editor = await _user(pool, "reviewer@ex")

    async with pool.privileged_connection() as conn:
        eid = await add_example_sentence(
            conn, vocab, lang, "De hond blaft.", "The dog barks.", source="human",
        )
        assert eid

        rows = await list_vocab_examples(conn, vocab)
        assert len(rows) == 1
        assert rows[0]["sentence"] == "De hond blaft."
        assert rows[0]["is_modified"] is False

        # Edit stamps provenance.
        changed = await edit_example_sentence(
            conn, eid, "De grote hond blaft luid.", "The big dog barks loudly.",
            editor,
        )
        assert changed is True
        rows = await list_vocab_examples(conn, vocab)
        assert rows[0]["sentence"] == "De grote hond blaft luid."
        assert rows[0]["translation"] == "The big dog barks loudly."
        assert rows[0]["is_modified"] is True

        modified_by = await conn.fetchval(
            "SELECT modified_by FROM example_sentences WHERE id = $1", eid
        )
        assert str(modified_by) == editor

        # Delete removes it.
        assert await delete_example_sentence(conn, eid) is True
        assert await list_vocab_examples(conn, vocab) == []
        # Deleting again is a no-op.
        assert await delete_example_sentence(conn, eid) is False
