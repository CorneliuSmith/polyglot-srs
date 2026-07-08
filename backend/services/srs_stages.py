"""Named SRS stages mapped from FSRS state — one definition for the dashboard
tiles, the item page, and the Related grid so a card never wears two names.

Bands are FSRS stability (days the memory is expected to hold):
< 7 beginner · < 30 adept · < 90 seasoned · < 180 expert · else master.
Relearning cards are ghosts (recently failed, still haunting the queue);
personal cards are self-study.
"""
from __future__ import annotations

STAGE_BANDS: tuple[tuple[float, str], ...] = (
    (7, "beginner"),
    (30, "adept"),
    (90, "seasoned"),
    (180, "expert"),
)


def stage_for(card_type: str, state: str | None, stability: float | None) -> str:
    if state == "relearning":
        return "ghost"
    if card_type == "personal":
        return "self_study"
    s = stability or 0.0
    for bound, name in STAGE_BANDS:
        if s < bound:
            return name
    return "master"
