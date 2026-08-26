"""Arabic, Hebrew and Persian readings — looked up, with the clitics peeled.

These three scripts write consonants and leave the short vowels to the reader,
so no rule can romanise them: كتاب carries no more about its vowels than `ktb`
does in English. Arabic was previously excluded from the reading layer for
exactly that reason. The exclusion confused two different things — it cannot
be COMPUTED is not it cannot be DONE — and the answer is the one Thai reached:
look it up.
"""
import csv

import pytest

from backend.services.nlp.semitic_reading import DATA, bare, semitic_reading
from backend.services.readings import READING_LANGS, sentence_reading


def test_all_three_are_in_the_reading_layer():
    assert {"ar", "he", "fa"} <= set(READING_LANGS)


@pytest.mark.parametrize("word,code,reading", [
    ("كتاب", "ar", "kitāb"),
    ("شلوم", "ar", None),          # not a headword — withheld, not guessed
    ("שלום", "he", "shalóm"),
    ("کتاب", "fa", "kitâb"),
])
def test_single_words(word, code, reading):
    got = sentence_reading(word, code)
    assert got == reading or (reading is None and not got)


def test_the_clitics_are_peeled():
    """Arabic glues its article, conjunctions and prepositions onto the next
    word, so a sentence token is frequently not a headword: والكتاب is
    و + ال + كتاب. Bare lookup covers 65% of Arabic sentence tokens; peeling
    is what makes the layer usable at all."""
    assert sentence_reading("الكتاب على الطاولة.", "ar") == "al-kitāb ʻalā al-ṭāwila."


def test_the_ipa_letters_are_replaced():
    """Wiktionary writes hamza and ayin as ʔ and ʕ. No learner reads IPA, so
    they become the ALA-LC ʼ and ʻ — the same problem that keeps Thai's
    tone-marked Paiboon form out of the shipping layer."""
    out = sentence_reading("الكتاب على الطاولة.", "ar")
    assert "ʕ" not in out and "ʔ" not in out
    assert "ʻ" in out


def test_persian_uses_one_long_a_convention():
    """Wiktionary carries the Classical ā and the modern â side by side, often
    on one entry. Mixing them inside a course is the same defect as Hausa
    naming one aspect four ways, so â wins throughout."""
    with (DATA / "fa_readings.tsv").open(encoding="utf-8-sig", newline="") as fh:
        readings = [r["reading"] for r in csv.DictReader(fh, delimiter="\t")]
    assert not any("ā" in r for r in readings), "Classical ā leaked into the table"
    assert any("â" in r for r in readings)


def test_hebrew_keeps_its_stress_accent():
    """Stress is unpredictable in Hebrew and not written in the script, so the
    acute on the stressed vowel is the most useful thing the layer carries."""
    assert sentence_reading("שלום", "he") == "shalóm"
    assert sentence_reading("כלב", "he") == "kélev"


def test_diacritics_are_stripped_but_letters_are_not():
    """The bug that made this look impossible for a while. Writing the mark
    ranges with literal characters produced [ؐ-ً], which is U+0610–U+064B and
    swallows the whole Arabic alphabet — bare("كتاب") returned "" and every
    lookup missed, at every call site, silently."""
    assert bare("كتاب") == "كتاب"
    assert bare("مُعَلِّم") == "معلم"
    assert bare("שָׁלוֹם") == "שלום"
    assert bare("میز") == "میز"


def test_a_partial_reading_is_no_reading():
    assert semitic_reading("كتاب زقزقزق", "ar") == ""


def test_the_cloze_blank_survives():
    out = sentence_reading("الكتاب {{answer}} الطاولة.", "ar")
    assert "{{answer}}" in out


@pytest.mark.parametrize("code,floor", [("ar", 0.35), ("he", 0.60), ("fa", 0.60)])
def test_coverage_has_not_silently_dropped(code, floor):
    """A ratchet. Arabic's floor is lower than the others because its sentences
    are full of inflected verb forms that are not headwords — the vocabulary is
    at 100% and the sentences are not, and that gap is real rather than a bug
    to be fixed by loosening the table.

    HEBREW'S FLOOR WENT DOWN ON PURPOSE, from 0.75 to 0.60. Clitic peeling was
    covering those sentences and a verification pass judged 22 of 108 peeled
    Hebrew forms wrong — not near-misses but different words: מחברות read as
    "from friends" when it is "notebooks", הילדות as "childhood" when it is
    "the girls", and every ב- prefix given as be- where Hebrew fuses the
    article and says ba-. Persian was worse, 10 of 11. Peeling is off for both
    now, and the coverage it was inflating went with it.

    A number moving down because the wrong answers were removed is the ratchet
    working, not failing. Do not restore the old floor by re-enabling the
    peeler."""
    with (DATA / f"{code}_sentences.tsv").open(encoding="utf-8-sig", newline="") as fh:
        rows = [(r.get("sentence") or "").strip() for r in csv.DictReader(fh, delimiter="\t")]
    rows = [s for s in rows if s]
    covered = sum(1 for s in rows if semitic_reading(s, code))
    assert covered / len(rows) > floor, f"{code}: {covered}/{len(rows)}"
