"""Retake variance in sample_placement_items.

Owner: "they should have the option to retake it ... the test should change
slightly to better gauge their improvements." A retake that asks the same
questions measures memory of the last test, not the learner — so the sampler
slides its per-level window down the ranked pool by the number of attempts
already made, and wraps rather than emptying a small language's staircase.
"""

from __future__ import annotations

import pytest

from backend.repositories.onboarding import sample_placement_items
from backend.services.extract import ANSWER_MARKER

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


class FakeConn:
    """Stands in for asyncpg, honouring the `rn <= $2` window each query asks
    for so the variant arithmetic is exercised for real."""

    def __init__(self, *, vocab_depth: int = 40, grammar_depth: int = 12):
        self.vocab_depth = vocab_depth
        self.grammar_depth = grammar_depth

    async def fetch(self, query: str, *args):
        limit = args[1]
        if "vocabulary" in query:
            return [
                {"id": f"v-{lvl}-{rn}", "level": lvl, "prompt": f"word {lvl} {rn}"}
                for lvl in LEVELS
                for rn in range(1, min(limit, self.vocab_depth) + 1)
            ]
        return [
            {"id": f"g-{lvl}-{rn}", "level": lvl, "rn": rn,
             "sentence": f"a {ANSWER_MARKER} b", "translation": f"t {lvl} {rn}"}
            for lvl in LEVELS
            for rn in range(1, min(limit, self.grammar_depth) + 1)
        ]


def ids(items, kind):
    return [it["id"] for it in items if it["kind"] == kind]


@pytest.mark.asyncio
class TestPlacementVariants:
    async def test_variant_zero_is_the_original_top_of_the_pool(self):
        items = await sample_placement_items(FakeConn(), "lang", per_level=3)
        # First placement is unchanged: the most frequent words, the earliest
        # drills — nothing about the original behaviour moved.
        assert ids(items, "vocabulary")[:3] == ["v-A1-1", "v-A1-2", "v-A1-3"]
        assert ids(items, "grammar")[:3] == ["g-A1-1", "g-A1-2", "g-A1-3"]

    async def test_a_retake_asks_different_items(self):
        first = await sample_placement_items(FakeConn(), "lang", per_level=3)
        second = await sample_placement_items(
            FakeConn(), "lang", per_level=3, variant=1
        )
        assert set(ids(first, "vocabulary")).isdisjoint(ids(second, "vocabulary"))
        assert set(ids(first, "grammar")).isdisjoint(ids(second, "grammar"))

    async def test_every_level_still_appears_on_a_retake(self):
        """The staircase is what the estimate walks — losing a level would
        make the retake worse than the first test, not better."""
        for variant in range(3):
            items = await sample_placement_items(
                FakeConn(), "lang", per_level=3, variant=variant
            )
            for kind in ("vocabulary", "grammar"):
                seen = {
                    it["level"] for it in items if it["kind"] == kind
                }
                assert seen == set(LEVELS), (variant, kind, seen)

    async def test_a_shallow_pool_wraps_instead_of_emptying(self):
        """A young language has 4 drills per level, not 40. Attempt 5 repeats
        items — far better than placing nobody."""
        conn = FakeConn(vocab_depth=4, grammar_depth=4)
        items = await sample_placement_items(conn, "lang", per_level=3, variant=4)
        assert {it["level"] for it in items} == set(LEVELS)
        assert len(ids(items, "grammar")) == 3 * len(LEVELS)

    async def test_answers_are_never_included(self):
        items = await sample_placement_items(FakeConn(), "lang", per_level=2)
        assert all("answer" not in it and "word" not in it for it in items)
        # The cloze blank replaces the marker — the drill never leaks its key.
        assert all(
            ANSWER_MARKER not in it["prompt"]
            for it in items if it["kind"] == "grammar"
        )
