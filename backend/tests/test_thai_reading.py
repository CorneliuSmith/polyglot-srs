"""Thai's reading layer — looked up, not computed, and that is the point.

The first attempt computed RTGS with pythainlp's engines and failed the same
adversarial verification Greek and Korean passed with one systematic defect
each: 38 defects over 60 corpus sentences in seven classes, 6/18 on the
confirmed set. The misses were ordinary words — สุขภาพ (health), อิสระ
(freedom), ฝรั่งเศส (France), and ไหม, the question particle ending a large
share of all Thai questions, read as two syllables *haimai*.

Reading WHICH words failed is what solved it. They were lexical failures, not
rule failures: Pali-derived compounds whose linking syllable no rule predicts,
and the silent leading ห that marks tone class rather than a sound. A
dictionary fixes exactly that class — and the repo already had one on disk.
"""
import csv

import pytest

from backend.services.nlp.thai_reading import READINGS_TSV, thai_to_roman
from backend.services.readings import READING_LANGS, sentence_reading

# (word, RTGS) — every one of these was WRONG under the computed engines.
FORMERLY_WRONG = [
    ("ไหม", "mai"),            # was haimai: silent ho-nam read as /h/
    ("ไหน", "nai"),
    ("สุขภาพ", "suk-kha-phap"),  # was sukphap: linking syllable dropped
    ("มุสลิม", "mut-sa-lim"),    # was mutlim
    ("อิสระ", "it-sa-ra"),       # was isara: closed first syllable lost
    ("ฝรั่งเศส", "fa-rang-set"),  # was frangset: invented an /fr/ cluster
    ("พิเศษ", "phi-set"),        # was thiset: wrong initial consonant
    ("เคาะ", "kho"),            # was khao: wrong vowel quality
]


@pytest.mark.parametrize("word,rtgs", FORMERLY_WRONG, ids=[w for w, _ in FORMERLY_WRONG])
def test_the_words_that_sank_the_computed_version(word, rtgs):
    assert thai_to_roman(word) == rtgs


def test_thai_has_a_reading_at_all():
    assert "th" in READING_LANGS
    assert sentence_reading("สวัสดี", "th") == "sa-wat-di"


def test_a_sentence_reads_word_by_word():
    assert sentence_reading("เขาเป็นคนไทย ใช่ไหม?", "th") == \
        "khao pen khon thai chai mai?"
    assert sentence_reading("ผมชอบอาหารไทย", "th") == "phom chop a-han thai"


def test_a_partial_reading_is_no_reading():
    """A line with a hole in it is read as a whole by someone who cannot see
    the hole. `ปาร์ก` (the loan 'Park') has no dictionary entry, so any text
    containing it gets nothing rather than a gap."""
    assert thai_to_roman("ปาร์ก") == ""
    assert thai_to_roman("ถนนปาร์ก") == ""


def test_both_blank_conventions_survive_with_their_spacing():
    """Thai carries no spaces of its own, so a blank lands flush against the
    words either side. The reading is computed from the CLOZE, so romanising
    must never spell the hidden word — CHECKS.md §11."""
    assert sentence_reading("ผมกิน{{answer}}ทุกวัน", "th") == \
        "phom kin {{answer}} thuk-wan"
    assert sentence_reading("ผมไป___โรงเรียน", "th") == "phom pai ___ rong-rian"


def test_punctuation_hugs_and_latin_passes_through():
    assert "John" in (sentence_reading("เขาชื่อ John ครับ", "th") or "")


def test_the_table_ships_and_is_well_formed():
    """The layer is a committed file, not a dependency: segmentation is a
    longest-match walk over this same table, so nothing needs installing at
    runtime. pythainlp is an optional extra used only to regenerate it."""
    assert READINGS_TSV.exists(), "data/th_readings.tsv is the whole layer"
    with READINGS_TSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) > 3000
    assert all(r["word"] and r["rtgs"] for r in rows)
    # RTGS is plain ASCII by construction; a stray Thai character would mean a
    # row that decodes nothing, which is the failure mode of the old engine.
    assert not any(any("฀" <= c <= "๿" for c in r["rtgs"]) for r in rows)


def test_the_runtime_needs_no_thai_dependency():
    """Guards the design decision. If someone reintroduces a pythainlp import
    at module scope, the reading layer silently becomes a 144 MB dependency
    again — and camel-tools already killed one DigitalOcean image build."""
    import backend.services.nlp.thai_reading as module
    source = open(module.__file__, encoding="utf-8").read()
    assert "import pythainlp" not in source
    assert "from pythainlp" not in source


def test_coverage_has_not_silently_dropped():
    """A ratchet. The layer is worth having at 89% of sentences; a table
    regenerated against a thinner extract would quietly halve that and still
    pass every other test here."""
    with open("data/th_sentences.tsv", encoding="utf-8-sig", newline="") as handle:
        sentences = [(r.get("sentence") or "").strip()
                     for r in csv.DictReader(handle, delimiter="\t")]
    sentences = [s for s in sentences if s]
    covered = sum(1 for s in sentences if thai_to_roman(s))
    assert covered / len(sentences) > 0.85, (
        f"only {covered}/{len(sentences)} sentences have a reading")


