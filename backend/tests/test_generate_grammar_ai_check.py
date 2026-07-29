"""ai_check_language: the bulk form of the per-point 'Run AI check' button.

An 'ai_ok'-policy language only shows a point once reviewed=true OR
ai_check_status='pass' (see curriculum.get_curriculum). seed_grammar leaves
everything unreviewed, and the only endpoint that sets ai_check_status
checks one point at a time — this is what actually turns a freshly seeded
language's grammar path on.
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.seeder.generate_grammar import ai_check_language


class FakeConn:
    """Enough of asyncpg.Connection for this function's three query shapes."""

    def __init__(self, language_id, points, drills_by_point=None):
        self.language_id = language_id
        self.points = points
        self.drills_by_point = drills_by_point or {}
        self.updates: list[tuple] = []
        self.closed = False

    async def fetchval(self, query, *args):
        assert "SELECT id FROM languages" in query
        return self.language_id

    async def fetch(self, query, *args):
        if "FROM grammar_points" in query:
            return self.points
        if "FROM drill_sentences" in query:
            point_id = args[-1]
            return self.drills_by_point.get(point_id, [])
        raise AssertionError(f"unexpected query: {query}")

    async def execute(self, query, *args):
        assert "UPDATE grammar_points" in query
        self.updates.append(args)
        return "UPDATE 1"

    async def close(self):
        self.closed = True


def _point(id_, title="Some point", explanation="An explanation"):
    return {"id": id_, "title": title, "explanation": explanation}


@pytest.fixture(autouse=True)
def _ai_configured():
    with patch(
        "backend.services.seeder.generate_grammar.ai_available", return_value=True
    ):
        yield


@pytest.mark.asyncio
async def test_checks_every_unchecked_point_and_stores_the_verdict():
    points = [_point("p1", "Point one"), _point("p2", "Point two")]
    conn = FakeConn("lang-1", points)
    verdicts = iter([
        {"status": "pass", "notes": "looks right"},
        {"status": "concerns", "notes": "check the gloss"},
    ])
    with patch("asyncpg.connect",
               new=AsyncMock(return_value=conn)), \
         patch("backend.services.seeder.generate_grammar.semantic_check_point",
               new=AsyncMock(side_effect=lambda *a, **k: next(verdicts))):
        result = await ai_check_language("postgresql://x", "he")

    assert result == {"checked": 2, "passed": 1, "concerns": 1}
    assert len(conn.updates) == 2
    assert conn.updates[0] == ("p1", "pass", "looks right")
    assert conn.updates[1] == ("p2", "concerns", "check the gloss")
    assert conn.closed


@pytest.mark.asyncio
async def test_only_missing_by_default_so_a_halted_run_can_resume():
    points = [_point("p1")]
    conn = FakeConn("lang-1", points)
    with patch("asyncpg.connect",
               new=AsyncMock(return_value=conn)), \
         patch("backend.services.seeder.generate_grammar.semantic_check_point",
               new=AsyncMock(return_value={"status": "pass", "notes": ""})) as check:
        await ai_check_language("postgresql://x", "he")
    assert check.await_count == 1


@pytest.mark.asyncio
async def test_recheck_all_does_not_filter_on_missing():
    conn = FakeConn("lang-1", [_point("p1")])
    captured_queries = []
    original_fetch = conn.fetch

    async def spying_fetch(query, *args):
        captured_queries.append(query)
        return await original_fetch(query, *args)

    conn.fetch = spying_fetch
    with patch("asyncpg.connect",
               new=AsyncMock(return_value=conn)), \
         patch("backend.services.seeder.generate_grammar.semantic_check_point",
               new=AsyncMock(return_value={"status": "pass", "notes": ""})):
        await ai_check_language("postgresql://x", "he", only_missing=False)

    grammar_query = next(q for q in captured_queries if "FROM grammar_points" in q)
    assert "ai_check_status IS NULL" not in grammar_query


@pytest.mark.asyncio
async def test_a_missing_language_raises():
    conn = FakeConn(None, [])
    with patch("asyncpg.connect",
               new=AsyncMock(return_value=conn)):
        with pytest.raises(ValueError, match="not found"):
            await ai_check_language("postgresql://x", "zz")
    assert conn.closed


@pytest.mark.asyncio
async def test_refuses_to_run_with_no_ai_configured():
    with patch(
        "backend.services.seeder.generate_grammar.ai_available", return_value=False
    ):
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            await ai_check_language("postgresql://x", "he")


@pytest.mark.asyncio
async def test_nothing_left_to_check_is_a_clean_no_op():
    conn = FakeConn("lang-1", [])
    with patch("asyncpg.connect",
               new=AsyncMock(return_value=conn)):
        result = await ai_check_language("postgresql://x", "he")
    assert result == {"checked": 0, "passed": 0, "concerns": 0}
    assert conn.closed
