"""Unified Review Inbox: review_inbox_counts rolls up every awaiting-review
queue for a language into one query. Runs against real Postgres."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_example_sentence,
    add_recommendation,
    flag_example_sentence,
    list_tester_recommendations,
    list_vocab_items,
    review_inbox_counts,
    review_inbox_other_languages,
    suggest_example_translation,
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


async def test_other_languages_strip_finds_work_the_selector_hides(pool):
    """The cross-language roll-up: an admin whose working language is quiet
    must still be told which OTHER language has traffic. This is the whole
    'testers say they're submitting and I see nothing' failure."""
    quiet = await _lang(pool, "xlq")
    busy = await _lang(pool, "xlb")

    async with pool.privileged_connection() as conn:
        # Nothing anywhere yet → the strip only ever lists non-zero languages,
        # so neither of these two shows up in the other's roll-up.
        assert not [
            r for r in await review_inbox_other_languages(conn, quiet)
            if r["id"] in (quiet, busy)
        ]

        vocab = await _word(pool, busy, "gato")
        await add_example_sentence(
            conn, vocab, busy, "El gato duerme.", None, source="ai"
        )

        # The working language itself is still empty…
        assert all(v == 0 for v in (await review_inbox_counts(conn, quiet)).values())
        # …but the strip names the language that isn't.
        strip = {r["id"]: r for r in await review_inbox_other_languages(conn, quiet)}
        assert busy in strip
        assert strip[busy]["code"] == "xlb"
        assert strip[busy]["total"] >= 1
        assert strip[busy]["counts"]["pending_examples"] >= 1

        # A language never lists ITSELF — that's the tiles' job.
        assert busy not in {
            r["id"] for r in await review_inbox_other_languages(conn, busy)
        }


async def test_tester_recommendations_are_counted_and_listed(pool):
    """A trial reviewer's advisory ✓/✗ is a queue in its own right, and its
    written note survives as text — until the item is decided, at which point
    the advice is spent and drops out of both."""
    lang = await _lang(pool, "trc")
    tester = await _user(pool, "tester@trc")

    async with pool.privileged_connection() as conn:
        vocab = await _word(pool, lang, "libro")
        example = await add_example_sentence(
            conn, vocab, lang, "Leo un libro.", "I read a book.", source="ai"
        )
        await conn.execute(
            "UPDATE example_sentences SET reviewed = false WHERE id = $1", example
        )
        await add_recommendation(
            conn, tester, lang, "example", example, "reject",
            note="'Leo' reads as the name Leo here.",
        )

        assert (await review_inbox_counts(conn, lang))["tester_recommendations"] == 1
        listed = await list_tester_recommendations(conn, lang)
        assert len(listed) == 1
        assert listed[0]["recommendation"] == "reject"
        assert "reads as the name Leo" in listed[0]["note"]
        assert listed[0]["target_label"] == "Leo un libro."
        assert listed[0]["context"] == "libro"

        # Publish the example: the advice has been acted on, so it leaves the
        # queue rather than sitting there forever.
        await conn.execute(
            "UPDATE example_sentences SET reviewed = true WHERE id = $1", example
        )
        assert (await review_inbox_counts(conn, lang))["tester_recommendations"] == 0
        assert await list_tester_recommendations(conn, lang) == []


async def test_vocab_list_locates_flagged_and_suggested_examples(pool):
    """The inbox counts flagged examples / translation fixes language-wide;
    without a per-word marker, finding them meant opening words at random."""
    lang = await _lang(pool, "vlo")
    editor = await _user(pool, "ed@vlo")

    async with pool.privileged_connection() as conn:
        marked = await _word(pool, lang, "silla", frequency_rank=1)
        clean = await _word(pool, lang, "mesa", frequency_rank=2)

        bad = await add_example_sentence(
            conn, marked, lang, "Silla.", None, source="ai"
        )
        await flag_example_sentence(conn, bad, "not a sentence", actor_id=editor)
        thin = await add_example_sentence(
            conn, marked, lang, "La silla es roja.", "chair red", source="ai"
        )
        await suggest_example_translation(
            conn, thin, "The chair is red.", "literal gloss"
        )
        await add_example_sentence(
            conn, clean, lang, "La mesa es grande.", "The table is big.", source="ai"
        )

        items = {i["word"]: i for i in await list_vocab_items(conn, lang)}
        assert items["silla"]["flagged_count"] == 1
        assert items["silla"]["suggestion_count"] == 1
        assert items["mesa"]["flagged_count"] == 0
        assert items["mesa"]["suggestion_count"] == 0
