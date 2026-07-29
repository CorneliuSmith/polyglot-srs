"""Publish policy + staff bypass, against a real database."""
import pytest
from backend.repositories.curriculum import get_curriculum
from backend.tests.integration.conftest import requires_db

pytestmark = requires_db


async def _setup(pool, code, policy):
    async with pool.privileged_connection() as conn:
        lang = await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, grammar_review_policy) "
            "VALUES ($1,$2,false,$3) ON CONFLICT (code) DO UPDATE "
            "SET grammar_review_policy = EXCLUDED.grammar_review_policy RETURNING id",
            code, code.upper(), policy)
        await conn.execute("DELETE FROM grammar_points WHERE language_id = $1", lang)
        for title, reviewed, ai in [
            ("raw", False, None), ("ai-passed", False, "pass"),
            ("human", True, None), ("both", True, "pass"),
        ]:
            await conn.execute(
                "INSERT INTO grammar_points (language_id,title,level,display_order,"
                "explanation,reviewed,ai_check_status) VALUES ($1,$2,'A1',1,'x',$3,$4)",
                lang, title, reviewed, ai)
        learner = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id",
            f"vis-learner-{code}@t")
        reviewer = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id",
            f"vis-reviewer-{code}@t")
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, role, language_id) "
            "VALUES ($1,'reviewer',$2)", reviewer, lang)
    return str(lang), str(learner), str(reviewer)


async def _titles(pool, user, lang):
    async with pool.rls_connection(user) as conn:
        return sorted(p["title"] for p in await get_curriculum(conn, user, lang))


@pytest.mark.parametrize("policy,expected", [
    ("human_only", ["both", "human"]),
    ("strict",     ["both", "human"]),          # legacy spelling
    ("ai_ok",      ["ai-passed", "both", "human"]),
    ("both",       ["both"]),
    ("all",        ["ai-passed", "both", "human", "raw"]),
])
async def test_policy_draws_the_line(pool, policy, expected):
    lang, learner, _ = await _setup(pool, f"z{policy[:3]}", policy)
    assert await _titles(pool, learner, lang) == expected


async def test_reviewer_sees_what_the_learner_cannot(pool):
    lang, learner, reviewer = await _setup(pool, "zrv", "human_only")
    assert await _titles(pool, learner, lang) == ["both", "human"]
    # The whole point of having reviewers: unpublished work is visible to
    # them, and only to them, until it is promoted.
    assert await _titles(pool, reviewer, lang) == [
        "ai-passed", "both", "human", "raw"]
