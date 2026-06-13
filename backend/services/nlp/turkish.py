"""
TurkishNLP backend — rule-based agglutinative suffix handling with optional zeyrek.

Turkish-specific behaviour:
  - Normalization uses Turkish casing rules: 'I' -> 'ı' and 'İ' -> 'i'.
    Python's str.lower() maps 'I' -> 'i', which is wrong for Turkish and
    would mark e.g. "IŞIK" typed for "ışık" as WRONG.
  - Lemmatization prefers zeyrek (a Zemberek port) when installed; otherwise
    a conservative suffix-stripping heuristic handles the most common
    inflectional suffixes (plural, case, copula) with vowel harmony.
  - Morphological family enumerates plural + primary case forms from the
    lemma so "evler" or "evde" typed for "ev" grades as CORRECT_SLOPPY
    instead of WRONG.
  - Turkish has no Slavic-style aspect pairs — get_aspect_partner returns None.

Optional dependency:
    pip install zeyrek   # better lemmatization; the heuristic is the fallback
"""
from __future__ import annotations

import logging

from backend.services.nlp.base import BaseNLP

logger = logging.getLogger(__name__)

try:
    import zeyrek
    _analyzer = zeyrek.MorphAnalyzer()
except ImportError:
    _analyzer = None
except Exception as _err:  # noqa: BLE001 — zeyrek can fail on data download
    logger.warning("TurkishNLP: zeyrek failed to initialize: %s", _err)
    _analyzer = None

_BACK_VOWELS = set("aıou")
_FRONT_VOWELS = set("eiöü")
_VOWELS = _BACK_VOWELS | _FRONT_VOWELS

# Inflectional suffixes ordered longest-first so the most specific match wins.
# Covers plural (-lar/-ler), the six cases, possessives, and common copulas.
_INFLECTIONAL_SUFFIXES = (
    "lardan", "lerden", "larda", "lerde", "ların", "lerin",
    "dir", "dır", "dur", "dür", "tir", "tır", "tur", "tür",
    "dan", "den", "tan", "ten",
    "lar", "ler",
    "da", "de", "ta", "te",
    "nın", "nin", "nun", "nün", "ın", "in", "un", "ün",
    "ya", "ye",
    "yı", "yi", "yu", "yü",
    "sı", "si", "su", "sü",
    "ı", "i", "u", "ü",
    "a", "e",
)

_MIN_STEM_LEN = 2


def turkish_lower(text: str) -> str:
    """Lowercase with Turkish dotted/dotless i rules ('I'->'ı', 'İ'->'i')."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _vowel_harmony_suffix(lemma: str, back: str, front: str) -> str:
    """Pick the back- or front-vowel variant of a suffix for *lemma*."""
    for ch in reversed(lemma):
        if ch in _BACK_VOWELS:
            return back
        if ch in _FRONT_VOWELS:
            return front
    return front


class TurkishNLP(BaseNLP):
    """Turkish NLP backend (agglutinative, vowel-harmony aware)."""

    def normalize(self, text: str) -> str:
        """Strip whitespace and lowercase using Turkish casing rules."""
        return turkish_lower(text.strip())

    def lemmatize(self, word: str) -> str:
        """Return the most likely base form of *word*.

        Uses zeyrek when available; otherwise strips at most two of the most
        common inflectional suffixes, never reducing the stem below
        _MIN_STEM_LEN characters or removing its last vowel entirely.
        """
        lowered = turkish_lower(word.strip())
        if not lowered:
            return lowered

        if _analyzer is not None:
            try:
                lemmas = _analyzer.lemmatize(lowered)
                # zeyrek returns [(word, [lemma, ...])]
                if lemmas and lemmas[0][1]:
                    return turkish_lower(lemmas[0][1][0])
            except Exception:  # noqa: BLE001 — fall back to the heuristic
                pass

        return self._strip_suffixes(lowered)

    @staticmethod
    def _strip_suffixes(word: str, max_rounds: int = 2) -> str:
        stem = word
        for _ in range(max_rounds):
            for suffix in _INFLECTIONAL_SUFFIXES:
                if stem.endswith(suffix):
                    candidate = stem[: -len(suffix)]
                    if len(candidate) >= _MIN_STEM_LEN and any(
                        c in _VOWELS for c in candidate
                    ):
                        stem = candidate
                        break
            else:
                break
        return stem

    def get_morphological_family(self, word: str) -> set[str]:
        """Return *word*, its lemma, and the lemma's plural + primary case forms."""
        lemma = self.lemmatize(word)
        family: set[str] = {turkish_lower(word.strip()), lemma}

        plural = lemma + _vowel_harmony_suffix(lemma, "lar", "ler")
        family.add(plural)
        # Locative, ablative, genitive, dative on the singular lemma
        family.add(lemma + _vowel_harmony_suffix(lemma, "da", "de"))
        family.add(lemma + _vowel_harmony_suffix(lemma, "dan", "den"))
        family.add(lemma + _vowel_harmony_suffix(lemma, "ın", "in"))
        family.add(lemma + _vowel_harmony_suffix(lemma, "a", "e"))
        return family

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Turkish has no aspect-pair system — always returns None."""
        return None
