"""Retake variance in sample_placement_items.

Owner: "they should have the option to retake it ... the test should change
slightly to better gauge their improvements." A retake that asks the same
questions measures memory of the last test, not the learner — so the sampler
slides its per-level window down the ranked pool by the number of attempts
already made, and wraps rather than emptying a small language's staircase.
"""

from __future__ import annotations

import json

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


class FakeInsightConn:
    """Enough asyncpg surface to exercise get_placement_insight's shaping."""

    def __init__(self, latest=None, previous=None, items=None):
        self.latest = latest
        self.previous = previous
        # Snapshot rows from placement_attempt_items, not live content.
        self.items = items or []

    async def fetchrow(self, query, *args):
        return self.latest

    async def fetchval(self, query, *args):
        return self.previous

    async def fetch(self, query, *args):
        return self.items


def attempt(**over):
    from datetime import UTC, datetime
    base = {
        "id": "attempt-1",
        "estimated_level": "B1",
        "items_asked": 7,
        "per_level": {"A1": {"correct": 3, "total": 3},
                      "A2": {"correct": 2, "total": 3},
                      "B1": {"correct": 1, "total": 3}},
        "created_at": datetime(2026, 7, 1, tzinfo=UTC),
    }
    return {**base, **over}


@pytest.mark.asyncio
class TestPlacementInsight:
    """Owner: the AI surfaces need the test's EVIDENCE, not just its verdict."""

    async def test_never_placed_is_none(self):
        from backend.repositories.onboarding import get_placement_insight
        assert await get_placement_insight(FakeInsightConn(), "u", "l") is None

    async def test_separates_levels_held_from_levels_failed(self):
        from backend.repositories.onboarding import get_placement_insight
        out = await get_placement_insight(
            FakeInsightConn(latest=attempt()), "u", "l"
        )
        # A1 3/3 and A2 2/3 clear the 0.6 bar; B1 at 1/3 does not.
        assert out["held_levels"] == ["A1", "A2"]
        assert out["struggled_levels"] == ["B1"]
        assert out["ceiling"] == "A2"

    async def test_json_encoded_per_level_is_still_read(self):
        """asyncpg hands back jsonb as text unless the codec is registered."""
        from backend.repositories.onboarding import get_placement_insight
        raw = json.dumps({"A1": {"correct": 3, "total": 3}})
        out = await get_placement_insight(
            FakeInsightConn(latest=attempt(per_level=raw)), "u", "l"
        )
        assert out["held_levels"] == ["A1"]

    async def test_names_the_missed_structures_and_words(self):
        from backend.repositories.onboarding import get_placement_insight
        conn = FakeInsightConn(
            latest=attempt(),
            items=[
                {"kind": "grammar", "label": "The subjunctive after querer"},
                {"kind": "vocabulary", "label": "aunque"},
            ],
        )
        out = await get_placement_insight(conn, "u", "l")
        # A bare uuid coaches nobody — the snapshotted label does.
        assert out["missed_structures"] == ["The subjunctive after querer"]
        assert out["missed_words"] == ["aunque"]

    async def test_reports_movement_against_the_previous_attempt(self):
        from backend.repositories.onboarding import get_placement_insight
        up = await get_placement_insight(
            FakeInsightConn(latest=attempt(), previous="A2"), "u", "l"
        )
        assert up["trend"] == "improved" and up["previous_level"] == "A2"
        flat = await get_placement_insight(
            FakeInsightConn(latest=attempt(), previous="B1"), "u", "l"
        )
        assert flat["trend"] == "steady"
        down = await get_placement_insight(
            FakeInsightConn(latest=attempt(), previous="C1"), "u", "l"
        )
        assert down["trend"] == "slipped"

    async def test_a_first_attempt_has_no_trend(self):
        from backend.repositories.onboarding import get_placement_insight
        out = await get_placement_insight(
            FakeInsightConn(latest=attempt()), "u", "l"
        )
        assert "trend" not in out

    async def test_a_level_with_no_items_is_neither_held_nor_failed(self):
        from backend.repositories.onboarding import get_placement_insight
        out = await get_placement_insight(
            FakeInsightConn(latest=attempt(
                per_level={"C2": {"correct": 0, "total": 0}}
            )), "u", "l"
        )
        assert out["held_levels"] == [] and out["struggled_levels"] == []

    async def test_a_retired_drill_does_not_erase_the_finding(self):
        """The point of snapshotting: the label lives on the attempt row, so
        a reviewer retiring the drill that proved it (drill_id -> NULL) leaves
        the coaching signal intact."""
        from backend.repositories.onboarding import get_placement_insight
        conn = FakeInsightConn(
            latest=attempt(),
            # drill_id is gone; the snapshot is not.
            items=[{"kind": "grammar", "label": "The subjunctive after querer"}],
        )
        out = await get_placement_insight(conn, "u", "l")
        assert out["missed_structures"] == ["The subjunctive after querer"]

    async def test_unlabelled_rows_are_skipped(self):
        from backend.repositories.onboarding import get_placement_insight
        out = await get_placement_insight(
            FakeInsightConn(latest=attempt(), items=[]), "u", "l"
        )
        assert "missed_structures" not in out and "missed_words" not in out
