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

# Characters that render as NOTHING. A learner cannot see whether they typed
# one, so grading on them fails an answer that looks identical on screen to
# the expected one — the purest form of "it works when I paste it and fails
# when I type it".
#
# Persian is the worst hit: its keyboards insert ZWNJ inside ordinary words
# (می‌روم), so a hand-typed answer and a copied one differ by an invisible
# character and only the copy was accepted. Bidi controls arrive the same way
# from RTL keyboards and clipboards. All of them come off BOTH sides, which
# keeps equality intact, and the result grades CORRECT — there is nothing
# here to coach a learner about.
_INVISIBLE = dict.fromkeys(
    [
        0x00AD,  # soft hyphen
        0x061C,  # Arabic letter mark
        0x200B,  # zero-width space
        0x200C,  # zero-width NON-joiner  (Persian می‌روم)
        0x200D,  # zero-width joiner
        0x200E,  # left-to-right mark
        0x200F,  # right-to-left mark
        0x2060,  # word joiner
        0xFEFF,  # BOM / zero-width no-break space
        *range(0x202A, 0x202F),  # bidi embedding/override controls
        *range(0x2066, 0x206A),  # bidi isolates
    ]
)


def _strip_invisible(text: str) -> str:
    """Drop characters with no glyph — see _INVISIBLE."""
    return text.translate(_INVISIBLE)


def _strip_marks(text: str) -> str:
    """Fold combining marks: você -> voce, está -> esta, ё -> е."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )


def _edit_distance(a: str, b: str, cap: int = 2) -> int:
    """Levenshtein distance, short-circuited at *cap* (only near-misses
    matter — anything farther is just wrong)."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        best = i
        for j, cb in enumerate(b, 1):
            cost = min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (ca != cb),
            )
            cur.append(cost)
            best = min(best, cost)
        if best > cap:
            return cap + 1
        prev = cur
    return prev[-1]


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

    def fold_lookalikes(self, text: str) -> str:
        """Collapse codepoints that render near-identically in this script.

        Default: no folding. Override where a script has letters a learner
        cannot tell apart on a phone screen and keyboards disagree about
        (Arabic ى/ي, Persian ک vs Arabic ك). Used by a COACHING layer, so a
        folded match is still flagged — the point is to say "check the letter
        forms", not to pretend the letters are the same.
        """
        return text

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
        user = _strip_invisible(
            unicodedata.normalize("NFC", user_input).translate(_TYPOGRAPHY_MAP)
        ).strip()
        correct = _strip_invisible(
            unicodedata.normalize("NFC", correct_answer).translate(_TYPOGRAPHY_MAP)
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

        # Layer 2.5: accent-folded match — the RIGHT word with missing or
        # wrong diacritics (voce/você, esta/está, е/ё). Coaches (amber),
        # never fails — even on grammar drills. This must run before the
        # strict-form gate below: that gate is about morphology (is vs am),
        # not typography, and without this layer it was failing accentless
        # answers across every Latin-script language's grammar drills.
        if norm_user and _strip_marks(norm_user) == _strip_marks(norm_correct):
            return (
                AnswerResult.CORRECT_SLOPPY,
                f"Almost — check the accents. Expected: {correct_answer}",
            )

        # Layer 2.6: look-alike letters. Scripts where two codepoints render
        # near-identically and phone keyboards disagree about which one to
        # emit — Arabic ى/ي, Persian ک vs Arabic ك — were failing answers the
        # learner had no way to see were different. Coached (amber), never
        # silently equal: these ARE distinct letters and worth learning.
        if norm_user:
            folded_user = self.fold_lookalikes(norm_user)
            folded_correct = self.fold_lookalikes(norm_correct)
            if folded_user != norm_user or folded_correct != norm_correct:
                if _strip_marks(folded_user) == _strip_marks(folded_correct):
                    return (
                        AnswerResult.CORRECT_SLOPPY,
                        "Almost — check the letter forms. "
                        f"Expected: {correct_answer}",
                    )

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

        # Layer 6: Answer alternatives. Callers disagree on the key —
        # placement sends "answer_alternatives", review/learn sessions send
        # "alternatives" — so accept both (the mismatch silently disabled
        # alternatives for every review card).
        alternatives: list[str] = []
        if card_context is not None:
            alternatives = (
                card_context.get("answer_alternatives")
                or card_context.get("alternatives")
                or []
            )
        for alt in alternatives:
            norm_alt = self.normalize(unicodedata.normalize("NFC", alt).strip())
            if norm_user == norm_alt:
                return AnswerResult.CORRECT, None

        # Default. A near-miss (a couple of letters off — usually a DIFFERENT
        # real word, слышать for слушать) previously failed with no feedback
        # at all; name both words so the learner sees where they diverge.
        if (
            len(norm_user) >= 3
            and len(norm_correct) >= 3
            and _edit_distance(norm_user, norm_correct, cap=2) <= 2
        ):
            return (
                AnswerResult.WRONG,
                f"Close, but that's a different word — compare "
                f"{user_input.strip()} with {correct_answer}.",
            )
        # Every rejection names the expected answer. Silence here read as a
        # bug ("it just says wrong") and left the learner with nothing to
        # learn from the card they'd just failed — the one moment the answer
        # is worth the most.
        typed = user_input.strip()
        if not typed:
            return AnswerResult.WRONG, f"Nothing entered. Expected: {correct_answer}"
        return (
            AnswerResult.WRONG,
            f"Not quite — expected {correct_answer}, you wrote {typed}.",
        )
