"""
HausaNLP backend — normalization for the Boko (Latin) orthography.

Hausa-specific behaviour:
  - Normalization: lowercase + strip, and fold the several Unicode variants of
    the glottal apostrophe (ʼ U+02BC, ’ U+2019, ' U+0027) to one form so
    "yaʼya" / "ya'ya" / "ya’ya" all match. The hooked consonants ɓ ɗ ƙ are
    distinct letters and are preserved.
  - Lemmatization: Hausa plurals are famously irregular (dozens of patterns,
    largely unpredictable), and tone/vowel-length are not written, so there is
    no safe productive stemmer. lemmatize() therefore returns the normalized
    surface form — better to grade an inflected form via the exact/alternatives
    layers than to guess wrong. Irregular plurals belong in the card's
    `alternatives` / morphology data, not in a rule.
  - No aspect-pair system — get_aspect_partner returns None.

This is intentionally a thin backend: for Hausa, accuracy comes from good
seed data (plurals stored as alternatives) rather than morphological rules.
"""
from __future__ import annotations

from backend.services.nlp.base import BaseNLP

# Map the apostrophe variants used for glottalization to a single canonical form.
_APOSTROPHES = {
    "ʼ": "'",  # ʼ modifier letter apostrophe
    "’": "'",  # ’ right single quotation mark
    "‘": "'",  # ‘ left single quotation mark
    "ˈ": "'",  # ˈ
}


def normalize_hausa(text: str) -> str:
    """Lowercase, strip, and canonicalize glottal-apostrophe variants."""
    text = text.strip().lower()
    for variant, canonical in _APOSTROPHES.items():
        text = text.replace(variant, canonical)
    return text


class HausaNLP(BaseNLP):
    """Hausa NLP backend (Boko orthography; thin, data-driven)."""

    def normalize(self, text: str) -> str:
        return normalize_hausa(text)

    def lemmatize(self, word: str) -> str:
        """Return the normalized surface form (no safe stemmer for Hausa)."""
        return normalize_hausa(word)

    def get_morphological_family(self, word: str) -> set[str]:
        """Return the normalized form only.

        Irregular Hausa plurals can't be derived by rule; store them in the
        card's alternatives/morphology instead so the answer-validation
        alternatives layer handles them.
        """
        return {normalize_hausa(word)}

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Hausa has no aspect-pair system — always returns None."""
        return None
