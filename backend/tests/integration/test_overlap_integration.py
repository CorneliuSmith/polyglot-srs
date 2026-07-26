"""Grammar-point overlap audit end-to-end (owner, 2026-07-26): the judge
scans the syllabus, overlapping pairs become open review rows, re-runs don't
stack duplicates, reviewers resolve, the inbox counts it. Real Postgres,
judge in dev-mock (titles sharing a 5+ letter word overlap)."""
from __future__ import annotations

from backend.repositories.contributor import (
    list_overlaps,
    resolve_overlap,
    review_inbox_counts,
)
from backend.services import generation_admin
from backend.services.generation_admin import run_overlap_audit

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


async def _point(pool, language_id: str, title: str, level: str = "A1") -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, $2, $3, true, "
            " (SELECT COALESCE(MAX(display_order),0)+1 FROM grammar_points WHERE language_id=$1)) "
            "RETURNING id",
            language_id, title, level,
        ))


async def _new_user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def test_overlap_audit_flags_resolves_and_stays_idempotent(pool, monkeypatch):
    monkeypatch.setattr(generation_admin, "resolve_model", lambda *a, **k: "mock-model")
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )

    lang = await _language(pool, "ovl")
    a = await _point(pool, lang, "Present tense of -ar verbs")
    b = await _point(pool, lang, "The present tense")     # overlaps a (mock)
    await _point(pool, lang, "Noun gender")               # overlaps nothing

    async with pool.privileged_connection() as conn:
        result = await run_overlap_audit(
            conn, language_id=lang, language_code="ovl", language_name="OVL"
        )
    assert result["points_audited"] == 3
    assert result["pairs_flagged"] == 1

    async with pool.privileged_connection() as conn:
        open_pairs = await list_overlaps(conn, lang, status="open")
        counts = await review_inbox_counts(conn, lang)
    assert counts["overlaps"] == 1
    (pair,) = open_pairs
    assert {pair["point_a"]["id"], pair["point_b"]["id"]} == {a, b}
    assert pair["verdict"] == "partial"
    assert "present" in (pair["reason"] or "")

    # Re-run: the same pair is reported again but NOT re-flagged (open-pair
    # dedupe) — running alongside the recheck repeatedly is safe.
    async with pool.privileged_connection() as conn:
        rerun = await run_overlap_audit(
            conn, language_id=lang, language_code="ovl", language_name="OVL"
        )
        still_open = await list_overlaps(conn, lang, status="open")
    assert rerun["pairs_reported"] == 1
    assert rerun["pairs_flagged"] == 0
    assert len(still_open) == 1

    # A reviewer resolves it; the queue and inbox empty out.
    reviewer = await _new_user(pool, "overlap-reviewer@x")
    async with pool.privileged_connection() as conn:
        assert await resolve_overlap(conn, pair["id"], "distinct", reviewer) is True
        # Only open rows resolve — a second verdict is a no-op.
        assert await resolve_overlap(conn, pair["id"], "dismissed", reviewer) is False
        assert await list_overlaps(conn, lang, status="open") == []
        assert (await review_inbox_counts(conn, lang))["overlaps"] == 0
        resolved = await list_overlaps(conn, lang, status="distinct")
    assert len(resolved) == 1

    # After resolution the pair CAN be re-flagged if the audit still sees it
    # (content drifted back together / reviewer wants a fresh look).
    async with pool.privileged_connection() as conn:
        again = await run_overlap_audit(
            conn, language_id=lang, language_code="ovl", language_name="OVL"
        )
    assert again["pairs_flagged"] == 1


async def test_overlap_audit_writes_change_log_for_both_points(pool, monkeypatch):
    monkeypatch.setattr(generation_admin, "resolve_model", lambda *a, **k: "mock-model")
    monkeypatch.setattr(generation_admin, "estimate_cost_usd", lambda *a, **k: 0.0)
    monkeypatch.setattr(
        "backend.services.generate.get_settings", lambda: _MockSettings()
    )

    lang = await _language(pool, "ovl2")
    a = await _point(pool, lang, "Question words overview")
    b = await _point(pool, lang, "Question formation")

    async with pool.privileged_connection() as conn:
        await run_overlap_audit(
            conn, language_id=lang, language_code="ovl2", language_name="OVL2"
        )
        rows = await conn.fetch(
            "SELECT entity_id::text AS eid FROM content_change_log "
            "WHERE action = 'overlap_flagged' AND language_id = $1",
            lang,
        )
    assert {r["eid"] for r in rows} == {a, b}
