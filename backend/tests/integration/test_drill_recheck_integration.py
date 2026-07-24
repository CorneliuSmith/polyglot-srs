"""--recheck for grammar: audit existing drills → flag the bad/too-simple ones
for reviewers (never delete), then top the point back up to target with fresh
alternatives. Real Postgres, maker/judge in dev-mock (a sentence containing
'bad' is rejected on correctness, 'simple' as too trivial)."""
from __future__ import annotations

from backend.repositories.contributor import list_drills, review_inbox_counts
from backend.services import generation_admin
from backend.services.generation_admin import recheck_drills

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


async def _drill(pool, point_id, sentence, answer) -> None:
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, source, reviewed, display_order) "
            "VALUES ($1, $2, $3, 'human', true, "
            " (SELECT COALESCE(MAX(display_order),0)+1 FROM drill_sentences WHERE grammar_point_id=$1))",
            point_id, sentence, answer,
        )


async def test_recheck_flags_bad_drills_and_leaves_good(pool, monkeypatch):
    monkeypatch.setattr(generation_admin, "resolve_model", lambda *a, **k: "mock-model")
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )

    lang = await _language(pool, "drk")
    point = await _point(pool, lang, "Present tense")
    await _drill(pool, point, "Yo {{answer}} agua todos los dias.", "bebo")   # good
    await _drill(pool, point, "Esta frase es bad aqui {{answer}}.", "malo")   # -> flagged
    await _drill(pool, point, "Es simple {{answer}} hoy.", "muy")             # -> flagged

    async with pool.privileged_connection() as conn:
        result = await recheck_drills(
            conn, language_id=lang, language_code="es", language_name="Spanish",
            target_per_item=3, max_items=50,
        )
    assert result["drills_flagged"] == 2  # one correctness, one complexity

    async with pool.privileged_connection() as conn:
        by_sentence = {d["sentence"]: d for d in await list_drills(conn, point)}
        counts = await review_inbox_counts(conn, lang)

    # The good drill is untouched.
    assert by_sentence["Yo {{answer}} agua todos los dias."]["flagged"] is False
    # The bad one is flagged with a reason, not deleted.
    bad = by_sentence["Esta frase es bad aqui {{answer}}."]
    assert bad["flagged"] is True and bad["flag_reason"]
    # The too-simple one is flagged on complexity.
    simple = by_sentence["Es simple {{answer}} hoy."]
    assert simple["flagged"] is True
    assert "simple" in (simple["flag_reason"] or "").lower()
    # The Review Inbox rolls the flagged drills up.
    assert counts["flagged_drills"] == 2
