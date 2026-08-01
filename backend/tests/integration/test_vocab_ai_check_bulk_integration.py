"""Bulk AI check over a language's vocabulary.

Grammar got a bulk runner when a freshly-seeded language turned out to have
40-odd points invisible behind the two-part visibility gate. Vocabulary has
the identical gate and three orders of magnitude more rows, and the only tool
was the per-word button (whose plumbing is covered in
test_vocab_ai_check_integration.py) — not so much a slow workflow as a reason
to give up.

The properties pinned here are the ones that make a ten-thousand-word run
survivable: resumable, so an interrupted run costs nothing already paid for;
narrowable by level, so it can be done in sittings; and unwilling to record a
verdict it has no basis for.

Real Postgres, with the model call patched out.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.services.seeder.ai_check_vocab import ai_check_vocabulary

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db


@pytest.fixture
def db_url():
    """The CLI opens its own connection rather than borrowing the app pool."""
    return INTEGRATION_DSN


async def _seed(pool, code: str, words: list[tuple[str, str, int]]) -> str:
    """words: (word, level, frequency_rank)"""
    async with pool.privileged_connection() as conn:
        lang = str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))
        for word, level, rank in words:
            vid = await conn.fetchval(
                "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
                "VALUES ($1, $2, $3, $4) RETURNING id",
                lang, word, level, rank,
            )
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'en', $2)",
                vid, f"meaning of {word}",
            )
    return lang


async def _verdicts(pool, lang: str) -> dict[str, str | None]:
    async with pool.privileged_connection() as conn:
        rows = await conn.fetch(
            "SELECT word, ai_check_status FROM vocabulary WHERE language_id = $1",
            lang,
        )
    return {r["word"]: r["ai_check_status"] for r in rows}


def _mock_model(status: str = "pass"):
    async def _check(language_code, word, definition, examples):
        return {"status": status, "notes": ""}
    return patch(
        "backend.services.seeder.ai_check_vocab.semantic_check_vocab", _check
    )


def _provider(available: bool = True):
    return patch(
        "backend.services.seeder.ai_check_vocab.ai_available", lambda: available
    )


async def test_it_stores_a_verdict_for_every_word(pool, db_url):
    lang = await _seed(pool, "vab1", [("aleph", "A1", 1), ("bet", "A1", 2)])
    with _mock_model(), _provider():
        stats = await ai_check_vocabulary(db_url, "vab1")
    assert stats["checked"] == 2 and stats["passed"] == 2
    assert await _verdicts(pool, lang) == {"aleph": "pass", "bet": "pass"}


async def test_a_second_run_costs_nothing(pool, db_url):
    """Resumability is why this is safe to start at all: an API hiccup ten
    thousand words in must not mean paying for those words again."""
    await _seed(pool, "vab2", [("aleph", "A1", 1), ("bet", "A1", 2)])
    with _mock_model(), _provider():
        first = await ai_check_vocabulary(db_url, "vab2")
        second = await ai_check_vocabulary(db_url, "vab2")
    assert first["checked"] == 2
    assert second["checked"] == 0


async def test_recheck_all_goes_over_them_again(pool, db_url):
    await _seed(pool, "vab3", [("aleph", "A1", 1)])
    with _mock_model(), _provider():
        await ai_check_vocabulary(db_url, "vab3")
        again = await ai_check_vocabulary(db_url, "vab3", only_missing=False)
    assert again["checked"] == 1


async def test_one_level_at_a_time(pool, db_url):
    lang = await _seed(
        pool, "vab4", [("aleph", "A1", 1), ("bet", "A2", 2), ("gimel", "C2", 3)]
    )
    with _mock_model(), _provider():
        stats = await ai_check_vocabulary(db_url, "vab4", level="A1")
    assert stats["checked"] == 1
    verdicts = await _verdicts(pool, lang)
    assert verdicts["aleph"] == "pass"
    assert verdicts["bet"] is None and verdicts["gimel"] is None


async def test_a_word_with_no_gloss_is_skipped_not_failed(pool, db_url):
    """Nothing to judge against. Leaving it unchecked keeps it queued for the
    definitions feed; recording a verdict would quietly declare an empty card
    fine and publish it to learners."""
    lang = await _seed(pool, "vab5", [("aleph", "A1", 1)])
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
            "VALUES ($1, 'orphan', 'A1', 2)", lang,
        )
    with _mock_model(), _provider():
        stats = await ai_check_vocabulary(db_url, "vab5")
    assert stats["checked"] == 1
    assert stats["skipped_no_definition"] == 1
    assert (await _verdicts(pool, lang))["orphan"] is None


async def test_limit_sizes_a_first_run(pool, db_url):
    """One model call per word. A first run over a new language should be a
    decision, not a discovery."""
    await _seed(pool, "vab6", [("a", "A1", 1), ("b", "A1", 2), ("c", "A1", 3)])
    with _mock_model(), _provider():
        stats = await ai_check_vocabulary(db_url, "vab6", limit=2)
    assert stats["checked"] == 2


async def test_concerns_are_counted_separately(pool, db_url):
    """A 'concerns' verdict does NOT publish the word — it routes to the
    review queue. The split is how an operator knows how much landed there."""
    lang = await _seed(pool, "vab7", [("aleph", "A1", 1)])
    with _mock_model("concerns"), _provider():
        stats = await ai_check_vocabulary(db_url, "vab7")
    assert stats["passed"] == 0 and stats["concerns"] == 1
    assert (await _verdicts(pool, lang))["aleph"] == "concerns"


async def test_it_refuses_to_run_without_a_provider(pool, db_url):
    await _seed(pool, "vab8", [("aleph", "A1", 1)])
    with _provider(False), pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        await ai_check_vocabulary(db_url, "vab8")
