"""The gate on rewritten drill hints (Phase 3).

A hint narrows the answer without supplying it. The two faults this phase
repairs are the audit's own, so the gate re-runs the audit's predicates
rather than reimplementing them — a hint it accepts is one `audit_content`
will not flag, and that cannot drift.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.apply_drill_hints import check  # noqa: E402


class TestTheFaultsBeingRepaired:
    def test_a_hint_that_still_sits_in_the_translation(self):
        """'she' under "She sings very well." — the learner reads it one line
        up, and for a closed-class answer it settles the question."""
        assert check("she", "Ella", "She sings very well.", "her") == \
            "still sits inside the drill's translation"

    def test_a_hint_that_is_still_only_the_agreement_features(self):
        """The feature IS the exercise: 'feminine singular' picks `La` out of
        {el, la, els, les} without the learner knowing casa is feminine."""
        assert check("feminine singular", "La", "The house is big.", "feminine") == \
            "still only the agreement features"

    def test_a_hint_that_contains_its_own_answer(self):
        """Worse than the defect being fixed."""
        assert check("use Ella here", "Ella", "She sings very well.", "she") == \
            "contains its own answer"


class TestWhatMayBeWritten:
    def test_a_hint_that_says_to_do_the_work(self):
        assert check("the definite article — check the noun's gender",
                     "La", "The house is big.", "feminine singular") is None

    def test_a_hint_that_names_the_referent_s_role(self):
        assert check("third-person subject, female referent",
                     "Ella", "She sings very well.", "she") is None

    def test_a_longer_hint_is_allowed_when_it_earns_it(self):
        assert check("the object form, after a preposition",
                     "mí", "It's for me.", "me") is None


class TestRefusalsThatProtectTheFile:
    def test_an_unchanged_hint_is_not_a_repair(self):
        assert check("she", "Ella", "", "she") == "identical to the hint it replaces"

    def test_an_empty_hint(self):
        assert check("   ", "Ella", "", "she") == "empty"

    def test_an_essay_is_not_a_hint(self):
        assert check("x " * 100, "Ella", "", "she").startswith("longer than")


class TestOneHintMayCoverSeveralAnswers:
    """`agreement_feature` forbids stating the feature; `duplicate_hint`
    forbids one hint covering several answers. For an agreement point the two
    are in direct conflict — every hint violates one or the other — unless a
    hint is allowed to say "work it out from the sentence". That is the same
    principle `_is_allomorph_set` already encodes for Turkish mı/mi/mu/mü;
    the heuristic simply could not reach `is`/`are`."""

    def test_a_hint_that_names_where_to_look_is_not_a_duplicate(self):
        from backend.services.quality.audit_content import _sends_you_to_the_sentence
        assert _sends_you_to_the_sentence(
            "existential 'there' — agree the verb with the noun that follows")
        assert _sends_you_to_the_sentence(
            "the definite article — check the noun's gender")
        assert _sends_you_to_the_sentence(
            "existential verb — let the number of things named decide the ending")

    def test_it_reads_the_phrasing_authors_actually_use(self):
        """The first version matched literal phrases and missed "agree IT
        with", "match IT to", "pick ... by the noun's number" — three real
        hints from three courses. It now wants a directive verb AND the
        evidence in the sentence, which is the thing being described rather
        than one wording of it."""
        from backend.services.quality.audit_content import _sends_you_to_the_sentence
        assert _sends_you_to_the_sentence(
            "the indefinite article — match it to the gender of the noun")
        assert _sends_you_to_the_sentence(
            "existential verb — agree it with the number of what exists")
        assert _sends_you_to_the_sentence(
            "pick the demonstrative by the noun's number and how near the thing is")

    def test_it_stays_narrow(self):
        """A long hint is not enough; it has to say where to look. Otherwise
        the exemption would swallow the rule it is carved out of."""
        from backend.services.quality.audit_content import _sends_you_to_the_sentence
        assert not _sends_you_to_the_sentence("existential verb")
        assert not _sends_you_to_the_sentence("feminine singular")
        assert not _sends_you_to_the_sentence(
            "the verb used to say that something exists somewhere")
        # Naming the evidence without an instruction is just the feature.
        assert not _sends_you_to_the_sentence("the noun's gender and number")
        # And an instruction with nothing to apply it to is not a method.
        assert not _sends_you_to_the_sentence("choose carefully")
