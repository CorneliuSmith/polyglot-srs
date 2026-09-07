"""The gate on authored definitions.

The definition is the layer that decides whether a card is answerable at all:
of 128 top-band cards that fail to determine their answer, the cheapest
repair was the definition for 77 (CHECKS §28). So a bad one written here is
expensive, and every rule below is one this programme has already paid for.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.apply_gloss_overrides import check, course_words  # noqa: E402

KNOWN = {"have": "have or possess", "gato": "cat", "que": "that", "na": "and"}


def _check(word, definition, pos="verb", current=None, code="en"):
    return check(code, word, pos, definition, KNOWN, current or {})


class TestARefusalIsCheaperThanABadCard:
    def test_a_definition_that_opens_with_its_own_word(self):
        assert _check("have", "have or possess") == "opens with the word it defines"

    def test_a_circular_definition_anywhere_in_the_line(self):
        """`audit_content.is_circular` is imported rather than re-implemented,
        so the gate and the audit cannot drift apart."""
        assert _check("have", "to possess or have something") == \
            "explains the word with the word"

    def test_a_part_of_speech_is_not_a_definition(self):
        assert _check("que", "a pronoun", pos="pron") == \
            "a part-of-speech label, not a definition"

    def test_an_empty_definition(self):
        assert _check("have", "   ") == "empty"

    def test_a_one_word_definition_is_allowed(self):
        """Italian `e` is glossed "and" and that is correct. A cap of two
        words would have refused it — the shipped corpus is the evidence,
        not taste."""
        assert _check("que", "and", pos="conj") is None

    def test_a_word_the_course_does_not_have(self):
        """A definition for an unknown headword is a typo or a hallucination,
        and must not create a row."""
        assert _check("perro", "a four-legged animal that barks", pos="noun") == \
            "word is not in this course"

    def test_a_definition_identical_to_the_one_already_shown(self):
        """Not a fix, and writing it inflates the override count with nothing
        behind it (quality rule 31)."""
        assert _check("gato", "The Cat.", pos="noun",
                      current={"gato": "the cat"}) == \
            "identical to the definition already shown"

    def test_an_over_long_definition(self):
        assert _check("gato", "x " * 300, pos="noun").startswith("longer than")


class TestAGoodDefinitionPasses:
    def test_a_repair_that_names_the_job(self):
        assert _check("que", "introduces the reason for something "
                             "('I left ___ it rained')", pos="conj") is None

    def test_a_blank_stands_in_for_the_word_in_an_example(self):
        """Writing the word into its own example would spell the answer, so
        the convention is a blank — and the gate must not mistake that for a
        malformed definition."""
        assert _check("gato", "the small animal that purrs ('el ___ duerme')",
                      pos="noun") is None

    def test_a_headword_inside_its_gloss_is_fine_off_english(self):
        """Off English the definition is in a DIFFERENT language from the
        headword, so a match is a coincidence or a correct translation:
        Catalan `ha` means "has", Spanish `me` means "me", and Swahili `na` is
        glossed "and; with (kuwa na, to have)" deliberately. Applying the
        English rules to all 27 refused 864 shipped overrides, none of them
        defects — the result `_audit_circular_glosses` documents."""
        assert _check("na", "and; with (kuwa na, to have)", pos="conj",
                      code="sw") is None

    def test_but_a_definition_that_is_only_the_headword_never_passes(self):
        """The one self-quoting rule that cannot be a coincidence."""
        assert _check("na", "na", pos="conj", code="sw") == \
            "is the word it defines"
        assert _check("na", "NA.", pos="conj", code="sw") == \
            "is the word it defines"


def test_the_shipped_overrides_all_pass_their_own_gate():
    """Nothing already in the file may be something the gate would refuse to
    write today — otherwise the rule is aspirational rather than enforced."""
    import csv
    with open("data/gloss_overrides.tsv", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    known_by_course: dict[str, dict[str, str]] = {}
    bad = []
    for r in rows:
        code = r["language"]
        known = known_by_course.setdefault(code, course_words(code))
        if not known:
            continue
        why = check(code, r["word"], r.get("pos", ""), r.get("en", ""),
                    known, {})
        # "identical to the definition already shown" is expected: an override
        # may legitimately restate what the frequency file holds.
        if why and why not in ("identical to the definition already shown",
                               "word is not in this course"):
            bad.append((code, r["word"], why, (r.get("en") or "")[:50]))
    assert not bad, f"{len(bad)} shipped overrides fail the gate: {bad[:5]}"
