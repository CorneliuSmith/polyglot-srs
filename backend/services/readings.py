"""Computed script→Latin readings for example sentences.

A learner of a non-Latin script can't recall — or even sound out — a
sentence they can't read. Where a practical romanizer exists we compute a
reading on the fly (no authoring, no storage) so grammar-path examples can
show it, greyed, ahead of the translation — the same "reading first" order
the review hint layers already use.

Only languages with reliable tooling are covered:
  - hi: the Hunterian-style romanizer used for vocabulary readings
  - ru: cyrtranslit (already a dependency for Latin→Cyrillic answer input)
Arabic is deliberately absent — unvocalized script drops the short vowels a
romanization would need, so a computed reading would mislead.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

READING_LANGS = ("hi", "ru")


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
        else:
            return None
    except Exception as exc:  # noqa: BLE001 — a missing reading must never 500
        logger.warning("reading failed for %s: %s", language_code, exc)
        return None
    reading = (reading or "").strip()
    # Nothing romanizable (already Latin, punctuation only) → no reading line.
    return reading or None
