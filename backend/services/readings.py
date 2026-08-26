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
  - el: ELOT 743, the scheme printed in Greek passports — regular mapping,
    a closed set of digraphs, and the <αυ/ευ> voicing rule that makes «αυτό»
    read *afto*
Arabic is deliberately absent — unvocalized script drops the short vowels a
romanization would need, so a computed reading would mislead.

Thai is absent too, and that one was MEASURED rather than assumed. The
romanizer exists (`backend/services/nlp/thai_reading.py`) and is deliberately
not wired here: both available engines fail on ordinary words. See that
module's docstring and `test_thai_reading_is_not_ready.py` for the numbers.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

READING_LANGS = ("hi", "ru", "el", "ko")


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
