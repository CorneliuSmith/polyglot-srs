"""AI content policy: a language's grammar_review_policy='ai_ok' serves verified
AI drills / example sentences to learners; 'strict' keeps them hidden."""
from __future__ import annotations

from backend.repositories.cards import get_cram_cards

from .conftest import requires_db

pytestmark = requires_db


async def _setup(pool, policy: str):
    """A language (with the given policy), a reviewed grammar point, and ONE
    unreviewed AI drill on it. Returns (user_id, point_id)."""
    async with pool.privileged_connection() as conn:
        lang = await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, grammar_review_policy) "
            "VALUES ($1, $2, false, $3) "
            "ON CONFLICT (code) DO UPDATE SET grammar_review_policy = EXCLUDED.grammar_review_policy "
            "RETURNING id",
            f"pt{policy[:2]}", "PolTest", policy,
        )
        point = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, display_order) "
            "VALUES ($1, 'Test point', true, 1) RETURNING id",
            lang,
        )
        await conn.fetchval(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, source, reviewed, display_order) "
            "VALUES ($1, 'Ich {{answer}} hier.', 'bin', 'ai', false, 1) RETURNING id",
            point,
        )
        user = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id",
            f"pass-{policy}@t",
        )
    return str(user), str(point)


async def test_strict_hides_unreviewed_ai_drills(pool):
    user, point = await _setup(pool, "strict")
    async with pool.rls_connection(user) as conn:
        cards = await get_cram_cards(conn, [point], user_id=user)
    assert cards == []  # the AI drill is pending → not served


async def test_ai_ok_serves_verified_ai_drills(pool):
    user, point = await _setup(pool, "ai_ok")
    async with pool.rls_connection(user) as conn:
        cards = await get_cram_cards(conn, [point], user_id=user)
    assert len(cards) == 1  # policy lets the verified AI drill through
    assert cards[0]["correct_answer"] == "bin"
