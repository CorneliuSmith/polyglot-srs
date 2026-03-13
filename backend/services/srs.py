"""
SM-2 Spaced Repetition Algorithm implementation.

Pure functions with no database dependency — trivially testable and reusable.
Includes ease recovery, quality auto-mapping, and interval fuzzing.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EASE_FLOOR: float = 1.3
"""Minimum ease factor — ease never drops below this value."""

EASE_RECOVERY_THRESHOLD: int = 5
"""Consecutive correct answers required to trigger ease recovery."""

EASE_RECOVERY_INCREMENT: float = 0.05
"""Amount ease increases per review during recovery."""

EASE_TARGET: float = 2.5
"""Target ease factor for recovery; recovery stops when reached."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AnswerResult(Enum):
    """User answer quality categories.

    This is a LOCKED DECISION — values map directly to SM-2 quality scores
    via QUALITY_MAP and must not be changed without updating dependent code.
    """
    CORRECT = "correct"
    CORRECT_SLOPPY = "correct_sloppy"
    WRONG_FORM = "wrong_form"
    WRONG = "wrong"


# ---------------------------------------------------------------------------
# Quality mapping (LOCKED DECISION)
# ---------------------------------------------------------------------------

QUALITY_MAP: dict[AnswerResult, int] = {
    AnswerResult.CORRECT: 4,
    AnswerResult.CORRECT_SLOPPY: 3,
    AnswerResult.WRONG_FORM: 2,
    AnswerResult.WRONG: 1,
}
"""Maps AnswerResult enum values to SM-2 quality integers (1–5).

LOCKED DECISION: CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1.
"""


def map_answer_to_quality(result: AnswerResult) -> int:
    """Convert an AnswerResult to its SM-2 quality integer.

    Args:
        result: The answer result from user input validation.

    Returns:
        Integer quality score in range 1–4.
    """
    return QUALITY_MAP[result]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CardState:
    """Current SRS state of a flashcard.

    Attributes:
        ease_factor: Ease factor (EF), starts at 2.5, floor at 1.3.
        interval: Current review interval in days.
        repetitions: Number of successful consecutive reviews.
        streak: Consecutive correct answers (used for ease recovery).
        lapses: Total number of failed reviews ever.
    """
    ease_factor: float = 2.5
    interval: int = 1
    repetitions: int = 0
    streak: int = 0
    lapses: int = 0


@dataclass
class SRSUpdate:
    """Result of applying sm2_update to a CardState.

    Attributes:
        ease_factor: Updated ease factor.
        interval: Updated review interval in days.
        repetitions: Updated repetitions count.
        streak: Updated streak count.
        lapses: Updated lapse count.
        next_review: Timezone-aware UTC datetime for next review.
    """
    ease_factor: float
    interval: int
    repetitions: int
    streak: int
    lapses: int
    next_review: datetime


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def sm2_update(state: CardState, quality: int) -> SRSUpdate:
    """Apply the SM-2 algorithm to produce the next card state.

    Implements SuperMemo 2 with the following extensions:
    - Ease floor: ease_factor never drops below EASE_FLOOR (1.3).
    - Ease recovery: after EASE_RECOVERY_THRESHOLD consecutive correct
      answers, ease nudges toward EASE_TARGET by EASE_RECOVERY_INCREMENT
      per review (capped at EASE_TARGET).
    - Interval fuzzing: intervals > 2 days are randomly adjusted by ±5%
      to prevent review clustering. Result is always >= 1.
    - next_review: computed as UTC now + interval days.

    Args:
        state: Current card state.
        quality: SM-2 quality score (1–5; scores < 3 are failures).

    Returns:
        SRSUpdate with the new card state and next review datetime.
    """
    ease = state.ease_factor
    interval = state.interval
    repetitions = state.repetitions
    streak = state.streak
    lapses = state.lapses

    if quality >= 3:
        # --- Success path ---
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease)

        new_repetitions = repetitions + 1
        new_streak = streak + 1
        new_lapses = lapses
    else:
        # --- Failure path ---
        new_interval = 1
        new_repetitions = 0
        new_streak = 0
        new_lapses = lapses + 1

    # SM-2 ease formula
    # EF' = EF + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    new_ease = ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ease = max(EASE_FLOOR, new_ease)

    # Ease recovery: after enough consecutive successes, nudge ease toward target.
    # Check uses the incoming streak so that streak=4 does NOT trigger recovery —
    # it takes EASE_RECOVERY_THRESHOLD consecutive correct answers already on record.
    if streak >= EASE_RECOVERY_THRESHOLD and new_ease < EASE_TARGET:
        new_ease = min(EASE_TARGET, new_ease + EASE_RECOVERY_INCREMENT)

    # Interval fuzzing: ±5% for intervals > 2 to prevent review clustering
    if new_interval > 2:
        fuzz = random.uniform(0.95, 1.05)
        new_interval = max(1, round(new_interval * fuzz))

    next_review = datetime.now(timezone.utc) + timedelta(days=new_interval)

    return SRSUpdate(
        ease_factor=round(new_ease, 10),  # avoid floating-point drift
        interval=new_interval,
        repetitions=new_repetitions,
        streak=new_streak,
        lapses=new_lapses,
        next_review=next_review,
    )
