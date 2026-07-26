"""Tiered learner-assessment context: each AI surface gets the depth it
needs — forms rollup for the Gym, reading tier for the Reader, full tier
for the Tutor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from backend.repositories.assessment import (
    get_assessment_summary,
    get_form_struggles,
    pick_struggling_cell,
)

USER = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"
POINT = "22222222-2222-2222-2222-222222222222"


class TestFormStruggles:
    def test_empty_point_list_never_queries(self):
        conn = AsyncMock()
        assert asyncio.run(get_form_struggles(conn, USER, [])) == {}
        conn.fetch.assert_not_awaited()

    def test_rolls_up_by_point_and_cell(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"point_id": POINT, "cell": "vosotros", "seen": 6, "misses": 3,
             "wrong_form": 2, "hint_used": 1},
            {"point_id": POINT, "cell": "yo", "seen": 8, "misses": 1,
             "wrong_form": 0, "hint_used": 0},
        ])
        out = asyncio.run(get_form_struggles(conn, USER, [POINT]))
        assert list(out) == [POINT]
        # Worst-first order is preserved from the query.
        assert [s["cell"] for s in out[POINT]] == ["vosotros", "yo"]
        assert out[POINT][0]["misses"] == 3


class TestPickStrugglingCell:
    def test_picks_the_first_evidenced_cell(self):
        assert pick_struggling_cell([
            {"cell": "tú", "seen": 3, "misses": 1, "wrong_form": 1, "hint_used": 0},
            {"cell": "vosotros", "seen": 5, "misses": 2, "wrong_form": 2, "hint_used": 0},
        ]) == "vosotros"

    def test_no_evidence_returns_none(self):
        assert pick_struggling_cell([]) is None
        assert pick_struggling_cell([
            {"cell": "yo", "seen": 2, "misses": 1, "wrong_form": 0, "hint_used": 0},
        ]) is None


def _tier_patches(weak=None, stats=None, profile=None):
    return (
        patch(
            "backend.repositories.assessment.get_learner_model",
            new=AsyncMock(return_value={
                "known_words": ["gato"], "learned_structures": ["Present tense"],
                "level": "A2", "known_count": 40,
            }),
        ),
        patch(
            "backend.repositories.assessment.get_weak_areas",
            new=AsyncMock(return_value=weak or []),
        ),
        patch(
            "backend.repositories.assessment.get_language_profile",
            new=AsyncMock(return_value={"profile": profile or {}, "session_summary": ""}),
        ),
        patch(
            "backend.repositories.assessment.get_study_stats",
            new=AsyncMock(return_value=stats or {"due_now": 4}),
        ),
    )


class TestAssessmentSummary:
    def test_reading_tier_shape(self):
        weak = [{"word": "ventana"}, {"word": None}]
        profile = {"_active_focus": [{"structure": "ser vs estar"}, "junk"]}
        p1, p2, p3, p4 = _tier_patches(weak=weak, profile=profile)
        with p1, p2 as mock_weak, p3, p4 as mock_stats:
            out = asyncio.run(
                get_assessment_summary(AsyncMock(), USER, LANG, depth="reading")
            )
        assert out["level"] == "A2"
        assert out["weak_words"] == ["ventana"]          # None filtered
        assert out["focus"] == ["ser vs estar"]          # non-dict filtered
        # Reading tier: bounded weak list, NO stats, NO weak-area detail.
        assert mock_weak.await_args.kwargs["limit"] == 6
        assert "study_stats" not in out and "weak_areas" not in out
        mock_stats.assert_not_awaited()

    def test_full_tier_is_a_superset(self):
        weak = [{"word": "ev", "lapses": 2}]
        p1, p2, p3, p4 = _tier_patches(weak=weak)
        with p1, p2 as mock_weak, p3, p4:
            out = asyncio.run(
                get_assessment_summary(AsyncMock(), USER, LANG, depth="full")
            )
        assert mock_weak.await_args.kwargs["limit"] == 12
        assert out["weak_areas"] == weak
        assert out["study_stats"] == {"due_now": 4}
        assert out["known_words"] == ["gato"]            # reading fields ride along

    def test_prefetched_language_profile_skips_the_query(self):
        p1, p2, p3, p4 = _tier_patches()
        with p1, p2, p3 as mock_profile, p4:
            out = asyncio.run(
                get_assessment_summary(
                    AsyncMock(), USER, LANG, depth="full",
                    language_profile={"_active_focus": [{"structure": "cases"}]},
                )
            )
        mock_profile.assert_not_awaited()
        assert out["focus"] == ["cases"]

    def test_writing_baseline_lifts_a_cold_start_level(self):
        # Fresh account: card-derived level is the A1 cold start, but the
        # onboarding writing sample said B1 — the tiers serve B1.
        p1, p2, p3, p4 = _tier_patches()
        with patch(
            "backend.repositories.assessment.get_learner_model",
            new=AsyncMock(return_value={
                "known_words": [], "learned_structures": [],
                "level": "A1", "known_count": 3,
            }),
        ), p2, p3, p4:
            out = asyncio.run(
                get_assessment_summary(
                    AsyncMock(), USER, LANG, depth="reading",
                    language_profile={"_writing_baseline": {"level": "B1"}},
                )
            )
        del p1
        assert out["level"] == "B1"

    def test_earned_card_evidence_outranks_the_baseline(self):
        # Plenty of cards: the level the cards demonstrate wins, and a
        # baseline never LOWERS an earned level either way.
        p1, p2, p3, p4 = _tier_patches()
        with patch(
            "backend.repositories.assessment.get_learner_model",
            new=AsyncMock(return_value={
                "known_words": ["x"], "learned_structures": [],
                "level": "B2", "known_count": 200,
            }),
        ), p2, p3, p4:
            out = asyncio.run(
                get_assessment_summary(
                    AsyncMock(), USER, LANG, depth="reading",
                    language_profile={"_writing_baseline": {"level": "C1"}},
                )
            )
        del p1
        assert out["level"] == "B2"

    def test_unknown_depth_raises(self):
        import pytest

        with pytest.raises(ValueError):
            asyncio.run(get_assessment_summary(AsyncMock(), USER, LANG, depth="forms"))
