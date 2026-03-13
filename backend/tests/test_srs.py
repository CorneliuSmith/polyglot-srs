"""
Comprehensive SM-2 SRS algorithm unit tests.

Tests cover:
- Basic SM-2 scheduling (SRS-01)
- Card state tracking (SRS-02)
- Failed review reset (SRS-03)
- Ease floor enforcement (SRS-02)
- Ease recovery
- Quality auto-mapping
- Interval fuzzing
- Review log / next_review support (SRS-04 prep)
- Due card ordering (SRS-05 prep)
"""
import pytest
from datetime import timezone, timedelta, datetime

from backend.services.srs import (
    CardState,
    SRSUpdate,
    AnswerResult,
    QUALITY_MAP,
    sm2_update,
    map_answer_to_quality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh_card(**kwargs) -> CardState:
    """Return a CardState with defaults overridden by kwargs."""
    defaults = dict(ease_factor=2.5, interval=1, repetitions=0, streak=0, lapses=0)
    defaults.update(kwargs)
    return CardState(**defaults)


# ---------------------------------------------------------------------------
# Basic SM-2 scheduling (SRS-01)
# ---------------------------------------------------------------------------

class TestBasicScheduling:
    def test_first_review_correct(self):
        """quality=4 on fresh card -> interval=1, repetitions=1."""
        state = fresh_card()
        result = sm2_update(state, quality=4)
        assert result.repetitions == 1
        assert result.interval == 1

    def test_second_review_correct(self):
        """repetitions=1, quality=4 -> interval=6, repetitions=2."""
        state = fresh_card(repetitions=1, interval=1)
        result = sm2_update(state, quality=4)
        assert result.repetitions == 2
        assert result.interval == 6

    def test_third_review_correct(self):
        """repetitions=2, interval=6, ease=2.5, quality=4 -> interval=15, repetitions=3."""
        state = fresh_card(repetitions=2, interval=6, ease_factor=2.5)
        result = sm2_update(state, quality=4)
        assert result.repetitions == 3
        # round(6 * 2.5) = 15 (before fuzzing; fuzzing only applies if interval > 2)
        # After fuzzing interval=15 is > 2 so it may vary slightly; we check approximate
        assert 14 <= result.interval <= 16

    def test_quality_5_increases_ease(self):
        """quality=5 on card with ease=2.5 -> ease > 2.5."""
        state = fresh_card(ease_factor=2.5)
        result = sm2_update(state, quality=5)
        assert result.ease_factor > 2.5

    def test_quality_3_decreases_ease(self):
        """quality=3 on card with ease=2.5 -> ease < 2.5."""
        state = fresh_card(ease_factor=2.5)
        result = sm2_update(state, quality=3)
        assert result.ease_factor < 2.5


# ---------------------------------------------------------------------------
# Card state defaults (SRS-02)
# ---------------------------------------------------------------------------

class TestCardStateDefaults:
    def test_card_state_defaults(self):
        """Fresh CardState has ease=2.5, interval=1, repetitions=0, streak=0, lapses=0."""
        state = CardState()
        assert state.ease_factor == 2.5
        assert state.interval == 1
        assert state.repetitions == 0
        assert state.streak == 0
        assert state.lapses == 0

    def test_srs_update_has_all_fields(self):
        """SRSUpdate contains ease_factor, interval, repetitions, streak, lapses, next_review."""
        state = fresh_card()
        result = sm2_update(state, quality=4)
        assert hasattr(result, "ease_factor")
        assert hasattr(result, "interval")
        assert hasattr(result, "repetitions")
        assert hasattr(result, "streak")
        assert hasattr(result, "lapses")
        assert hasattr(result, "next_review")


# ---------------------------------------------------------------------------
# Failed review reset (SRS-03)
# ---------------------------------------------------------------------------

class TestFailedReview:
    def test_failed_review_resets(self):
        """quality=1 on card with repetitions=5, interval=30 -> repetitions=0, interval=1."""
        state = fresh_card(repetitions=5, interval=30)
        result = sm2_update(state, quality=1)
        assert result.repetitions == 0
        assert result.interval == 1

    def test_failed_review_increments_lapses(self):
        """quality=2 on card with lapses=2 -> lapses=3."""
        state = fresh_card(lapses=2)
        result = sm2_update(state, quality=2)
        assert result.lapses == 3

    def test_failed_review_resets_streak(self):
        """quality=1 on card with streak=7 -> streak=0."""
        state = fresh_card(streak=7)
        result = sm2_update(state, quality=1)
        assert result.streak == 0

    def test_quality_2_is_failure(self):
        """quality=2 is treated as failure (repetitions reset, interval=1)."""
        state = fresh_card(repetitions=3, interval=15)
        result = sm2_update(state, quality=2)
        assert result.repetitions == 0
        assert result.interval == 1


# ---------------------------------------------------------------------------
# Ease floor (SRS-02)
# ---------------------------------------------------------------------------

class TestEaseFloor:
    def test_ease_floor_enforced(self):
        """Repeated quality=1 reviews never drop ease below 1.3."""
        state = fresh_card(ease_factor=1.5)
        for _ in range(10):
            result = sm2_update(state, quality=1)
            state = CardState(
                ease_factor=result.ease_factor,
                interval=result.interval,
                repetitions=result.repetitions,
                streak=result.streak,
                lapses=result.lapses,
            )
            assert state.ease_factor >= 1.3

    def test_ease_floor_1_3_exact(self):
        """After many failures, ease is exactly 1.3 (not lower)."""
        state = fresh_card(ease_factor=1.4)
        for _ in range(20):
            result = sm2_update(state, quality=1)
            state = CardState(
                ease_factor=result.ease_factor,
                interval=result.interval,
                repetitions=result.repetitions,
                streak=result.streak,
                lapses=result.lapses,
            )
        assert state.ease_factor == 1.3


# ---------------------------------------------------------------------------
# Ease recovery
# ---------------------------------------------------------------------------

class TestEaseRecovery:
    def test_no_recovery_below_threshold(self):
        """4 consecutive correct (streak=4) with ease=1.3 -> ease stays at 1.3."""
        state = fresh_card(ease_factor=1.3, repetitions=4, streak=4)
        result = sm2_update(state, quality=4)
        # SM-2 formula for q=4: ease + 0.1 - (5-4)*(0.08 + (5-4)*0.02) = ease + 0.1 - 0.1 = ease
        # So ease stays at 1.3 (no recovery below threshold of 5)
        assert result.ease_factor == 1.3

    def test_recovery_at_threshold(self):
        """5 consecutive correct (streak=5, quality=4) with ease=1.3 -> ease > 1.3."""
        state = fresh_card(ease_factor=1.3, repetitions=5, streak=5)
        result = sm2_update(state, quality=4)
        assert result.ease_factor > 1.3

    def test_recovery_nudges_toward_target(self):
        """Ease recovery increments by 0.05 at threshold."""
        state = fresh_card(ease_factor=1.3, repetitions=5, streak=5)
        result = sm2_update(state, quality=4)
        # q=4 SM-2 formula gives +0.0 change, then recovery adds 0.05
        assert result.ease_factor == pytest.approx(1.35, abs=1e-9)

    def test_recovery_stops_at_target(self):
        """Card with ease=2.48 and streak=5 -> ease becomes 2.5 (not higher)."""
        state = fresh_card(ease_factor=2.48, repetitions=5, streak=5)
        result = sm2_update(state, quality=4)
        assert result.ease_factor == pytest.approx(2.5, abs=1e-9)


# ---------------------------------------------------------------------------
# Quality auto-mapping
# ---------------------------------------------------------------------------

class TestQualityMapping:
    def test_correct_maps_to_4(self):
        """AnswerResult.CORRECT -> quality 4."""
        assert map_answer_to_quality(AnswerResult.CORRECT) == 4

    def test_sloppy_maps_to_3(self):
        """AnswerResult.CORRECT_SLOPPY -> quality 3."""
        assert map_answer_to_quality(AnswerResult.CORRECT_SLOPPY) == 3

    def test_wrong_form_maps_to_2(self):
        """AnswerResult.WRONG_FORM -> quality 2."""
        assert map_answer_to_quality(AnswerResult.WRONG_FORM) == 2

    def test_wrong_maps_to_1(self):
        """AnswerResult.WRONG -> quality 1."""
        assert map_answer_to_quality(AnswerResult.WRONG) == 1


# ---------------------------------------------------------------------------
# Interval fuzzing
# ---------------------------------------------------------------------------

class TestIntervalFuzzing:
    def test_interval_fuzzed_for_large_intervals(self, fixed_seed):
        """interval > 2 gets +/- 5% fuzzing (run 100 times, verify not all identical)."""
        state = fresh_card(repetitions=2, interval=10, ease_factor=2.5)
        intervals = set()
        for _ in range(100):
            result = sm2_update(state, quality=4)
            intervals.add(result.interval)
        assert len(intervals) > 1, "Intervals should vary due to fuzzing"

    def test_no_fuzz_for_small_intervals(self, fixed_seed):
        """interval <= 2 is not fuzzed (repetitions=0 -> interval=1)."""
        state = fresh_card(repetitions=0)
        intervals = set()
        for _ in range(20):
            result = sm2_update(state, quality=4)
            intervals.add(result.interval)
        assert len(intervals) == 1, "Small intervals should not be fuzzed"

    def test_fuzzed_interval_never_below_1(self, fixed_seed):
        """Even with fuzzing, interval >= 1."""
        state = fresh_card(repetitions=2, interval=3, ease_factor=1.3)
        for _ in range(100):
            result = sm2_update(state, quality=4)
            assert result.interval >= 1


# ---------------------------------------------------------------------------
# Review log support (SRS-04 prep)
# ---------------------------------------------------------------------------

class TestNextReview:
    def test_srs_update_contains_next_review(self):
        """next_review is a timezone-aware datetime in the future."""
        state = fresh_card()
        before = datetime.now(timezone.utc)
        result = sm2_update(state, quality=4)
        assert result.next_review.tzinfo is not None
        assert result.next_review > before


# ---------------------------------------------------------------------------
# Due card ordering (SRS-05 prep)
# ---------------------------------------------------------------------------

class TestDueOrdering:
    def test_next_review_increases_with_interval(self):
        """Higher interval -> further out next_review."""
        state_short = fresh_card(repetitions=1, interval=1)
        state_long = fresh_card(repetitions=2, interval=30, ease_factor=2.5)

        result_short = sm2_update(state_short, quality=4)
        result_long = sm2_update(state_long, quality=4)

        assert result_long.next_review > result_short.next_review
