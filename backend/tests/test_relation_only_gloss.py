"""A definition that names a grammatical relation and gives no meaning — §36.

The owner reported this class: "coche as the definition for coches". Spanish
rank 204 `necesito` is defined as "first-person singular present indicative of
necesitar" — true, and useless. The word means "I need".

It is the largest content defect left: 27,794 live rows on 10 Sep 2026, of
which 4,397 sit in the top-2,000 band a learner reaches. The band boundary is
the finding — Phase 2d repaired the top-200 per course and the defect resumes
at exactly rank 201.

Two things this file pins beyond the regex. First, the rule reads the
frequency file **with `gloss_overrides.tsv` laid over it**, because that is
what production serves (CHECKS §31); auditing the raw column grades text
nobody is shown. Second, the GOOD shape — meaning first, relation in
parentheses — must never be reported, or the rule would push editors away
from the one form the programme has settled on.
"""
from __future__ import annotations

import csv

import pytest

from backend.services.quality.audit_content import (
    CARD_RULE_BAND,
    DATA,
    REPORT_RULES,
    _frequency_rows,
    is_relation_only,
)


class TestWhatItCatches:
    @pytest.mark.parametrize("gloss", [
        "first-person singular present indicative of necesitar",
        "plural of Woche",
        "nominative plural of çocuk",
        "second-person singular imperative of tener",
        "past participle of vragen",
        "feminine singular of bueno",
        "third-person singular past historic of dire",
        "ablative singular of bu",
        "first-person singular possessive singular of el",
        "masculine equivalent of tūī",
        "The plural of dólar.",
    ])
    def test_a_relation_with_no_meaning_is_reported(self, gloss):
        assert is_relation_only(gloss)


class TestWhatItLeavesAlone:
    @pytest.mark.parametrize("gloss", [
        # THE house shape: meaning first, relation in parentheses. Reporting
        # this would push editors off the one form the programme settled on.
        "arrive (present subjunctive of llegar)",
        "I need; I have to (first-person singular present of necesitar)",
        "he has, she has; you have (formal) — owns or holds something",
        "I know — a fact, information, or how to do something",
        # Ordinary definitions that merely contain the word "of".
        "a member of a family",
        "the edge of a blade",
        "made of wood",
        "to think of something",
        "",
    ])
    def test_a_real_definition_is_not_reported(self, gloss):
        assert not is_relation_only(gloss)

    def test_a_relation_that_still_gives_the_meaning_is_kept(self):
        """The distinction the whole rule turns on: the relation is welcome,
        it just may not be the entire definition."""
        assert is_relation_only("plural of dólar")
        assert not is_relation_only("dollars (plural of dólar)")


def test_it_is_a_report_rule():
    """Report, not fail. The count is in the thousands while the repair passes
    run, and a threshold set there is a number nobody could defend (the
    `gender_marking` argument). Unlike the other report rules its target IS
    zero, so it can be promoted when the courses reach it."""
    assert "relation_only_gloss" in REPORT_RULES


def test_the_rule_reads_what_production_serves_not_the_raw_column():
    """`_frequency_rows` lays `gloss_overrides.tsv` over the file, the same
    overlay `BaseSeeder.prepare_records` and `reconcile.expected_rows` use.

    Measured 10 Sep 2026: of 3,441 top-2000 rows an override covers, 1,734
    differ from the file column. Auditing the column alone can report a defect
    the override already fixed AND miss one the override introduced — and an
    override introducing a defect is what shipped the wrong Yoruba pronoun
    (quality rule 51).
    """
    raw = {}
    path = DATA / "ar_frequency.tsv"
    if not path.exists():
        pytest.skip("no Arabic frequency file in this checkout")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            raw[(row.get("word") or "").strip()] = (row.get("en") or "").strip()

    overlaid = {(r.get("word") or "").strip(): (r.get("en") or "").strip()
                for r in _frequency_rows("ar")}
    assert overlaid, "the overlay returned nothing for ar"
    assert set(overlaid) == set(raw), "the overlay must not add or drop rows"
    changed = [w for w in raw if raw[w] != overlaid[w]]
    assert changed, (
        "no Arabic row differs after the overlay — either gloss_overrides.tsv "
        "lost its Arabic rows or _frequency_rows stopped applying it"
    )


def test_the_band_is_the_one_a_learner_reaches():
    """Scoped like the card rules: a defect on rank 8,000 is real and nobody
    meets it. Keeping the two in step is deliberate."""
    assert CARD_RULE_BAND == 2000
