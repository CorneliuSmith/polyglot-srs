"""Arabic, Hebrew and Persian readings — looked up, with the clitics peeled.

These three scripts write consonants and leave the short vowels to the reader,
so no rule can romanise them: كتاب carries no more about its vowels than `ktb`
does in English. Arabic was previously excluded from the reading layer for
exactly that reason. The exclusion confused two different things — it cannot
be COMPUTED is not it cannot be DONE — and the answer is the one Thai reached:
look it up.
"""
import csv
import random

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


@pytest.mark.parametrize("code,floor", [("ar", 0.78), ("he", 0.85), ("fa", 0.90)])
def test_coverage_has_not_silently_dropped(code, floor):
    """A ratchet on TOKEN coverage — what share of words the lookup knows.

    IT USED TO MEASURE SENTENCES fully covered, and that unit was wrong: a
    sentence needs EVERY word known, so the number falls as sentences get
    longer even when the table has not changed. Arabic's floor was moved
    twice in two days (0.38 -> 0.35 -> 0.33) chasing exactly that, and both
    times because sentence quality had been RAISED — 684 authored sentences
    of 7-14 words, then thousands of fragments dropped. A ratchet that falls
    when the content improves is measuring the wrong thing.

    Tokens are independent of how words are grouped into sentences. Measured
    31 Aug: ar 81.5%, he 89.1%, fa 95.1%, against a sentence-coverage figure
    of 27.5% for the same Arabic corpus. Both are true; only one answers
    "how much of this language can the table read".

    HEBREW AND PERSIAN ARE STILL WHERE THE PEELER LEFT THEM. Clitic peeling
    covered sentences the table could not read, and a verification pass
    judged 22 of 108 peeled Hebrew forms wrong — different words, not near
    misses: מחברות read as "from friends" when it is "notebooks". Persian
    was 10 of 11. Peeling is off for both; do not restore coverage by
    re-enabling it.
    """
    import unicodedata

    def _tokens(text):
        out, cur = [], ""
        for ch in text:
            if unicodedata.category(ch).startswith(("L", "M")):
                cur += ch
            else:
                if cur:
                    out.append(cur)
                    cur = ""
        if cur:
            out.append(cur)
        return out

    with (DATA / f"{code}_sentences.tsv").open(encoding="utf-8-sig", newline="") as fh:
        rows = [r["sentence"] for r in csv.DictReader(fh, delimiter="\t")
                if (r.get("sentence") or "").strip()]
    random.seed(11)
    sample = random.sample(rows, min(400, len(rows)))
    total = known = 0
    for sentence in sample:
        for token in _tokens(sentence):
            total += 1
            if semitic_reading(token, code):
                known += 1
    assert known / total > floor, f"{code}: {known}/{total} = {known / total:.3f}"
