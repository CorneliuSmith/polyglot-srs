"""Tests for the FSRS-5 scheduler (pure, deterministic with fuzz disabled)."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.services.fsrs import (
    DEFAULT_RETENTION,
    NEW,
    RELEARNING,
    REVIEW,
    AnswerResult,
    CardState,
    Rating,
    _interval_from_stability,
    fsrs_review,
    map_answer_to_quality,
    map_answer_to_rating,
    retrievability,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def review(card, rating, elapsed=0.0):
    return fsrs_review(card, rating, elapsed, now=NOW, enable_fuzz=False)


# ── answer → grade / quality mapping ─────────────────────────────────────────

class TestMapping:
    def test_rating_mapping(self):
        assert map_answer_to_rating(AnswerResult.CORRECT) == Rating.GOOD
        assert map_answer_to_rating(AnswerResult.CORRECT_SLOPPY) == Rating.HARD
        # A wrong inflection is a real lapse, like an outright miss.
        assert map_answer_to_rating(AnswerResult.WRONG_FORM) == Rating.AGAIN
        assert map_answer_to_rating(AnswerResult.WRONG) == Rating.AGAIN

    def test_quality_mapping(self):
        assert map_answer_to_quality(AnswerResult.CORRECT) == 4
        assert map_answer_to_quality(AnswerResult.WRONG) == 1


# ── forgetting curve ─────────────────────────────────────────────────────────

class TestRetrievability:
    def test_full_recall_at_zero_elapsed(self):
        assert retrievability(0.0, 10.0) == pytest.approx(1.0)

    def test_monotonic_decreasing(self):
        r0 = retrievability(1, 10)
        r1 = retrievability(5, 10)
        r2 = retrievability(20, 10)
        assert r0 > r1 > r2

    def test_hits_target_retention_at_stability(self):
        # By definition, R falls to the target retention after S days.
        assert retrievability(10.0, 10.0) == pytest.approx(DEFAULT_RETENTION, abs=1e-9)


class TestIntervalFromStability:
    def test_interval_approximates_stability_at_default_retention(self):
        # interval that targets 0.9 retention is ~= stability (within rounding)
        assert _interval_from_stability(30.0, DEFAULT_RETENTION, 36500) == 30

    def test_higher_retention_shortens_interval(self):
        lenient = _interval_from_stability(100.0, 0.85, 36500)
        strict = _interval_from_stability(100.0, 0.95, 36500)
        assert strict < lenient


# ── first review of a new card ───────────────────────────────────────────────

class TestFirstReview:
    def test_initializes_state_and_is_due_in_future(self):
        r = review(CardState(), Rating.GOOD)
        assert r.stability > 0
        assert 1 <= r.difficulty <= 10
        assert r.state == REVIEW
        assert r.interval >= 1
        assert (r.next_review - NOW).days == r.interval  # due now + interval
        assert r.repetitions == 1 and r.streak == 1 and r.lapses == 0

    def test_better_grade_gives_longer_interval(self):
        again = review(CardState(), Rating.AGAIN)
        hard = review(CardState(), Rating.HARD)
        good = review(CardState(), Rating.GOOD)
        easy = review(CardState(), Rating.EASY)
        assert again.stability < hard.stability < good.stability < easy.stability
        assert again.interval <= hard.interval <= good.interval <= easy.interval

    def test_again_on_new_card_counts_as_lapse(self):
        r = review(CardState(), Rating.AGAIN)
        assert r.state == RELEARNING
        assert r.lapses == 1 and r.streak == 0 and r.repetitions == 0
        assert r.interval >= 1  # never schedules in the past


# ── subsequent reviews ───────────────────────────────────────────────────────

def _seen(stability=10.0, difficulty=5.0, reps=3, streak=3, lapses=0):
    return CardState(
        stability=stability, difficulty=difficulty, state=REVIEW,
        repetitions=reps, streak=streak, lapses=lapses,
    )


class TestSubsequentReview:
    def test_success_grows_stability_and_counts(self):
        card = _seen()
        r = review(card, Rating.GOOD, elapsed=10.0)
        assert r.stability > card.stability  # memory strengthened
        assert r.interval >= card_interval(card)
        assert r.repetitions == 4 and r.streak == 4 and r.lapses == 0

    def test_lapse_never_increases_stability(self):
        card = _seen()
        r = review(card, Rating.AGAIN, elapsed=10.0)
        assert 0 < r.stability <= card.stability
        assert r.state == RELEARNING
        assert r.lapses == 1 and r.streak == 0 and r.repetitions == 0

    def test_again_raises_difficulty_easy_lowers_it(self):
        card = _seen(difficulty=5.0)
        harder = review(card, Rating.AGAIN, elapsed=10.0)
        easier = review(card, Rating.EASY, elapsed=10.0)
        assert harder.difficulty > 5.0
        assert easier.difficulty < 5.0

    def test_difficulty_stays_in_bounds(self):
        # Repeated failures must not push difficulty past 10.
        card = _seen(difficulty=9.8)
        for _ in range(20):
            r = review(card, Rating.AGAIN, elapsed=5.0)
            card = CardState(
                stability=r.stability, difficulty=r.difficulty, state=REVIEW,
                repetitions=r.repetitions, streak=r.streak, lapses=r.lapses,
            )
            assert 1.0 <= r.difficulty <= 10.0

    def test_deterministic_without_fuzz(self):
        card = _seen()
        a = review(card, Rating.GOOD, elapsed=10.0)
        b = review(card, Rating.GOOD, elapsed=10.0)
        assert a == b

    def test_unseen_state_treats_card_as_new(self):
        # stability/difficulty None but state left at default 'new'
        card = CardState(state=NEW)
        r = review(card, Rating.GOOD)
        assert r.stability > 0 and r.state == REVIEW


def card_interval(card: CardState) -> int:
    return _interval_from_stability(card.stability, DEFAULT_RETENTION, 36500)
