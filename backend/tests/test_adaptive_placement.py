"""Tests for the adaptive placement staircase (WP11).

The walk is pure and deterministic: probe starts at A2, steps up on a
correct answer and down on a miss, and stops early once the estimate is
stable — beginners exit in ~3 items, experts in ~7, everyone by 12.
"""
from backend.repositories.onboarding import (
    CEFR_ORDER,
    MAX_ADAPTIVE_ITEMS,
    adaptive_next,
)


def make_pool(per_level: int = 3) -> list[dict]:
    pool = []
    for lvl in CEFR_ORDER:
        for i in range(per_level):
            kind = "grammar" if i % 2 == 0 else "vocabulary"
            pool.append({"id": f"{lvl}-{kind}-{i}", "kind": kind, "level": lvl})
    return pool


def walk(pool, answer_fn, max_steps=40):
    """Drive the staircase with answer_fn(item) -> bool; return the history."""
    history: list[tuple[dict, bool]] = []
    for _ in range(max_steps):
        item = adaptive_next(pool, history)
        if item is None:
            return history
        history.append((item, answer_fn(item)))
    raise AssertionError("walk never terminated")


class TestAdaptiveWalk:
    def test_starts_at_a2_with_grammar(self):
        first = adaptive_next(make_pool(), [])
        assert first["level"] == "A2"
        assert first["kind"] == "grammar"  # grammar is the weighted signal

    def test_total_beginner_exits_fast_at_the_floor(self):
        history = walk(make_pool(), lambda item: False)
        # A2 miss -> A1, two consecutive floor misses -> stop.
        assert len(history) == 3
        assert [i["level"] for i, _ in history] == ["A2", "A1", "A1"]

    def test_expert_climbs_to_the_ceiling_and_stops(self):
        history = walk(make_pool(), lambda item: True)
        # A2..C2 is 4 steps up, then two consecutive C2 passes -> stop.
        assert [i["level"] for i, _ in history] == \
            ["A2", "B1", "B2", "C1", "C2", "C2"]

    def test_oscillator_stops_on_reversals_around_their_level(self):
        # Knows everything at or below B1, nothing above: classic boundary.
        def answer(item):
            return CEFR_ORDER.index(item["level"]) <= CEFR_ORDER.index("B1")

        history = walk(make_pool(per_level=6), answer)
        assert len(history) < MAX_ADAPTIVE_ITEMS  # early stop, not the cap
        # The walk spends its time bouncing between B1 and B2.
        probed = {i["level"] for i, _ in history}
        assert probed <= {"A2", "B1", "B2"}

    def test_never_exceeds_the_cap(self):
        # Coin-flip-ish deterministic pattern that dodges the reversal stop
        # is impossible (any alternation reverses), so force the cap with a
        # long climb-then-fall shape on a big pool.
        seq = [True, True, True, False, False, False, True, True, True,
               False, False, False, True, True]

        def answer(item, it=iter(seq)):
            return next(it, False)

        history = walk(make_pool(per_level=8), answer)
        assert len(history) <= MAX_ADAPTIVE_ITEMS

    def test_repeats_no_item(self):
        history = walk(make_pool(), lambda item: True)
        ids = [i["id"] for i, _ in history]
        assert len(ids) == len(set(ids))

    def test_exhausted_pool_stops(self):
        tiny = [{"id": "x", "kind": "grammar", "level": "A2"}]
        history = [(tiny[0], True)]
        assert adaptive_next(tiny, history) is None

    def test_falls_back_to_nearest_level_when_probe_level_empty(self):
        # No C1/C2 content: an expert tops out on what exists.
        pool = [it for it in make_pool()
                if it["level"] in ("A1", "A2", "B1", "B2")]
        history = walk(pool, lambda item: True)
        assert all(i["level"] in ("A2", "B1", "B2") for i, _ in history)

    def test_grammar_outweighs_vocab(self):
        history = walk(make_pool(per_level=6),
                       lambda item: item["level"] in ("A1", "A2", "B1"))
        kinds = [i["kind"] for i, _ in history]
        assert kinds.count("grammar") >= kinds.count("vocabulary")

    def test_deterministic(self):
        pool = make_pool()
        h1 = walk(pool, lambda item: item["level"] in ("A1", "A2"))
        h2 = walk(pool, lambda item: item["level"] in ("A1", "A2"))
        assert [i["id"] for i, _ in h1] == [i["id"] for i, _ in h2]
