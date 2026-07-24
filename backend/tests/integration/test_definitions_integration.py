"""Definitions gap-fill: gap-list → maker-check → gate (queue vs ai_ok apply) →
reviewer approve lands it in `translations`. Real Postgres, generator mocked."""
from __future__ import annotations

from backend.repositories.contributor import (
    apply_definition,
    list_translation_reviews,
    queue_definition_review,
    resolve_translation_review,
    vocab_needing_definition,
)

from .conftest import requires_db

pytestmark = requires_db


async def _language(pool, code: str, policy: str = "strict") -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, grammar_review_policy) "
            "VALUES ($1, $2, false, $3) ON CONFLICT (code) DO UPDATE SET "
            "grammar_review_policy = EXCLUDED.grammar_review_policy RETURNING id",
            code, code.upper(), policy,
        ))


async def _word(pool, language_id: str, word: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word) VALUES ($1, $2) RETURNING id",
            language_id, word,
        ))


async def _definition(pool, vocabulary_id: str, locale: str = "en") -> str | None:
    async with pool.privileged_connection() as conn:
        return await conn.fetchval(
            "SELECT definition FROM translations "
            "WHERE vocabulary_id = $1 AND locale = $2",
            vocabulary_id, locale,
        )


async def test_gap_list_gate_and_approval(pool):
    lang = await _language(pool, "dfn", "strict")
    w_defined = await _word(pool, lang, "ndio")
    w_gap = await _word(pool, lang, "kupanga")

    async with pool.privileged_connection() as conn:
        # Give one word a definition; it should drop out of the gap list.
        await apply_definition(conn, w_defined, "en", "yes")
        gap = await vocab_needing_definition(conn, lang, "en", 50)
        assert [g["vocabulary_id"] for g in gap] == [w_gap]

        # Strict policy → the AI definition is QUEUED, not applied.
        await queue_definition_review(conn, w_gap, "en", "to arrange", "looks good")
        assert await _word_pending(conn, w_gap) is True
        # Queued word no longer appears as a gap (won't be re-generated).
        assert await vocab_needing_definition(conn, lang, "en", 50) == []
        # Still no live definition until a human approves.
    assert await _definition(pool, w_gap) is None

    async with pool.privileged_connection() as conn:
        reviews = await list_translation_reviews(conn)
        review = next(r for r in reviews if r["word"] == "kupanga")
        assert review["proposed"] == "to arrange"
        # Approve → lands in translations at the row's locale.
        assert await resolve_translation_review(conn, review["id"], approve=True) == "ok"
    assert await _definition(pool, w_gap) == "to arrange"


async def _word_pending(conn, vocabulary_id: str) -> bool:
    return bool(await conn.fetchval(
        "SELECT 1 FROM translation_reviews "
        "WHERE vocabulary_id = $1 AND status = 'pending'",
        vocabulary_id,
    ))


async def test_ai_ok_policy_applies_definition_directly(pool):
    lang = await _language(pool, "dfk", "ai_ok")
    w = await _word(pool, lang, "haraka")
    # The ai_ok path writes straight to translations (what _run_definitions does
    # when policy == 'ai_ok').
    async with pool.privileged_connection() as conn:
        assert await apply_definition(conn, w, "en", "quickly") is True
    assert await _definition(pool, w) == "quickly"


class _MockSettings:
    tutor_dev_mock = True
    anthropic_api_key = ""


async def test_run_definitions_orchestration(pool, monkeypatch):
    """The CLI _run_definitions end to end: strict queues, ai_ok applies."""
    from types import SimpleNamespace

    from backend.services.seeder import generate_content

    monkeypatch.setattr(
        "backend.services.define.get_settings", lambda: _MockSettings()
    )
    args = SimpleNamespace(locale="en", max=50, dry_run=False)

    # Strict: mock rejects item 0, passes item 1 → both queued (none live).
    strict = await _language(pool, "dfo", "strict")
    ws = [await _word(pool, strict, w) for w in ("alfa", "beta")]
    async with pool.privileged_connection() as conn:
        lang = await conn.fetchrow(
            "SELECT id, code, name FROM languages WHERE id = $1", strict
        )
        await generate_content._run_definitions(conn, lang, args)
    for w in ws:
        assert await _definition(pool, w) is None  # nothing live under strict
    async with pool.privileged_connection() as conn:
        assert len(await list_translation_reviews(conn)) >= 2

    # ai_ok: the checker-passed word goes live immediately.
    aiok = await _language(pool, "dfp", "ai_ok")
    wa = [await _word(pool, aiok, w) for w in ("gamma", "delta")]
    async with pool.privileged_connection() as conn:
        lang = await conn.fetchrow(
            "SELECT id, code, name FROM languages WHERE id = $1", aiok
        )
        await generate_content._run_definitions(conn, lang, args)
    # The mock passes one word (applied live) and rejects the other (queued);
    # the gap list is alphabetical, so assert by outcome, not insertion order.
    defs = [await _definition(pool, w) for w in wa]
    live = [d for d in defs if d]
    assert len(live) == 1 and live[0].startswith("meaning of")
    assert defs.count(None) == 1
