"""The admin's per-language model override (languages.tutor_model) actually
reaches a real generation run (owner report: "admin values not persisting").

Root cause was NOT that the value failed to persist in the DB — it always
did — but that resolve_model()'s override arg was only ever threaded through
by 2 of ~20 call sites (tutor chat + the Reader). An admin who set a
language's model, then ran Generate/Recheck/Overlap/Forms from the panel,
saw the plain default instead and reasonably concluded the setting "didn't
stick". This is real Postgres end-to-end (no resolve_model mocking) so it
actually exercises generation_admin.py's DB fetch, not a patched stand-in."""
from __future__ import annotations

from backend.services import generation_admin
from backend.services.generation_admin import (
    plan_forms,
    plan_overlap,
    plan_recheck,
    plan_run,
)

from .conftest import requires_db

pytestmark = requires_db


class _MockSettings:
    tutor_dev_mock = True
    anthropic_api_key = ""


async def _language(pool, code: str, tutor_model: str | None = None) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, tutor_model) "
            "VALUES ($1, $2, false, $3) "
            "ON CONFLICT (code) DO UPDATE SET tutor_model = EXCLUDED.tutor_model "
            "RETURNING id",
            code, code.upper(), tutor_model,
        ))


async def test_generation_plan_honors_the_override(pool, monkeypatch):
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)

    with_override = await _language(pool, "mo1", tutor_model="claude-opus-4-8")
    without_override = await _language(pool, "mo2")

    async with pool.privileged_connection() as conn:
        plan = await plan_run(
            conn, kind="vocab", language_id=with_override, language_code="mo1",
            target_per_item=1, max_items=1,
        )
        assert plan["model"] == "claude-opus-4-8"

        default_plan = await plan_run(
            conn, kind="vocab", language_id=without_override, language_code="mo2",
            target_per_item=1, max_items=1,
        )
        assert default_plan["model"] != "claude-opus-4-8"


async def test_recheck_and_overlap_plans_honor_the_override(pool, monkeypatch):
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)

    lang = await _language(pool, "mo3", tutor_model="admin-override-sentinel")

    async with pool.privileged_connection() as conn:
        recheck_plan = await plan_recheck(
            conn, language_id=lang, language_code="mo3", max_items=1,
        )
        overlap_plan = await plan_overlap(conn, language_id=lang, language_code="mo3")
        forms_plan = await plan_forms(
            conn, language_id=lang, language_code="mo3", max_items=1,
        )
    # sentence_checker/grammar_checker map to the low-resource FIELD, not
    # tutor_model — the override must NOT leak into a checker (that would
    # weaken the "verify one tier up" guarantee). forms uses grammar_maker
    # (a maker task) and DOES honor it.
    assert recheck_plan["model"] != "admin-override-sentinel"
    assert overlap_plan["model"] != "admin-override-sentinel"
    assert forms_plan["model"] == "admin-override-sentinel"
