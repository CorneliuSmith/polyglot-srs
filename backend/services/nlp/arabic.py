"""
Arabic NLP backend using camel-tools morphological analysis.

Covers NLP-06, NLP-07, NLP-08:
  - NLP-06: Normalization (tashkeel stripping, alef normalization, tatweel removal,
            lemmatization with camel-tools Analyzer, root extraction)
  - NLP-07: Diacritic-invariant answer validation — answers never fail purely on
            tashkeel presence/absence
  - NLP-08: Verb form detection — same root, different pattern → WRONG_FORM

Design notes:
  - normalize() strips diacritics, normalizes alef variants, and removes tatweel.
  - normalize() does NOT normalize taa marbuta (ة → ه) — per research pitfall #6
    that conflates semantically distinct words.
  - Taa marbuta vs ha difference is caught in the overridden check_answer() as
    CORRECT_SLOPPY.
  - get_aspect_partner() always returns None — Arabic verb aspect is handled through
    verb form detection, not Russian-style imperfective/perfective pairs.
  - Module-level Analyzer initialization is wrapped in try/except so the app starts
    even when camel-tools data has not been downloaded yet.
"""
from __future__ import annotations

import logging
import re

from backend.services.nlp.arabic_script import TASHKEEL as _TASHKEEL
from backend.services.nlp.arabic_script import fold_arabic_script
from backend.services.nlp.base import AnswerResult, BaseNLP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level camel-tools initialization
# ---------------------------------------------------------------------------

_analyzer = None

try:
    from camel_tools.morphology.analyzer import Analyzer
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.utils.dediac import dediac_ar

    _db = MorphologyDB.builtin_db()
    _analyzer = Analyzer(_db, backoff="NOAN_PROP")
    logger.info("camel-tools Analyzer initialized successfully (calima-msa-r13)")
except Exception as exc:  # noqa: BLE001
    logger.warning(
        "camel-tools Analyzer unavailable — Arabic NLP will use fallback mode: %s", exc
    )

    # Provide stub implementations so the rest of the module compiles even when
    # camel-tools is not installed.
    def dediac_ar(text: str) -> str:  # type: ignore[misc]
        """Fallback: remove Arabic diacritics via Unicode range."""
        # Tashkeel is U+064B–U+065F, Shadda is U+0651, Sukun is U+0652, etc.
        return re.sub(r"[\u064b-\u065f]", "", text)



# Tatweel character (Arabic kashida, used for elongation)
_TATWEEL = "\u0640"

# Alef maqsura \u0649 (U+0649) and Farsi yeh \u06cc (U+06CC) \u2192 Arabic yeh \u064a (U+064A).
# The same shape at the end of a word; which one a learner produces is
# decided by their keyboard, not their knowledge.
_YEH_FOLD = str.maketrans("\u0649\u06cc", "\u064a\u064a")

# Taa marbuta → ha mapping for the secondary soft-match check
_TAA_MARBUTA = "\u0629"  # ة
_HA = "\u0647"  # ه


def _taa_to_ha(text: str) -> str:
    """Replace taa marbuta with ha for soft-match comparison."""
    return text.replace(_TAA_MARBUTA, _HA)


def _extract_root(analyses: list[dict]) -> str | None:
    """Extract the most-probable root from a camel-tools analysis list.

    Analyses are sorted by pos_lex_logprob (least-negative = most likely first).
    Returns the root string from the best analysis, or None if unavailable.
    """
    if not analyses:
        return None
    try:
        sorted_analyses = sorted(
            analyses,
            key=lambda a: a.get("pos_lex_logprob", float("-inf")),
            reverse=True,
        )
        root = sorted_analyses[0].get("root")
        return root if root and root not in ("NONE", "NO_ROOT") else None
    except Exception:  # noqa: BLE001
        return None


def _clean_lex(lex: str) -> str:
    """Strip sense-ID suffix from camel-tools lex field.

    camel-tools appends "_N" (e.g. "كَتَب_1") to disambiguate homographs.
    We remove the suffix and then dediacritize the lemma.
    """
    cleaned = re.sub(r"_\d+$", "", lex)
    return dediac_ar(cleaned)


