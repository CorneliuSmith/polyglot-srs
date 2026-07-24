"""Unified Review Inbox: review_inbox_counts rolls up every awaiting-review
queue for a language into one query. Runs against real Postgres."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_example_sentence,
    flag_example_sentence,
    review_inbox_counts,
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


async def _word(pool, lang: str, word: str, **kw) -> str:
    cols = "language_id, word"
    vals = "$1, $2"
    args = [lang, word]
    for i, (k, v) in enumerate(kw.items(), start=3):
        cols += f", {k}"
        vals += f", ${i}"
        args.append(v)
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            f"INSERT INTO vocabulary ({cols}) VALUES ({vals}) RETURNING id", *args
        ))


async def test_inbox_counts_are_isolated_per_language(pool):
    lang = await _lang(pool, "inb")
    other = await _lang(pool, "ino")
    editor = await _user(pool, "ed@inb")

    async with pool.privileged_connection() as conn:
        # Empty to start.
        counts = await review_inbox_counts(conn, lang)
        assert all(v == 0 for v in counts.values())

        # A pending AI example + a flagged one on THIS language.
        vocab = await _word(pool, lang, "cat")
        pending = await add_example_sentence(
            conn, vocab, lang, "The cat sits.", "A cat sits.", source="ai"
        )
        await conn.execute(
            "UPDATE example_sentences SET reviewed = false WHERE id = $1", pending
        )
        flagged = await add_example_sentence(
            conn, vocab, lang, "Cat.", None, source="ai"
        )
        await flag_example_sentence(conn, flagged, "too simple", actor_id=editor)

        # An AI-levelled word contributes to ai_levels.
        await _word(pool, lang, "dog", level="B1", level_source="ai")

        # Noise on ANOTHER language must not leak in.
        ovocab = await _word(pool, other, "perro")
        await add_example_sentence(
            conn, ovocab, other, "El perro.", None, source="ai"
        )

        counts = await review_inbox_counts(conn, lang)
        assert counts["pending_examples"] >= 1
        assert counts["flagged_examples"] == 1
        assert counts["ai_levels"] == 1

        # The other language is counted on its own.
        ocounts = await review_inbox_counts(conn, other)
        assert ocounts["flagged_examples"] == 0
        assert ocounts["pending_examples"] >= 1
