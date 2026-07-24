"""Reviewer editing of vocab example sentences: list / edit / delete against a
real Postgres."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_example_sentence,
    delete_example_sentence,
    edit_example_sentence,
    flag_example_sentence,
    list_pending_examples,
    list_vocab_examples,
    review_examples_bulk,
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


async def test_bulk_review_examples(pool):
    lang = await _language(pool, "blk")
    vocab = await _vocab(pool, lang, "kat")

    async with pool.privileged_connection() as conn:
        # Three AI (pending) + one human (already live).
        ok1 = await add_example_sentence(conn, vocab, lang, "AI een.", "one", source="ai")
        ok2 = await add_example_sentence(conn, vocab, lang, "AI twee.", "two", source="ai")
        flagged = await add_example_sentence(
            conn, vocab, lang, "AI drie.", "three", source="ai"
        )
        await add_example_sentence(conn, vocab, lang, "Mens vier.", "four", source="human")
        await flag_example_sentence(conn, flagged, "too simple")

        # Bulk approve skips the flagged one.
        changed = await review_examples_bulk(conn, lang, approve=True)
        assert changed == 2
        pending = await list_pending_examples(conn, lang)
        assert [p["id"] for p in pending] == [flagged]  # only the flagged one remains

        # The two approved are now live; the human one was never pending.
        live = await conn.fetchval(
            "SELECT count(*) FROM example_sentences "
            "WHERE vocabulary_id = $1 AND reviewed = true",
            vocab,
        )
        assert live == 3  # ok1, ok2, human
        assert {ok1, ok2}  # (ids exist)

        # Bulk reject clears whatever pending remains (the flagged one).
        removed = await review_examples_bulk(conn, lang, approve=False)
        assert removed == 1
        assert await list_pending_examples(conn, lang) == []
