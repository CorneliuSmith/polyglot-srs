"""FSRS-5 spaced-repetition scheduler.

Pure functions, no database — trivially testable and reusable. Replaces the
previous SM-2 scheduler.

FSRS (Free Spaced Repetition Scheduler) models each card with two latent
variables:

* **stability** (S) — the number of days until the probability of recall decays
  to the requested retention (default 0.9). Bigger S ⇒ longer intervals.
* **difficulty** (D) — 1 (easy) .. 10 (hard); harder cards gain stability more
  slowly.

After each review it updates S and D from the grade and the card's current
*retrievability* (how likely recall was at review time), then schedules the next
review at the interval that lands on the target retention. This adapts to each
card's real memory curve far better than SM-2's single ease factor.

Reference: open-spaced-repetition, FSRS-5 (19 parameters).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import IntEnum

from backend.services.nlp.base import AnswerResult  # noqa: F401 — re-exported

# FSRS-5 default parameters (w0..w18) — the optimizer's priors, used until a
# learner has enough review history to fit personalized weights.
DEFAULT_PARAMS: tuple[float, ...] = (
    0.40255, 1.18385, 3.173, 15.69105, 7.1949, 0.5345, 1.4604, 0.0046,
    1.54575, 0.1192, 1.01925, 1.9395, 0.11, 0.29605, 2.2698, 0.2315,
    2.9898, 0.51655, 0.6621,
)

# Forgetting curve: R(t) = (1 + FACTOR * t / S) ** DECAY
DECAY: float = -0.5
FACTOR: float = 0.9 ** (1.0 / DECAY) - 1.0  # == 19/81

DEFAULT_RETENTION: float = 0.9
MIN_INTERVAL: int = 1
MAX_INTERVAL: int = 36500  # ~100 years

MIN_DIFFICULTY: float = 1.0
MAX_DIFFICULTY: float = 10.0
MIN_STABILITY: float = 0.01


class Rating(IntEnum):
    """The four FSRS grades."""
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


# Learning-state labels stored on user_cards.state.
NEW = "new"
REVIEW = "review"
RELEARNING = "relearning"


# How the app's answer judgements map to FSRS grades. A wrong inflection
# (WRONG_FORM) is a genuine lapse — it forgets the form — so it grades AGAIN,
# matching the old SM-2 mapping where it was a failure.
ANSWER_TO_RATING: dict[AnswerResult, Rating] = {
    AnswerResult.CORRECT: Rating.GOOD,
    AnswerResult.CORRECT_SLOPPY: Rating.HARD,
    AnswerResult.WRONG_FORM: Rating.AGAIN,
    AnswerResult.WRONG: Rating.AGAIN,
}

# Retained for the review_log.quality analytics column (0–5 scale).
QUALITY_MAP: dict[AnswerResult, int] = {
    AnswerResult.CORRECT: 4,
    AnswerResult.CORRECT_SLOPPY: 3,
    AnswerResult.WRONG_FORM: 2,
    AnswerResult.WRONG: 1,
}


def map_answer_to_rating(result: AnswerResult) -> Rating:
    """Convert an AnswerResult to the FSRS grade used for scheduling."""
    return ANSWER_TO_RATING[result]


def map_answer_to_quality(result: AnswerResult) -> int:
    """Convert an AnswerResult to the 1–4 quality stored in review_log."""
    return QUALITY_MAP[result]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class CardState:
    """A card's FSRS memory state before a review.

    stability/difficulty are None for a card that has never been reviewed; the
    first review initializes them from the grade.
    """
    stability: float | None = None
    difficulty: float | None = None
    state: str = NEW
    repetitions: int = 0
    streak: int = 0
    lapses: int = 0


@dataclass
class FSRSUpdate:
    """Result of fsrs_review — the card's new state and when it's next due."""
    stability: float
    difficulty: float
    state: str
    interval: int
    repetitions: int
    streak: int
    lapses: int
    next_review: datetime


# ---------------------------------------------------------------------------
# Core equations
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def retrievability(elapsed_days: float, stability: float) -> float:
    """Probability of recall after *elapsed_days* given *stability*."""
    if stability <= 0:
        return 0.0
    return (1.0 + FACTOR * elapsed_days / stability) ** DECAY


def _interval_from_stability(
    stability: float, retention: float, maximum_interval: int
) -> int:
    """Days until recall probability falls to *retention* (whole days)."""
    ivl = (stability / FACTOR) * (retention ** (1.0 / DECAY) - 1.0)
    return int(_clamp(round(ivl), MIN_INTERVAL, maximum_interval))


def _init_difficulty(w: tuple[float, ...], rating: int) -> float:
    return _clamp(
        w[4] - math.exp(w[5] * (rating - 1)) + 1.0, MIN_DIFFICULTY, MAX_DIFFICULTY
    )


def _init_stability(w: tuple[float, ...], rating: int) -> float:
    return max(w[rating - 1], MIN_STABILITY)


def _next_difficulty(w: tuple[float, ...], difficulty: float, rating: int) -> float:
    # Linear damping toward the bounds (FSRS-5), then mean-reversion toward the
    # difficulty an Easy first answer would have produced.
    delta = -w[6] * (rating - 3)
    damped = difficulty + delta * (10.0 - difficulty) / 9.0
    reverted = w[7] * _init_difficulty(w, Rating.EASY) + (1.0 - w[7]) * damped
    return _clamp(reverted, MIN_DIFFICULTY, MAX_DIFFICULTY)


def _stability_on_recall(
    w: tuple[float, ...], difficulty: float, stability: float, r: float, rating: int
) -> float:
    hard_penalty = w[15] if rating == Rating.HARD else 1.0
    easy_bonus = w[16] if rating == Rating.EASY else 1.0
    return stability * (
        1.0
        + math.exp(w[8])
        * (11.0 - difficulty)
        * (stability ** -w[9])
        * (math.exp(w[10] * (1.0 - r)) - 1.0)
        * hard_penalty
        * easy_bonus
    )


def _stability_on_forget(
    w: tuple[float, ...], difficulty: float, stability: float, r: float
) -> float:
    forget = (
        w[11]
        * (difficulty ** -w[12])
        * ((stability + 1.0) ** w[13] - 1.0)
        * math.exp(w[14] * (1.0 - r))
    )
    # A lapse must never increase stability.
    return min(forget, stability)


# Graduated interval fuzz (FSRS reference ranges) to prevent review pile-ups.
_FUZZ_RANGES: tuple[tuple[float, float, float], ...] = (
    (2.5, 7.0, 0.15),
    (7.0, 20.0, 0.10),
    (20.0, math.inf, 0.05),
)


def _fuzz(interval: int, maximum_interval: int) -> int:
    if interval < 2.5:
        return interval
    delta = 1.0
    for start, end, factor in _FUZZ_RANGES:
        delta += factor * max(min(interval, end) - start, 0.0)
    lo = max(2, round(interval - delta))
    hi = min(round(interval + delta), maximum_interval)
    lo = min(lo, hi)
    return random.randint(lo, hi)


def fsrs_review(
    card: CardState,
    rating: Rating,
    elapsed_days: float = 0.0,
    *,
    now: datetime | None = None,
    retention: float = DEFAULT_RETENTION,
    maximum_interval: int = MAX_INTERVAL,
    params: tuple[float, ...] = DEFAULT_PARAMS,
    enable_fuzz: bool = True,
) -> FSRSUpdate:
    """Apply one FSRS review and return the next state + due date.

    Args:
        card: the card's current memory state.
        rating: the FSRS grade for this review.
        elapsed_days: days since the card's last review (0 for a first review).
        now: review time (defaults to UTC now); next_review = now + interval.
        retention: target probability of recall the interval aims for.
        maximum_interval: hard cap on the interval in days.
        params: FSRS weights.
        enable_fuzz: apply interval fuzz (disable for deterministic tests).
    """
    now = now or datetime.now(UTC)
    w = params
    is_lapse = rating == Rating.AGAIN

    if card.stability is None or card.difficulty is None or card.state == NEW:
        # First review: seed stability and difficulty from the grade.
        stability = _init_stability(w, rating)
        difficulty = _init_difficulty(w, rating)
    else:
        r = retrievability(max(0.0, elapsed_days), card.stability)
        difficulty = _next_difficulty(w, card.difficulty, rating)
        if is_lapse:
            stability = _stability_on_forget(w, card.difficulty, card.stability, r)
        else:
            stability = _stability_on_recall(
                w, card.difficulty, card.stability, r, rating
            )

    stability = max(stability, MIN_STABILITY)

    if is_lapse:
        repetitions, streak, lapses, state = 0, 0, card.lapses + 1, RELEARNING
    else:
        repetitions = card.repetitions + 1
        streak = card.streak + 1
        lapses = card.lapses
        state = REVIEW

    interval = _interval_from_stability(stability, retention, maximum_interval)
    if enable_fuzz:
        interval = _fuzz(interval, maximum_interval)

    return FSRSUpdate(
        stability=round(stability, 6),
        difficulty=round(difficulty, 6),
        state=state,
        interval=interval,
        repetitions=repetitions,
        streak=streak,
        lapses=lapses,
        next_review=now + timedelta(days=interval),
    )
