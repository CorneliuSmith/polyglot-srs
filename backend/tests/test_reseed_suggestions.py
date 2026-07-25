"""Option B — doc re-seed proposal logic.

The DB glue (routing curated words to the suggestion queue, the audit log, the
admin metrics) is exercised against a live database; this file pins the pure
decision the routing turns on: given a re-seed record and the live curated
card, what — if anything — should be PROPOSED rather than overwritten.
"""
from __future__ import annotations

from backend.repositories.contributor import reseed_vocab_proposal


def _record(pos=None, definition=None):
    return {
        "word": "casa",
        "pos": pos,
        "translations": {"en": definition} if definition is not None else {},
    }


class TestReseedVocabProposal:
    def test_new_pos_and_definition_both_proposed(self):
        cur = {"part_of_speech": "verb", "definition": "old gloss"}
        proposal = reseed_vocab_proposal(_record("noun", "house, home"), cur)
        assert proposal == {"part_of_speech": "noun", "definition": "house, home"}

    def test_only_the_differing_field_is_proposed(self):
        cur = {"part_of_speech": "noun", "definition": "old gloss"}
        proposal = reseed_vocab_proposal(_record("noun", "house, home"), cur)
        assert proposal == {"definition": "house, home"}

    def test_identical_reseed_proposes_nothing(self):
        cur = {"part_of_speech": "noun", "definition": "house"}
        assert reseed_vocab_proposal(_record("noun", "house"), cur) == {}

    def test_blank_reseed_values_are_ignored(self):
        # A reseed that carries no pos / no definition must not blank the card.
        cur = {"part_of_speech": "noun", "definition": "house"}
        assert reseed_vocab_proposal(_record(None, None), cur) == {}
        assert reseed_vocab_proposal(_record("  ", "  "), cur) == {}

    def test_whitespace_only_difference_is_not_a_change(self):
        cur = {"part_of_speech": "noun", "definition": "house"}
        assert reseed_vocab_proposal(_record(" noun ", " house "), cur) == {}

    def test_missing_current_fields_treated_as_empty(self):
        # A curated card with no English gloss yet — the reseed's gloss is new.
        proposal = reseed_vocab_proposal(_record("noun", "house"), {})
        assert proposal == {"part_of_speech": "noun", "definition": "house"}