THAI_CODAS = ("k", "ng", "t", "n", "p", "m")


def test_no_reading_closes_a_syllable_on_a_sound_thai_cannot_make():
    """Thai closes a syllable only on k ng t n p m or a vowel. Wiktionary's
    loanword rows are spelled from the SOURCE language instead of transcribed
    — บราซิล as *bra-sil*, กรีซ as *kris* — and contradict the native rows in
    the same table (บอล bon, บิล bin). 59 rows were folded onto the RTGS
    final-consonant map; this stops a regenerated table reintroducing them."""
    with READINGS_TSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    bad = []
    for row in rows:
        for syllable in row["rtgs"].split("-"):
            if not syllable or not syllable[-1].isalpha():
                continue
            if syllable[-1] in "aeiou" or syllable.endswith(THAI_CODAS):
                continue
            bad.append((row["word"], row["rtgs"]))
            break
    assert not bad, f"{len(bad)} impossible codas, e.g. {bad[:3]}"


def test_the_table_holds_no_bare_letter_names():
    """A single Thai consonant in the table is the letter's NAME (นอ หนู →
    "no"), not a word. Longest-match segmentation then uses it as filler for a
    word the table lacks: `ฉันไม่รู้จักคุณ` came apart into `รู้` plus a
    meaningless `cho`, and produced a confident, wrong reading. Withholding
    the reading is the honest failure."""
    with READINGS_TSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    letters = [r["word"] for r in rows
               if len(r["word"]) == 1 and "ก" <= r["word"] <= "ฮ"]
    assert not letters, f"letter names in the table: {letters}"
    assert thai_to_roman("ฉันไม่รู้จักคุณ") == "", "segmentation must fail loudly"


def test_the_words_a_bad_rule_broke_are_still_right():
    """A regression pin with a story. Correcting the medial-ส loanwords by
    RULE — 'the word contains ส, so insert the epenthetic syllable' — fired on
    71 rows and turned สวัสดี into *sa-wat-sa-di*, the most common word in the
    language. Placing that epenthesis needs a syllable-aligned parse of the
    Thai, which is precisely the work this lookup table exists to avoid, so
    the unresolvable rows are EXCLUDED by name instead (0.5% of sentences)."""
    for word, rtgs in [("สวัสดี", "sa-wat-di"), ("ตัดสิน", "tat-sin"),
                       ("รถบัส", "rot-bat"), ("สัตว์ป่า", "sat-pa"),
                       ("สุดท้าย", "sut-thai")]:
        assert thai_to_roman(word) == rtgs
    # ...while the native words that DO show the epenthesis keep it.
    assert thai_to_roman("ทศวรรษ") == "thot-sa-wat"
    assert thai_to_roman("โฆษณา") == "khot-sa-na"


def test_the_unresolved_loanwords_get_no_reading_rather_than_a_guess():
    """ออสเตรเลีย is ออด-สะ-เตฺร-เลีย — four syllables — and Wiktionary's column
    gives a three-syllable os-tre-lia. Two independent refuters said the
    reading was wrong and two, checking the source, said the source itself was.
    Where the evidence splits, the layer withholds."""
    assert thai_to_roman("ออสเตรเลีย") == ""
    assert thai_to_roman("คุณไปเที่ยวที่ไหนในออสเตรเลีย") == ""


def test_the_phonetics_layer_carries_the_tone_the_reading_cannot():
    """RTGS drops tone and Thai is tonal, so the reading alone tells a learner
    how to approximate a word rather than how to say it. Paiboon has the tone
    but writes 32% of its entries in IPA letters no learner reads. The
    phonetics line is the RTGS spelling with Paiboon's marks moved onto it,
    syllable by syllable — readable letters, real tone."""
    from backend.services.readings import sentence_phonetics
    assert thai_to_roman("กฎหมาย") == "kot-mai"
    assert thai_to_roman("กฎหมาย", "phonetics") == "kòt-mǎi"
    assert sentence_phonetics("เขาเป็นคนไทย ใช่ไหม?", "th") == \
        "khǎo pen khon thai châi mǎi?"


def test_only_thai_has_phonetics_today():
    from backend.services.readings import PHONETICS_LANGS, sentence_phonetics
    assert PHONETICS_LANGS == ("th",)
    assert sentence_phonetics("Я живу в Москве.", "ru") is None


def test_every_row_has_a_phonetics_form():
    """The transfer is positional, so it only works while the RTGS and Paiboon
    forms agree on syllable count. All 4,045 rows do; a regenerated table that
    did not would silently drop the layer for those words."""
    with READINGS_TSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert all("phonetics" in r for r in rows)
    filled = [r for r in rows if (r.get("phonetics") or "").strip()]
    assert len(filled) == len(rows), f"{len(rows) - len(filled)} rows lost the tone"
