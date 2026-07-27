"""Gym serving end-to-end: a drill with a stored lemma gets its chart attached
directly (no NLP needed), the baseline is standardized to "word (form)" in the
native language, and the manifest-facing fields (cell) ride along. Real PG."""
from __future__ import annotations

import json

from backend.repositories.cards import get_cram_cards

from .conftest import requires_db

pytestmark = requires_db

CHARTS = {
    "chips": [],
    "charts": [{"title": "Present", "rows": [["yo", "preparo"], ["tú", "preparas"]]}],
}


async def _lang(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def test_lemma_anchored_chart_and_standardized_baseline(pool):
    lang = await _lang(pool, "es")
    async with pool.privileged_connection() as conn:
        point = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Present tense', 'A1', true, 1) RETURNING id", lang,
        ))
        # The chartable dictionary form, with an English definition.
        vocab = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, morphology) "
            "VALUES ($1, 'preparar', $2::jsonb) RETURNING id",
            lang, json.dumps(CHARTS),
        )
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'to prepare; to get ready')", vocab,
        )
        # A generated-style drill: inflected answer, stored lemma + cell, and a
        # legacy-format hint ("lemma, person") that should be UPGRADED.
        await conn.execute(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, hint, cell, lemma, source, reviewed, display_order) "
            "VALUES ($1, 'Tú {{answer}} la cena.', 'preparas', 'preparar, tú', 'tú', 'preparar', 'ai', true, 1)",
            point,
        )

        cards = await get_cram_cards(conn, [point], per_point=3)

    assert len(cards) == 1
    card = cards[0]
    # Chart attached via the stored lemma (direct vocab lookup).
    assert card["morphology"] is not None
    assert card["chart_word"] == "preparar"
    # Standardized baseline: native-language word + the drill's cell.
    # Practice, not recall: target-language base + explained cell.
    assert card["baseline"] == "preparar (tú; you, singular)"
    assert card["cell"] == "tú"


async def test_baseline_without_chart_still_standardizes(pool):
    lang = await _lang(pool, "gb2")
    async with pool.privileged_connection() as conn:
        point = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Weak verbs', 'A1', true, 1) RETURNING id", lang,
        ))
        # No vocabulary row at all → no chart; recipe hint + cell.
        await conn.execute(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, hint, cell, source, reviewed, display_order) "
            "VALUES ($1, 'She {{answer}} TV.', 'watches', 'to watch — add -es', 'he/she', 'human', true, 1)",
            point,
        )
        cards = await get_cram_cards(conn, [point], per_point=3)

    assert len(cards) == 1
    card = cards[0]
    assert card["morphology"] is None  # nothing chartable — toggle stays hidden
    # Recipe stripped, cell appended: one shape everywhere.
    assert card["baseline"] == "to watch (he/she)"


async def test_chart_found_from_the_answer_when_there_is_no_lemma(pool):
    """The ordinary seeded-drill case, which used to show no chart at all:
    the drill stores NO lemma, its hint is an English gloss, and the language
    has no real lemmatizer. The answer's own form appears inside the chart, so
    that is what we look it up by."""
    from backend.repositories.cards import (
        _reset_chart_form_index,
        attach_cram_charts,
    )

    _reset_chart_form_index()
    lang = await _lang(pool, "pt")
    chart = {
        "charts": [{
            "title": "Presente",
            "columns": ["", "forma"],
            # Note the stress mark: the drill answer has none.
            "rows": [["eu", "moro"], ["tu", "moras"], ["ele", "mora"]],
        }],
    }
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level, morphology) "
            "VALUES ($1, 'morar', 1, 'A1', $2::jsonb)",
            lang, json.dumps(chart, ensure_ascii=False),
        )

    card = {
        "language_code": "pt",
        "correct_answer": "moras",   # inflected form, not the headword
        "hint": "to live (you)",     # English gloss — never a chart key
        "lemma": None,               # seeded drills have none
        "morphology": None,
    }
    async with pool.privileged_connection() as conn:
        await attach_cram_charts(conn, [card])
    assert card["morphology"] is not None
    assert card["chart_word"] == "morar"
    _reset_chart_form_index()


async def test_answer_lookup_does_not_invent_charts(pool):
    """A word with no chart anywhere still yields no chart — the fallback
    must not attach something merely similar."""
    from backend.repositories.cards import (
        _reset_chart_form_index,
        attach_cram_charts,
    )

    _reset_chart_form_index()
    lang = await _lang(pool, "pt2")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'gato', 1, 'A1')",
            lang,
        )
    card = {
        "language_code": "pt2", "correct_answer": "gatos",
        "hint": "cat", "lemma": None, "morphology": None,
    }
    async with pool.privileged_connection() as conn:
        await attach_cram_charts(conn, [card])
    assert card["morphology"] is None
    _reset_chart_form_index()
