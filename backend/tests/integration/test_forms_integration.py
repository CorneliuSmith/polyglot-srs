"""-k forms chart backfill end-to-end (WP45 track 3): the plan finds only the
drill answers the Gym cannot resolve to a chart, the run creates/updates the
vocabulary rows with verified charts, attach_cram_charts then FINDS those
charts, and a re-run finds nothing left to do. Real Postgres, maker in
dev-mock (its chart always contains the given answer, except answers
containing 'bad')."""
from __future__ import annotations

import json

from backend.repositories.cards import (
    _reset_chart_form_index,
    attach_cram_charts,
)
from backend.repositories.contributor import upsert_vocabulary_charts
from backend.services import generation_admin
from backend.services.generation_admin import plan_forms, run_forms

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


async def _point(pool, language_id: str, title: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, $2, 'A1', true, 1) RETURNING id",
            language_id, title,
        ))


async def _drill(pool, point_id: str, answer: str, lemma: str | None = None) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, hint, lemma) "
            "VALUES ($1, $2, $3, 'to dwell (you)', $4) RETURNING id",
            point_id, "Nós {{answer}} aqui.", answer, lemma,
        ))


async def _vocab(pool, language_id: str, word: str, morphology: dict | None) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, morphology) "
            "VALUES ($1, $2, $3::jsonb) RETURNING id",
            language_id, word,
            json.dumps(morphology) if morphology is not None else "{}",
        ))


def _mock_generation(monkeypatch):
    monkeypatch.setattr(generation_admin, "resolve_model", lambda *a, **k: "mock-model")
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )


async def test_forms_run_creates_charts_the_gym_then_finds(pool, monkeypatch):
    _mock_generation(monkeypatch)
    _reset_chart_form_index()

    lang = await _language(pool, "frm")
    point = await _point(pool, lang, "Present tense")
    # Two forms of the same missing word (stored lemma dedupes them into ONE
    # chart attempt) + one form already covered by an existing chart.
    await _drill(pool, point, "moramos", lemma="morar")
    await _drill(pool, point, "moras", lemma="morar")
    await _vocab(pool, lang, "falar", {
        "charts": [{"title": "Present", "rows": [["tu", "falas"]]}],
    })
    await _drill(pool, point, "falas")

    async with pool.privileged_connection() as conn:
        plan = await plan_forms(
            conn, language_id=lang, language_code="frm", max_items=50
        )
    assert plan["answers_scanned"] == 3
    assert plan["charts_to_attempt"] == 1  # falas resolves; morar dedupes

    async with pool.privileged_connection() as conn:
        result = await run_forms(
            conn, language_id=lang, language_code="frm",
            language_name="FRM", max_items=50,
        )
    assert result["charts_attempted"] == 1
    assert result["words_created"] == 1
    assert result["charts_rejected"] == 0

    # The vocabulary row exists, chartable, and provenance was logged.
    async with pool.privileged_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, morphology FROM vocabulary "
            "WHERE language_id = $1 AND word = 'morar'", lang,
        )
        assert row is not None
        morph = json.loads(row["morphology"])
        forms = [f for ch in morph["charts"] for _l, f in ch["rows"]]
        assert "moramos" in forms or "moras" in forms
        logged = await conn.fetchval(
            "SELECT count(*) FROM content_change_log "
            "WHERE entity_type = 'vocabulary' AND entity_id = $1 "
            "AND action = 'charts_generated'", row["id"],
        )
        assert logged == 1

    # The Gym now finds the generated chart from the drill's own answer.
    card = {
        "language_code": "frm", "correct_answer": "moramos",
        "morphology": None, "lemma": None, "hint": "to dwell (you)",
    }
    async with pool.privileged_connection() as conn:
        await attach_cram_charts(conn, [card])
    assert card["morphology"] is not None
    assert card["chart_word"] == "morar"

    # Idempotent: everything now resolves, so a re-run attempts nothing.
    async with pool.privileged_connection() as conn:
        replan = await plan_forms(
            conn, language_id=lang, language_code="frm", max_items=50
        )
    assert replan["charts_to_attempt"] == 0


async def test_forms_run_never_overwrites_existing_charts(pool, monkeypatch):
    _mock_generation(monkeypatch)
    _reset_chart_form_index()

    lang = await _language(pool, "fr2")
    point = await _point(pool, lang, "Past tense")
    # The word HAS charts, but they lack this drill's form. The plan excludes
    # it up front — the upsert would never overwrite the existing
    # (kaikki-authoritative) tables, so attempting would be pure waste and
    # would stop repeated runs from converging to zero.
    existing = {"charts": [{"title": "Present", "rows": [["eu", "parto"]]}],
                "gender": "n/a"}
    await _vocab(pool, lang, "partir", existing)
    await _drill(pool, point, "partimos", lemma="partir")

    async with pool.privileged_connection() as conn:
        result = await run_forms(
            conn, language_id=lang, language_code="fr2",
            language_name="FR2", max_items=50,
        )
    assert result["charts_attempted"] == 0
    assert result["words_created"] == 0

    # And even a direct upsert against the charted row refuses to overwrite.
    async with pool.privileged_connection() as conn:
        _vid, status = await upsert_vocabulary_charts(
            conn, lang, "partir", "verb",
            [{"title": "Generated", "rows": [["nós", "partimos"]]}],
            None, origin_detail="mock-model",
        )
        assert status == "skipped"
        morph = json.loads(await conn.fetchval(
            "SELECT morphology FROM vocabulary "
            "WHERE language_id = $1 AND word = 'partir'", lang,
        ))
    assert morph == existing


async def test_forms_run_fills_chartless_existing_word(pool, monkeypatch):
    _mock_generation(monkeypatch)
    _reset_chart_form_index()

    lang = await _language(pool, "fr3")
    point = await _point(pool, lang, "Present tense")
    # The word exists with chips-only morphology (the sw/xh/yo builder case):
    # the run must ADD charts while keeping the chips.
    await _vocab(pool, lang, "sema", {"pos_note": "verb"})
    await _drill(pool, point, "unasema", lemma="sema")

    async with pool.privileged_connection() as conn:
        result = await run_forms(
            conn, language_id=lang, language_code="fr3",
            language_name="FR3", max_items=50,
        )
    assert result["words_updated"] == 1

    async with pool.privileged_connection() as conn:
        morph = json.loads(await conn.fetchval(
            "SELECT morphology FROM vocabulary "
            "WHERE language_id = $1 AND word = 'sema'", lang,
        ))
    assert morph["pos_note"] == "verb"       # chips kept
    forms = [f for ch in morph["charts"] for _l, f in ch["rows"]]
    assert "unasema" in forms                # chart added, containing the form


async def test_rejected_chart_is_counted_and_not_stored(pool, monkeypatch):
    _mock_generation(monkeypatch)
    _reset_chart_form_index()

    lang = await _language(pool, "fr4")
    point = await _point(pool, lang, "Present tense")
    # The dev-mock omits an answer containing 'bad' from its chart, so the
    # containment checker rejects it — nothing may be persisted.
    await _drill(pool, point, "badform", lemma="badlemma")

    async with pool.privileged_connection() as conn:
        result = await run_forms(
            conn, language_id=lang, language_code="fr4",
            language_name="FR4", max_items=50,
        )
    assert result["charts_attempted"] == 1
    assert result["charts_rejected"] == 1
    assert result["words_created"] == 0

    async with pool.privileged_connection() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM vocabulary WHERE language_id = $1", lang,
        )
    assert count == 0
