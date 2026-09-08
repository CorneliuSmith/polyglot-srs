"""The hint that spells the answer's own stem — CHECKS §33.

The owner met it on a Spanish card: hint "coche, plural", answer *coches*.
Four hint rules already existed and all four missed it. `leak_hard` matches
the answer as a WHOLE word and "coches" is not in the hint; `self_answering`
wants the answer then a dash; `giveaway_by_gloss` looks for the hint inside
the translation ("The cars are new"); `agreement_feature` wants a feature and
nothing else, and this hint carries a lemma too.

It is a REPORT rule, and that is the finding rather than a compromise — see
`test_the_same_shape_is_a_giveaway_in_one_language_and_teaching_in_another`.
"""
from __future__ import annotations

import pytest

from backend.services.quality.audit_content import (
    REPORT_RULES,
    _stem_of_answer_in_hint,
    audit_language,
)


class TestTheRule:
    def test_the_card_the_owner_reported(self):
        assert _stem_of_answer_in_hint("coche, plural", "coches") == "coche"

    def test_the_hint_that_replaced_it_does_not_trip(self):
        assert _stem_of_answer_in_hint("car (m.), plural", "coches") is None

    @pytest.mark.parametrize("hint,answer", [
        ("plural of libro", "libros"),
        ("hermana, plural", "hermanas"),
        ("it-to-him (glie + lo)", "glielo"),
        ("the noun meaning house, as a diminutive", "huisje"),
    ])
    def test_other_shapes_of_the_same_fault(self, hint, answer):
        got = _stem_of_answer_in_hint(hint, answer)
        assert (got is not None) == ("glie" in hint or "libro" in hint
                                     or "hermana" in hint)

    def test_a_short_english_function_word_is_a_collision_not_a_leak(self):
        assert _stem_of_answer_in_hint("the one that goes", "theatre") is None

    def test_a_stem_that_is_most_of_the_answer_but_not_a_prefix(self):
        assert _stem_of_answer_in_hint("ending in -ar", "hablar") is None

    def test_the_remainder_must_be_short(self):
        """`vend` in a hint for `vendedores` is not this fault — the answer is
        a derivation, not the stem plus an ending."""
        assert _stem_of_answer_in_hint("vend, agent noun", "vendedores") is None


class TestWhyItReportsRatherThanFails:
    def test_it_is_registered_as_a_report_rule(self):
        assert "stem_in_hint" in REPORT_RULES

    def test_the_same_shape_is_a_giveaway_in_one_language_and_teaching_in_another(self):
        """Spanish `coche → coches` is always +s, so the hint hands over the
        answer. Dutch `boek → boeken` makes the learner choose -en over -s and
        Romanian `scaun → scaune` -e over -uri; readers of those languages
        judged both legitimate on 7 Sep 2026. The rule sees the same shape in
        all three, so it cannot decide — it names candidates for a reader.
        """
        assert _stem_of_answer_in_hint("coche, plural", "coches") == "coche"
        assert _stem_of_answer_in_hint("plural of boek", "boeken") == "boek"
        assert _stem_of_answer_in_hint("chairs (scaun, neuter)", "scaune") == "scaun"


class TestAgainstTheCorpus:
    def test_the_spanish_point_the_owner_saw_is_clean(self):
        found = audit_language("es")["findings"].get("stem_in_hint") or []
        assert not [f for f in found if "Gender and number of nouns" in f], found

    def test_the_rule_still_finds_the_candidates_it_should(self):
        """It is a report rule: a zero here would mean it had stopped looking,
        not that the corpus were clean. Legitimate citations — "sold — they
        (vender)" — are supposed to appear."""
        found = audit_language("pt")["findings"].get("stem_in_hint") or []
        assert found, "the rule found nothing in Portuguese; has it stopped looking?"

    def test_no_fail_level_rule_was_added(self):
        """A rule that cannot separate the classes must not fail a build."""
        from backend.services.quality.audit_content import FAIL_RULES
        assert "stem_in_hint" not in FAIL_RULES
