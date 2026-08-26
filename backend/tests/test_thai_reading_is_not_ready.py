"""Why Thai has no reading layer — the measurement, kept executable.

Thai was the last non-Roman script in this corpus with no romanisation. The
seeder deferred it as "romanization with tones ... rather than shipped wrong",
and unlike Korean's deferral ("Hangul is phonetic", true only for someone who
can already read it) that reasoning survived scrutiny. This file is the
scrutiny.

A full RTGS romanizer WAS built (`backend/services/nlp/thai_reading.py`) on
pythainlp — a real segmenter, since Thai marks no word boundaries — and put
through the same adversarial verification that Greek and Korean passed with
one systematic defect each. Thai returned **38 claimed defects over 60 corpus
sentences in seven distinct classes**, and on the confirmed set the better of
the two available engines scores 6/18.

The failures are not exotic. They are `สุขภาพ` (health), `อิสระ` (freedom),
`ฝรั่งเศส` (France) and `ไหม` — the question particle that ends a large share
of all Thai questions, which comes out as two syllables, *haimai*.

So `th` is deliberately absent from `READING_LANGS`, and pythainlp is an
optional extra rather than a dependency. These tests pin the gap so that
whoever closes it — a better engine, or the native reviewer the seeder asked
for — can see immediately when it is closed. **They are written to pass
TODAY, asserting the failures that exist**, because a red suite nobody can
fix is noise. When one starts failing, the engine got better; delete the row
and move it into the shipping set.
"""
import pytest

from backend.services.readings import READING_LANGS, sentence_reading

pythainlp = pytest.importorskip(
    "pythainlp", reason="optional extra: pip install -e '.[thai]'")


def test_thai_has_no_reading_layer():
    """The guard that matters: nothing wires this in by accident."""
    assert "th" not in READING_LANGS
    assert sentence_reading("สวัสดี", "th") is None


# (word, what RTGS says, what the romanizer currently produces)
KNOWN_WRONG = [
    ("ไหม", "mai", "haimai"),        # question particle; silent ho-nam read as /h/
    ("สุขภาพ", "sukkhaphap", "sukphap"),    # linking syllable dropped
    ("มุสลิม", "mutsalim", "mutlim"),        # linking syllable dropped
    ("อิสระ", "itsara", "isara"),            # closed first syllable lost
    ("ฝรั่งเศส", "farangset", "frangset"),   # invents an /fr/ cluster Thai lacks
    ("ปาร์ก", "pak", "pa"),                  # live final consonant dropped
    ("เคาะ", "kho", "khao"),                 # wrong vowel quality
]


@pytest.mark.parametrize("word,rtgs,current", KNOWN_WRONG,
                         ids=[w for w, _, _ in KNOWN_WRONG])
def test_the_known_failures_are_still_the_known_failures(word, rtgs, current):
    """A ratchet on a gap rather than on a feature. If this fails because the
    output changed, check it against `rtgs`: either the engine improved (good
    — move this row out) or it regressed differently (also worth knowing)."""
    from backend.services.nlp.thai_reading import thai_to_roman
    got = thai_to_roman(word)
    assert got != rtgs, (
        f"{word} now romanizes correctly as {rtgs!r} — the engine improved. "
        "Drop this row and re-run the adversarial check; Thai may be shippable.")
    assert got == current, f"{word}: expected the known-wrong {current!r}, got {got!r}"


def test_the_repetition_mark_was_fixable_and_is_fixed():
    """ๆ (mai yamok) is not a letter — it repeats the preceding word. Fed to
    the neural engine as a token it hallucinated a syllable from nothing:
    มากๆ → *mak wi*, นานๆ → *nano*, ต่างๆ → *tango*. Expanding it before
    romanising is deterministic, so it is fixed even though the layer does not
    ship — it is one class the next person does not have to rediscover."""
    from backend.services.nlp.thai_reading import thai_to_roman
    assert thai_to_roman("มากๆ") == "mak mak"
    assert thai_to_roman("นานๆ") == "nan nan"
    assert thai_to_roman("ต่างๆ") == "tang tang"


def test_the_repetition_mark_still_repeats_too_much_after_a_compound():
    """The residual: the tokenizer hands back แย่มาก as ONE token, so ๆ doubles
    the whole compound — *yaemak yaemak* where RTGS wants *yae mak mak*.
    Fixing this needs syllable-level segmentation, not another rule here."""
    from backend.services.nlp.thai_reading import thai_to_roman
    assert thai_to_roman("แย่มากๆ") == "yaemak yaemak"


def test_what_does_work_still_works():
    """Not everything is broken, which is exactly why this was worth measuring
    rather than assuming. Segmentation and the common vocabulary are fine; it
    is the Pali-derived compounds and the silent ho-nam that are not."""
    from backend.services.nlp.thai_reading import thai_to_roman
    assert thai_to_roman("ผมชอบอาหารไทย") == "phom chop ahan thai"
    assert thai_to_roman("มหาวิทยาลัย") == "mahawitthayalai"
    assert thai_to_roman("ผมกิน{{answer}}ทุกวัน") == "phom kin {{answer}} thukwan"
