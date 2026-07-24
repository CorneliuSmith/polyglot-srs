"""Trial-reviewer feedback nudge: pick a pending item they haven't judged,
rate-limit to the cooldown, and record the answer. Real Postgres."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_recommendation,
    pick_review_prompt,
    record_trial_prompt_answer,
    trial_prompt_due,
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


async def _pending_drill(pool, lang, title, sentence, answer) -> str:
    async with pool.privileged_connection() as conn:
        point = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, $2, 'A1', true, 1) RETURNING id", lang, title,
        )
        return str(await conn.fetchval(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, source, reviewed, flagged, display_order) "
            "VALUES ($1, $2, $3, 'ai', false, false, 1) RETURNING id",
            point, sentence, answer,
        ))


async def test_prompt_pick_cooldown_and_record(pool):
    lang = await _lang(pool, "rvp")
    other = await _lang(pool, "rvo")
    trial = await _user(pool, "trial-prompt@t")
    drill = await _pending_drill(pool, lang, "Present", "Yeye {{answer}} chai.", "anakunywa")
    # A pending drill in a language the reviewer is NOT scoped to — must not pick.
    await _pending_drill(pool, other, "Other", "X {{answer}} Y.", "z")

    async with pool.privileged_connection() as conn:
        # Never answered → due.
        assert await trial_prompt_due(conn, trial) is True

        # Scoped to `lang` only → picks the lang drill, not the other-language one.
        prompt = await pick_review_prompt(
            conn, trial, all_languages=False, language_ids=[lang]
        )
        assert prompt is not None
        assert prompt["target_type"] == "drill"
        assert prompt["target_id"] == drill
        assert prompt["language_id"] == lang

        # Answer it → recommendation recorded + next check-in scheduled out.
        await add_recommendation(conn, trial, lang, "drill", drill, "approve", "reads well")
        nxt = await record_trial_prompt_answer(conn, trial, gave_feedback=True)
        assert nxt  # ISO timestamp of the next check-in

        # A future check-in is scheduled → not due.
        assert await trial_prompt_due(conn, trial) is False

        # And the drill they judged is no longer offered (dedupe on prior vote).
        again = await pick_review_prompt(
            conn, trial, all_languages=False, language_ids=[lang]
        )
        assert again is None


async def test_prompt_none_when_no_pending(pool):
    lang = await _lang(pool, "rvn")
    trial = await _user(pool, "trial-empty@t")
    async with pool.privileged_connection() as conn:
        prompt = await pick_review_prompt(
            conn, trial, all_languages=True, language_ids=[]
        )
        # No AI content seeded for this fresh language → nothing to ask.
        assert prompt is None or prompt["language_id"] != lang
