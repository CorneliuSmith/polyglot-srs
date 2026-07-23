"""Unit tests for the adaptive-Gym selection weight (pure function)."""
from backend.services.gym_weight import drill_weight


def _stats(seen=1, misses=0, wrong_form=0, hint_used=0, streak=0, age_seconds=0.0):
    return {"seen": seen, "misses": misses, "wrong_form": wrong_form,
            "hint_used": hint_used, "streak": streak, "age_seconds": age_seconds}


def test_unseen_ranks_above_an_average_seen_drill():
    assert drill_weight(None) > drill_weight(_stats(seen=3, streak=1))


def test_misses_raise_weight():
    calm = drill_weight(_stats(seen=4, misses=0))
    missed = drill_weight(_stats(seen=4, misses=3))
    assert missed > calm


def test_wrong_form_counts_more_than_a_plain_miss():
    plain = drill_weight(_stats(seen=4, misses=2, wrong_form=0))
    form = drill_weight(_stats(seen=4, misses=2, wrong_form=2))
    assert form > plain


def test_hint_dependence_raises_weight():
    clean = drill_weight(_stats(seen=4, hint_used=0))
    hinted = drill_weight(_stats(seen=4, hint_used=3))
    assert hinted > clean


def test_mastery_streak_lowers_weight():
    fresh = drill_weight(_stats(seen=5, streak=0))
    mastered = drill_weight(_stats(seen=5, streak=5))
    assert mastered < fresh


def test_spacing_resurfaces_old_drills():
    just_seen = drill_weight(_stats(seen=3, age_seconds=0))
    week_old = drill_weight(_stats(seen=3, age_seconds=8 * 86400))
    assert week_old > just_seen


def test_irregular_outranks_regular_all_else_equal():
    reg = drill_weight(_stats(seen=3, misses=1), is_irregular=False)
    irr = drill_weight(_stats(seen=3, misses=1), is_irregular=True)
    assert irr > reg


def test_irregular_and_failing_stays_high_despite_recent_repetition():
    # Just seen (recency would bury it) AND a long "correct" streak would
    # normally damp it — but an irregular form still being gotten WRONG is
    # floored high so it keeps coming back.
    buried = _stats(seen=8, misses=1, wrong_form=1, streak=6, age_seconds=0)
    assert drill_weight(buried, is_irregular=True) >= 2.5


def test_weight_is_always_positive():
    assert drill_weight(_stats(seen=99, streak=99, age_seconds=0)) > 0
