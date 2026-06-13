"""
YorubaNLP backend — tone-mark-aware matching for a fully diacritized lexicon.

Yoruba-specific behaviour:
  - Yoruba is tonal: à (low), a (mid), á (high) distinguish words, and the
    underdotted letters ẹ, ọ, ṣ are distinct phonemes — "ọkọ" (husband),
    "ọkọ̀" (vehicle), "oko" (farm) are different words.
  - Normalization keeps ALL diacritics (lowercase + strip only), so a fully
    diacritized answer must match exactly to be CORRECT.
  - Lemmatization strips tone marks but keeps underdots: a learner typing
    "oko" for "ọkọ̀" went through TWO mistakes (tones AND vowel quality),
    while "ọkọ" for "ọkọ̀" missed only tone. Tone-stripped matches surface
    as CORRECT_SLOPPY via the lemma layer — never as flat WRONG, mirroring
    the Arabic tashkeel decision (diacritics coach, they don't fail you).
  - The morphological family adds the fully ASCII-folded form so even a
    bare-keyboard answer ("oko") grades as CORRECT_SLOPPY.
  - Yoruba is isolating (no inflection to strip, no aspect pairs).
"""
from __future__ import annotations

import unicodedata

from backend.services.nlp.base import BaseNLP

# Combining marks used for tone in NFD-decomposed Yoruba text.
_TONE_MARKS = {"̀", "́", "̄"}  # grave (low), acute (high), macron
# Combining dot below — vowel quality (ẹ, ọ) and ṣ. NOT a tone mark.
_DOT_BELOW = "̣"


def strip_tones(text: str) -> str:
    """Remove tone marks while keeping underdots (ẹ ọ ṣ stay distinct)."""
    decomposed = unicodedata.normalize("NFD", text)
    kept = "".join(c for c in decomposed if c not in _TONE_MARKS)
    return unicodedata.normalize("NFC", kept)


def ascii_fold(text: str) -> str:
    """Remove tone marks AND underdots — the bare-QWERTY form of a word."""
    decomposed = unicodedata.normalize("NFD", text)
    kept = "".join(c for c in decomposed if c not in _TONE_MARKS and c != _DOT_BELOW)
    return unicodedata.normalize("NFC", kept)


class YorubaNLP(BaseNLP):
    """Yoruba NLP backend (tonal, isolating)."""

    def normalize(self, text: str) -> str:
        """Lowercase and strip — diacritics are preserved (they carry meaning)."""
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        """Return the tone-stripped form (underdots kept).

        Yoruba has no inflectional morphology to remove; the "base form" for
        matching purposes is the word without tone marks, so tone errors
        match at the lemma layer (CORRECT_SLOPPY) instead of failing.
        """
        return strip_tones(word.strip().lower())

    def get_morphological_family(self, word: str) -> set[str]:
        """Return *word*, its tone-stripped form, and its ASCII-folded form."""
        lowered = word.strip().lower()
        return {lowered, strip_tones(lowered), ascii_fold(lowered)}

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Yoruba has no aspect-pair system — always returns None."""
        return None