class ArabicNLP(BaseNLP):
    """Arabic NLP backend with camel-tools morphological analysis.

    Falls back to regex-based diacritic stripping when camel-tools data is not
    installed, so tests can import the class regardless.
    """

    # ------------------------------------------------------------------
    # Core abstract-method implementations
    # ------------------------------------------------------------------

    def normalize(self, text: str) -> str:
        """Normalize Arabic text for comparison.

        Steps (order matters):
          1. Strip leading/trailing whitespace
          2. Strip tashkeel (diacritics) via dediac_ar
          3. Normalize yeh variants (ى / Farsi ی → ي)
          4. Remove tatweel (kashida, U+0640)

        **Alef variants are deliberately NOT folded here.** They used to be,
        and it merged 118 cards onto other cards at layer 2 — before any
        coaching layer or the collision guard could see them, so they graded
        full CORRECT. The damage sat at the very top of the list: rank 1 أن
        ("to, that") was the same card as إن ("if") and آن ("time"); rank 4
        كان ("to be") as كأن ("as if"); rank 21 هنا ("here") as هنأ ("to be
        wholesome"); rank 33 أمر ("to order") as آمر ("to ask advice of").
        The hamza seat is a spelling rule learners get wrong, so the fold
        still belongs — but as COACHING, which is what fold_lookalikes is
        for. It already carries every alef shape (_ALEF in arabic_script.py),
        so dropping it here loses no leniency: a learner typing انا for أنا
        still passes, now amber with the proper spelling named, and a learner
        typing a genuinely different word is told so.

        Yeh sits here rather than in the coaching fold: word-final ى vs ي is
        a keyboard difference more than a knowledge difference (Egyptian
        orthography writes ي for both), and the owner's call is that typing
        the dotless form is simply right — green, not amber. That call has a
        measured cost, recorded in docs/quality/ar.md: it merges 84 further
        cards, including rank 8 على ("on") with rank 144 علي ("to be
        exalted"). Kaf/heh variants stay in fold_lookalikes, where a match is
        accepted but the proper form is still named.

        Intentionally does NOT normalize taa marbuta (ة → ه) to avoid
        conflating semantically distinct words (research pitfall #6).

        Args:
            text: Raw Arabic string (already NFC-normalized by check_answer).

        Returns:
            Normalized string suitable for comparison.
        """
        text = text.strip()
        text = dediac_ar(text)
        text = text.translate(_YEH_FOLD)
        text = text.replace(_TATWEEL, "")
        return text

    def fold_lookalikes(self, text: str) -> str:
        """Fold yeh/alef-maqsura, kaf, heh and presentation forms.

        The failure this fixes: إلى ends in alef maqsura ى, phone keyboards
        offer ي, and the two are the same shape at the end of a word. Every
        learner typing that preposition — one of the commonest words in the
        language — was marked wrong unless they pasted it.
        """
        return fold_arabic_script(text)

    def lemmatize(self, word: str) -> str:
        """Return the base/dictionary form of *word* using camel-tools.

        Uses the 'lex' field from the highest-probability analysis.  If no
        analysis is found, returns the dediacritized input as a fallback.

        Args:
            word: A single Arabic token (may contain diacritics).

        Returns:
            Lemma string (no diacritics, no sense-ID suffix).
        """
        if _analyzer is None:
            return dediac_ar(word)

        try:
            # Analyze the dediacritized form for more consistent results
            bare = dediac_ar(word)
            analyses = _analyzer.analyze(bare)
            if not analyses:
                return bare

            # Sort by pos_lex_logprob descending (most likely analysis first)
            sorted_analyses = sorted(
                analyses,
                key=lambda a: a.get("pos_lex_logprob", float("-inf")),
                reverse=True,
            )
            lex = sorted_analyses[0].get("lex", "")
            if lex and lex not in ("", "NONE"):
                return _clean_lex(lex)
            return bare
        except Exception:  # noqa: BLE001
            return dediac_ar(word)

    def get_morphological_family(self, word: str) -> set[str]:
        """Return a minimal morphological family for *word*.

        Returns a set containing the input word and its lemma.  Full Generator
        enumeration via camel-tools is too slow for real-time use; the 6-layer
        pipeline in check_answer catches most matches at the lemma layer (Layer 3)
        before reaching this method.

        Args:
            word: A single Arabic token.

        Returns:
            Set of related surface forms.
        """
        return {word, self.lemmatize(word)}

    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        """Arabic has no Russian-style aspect partner system.

        Arabic verb aspect (past/present/imperative) is handled through verb form
        detection in check_answer(), not through imperfective/perfective pairs.

        Args:
            verb: Arabic verb surface form (unused).
            card_context: Optional card metadata dict (unused).

        Returns:
            Always None.
        """
        return None

    # ------------------------------------------------------------------
    # Overridden check_answer with Arabic-specific post-processing
    # ------------------------------------------------------------------

    def check_answer(
        self,
        user_input: str,
        correct_answer: str,
        card_context: dict | None = None,
    ) -> tuple[AnswerResult, str | None]:
        """Run the 6-layer pipeline and apply Arabic-specific enhancements.

        After calling the parent pipeline, two additional Arabic checks run
        in order of specificity:

          A. Taa marbuta soft-match: if the only difference between the
             normalized forms is ة vs ه, return CORRECT_SLOPPY (upgrades WRONG).

          B. Verb form detection: if user and correct share the same root but
             have different lemmas, return WRONG_FORM with a root display
             (applies when parent returned WRONG).

        Args:
            user_input: Learner's typed answer.
            correct_answer: Expected answer from the card.
            card_context: Optional card metadata (may contain morphology.root).

        Returns:
            Tuple of (AnswerResult, optional feedback message).
        """
        import unicodedata

        # The alphabet deck asks for a single letter, and a phone's long-press
        # row offers أ/إ/آ where the card shows bare ا. On a one-letter answer
        # the hamza seat cannot be "a different word" — there is no word — so
        # this stays fully CORRECT, as it was before the alef fold moved out
        # of normalize() for the vocabulary's sake.
        stripped_correct = unicodedata.normalize("NFC", correct_answer).strip()
        if len(stripped_correct) == 1:
            typed_one = unicodedata.normalize("NFC", user_input).strip()
            if fold_arabic_script(typed_one) == fold_arabic_script(stripped_correct):
                return AnswerResult.CORRECT, None

        # Run parent pipeline first
        base_result, base_msg = super().check_answer(user_input, correct_answer, card_context)

        # NFC + strip (mirror what BaseNLP does internally so our extras match)
        user = unicodedata.normalize("NFC", user_input).strip()
        correct = unicodedata.normalize("NFC", correct_answer).strip()

        norm_user = self.normalize(user)
        norm_correct = self.normalize(correct)

        # ------------------------------------------------------------------
        # Check 0: the short vowels ARE the answer on a form drill
        # ------------------------------------------------------------------
        # normalize() dediacritizes, so tashkeel never reaches the comparison
        # — right for ordinary vocabulary, where the marks are optional and
        # failing on them is the diacritic-invariance rule (NLP-07). On a
        # GRAMMAR drill it erased the very contrast being taught: وُلد ("was
        # born") accepted its active ولد inside a point whose explanation
        # says the passive changes the verb's vowels and not its letters,
        # أنتِ accepted the masculine أنت sitting in the same point, and
        # Form II يدرّس accepted Form I يدرس.
        #
        # So only where the author DELIBERATELY vocalized the answer, and
        # only on a form drill, a bare answer is the right word in the wrong
        # cell — which is exactly what WRONG_FORM already means here.
        # CORRECT_SLOPPY counts too: since the alef fold moved out of
        # normalize() into the coaching layer, a bare أعلن for a vocalized
        # أُعلن arrives here as sloppy rather than correct. How the learner
        # got to the right letters does not change that the vowels were the
        # point of the drill.
        if (
            base_result in (AnswerResult.CORRECT, AnswerResult.CORRECT_SLOPPY)
            and card_context
            and card_context.get("card_type") == "grammar"
            and _TASHKEEL.search(correct)
            and _TASHKEEL.findall(user) != _TASHKEEL.findall(correct)
        ):
            return (
                AnswerResult.WRONG_FORM,
                "The short vowels are the answer here. "
                f"Expected: {correct_answer}",
            )

        # ------------------------------------------------------------------
        # Check A: Taa marbuta vs ha soft-match (NLP-06 pitfall #6)
        # ------------------------------------------------------------------
        # If normalized forms differ only by ة ↔ ه, it's a close-but-sloppy match.
        # This applies even if the parent already returned CORRECT_SLOPPY (we keep it)
        # or WRONG (we upgrade to CORRECT_SLOPPY).
        if norm_user != norm_correct:
            if _taa_to_ha(norm_user) == _taa_to_ha(norm_correct):
                return (
                    AnswerResult.CORRECT_SLOPPY,
                    "Close -- check taa marbuta (\u0629) vs ha (\u0647)",
                )

        # ------------------------------------------------------------------
        # Check B: Verb form detection (NLP-08)
        # ------------------------------------------------------------------
        # Only applies when the parent returned WRONG — if it already matched
        # at any level (CORRECT, CORRECT_SLOPPY, WRONG_FORM) we don't override.
        if base_result == AnswerResult.WRONG:
            root = self._get_root(user, correct, card_context)
            if root is not None:
                # Format root for display: "ك.ت.ب" → "ك-ت-ب"
                root_display = root.replace(".", "-")
                msg = f"Wrong verb form -- Root: {root_display}"
                if card_context:
                    morph = card_context.get("morphology") or {}
                    verb_form = morph.get("verb_form")
                    if verb_form:
                        msg += f" (Form {verb_form})"
                return AnswerResult.WRONG_FORM, msg

        return base_result, base_msg

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_root(
        self,
        user: str,
        correct: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Return the shared root if user and correct share one, else None.

        Resolution order:
          1. card_context['morphology']['root'] (most reliable — curator-provided)
          2. camel-tools Analyzer root for both words (must match)

        Returns:
            Root string (e.g. "ك.ت.ب") if shared, else None.
        """
        # 1. Context-provided root: assume the user's word must share it
        if card_context:
            morph = card_context.get("morphology") or {}
            ctx_root = morph.get("root")
            if ctx_root:
                # Verify user word also belongs to this root via analyzer
                user_root = self._analyze_root(user)
                if user_root is not None:
                    # Normalize both roots for comparison (strip dots/dashes)
                    u_normalized = re.sub(r"[.\-\s]", "", user_root)
                    c_normalized = re.sub(r"[.\-\s]", "", ctx_root)
                    if u_normalized == c_normalized:
                        return ctx_root
                # Even without analyzer confirmation, trust context root if provided
                # (card curators know the root; user may have typed a form of it)
                return ctx_root

        # 2. Analyzer-based root for both words
        if _analyzer is None:
            return None

        user_root = self._analyze_root(user)
        correct_root = self._analyze_root(correct)

        if user_root and correct_root:
            # Normalize roots for comparison (strip punctuation)
            u_norm = re.sub(r"[.\-\s]", "", user_root)
            c_norm = re.sub(r"[.\-\s]", "", correct_root)
            if u_norm == c_norm and u_norm:
                return correct_root  # Return the correct's root for display

        return None

    def _analyze_root(self, word: str) -> str | None:
        """Extract root from camel-tools analysis of *word*."""
        if _analyzer is None:
            return None
        try:
            bare = dediac_ar(word)
            analyses = _analyzer.analyze(bare)
            return _extract_root(analyses)
        except Exception:  # noqa: BLE001
            return None
