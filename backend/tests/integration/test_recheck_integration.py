"""--recheck: audit existing sentences → flag bad, backfill missing translation,
top the word back up to target with fresh alternatives. Runs against real PG
with the maker/judge in dev-mock (a sentence containing 'bad' is rejected)."""
from __future__ import annotations

from backend.repositories.contributor import list_vocab_examples
from backend.services import generation_admin
from backend.services.generation_admin import recheck_examples

from .conftest import requires_db

pytestmark = requires_db


class _MockSettings:
    tutor_dev_mock = True
    anthropic_api_key = ""


async def _language(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _word(pool, language_id: str, word: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word) VALUES ($1, $2) RETURNING id",
            language_id, word,
        ))


async def _example(pool, language_id, vocabulary_id, sentence, translation) -> None:
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO example_sentences "
            "(language_id, vocabulary_id, sentence, translation, source, reviewed) "
            "VALUES ($1, $2, $3, $4, 'human', true)",
            language_id, vocabulary_id, sentence, translation,
        )


async def test_recheck_flags_backfills_and_tops_up(pool, monkeypatch):
    # Pin models offline so the test exercises DB logic, not the registry/pricing.
    monkeypatch.setattr(generation_admin, "resolve_model", lambda *a, **k: "mock-model")
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )

    lang = await _language(pool, "rck")
    wid = await _word(pool, lang, "gato")
    await _example(pool, lang, wid, "El gato duerme aqui.", "The cat sleeps.")
    await _example(pool, lang, wid, "Este gato es bad aqui.", "")   # -> flagged
    await _example(pool, lang, wid, "El gato corre mucho hoy.", "")  # -> backfilled

    async with pool.privileged_connection() as conn:
        result = await recheck_examples(
            conn,
            language_id=lang, language_code="es", language_name="Spanish",
            target_per_item=4, max_items=50,
        )
    assert result["sentences_flagged"] == 1
    assert result["translations_backfilled"] == 1
    assert result["alternatives_generated"] >= 1

    async with pool.privileged_connection() as conn:
        rows = await list_vocab_examples(conn, wid)

    by_sentence = {r["sentence"]: r for r in rows}
    # The 'bad' sentence is flagged with a reason, not deleted.
    bad = by_sentence["Este gato es bad aqui."]
    assert bad["flagged"] is True
    assert bad["flag_reason"]
    # The good-but-untranslated sentence now has a translation.
    fixed = by_sentence["El gato corre mucho hoy."]
    assert fixed["flagged"] is False
    assert (fixed["translation"] or "").strip()
    # A fresh alternative was added, pending review.
    ai_rows = [r for r in rows if r["source"] == "ai"]
    assert ai_rows and all(r["reviewed"] is False for r in ai_rows)
