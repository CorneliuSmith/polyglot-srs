"""Unit tests for FSRS weight resolution + sequence building (DB faked)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.repositories.fsrs_weights import (
    _grade_from_row,
    fetch_review_sequences,
    get_effective_params,
)
from backend.services.fsrs import DEFAULT_PARAMS

USER = "11111111-1111-1111-1111-111111111111"
LANG = "22222222-2222-2222-2222-222222222222"

LANG_W = [0.5] * 19
USER_W = [0.7] * 19


class FakeConn:
    """Minimal asyncpg-like connection returning canned rows from fetch()."""
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, *args, **kwargs):
        return self._rows


class TestGetEffectiveParams:
    @pytest.mark.asyncio
    async def test_prefers_user_over_language(self):
        conn = FakeConn([
            {"scope": "language", "params": LANG_W},
            {"scope": "user_language", "params": USER_W},
        ])
        assert await get_effective_params(conn, USER, LANG) == tuple(USER_W)

    @pytest.mark.asyncio
    async def test_falls_back_to_language(self):
        conn = FakeConn([{"scope": "language", "params": LANG_W}])
        assert await get_effective_params(conn, USER, LANG) == tuple(LANG_W)

    @pytest.mark.asyncio
    async def test_defaults_when_nothing_fit(self):
        conn = FakeConn([])
        assert await get_effective_params(conn, USER, LANG) == DEFAULT_PARAMS


class TestGradeFromRow:
    def test_maps_answer_result(self):
        assert _grade_from_row({"answer_result": "correct", "quality": None}) == 3
        assert _grade_from_row({"answer_result": "correct_sloppy", "quality": None}) == 2
        assert _grade_from_row({"answer_result": "wrong_form", "quality": None}) == 1
        assert _grade_from_row({"answer_result": "wrong", "quality": None}) == 1

    def test_falls_back_to_quality(self):
        assert _grade_from_row({"answer_result": None, "quality": 4}) == 3
        assert _grade_from_row({"answer_result": None, "quality": 2}) == 2
        assert _grade_from_row({"answer_result": None, "quality": 1}) == 1

    def test_none_when_unknown(self):
        assert _grade_from_row({"answer_result": None, "quality": None}) is None


class TestFetchReviewSequences:
    @pytest.mark.asyncio
    async def test_groups_by_card_and_computes_elapsed_days(self):
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [
            # card A: two reviews three days apart
            {"card_id": "A", "created_at": t0, "answer_result": "correct", "quality": 4},
            {"card_id": "A", "created_at": t0 + timedelta(days=3),
             "answer_result": "wrong", "quality": 1},
            # card B: one review
            {"card_id": "B", "created_at": t0, "answer_result": "correct", "quality": 4},
        ]
        seqs = await fetch_review_sequences(FakeConn(rows), LANG)
        assert seqs == [[(0.0, 3), (3.0, 1)], [(0.0, 3)]]
