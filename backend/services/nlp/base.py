"""
BaseNLP abstract interface and AnswerResult enum for the NLP answer-validation layer.

This module defines:
  - AnswerResult: the four answer judgements (LOCKED values), re-exported by
    services/fsrs.py for the scheduler
  - BaseNLP: ABC with 4 abstract methods and a concrete 6-layer check_answer template
"""
from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from enum import Enum

# ---------------------------------------------------------------------------
# AnswerResult (relocated from srs.py — LOCKED DECISION)
# ---------------------------------------------------------------------------

class AnswerResult(Enum):
    """User answer quality categories.

    LOCKED DECISION — values map directly to SM-2 quality scores via QUALITY_MAP
    and must not be changed without updating dependent code.
    """
    CORRECT = "correct"
    CORRECT_SLOPPY = "correct_sloppy"
    WRONG_FORM = "wrong_form"
    WRONG = "wrong"


# ---------------------------------------------------------------------------
# Mobile keyboard typography (language-agnostic)
# ---------------------------------------------------------------------------

# Phone keyboards rewrite what the learner typed: iOS smart punctuation curls
# apostrophes ('ll -> ’ll), double-space inserts a period (am -> am. ), and
# dictation wraps or capitalizes. None of that is a language error, so
# check_answer undoes it SYMMETRICALLY (both sides mapped, so equal answers
# stay equal) before the grading layers run. A beta tester typed a correct
# "am" on an iPhone and was marked wrong — that class of failure.
_TYPOGRAPHY_MAP = str.maketrans({
    "‘": "'", "’": "'", "‛": "'",  # curly single quotes
    "“": '"', "”": '"', "„": '"',  # curly double quotes
})
_TRAILING_PUNCT = ".,!?;:…。？！"
_WRAPPING_QUOTES = (("'", "'"), ('"', '"'), ("«", "»"))


def _undo_keyboard_typography(user: str, correct: str) -> str:
    """Strip keyboard-added typography from *user*, guarded by *correct*.

    Only removes what the expected answer itself doesn't carry — an answer
    that legitimately ends in punctuation or is quoted stays untouched.
    """
    cleaned = user
    if not (correct and correct[-1] in _TRAILING_PUNCT):
        cleaned = cleaned.rstrip(_TRAILING_PUNCT).rstrip()
    if len(cleaned) > 2 and (not correct or correct[0] not in "'\"«"):
        for opener, closer in _WRAPPING_QUOTES:
            if cleaned.startswith(opener) and cleaned.endswith(closer):
                cleaned = cleaned[1:-1].strip()
                break
    return cleaned


# ---------------------------------------------------------------------------
# BaseNLP ABC
# ---------------------------------------------------------------------------

