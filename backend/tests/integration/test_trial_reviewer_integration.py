"""Trial (advisory) reviewers: gating, recommendations, and activity."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_recommendation,
    can_review,
    can_trial_review,
    recommendations_for_targets,
    trial_reviewer_activity,
)

from .conftest import requires_db

pytestmark = requires_db


async def _language(pool, code: str) -> str:
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


async def _grant(pool, user_id: str, language_id: str, role: str) -> None:
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, language_id, role) "
            "VALUES ($1, $2, $3)",
            user_id, language_id, role,
        )


def _roles(language_id: str, role: str) -> list[dict]:
    return [{"role": role, "language_id": language_id}]


def test_trial_reviewer_can_review_but_not_publish():
    lang = "11111111-1111-1111-1111-111111111111"
    trial = _roles(lang, "trial_reviewer")
    assert can_trial_review(trial, lang) is True
    assert can_review(trial, lang) is False  # advisory only, no publish
    full = _roles(lang, "reviewer")
    assert can_trial_review(full, lang) is True
    assert can_review(full, lang) is True


async def test_recommendations_tally_and_activity(pool):
    lang = await _language(pool, "trv")
    alice = await _user(pool, "alice-trial@t")
    bob = await _user(pool, "bob-trial@t")
    await _grant(pool, alice, lang, "trial_reviewer")
    await _grant(pool, bob, lang, "trial_reviewer")

    # A pending drill to recommend on.
    async with pool.privileged_connection() as conn:
        point = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, display_order) "
            "VALUES ($1, 'P', true, 1) RETURNING id", lang,
        )
        drill = str(await conn.fetchval(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, source, reviewed, display_order) "
            "VALUES ($1, 'a {{answer}} b', 'x', 'ai', false, 1) RETURNING id", point,
        ))

        await add_recommendation(conn, alice, lang, "drill", drill, "approve", "reads well")
        await add_recommendation(conn, bob, lang, "drill", drill, "reject", "unnatural")
        # Alice changes her mind — upsert, not a second row.
        await add_recommendation(conn, alice, lang, "drill", drill, "reject", "on reflection, no")

        tally = await recommendations_for_targets(conn, "drill", [drill])
        assert tally[drill]["approve"] == 0
        assert tally[drill]["reject"] == 2
        assert len(tally[drill]["notes"]) == 2

        activity = await trial_reviewer_activity(conn, lang)
        by_email = {a["email"]: a for a in activity}
        assert by_email["alice-trial@t"]["recommendations"] == 1
        assert by_email["bob-trial@t"]["recommendations"] == 1
