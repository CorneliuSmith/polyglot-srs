"""Grammar re-seed protection — the pure decision logic.

The DB glue runs against a live database; these tests pin the two policies the
re-seed turns on: which drills change (plan_drill_sync) and what a curated
point's text diff proposes (reseed_grammar_proposal).
"""
from __future__ import annotations

from backend.repositories.contributor import reseed_grammar_proposal
from backend.services.seeder.seed_grammar import plan_drill_sync


def _row(sentence, answer, *, source="seed", is_modified=False, flagged=False, id=None):
    return {"id": id or f"{sentence}/{answer}", "sentence": sentence,
            "answer": answer, "source": source, "is_modified": is_modified,
            "flagged": flagged}


def _drill(sentence, answer, **extra):
    return {"sentence": sentence, "answer": answer, "translation": "t",
            "hint": "h", "display_order": 1, **extra}


class TestPlanDrillSync:
    def test_matched_drill_updates_in_place_keeping_its_id(self):
        # The whole point of the diff-sync: a matched row is updated, not
        # deleted+reinserted, so gym_progress rows referencing its id survive.
        existing = [_row("Na {{answer}}.", "gata", id="keep-me")]
        plan = plan_drill_sync(existing, [_drill("Na {{answer}}.", "gata")])
        assert plan["insert"] == [] and plan["delete"] == []
        assert len(plan["update"]) == 1
        assert plan["update"][0][0]["id"] == "keep-me"

    def test_new_drill_inserts(self):
        plan = plan_drill_sync([], [_drill("A {{answer}}.", "x")])
        assert len(plan["insert"]) == 1
        assert plan["update"] == [] and plan["delete"] == []

    def test_stale_untouched_seed_drill_is_deleted(self):
        existing = [_row("Old {{answer}}.", "y")]
        plan = plan_drill_sync(existing, [_drill("New {{answer}}.", "z")])
        assert [r["sentence"] for r in plan["delete"]] == ["Old {{answer}}."]

    def test_human_modified_flagged_and_nonseed_drills_are_never_deleted(self):
        existing = [
            _row("Human {{answer}}.", "a", source="human"),
            _row("Edited {{answer}}.", "b", is_modified=True),
            _row("Flagged {{answer}}.", "c", flagged=True),
            _row("Pending {{answer}}.", "d", source="ai"),
        ]
        plan = plan_drill_sync(existing, [_drill("Only {{answer}}.", "e")])
        assert plan["delete"] == []  # none qualify, despite all being stale

    def test_protect_mode_is_additive_only(self):
        # A curated point: nothing is updated or deleted; only genuinely new
        # drills come back (the caller lands them reviewed=false).
        existing = [_row("Keep {{answer}}.", "k")]
        incoming = [_drill("Keep {{answer}}.", "k"), _drill("New {{answer}}.", "n")]
        plan = plan_drill_sync(existing, incoming, protect=True)
        assert plan["update"] == [] and plan["delete"] == []
        assert [d["answer"] for d in plan["insert"]] == ["n"]

    def test_incoming_duplicates_are_deduped(self):
        # A merged multi-chunk extraction can repeat a drill; first wins.
        incoming = [_drill("D {{answer}}.", "x", display_order=1),
                    _drill("D {{answer}}.", "x", display_order=9)]
        plan = plan_drill_sync([], incoming)
        assert len(plan["insert"]) == 1
        assert plan["insert"][0]["display_order"] == 1

    def test_same_sentence_different_answer_is_a_different_drill(self):
        existing = [_row("S {{answer}}.", "a")]
        plan = plan_drill_sync(existing, [_drill("S {{answer}}.", "b")])
        assert len(plan["insert"]) == 1          # new (sentence, answer) pair
        assert len(plan["delete"]) == 1          # old untouched seed row goes


class TestReseedGrammarProposal:
    def test_differing_fields_are_proposed(self):
        point = {"function": "marks the topic", "explanation": "new text",
                 "culture_note": ""}
        cur = {"function_note": "old", "explanation": "old text",
               "culture_note": "keep"}
        assert reseed_grammar_proposal(point, cur) == {
            "function_note": "marks the topic", "explanation": "new text",
        }

    def test_identical_reseed_proposes_nothing(self):
        point = {"function": "f", "explanation": "e", "culture_note": "c"}
        cur = {"function_note": "f", "explanation": "e", "culture_note": "c"}
        assert reseed_grammar_proposal(point, cur) == {}

    def test_blank_incoming_never_proposes_blanking(self):
        point = {"function": "", "explanation": None, "culture_note": "  "}
        cur = {"function_note": "human wrote this", "explanation": "and this",
               "culture_note": "and this too"}
        assert reseed_grammar_proposal(point, cur) == {}

    def test_whitespace_only_difference_is_not_a_change(self):
        point = {"function": " f ", "explanation": "e", "culture_note": None}
        cur = {"function_note": "f", "explanation": "e", "culture_note": None}
        assert reseed_grammar_proposal(point, cur) == {}