class BaseNLP(ABC):
    """Abstract base class for language-specific NLP backends.

    Concrete subclasses must implement normalize, lemmatize,
    get_morphological_family, and get_aspect_partner.

    The check_answer template method runs a 6-layer pipeline that is
    language-agnostic; language-specific behaviour is injected through the
    abstract methods above.
    """

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Apply language-specific normalization (lowercasing, diacritic handling, etc.).

        Do NOT apply NFC normalization here — check_answer applies NFC before calling
        this method. Do NOT normalize taa marbuta in the base class; that is
        language-specific.

        Args:
            text: Raw input string (already NFC-normalized).

        Returns:
            Normalized string.
        """

    @abstractmethod
    def lemmatize(self, word: str) -> str:
        """Return the dictionary/base form of *word*.

        Args:
            word: A single token.

        Returns:
            Lemma string.
        """

    @abstractmethod
    def get_morphological_family(self, word: str) -> set[str]:
        """Return the set of surface forms that share the same root/lemma as *word*.

        Must include *word* itself and at least its lemma.

        Args:
            word: A single token.

        Returns:
            Set of related surface forms.
        """

    @abstractmethod
    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        """Return the aspect partner of *verb*, or None if unknown.

        STANDARDIZED SIGNATURE: always takes (verb, card_context=None).
        Layer 5 in check_answer calls self.get_aspect_partner(correct, card_context)
        so all backends must accept both parameters even if they ignore card_context.

        Args:
            verb: The verb surface form.
            card_context: Optional card metadata dict (may contain morphology data).

        Returns:
            Aspect partner surface form, or None.
        """

    # ------------------------------------------------------------------
    # Concrete template method: 6-layer check_answer pipeline
    # ------------------------------------------------------------------

    def check_answer(
        self,
        user_input: str,
        correct_answer: str,
        card_context: dict | None = None,
    ) -> tuple[AnswerResult, str | None]:
        """Run the 6-layer answer validation pipeline.

        Layers (evaluated in order; first match wins):
          1. Exact match after NFC + strip                  -> CORRECT
          2. normalize(user) == normalize(correct)          -> CORRECT
          3. lemmatize(user) == lemmatize(correct)          -> CORRECT_SLOPPY
          4. normalize(user) in morphological_family(correct) -> CORRECT_SLOPPY
          5. normalize(user) == normalize(aspect_partner)   -> WRONG_FORM
          6. normalize(user) in normalized alternatives     -> CORRECT
          Default                                           -> WRONG
        With card_context["card_type"] == "grammar", layers 3-4 grade
        WRONG_FORM instead of CORRECT_SLOPPY — a form drill is testing
        exactly the inflection, so the right lemma in the wrong cell fails.

        Args:
            user_input: The learner's typed answer.
            correct_answer: The expected answer for the card.
            card_context: Optional card metadata dict.  May contain:
                - "answer_alternatives": list[str] — additional correct answers
                - "morphology": dict — language-specific morphology data

        Returns:
            Tuple of (AnswerResult, optional feedback message).
        """
        # Apply NFC normalization as the very first step (research pitfall #1).
        # Then undo phone-keyboard typography: curly quotes map to straight on
        # BOTH sides (symmetric — equality is preserved), and keyboard-added
        # trailing punctuation / wrapping quotes come off the user's input.
        user = unicodedata.normalize("NFC", user_input).translate(
            _TYPOGRAPHY_MAP
        ).strip()
        correct = unicodedata.normalize("NFC", correct_answer).translate(
            _TYPOGRAPHY_MAP
        ).strip()
        user = _undo_keyboard_typography(user, correct)

        # Layer 1: Exact match
        if user == correct:
            return AnswerResult.CORRECT, None

        # Layer 2: Normalized match
        norm_user = self.normalize(user)
        norm_correct = self.normalize(correct)
        if norm_user == norm_correct:
            return AnswerResult.CORRECT, None

        # Grammar drills test the FORM — "is" where "am" belongs is the very
        # thing being drilled, so lemma/family matches (layers 3–4) grade
        # WRONG_FORM instead of passing. Vocabulary keeps the leniency: the
        # word was recalled, the exact inflection is secondary.
        strict_form = bool(
            card_context and card_context.get("card_type") == "grammar"
        )

        # Layer 3: Lemma match
        if self.lemmatize(user) == self.lemmatize(correct):
            if strict_form:
                return (
                    AnswerResult.WRONG_FORM,
                    f"Right word, wrong form. Expected: {correct_answer}",
                )
            return (
                AnswerResult.CORRECT_SLOPPY,
                f"Correct meaning, but check the exact form. Expected: {correct_answer}",
            )

        # Layer 4: Morphological family match
        morph_family_normalized = {
            self.normalize(unicodedata.normalize("NFC", f))
            for f in self.get_morphological_family(correct)
        }
        if norm_user in morph_family_normalized:
            if strict_form:
                return (
                    AnswerResult.WRONG_FORM,
                    f"Right word, wrong form. Expected: {correct_answer}",
                )
            return (
                AnswerResult.CORRECT_SLOPPY,
                f"Right word family, but the exact form differs. Expected: {correct_answer}",
            )

        # Layer 5: Aspect partner check
        partner = self.get_aspect_partner(correct, card_context)
        if partner is not None:
            norm_partner = self.normalize(unicodedata.normalize("NFC", partner).strip())
            if norm_user == norm_partner:
                return (
                    AnswerResult.WRONG_FORM,
                    f"You typed the aspect partner. Expected: {correct_answer}",
                )

        # Layer 6: Answer alternatives
        alternatives: list[str] = []
        if card_context is not None:
            alternatives = card_context.get("answer_alternatives") or []
        for alt in alternatives:
            norm_alt = self.normalize(unicodedata.normalize("NFC", alt).strip())
            if norm_user == norm_alt:
                return AnswerResult.CORRECT, None

        # Default
        return AnswerResult.WRONG, None
