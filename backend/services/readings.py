"""Computed script→Latin readings for example sentences.

A learner of a non-Latin script can't recall — or even sound out — a
sentence they can't read. Where a practical romanizer exists we compute a
reading on the fly (no authoring, no storage) so grammar-path examples can
show it, greyed, ahead of the translation — the same "reading first" order
the review hint layers already use.

Only languages with reliable tooling are covered:
  - hi: the Hunterian-style romanizer used for vocabulary readings
  - ru: cyrtranslit (already a dependency for Latin→Cyrillic answer input)
  - ko: Revised Romanization, with the assimilation rules that make 신라
    read *Silla* rather than *sinla* — Hangul spells morphemes and pronounces
    something else, so a syllable-by-syllable mapping is wrong in a way a
    learner cannot detect
  - th: RTGS, looked up from `data/th_readings.tsv` (Wiktionary's Royal
    Institute readings) and segmented by longest match over that same table,
    so there is no runtime dependency
  - el: ELOT 743, the scheme printed in Greek passports — regular mapping,
    a closed set of digraphs, and the <αυ/ευ> voicing rule that makes «αυτό»
    read *afto*
Arabic, Hebrew and Persian cannot be romanized by RULE at all — the scripts
write consonants and leave the short vowels to the reader — so their readings
are looked up from Wiktionary, with the clitics peeled. See
`backend/services/nlp/semitic_reading.py`, and `scripts/build_semitic_readings.py`
for the standard each one follows.

Thai took two attempts. Computing it failed adversarial verification on
ordinary words, so it is LOOKED UP instead, from a committed table built out
of Wiktionary's Royal Institute readings — see `thai_reading.py`. It covers
99% of the vocabulary and 89% of sentences, and returns nothing rather than a
partial line for the rest. RTGS carries no tone, so a Thai reading
approximates a word rather than pronouncing it.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

READING_LANGS = ("hi", "ru", "el", "ko", "th", "ar", "he", "fa")

# Courses that additionally carry a PHONETICS line beneath the romanisation.
# A romanisation says which letters; phonetics says how to say them. Thai needs
# it because RTGS drops tone entirely and Thai is tonal — คำ and ค่ำ are both
# "kham" — so the reading alone tells a learner how to approximate a word
# rather than how to pronounce it. Owner decision 26 Aug 2026; the layer is
# built general because other courses are expected to follow.
PHONETICS_LANGS = ("th",)


def sentence_reading(text: str | None, language_code: str) -> str | None:
    """A romanized reading for *text*, or None when unavailable/not needed."""
    if not text or not text.strip():
        return None
    try:
        if language_code == "hi":
            from backend.services.nlp.hindi import devanagari_to_roman
            reading = devanagari_to_roman(text)
        elif language_code == "ru":
            import cyrtranslit
            reading = cyrtranslit.to_latin(text, "ru")
        elif language_code in ("ar", "he", "fa"):
            from backend.services.nlp.semitic_reading import semitic_reading
            reading = semitic_reading(text, language_code)
        elif language_code == "th":
            from backend.services.nlp.thai_reading import thai_to_roman
            reading = thai_to_roman(text)
        elif language_code == "ko":
            from backend.services.nlp.korean_reading import korean_to_roman
            reading = korean_to_roman(text)
        elif language_code == "el":
            from backend.services.nlp.greek_reading import greek_to_roman
            reading = greek_to_roman(text)
        else:
            return None
    except Exception as exc:  # noqa: BLE001 — a missing reading must never 500
        logger.warning("reading failed for %s: %s", language_code, exc)
        return None
    reading = (reading or "").strip()
    # Nothing romanizable (already Latin, punctuation only) → no reading line.
    return reading or None


def sentence_phonetics(text: str | None, language_code: str) -> str | None:
    """A pronunciation line for *text* — the romanisation's letters carrying
    the marks the romanisation itself cannot express. None when the course has
    no phonetics layer, or the text is not covered."""
    if not text or not text.strip() or language_code not in PHONETICS_LANGS:
        return None
    try:
        if language_code == "th":
            from backend.services.nlp.thai_reading import thai_to_roman
            out = (thai_to_roman(text, "phonetics") or "").strip()
        else:
            return None
    except Exception as exc:  # noqa: BLE001 — a hint must never 500
        logger.warning("phonetics failed for %s: %s", language_code, exc)
        return None
    return out or None
