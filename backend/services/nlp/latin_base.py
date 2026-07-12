"""
Shared NLP backends for Latin-script languages with diacritics.

These languages (Spanish, Italian, French, Catalan, German, Māori) are
well-documented but have no lightweight morphological analyzer bundled here,
so the backends are rule-based and share one pattern:

  - normalize: lowercase + strip, and drop a leading article (el/la, le/les,
    der/die/das, te/ngā …) so "el libro" and "libro" match.
  - lemmatize: additionally fold diacritics, so an answer typed without
    accents/macrons/umlauts (café -> cafe, kēkē -> keke, schön -> schon)
    grades as CORRECT_SLOPPY rather than WRONG — diacritics coach, they don't
    fail you (the Arabic tashkeel / Yoruba tone principle).
  - no aspect-pair system.

A bundled morphological seed (irregular forms as answer alternatives) or a
spaCy backend can replace any of these later without changing the interface.
"""
from __future__ import annotations

import unicodedata

from backend.services.nlp.base import BaseNLP


def fold_diacritics(text: str) -> str:
    """Remove combining accent/macron marks (café -> cafe, kēkē -> keke)."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", stripped)


class AccentFoldingNLP(BaseNLP):
    """Base for Latin-script languages: article stripping + diacritic folding."""

    leading_articles: tuple[str, ...] = ()

    def normalize(self, text: str) -> str:
        t = text.strip().lower()
        for article in self.leading_articles:
            if t.startswith(article) and len(t) > len(article):
                return t[len(article):].strip()
        return t

    def _fold(self, text: str) -> str:
        return fold_diacritics(text)

    def lemmatize(self, word: str) -> str:
        return self._fold(self.normalize(word))

    def get_morphological_family(self, word: str) -> set[str]:
        lowered = word.strip().lower()
        normalized = self.normalize(lowered)
        return {lowered, normalized, self._fold(normalized)}

    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        return None


class SpanishNLP(AccentFoldingNLP):
    leading_articles = ("el ", "la ", "los ", "las ", "un ", "una ", "unos ", "unas ")


class RomanianNLP(AccentFoldingNLP):
    # Romanian's definite article is a suffix (casa, omul) — nothing to strip.
    leading_articles = ()


class GreekNLP(AccentFoldingNLP):
    # Accent folding is script-agnostic (NFD strips the Greek tonos too).
    leading_articles = ("ο ", "η ", "το ", "οι ", "τα ", "ένας ", "μια ", "ένα ")


class PortugueseNLP(AccentFoldingNLP):
    leading_articles = ("o ", "a ", "os ", "as ", "um ", "uma ", "uns ", "umas ")


class ItalianNLP(AccentFoldingNLP):
    leading_articles = ("il ", "lo ", "la ", "i ", "gli ", "le ", "un ", "uno ", "una ", "l'")


class FrenchNLP(AccentFoldingNLP):
    leading_articles = ("le ", "la ", "les ", "un ", "une ", "des ", "du ", "l'")


class CatalanNLP(AccentFoldingNLP):
    leading_articles = ("el ", "la ", "els ", "les ", "un ", "una ", "uns ", "unes ", "l'")


class GermanNLP(AccentFoldingNLP):
    leading_articles = ("der ", "die ", "das ", "den ", "dem ", "ein ", "eine ", "einen ")

    def _fold(self, text: str) -> str:
        # ß ↔ ss is a real spelling alternation, so fold it before stripping umlauts.
        return fold_diacritics(text.replace("ß", "ss"))


class MaoriNLP(AccentFoldingNLP):
    leading_articles = ("te ", "ngā ", "nga ", "he ")
