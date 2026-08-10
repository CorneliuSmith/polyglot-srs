"""Placement grading: synonym acceptance and level blending."""
from __future__ import annotations

from backend.services.placement_grade import (
    blend_levels,
    senses,
    shares_a_sense,
)


class TestSenses:
    def test_splits_on_semicolons_and_commas(self):
        assert senses("big; large, huge") == {"big", "large", "huge"}

    def test_strips_the_infinitive_marker_so_walk_matches_to_walk(self):
        assert senses("to walk") == senses("walk") == {"walk"}

    def test_drops_parenthetical_usage_notes(self):
        assert senses("bank (of a river)") == {"bank"}

    def test_drops_bare_function_words(self):
        # "of; 's; used after the thing owned" — the gloss of Spanish *de*.
        # Nothing here may become a synonym key, or every function word
        # matches every other.
        assert "of" not in senses("of; 's; used after the thing owned")

    def test_keeps_multiword_senses_whole(self):
        assert senses("to go on foot") == {"go on foot"}


class TestSharesASense:
    def test_accepts_a_genuine_synonym(self):
        # The owner's case: the seeds accept only one headword per gloss.
        assert shares_a_sense("to walk", "to walk; to stroll")

    def test_accepts_across_a_list_of_near_equivalents(self):
        assert shares_a_sense("big", "large, big")

    def test_rejects_a_merely_related_word(self):
        # *ir* ("to go") is not an answer to "to walk; to go on foot" —
        # matching the bare token "go" would accept it, which is why senses
        # are compared whole.
        assert not shares_a_sense("to walk; to go on foot", "to go")

    def test_rejects_when_only_a_function_word_is_shared(self):
        assert not shares_a_sense("of; 's", "of; from")

    def test_handles_missing_definitions(self):
        assert not shares_a_sense(None, "to walk")
        assert not shares_a_sense("to walk", None)


class TestBlendLevels:
    def test_writing_outranks_the_quiz(self):
        # Production is the better guide, so a stronger sample lifts them.
        assert blend_levels("B1", "B2") == "B2"

    def test_writing_can_also_lower_the_estimate(self):
        assert blend_levels("B2", "B1") == "B1"

    def test_a_lucky_paragraph_cannot_move_two_bands(self):
        assert blend_levels("A2", "C1") == "B1"
        assert blend_levels("C1", "A1") == "B2"

    def test_either_signal_alone_stands(self):
        assert blend_levels("B1", None) == "B1"
        assert blend_levels(None, "B2") == "B2"
        assert blend_levels("B1", "nonsense") == "B1"
