"""
EnglishNLP backend using spaCy lemmatization and lemminflect inflection generation.

Covers NLP-09 requirements:
  - Normalization: lowercase, strip leading articles (the/a/an), strip whitespace
  - Lemmatization: irregular verbs and nouns via spaCy (went -> go, mice -> mouse)
  - Morphological family: all inflected forms via lemminflect.getAllInflections
  - Aspect partner: English has no aspect system, always returns None

Install dependencies:
    pip install spacy lemminflect
    python -m spacy download en_core_web_sm
"""
from __future__ import annotations

import logging

from backend.services.nlp.base import BaseNLP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level spaCy model initialization
# ---------------------------------------------------------------------------
# lemminflect must be imported to register its spaCy extensions (token._.inflect, etc.)
# Both imports are attempted at module load so the module can still be imported
# when spaCy is present but the model is not downloaded.

try:
    import spacy
    import lemminflect  # noqa: F401 -- side effect: registers spaCy extensions
    _nlp = spacy.load("en_core_web_sm")
except ImportError as _import_err:
    logger.warning(
        "EnglishNLP: spaCy or lemminflect not installed — lemmatization disabled. %s",
        _import_err,
    )
    _nlp = None  # type: ignore[assignment]
except OSError as _model_err:
    logger.warning(
        "EnglishNLP: en_core_web_sm model not found — run "
        "'python -m spacy download en_core_web_sm'. %s",
        _model_err,
    )
    _nlp = None  # type: ignore[assignment]


# Leading articles to strip from the front of normalized text.
# Order matters: "an" must come before "a" so that "an " is matched first.
_LEADING_ARTICLES = ("the ", "an ", "a ")


# ---------------------------------------------------------------------------
# EnglishNLP
# ---------------------------------------------------------------------------

class EnglishNLP(BaseNLP):
    """English NLP backend.

    Relies on spaCy (en_core_web_sm) for lemmatization and on lemminflect
    for inflection enumeration.  If either dependency is unavailable the
    backend degrades gracefully:
      - normalize() still strips articles and lowercases.
      - lemmatize() returns word.lower() (no spaCy).
      - get_morphological_family() returns a minimal {word, lemma} set.
    """

    # ------------------------------------------------------------------
    # normalize
    # ------------------------------------------------------------------

    def normalize(self, text: str) -> str:
        """Lowercase, strip whitespace, then strip a single leading article.

        Stripping is performed case-insensitively and only removes the article
        when it is followed by at least one more character (i.e. the entire
        text is not just the article itself).

        Examples:
            "The Dog" -> "dog"
            "A cat"   -> "cat"
            "An elephant" -> "elephant"
            "the"     -> "the"  (edge case: article is the whole word)
            "house of the dog" -> "house of the dog"  (only leading articles)
        """
        normalized = text.strip().lower()
        for article in _LEADING_ARTICLES:
            if normalized.startswith(article):
                # Only strip if something remains after the article
                remainder = normalized[len(article):]
                if remainder:
                    return remainder
                break  # Text is just the article — don't strip
        return normalized

    # ------------------------------------------------------------------
    # lemmatize
    # ------------------------------------------------------------------

    def lemmatize(self, word: str) -> str:
        """Return the dictionary base form of *word* using spaCy.

        Falls back to word.lower() when the spaCy model is unavailable.

        Args:
            word: A single token (e.g. "went", "mice", "running").

        Returns:
            The lemma string (e.g. "go", "mouse", "run").
        """
        if _nlp is None:
            return word.lower()
        doc = _nlp(word.lower())
        if not doc:
            return word.lower()
        return doc[0].lemma_

    # ------------------------------------------------------------------
    # get_morphological_family
    # ------------------------------------------------------------------

    def get_morphological_family(self, word: str) -> set[str]:
        """Return all inflected surface forms sharing the same lemma as *word*.

        Uses lemminflect.getAllInflections to enumerate every POS-tagged
        inflection so that irregular forms (e.g. "went", "gone") are included
        rather than naive suffix concatenation.

        If lemminflect is unavailable the method falls back to the minimal
        set {word, lemma}.

        Args:
            word: A single token.

        Returns:
            Set of surface forms (always includes *word* and its lemma).
        """
        lemma = self.lemmatize(word)
        family: set[str] = {word, lemma}

        try:
            from lemminflect import getAllInflections
            inflection_map = getAllInflections(lemma)
            for forms in inflection_map.values():
                family.update(forms)
        except ImportError:
            pass  # Graceful degradation — return minimal set

        return family

    # ------------------------------------------------------------------
    # get_aspect_partner
    # ------------------------------------------------------------------

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """English has no aspect partner system — always returns None.

        Args:
            verb: The verb surface form (ignored).
            card_context: Optional card metadata (ignored).

        Returns:
            None
        """
        return None
