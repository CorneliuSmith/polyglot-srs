"""
Russian NLP backend using pymorphy3 morphological analysis.

Covers NLP-03, NLP-04, NLP-05:
  - NLP-03: Lemmatization and morphological family via pymorphy3
  - NLP-04: Latin-to-Cyrillic transliteration fallback (cyrtranslit)
  - NLP-05: Aspect partner detection from card_context morphology JSONB

Design notes:
  - normalize() is lowercase + strip only — standard Cyrillic has no diacritics.
  - MorphAnalyzer is instantiated at module level (singleton per research).
  - get_aspect_partner() reads from card_context only — pymorphy3 does not
    provide aspect partner data (research pitfall #2).
  - check_answer() overrides the base to add a transliteration pre-check:
    if input is ASCII, transliterate to Cyrillic and compare before delegating
    to the 6-layer base pipeline.
"""
from __future__ import annotations

import logging
import unicodedata

from backend.services.nlp.base import AnswerResult, BaseNLP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level pymorphy3 + cyrtranslit initialization
# ---------------------------------------------------------------------------

try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer()
except ImportError as _exc:
    logger.warning("pymorphy3 not installed — Russian NLP disabled: %s", _exc)
    _morph = None  # type: ignore[assignment]

try:
    import cyrtranslit
except ImportError as _exc:
    logger.warning("cyrtranslit not installed — transliteration disabled: %s", _exc)
    cyrtranslit = None  # type: ignore[assignment]


def _is_ascii(text: str) -> bool:
    """Return True if text contains only ASCII characters."""
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


class RussianNLP(BaseNLP):
    """Russian NLP backend with pymorphy3 morphological analysis.

    Provides lemmatization, morphological family enumeration,
    Latin-to-Cyrillic transliteration fallback, and aspect partner
    detection from card context.
    """

    def normalize(self, text: str) -> str:
        """Lowercase and strip whitespace.

        Russian Cyrillic has no diacritics to strip in standard usage.
        """
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        """Return the dictionary form of *word* via pymorphy3.

        Uses the first (highest-scoring) parse result's normal_form.
        Falls back to word.lower() if pymorphy3 is unavailable.
        """
        if _morph is None:
            return word.lower()
        return _morph.parse(word.lower())[0].normal_form

    def get_morphological_family(self, word: str) -> set[str]:
        """Return all inflected forms sharing the same lemma as *word*.

        Uses pymorphy3's lexeme enumeration. Falls back to {word, lemma}
        if pymorphy3 is unavailable.
        """
        if _morph is None:
            return {word, word.lower()}
        parsed = _morph.parse(word.lower())[0]
        return {form.word for form in parsed.lexeme}

    def get_aspect_partner(
        self, verb: str, card_context: dict | None = None
    ) -> str | None:
        """Return the aspect partner from card_context morphology data.

        Does NOT compute aspect partners from pymorphy3 — it doesn't have
        them (research pitfall #2). Relies entirely on curator-provided
        card_context["morphology"]["aspect_partner"].
        """
        if card_context is None:
            return None
        morphology = card_context.get("morphology")
        if morphology is None:
            return None
        return morphology.get("aspect_partner")

    # ------------------------------------------------------------------
    # Overridden check_answer with transliteration pre-check (NLP-04)
    # ------------------------------------------------------------------

    def check_answer(
        self,
        user_input: str,
        correct_answer: str,
        card_context: dict | None = None,
    ) -> tuple[AnswerResult, str | None]:
        """Run the 6-layer pipeline with a transliteration pre-check.

        If the user typed ASCII text (Latin keyboard), transliterate it to
        Cyrillic and compare. If the transliterated form matches the
        normalized correct answer, return CORRECT_SLOPPY with a nudge to
        switch to Cyrillic keyboard.

        Otherwise, delegate to the base 6-layer pipeline.
        """
        user = unicodedata.normalize("NFC", user_input).strip()
        correct = unicodedata.normalize("NFC", correct_answer).strip()

        # Transliteration pre-check: only when input is ASCII and cyrtranslit is available
        if cyrtranslit is not None and _is_ascii(user) and user:
            transliterated = cyrtranslit.to_cyrillic(user, "ru")
            if self.normalize(transliterated) == self.normalize(correct):
                return (
                    AnswerResult.CORRECT_SLOPPY,
                    "Correct! Use Cyrillic next time.",
                )

        return super().check_answer(user_input, correct_answer, card_context)
