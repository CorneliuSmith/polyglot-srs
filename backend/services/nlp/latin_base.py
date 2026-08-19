"""
Shared NLP backends for Latin-script languages with diacritics — plus two
non-Latin exceptions (Hebrew, Persian) that reuse the SAME mechanism for a
different reason: their optional vowel points/harakat are Unicode combining
marks too, so the shared diacritic-folding here absorbs them exactly like it
absorbs a Spanish á or a German ü, letting an answer with or without them
match. Article stripping doesn't apply to either — Hebrew's ה is fused onto
the word (not a separable "the "), and Persian has no articles to strip.

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

from backend.services.nlp.arabic_script import fold_arabic_script
from backend.services.nlp.base import AnswerResult, BaseNLP


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
        article = self._leading_article(t)
        return t[len(article):].strip() if article else t

    def _leading_article(self, text: str) -> str | None:
        """The article *text* opens with, or None. Longest first, so "las "
        is never read as "la " + "s"."""
        t = text.strip().lower()
        for article in sorted(self.leading_articles, key=len, reverse=True):
            if t.startswith(article) and len(t) > len(article):
                return article
        return None

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

    # ------------------------------------------------------------------
    # Article agreement
    # ------------------------------------------------------------------

    def check_answer(
        self,
        user_input: str,
        correct_answer: str,
        card_context: dict | None = None,
    ) -> tuple[AnswerResult, str | None]:
        """Parent pipeline, then refuse to launder a wrong-gender article.

        normalize() drops a leading article so "libro" passes for "el libro"
        — deliberate leniency about whether the learner bothered to type it.
        But it applied just as happily when the learner typed a DIFFERENT
        article, so "la libro" graded fully CORRECT, and every one of these
        languages silently accepted the wrong gender on every noun. The
        Catalan course was reported for exactly this.

        Omitting the article stays free. Getting it WRONG is now named:
        amber on vocabulary (the word was recalled), and on a grammar drill
        — where the article IS the thing being tested — WRONG_FORM, the same
        treatment layers 3-4 already give a right-word-wrong-cell answer.
        """
        result, message = super().check_answer(user_input, correct_answer, card_context)
        # For this family lemmatize IS the diacritic fold, so a CORRECT_SLOPPY
        # from layers 3-4 is typographic, not morphological — and marks the
        # base layer's guard cannot see (ș, ț, ñ have no combining
        # decomposition) still merge here. Re-apply the collision guard at
        # this level: a fold that lands on another course word is that word.
        if result is AnswerResult.CORRECT_SLOPPY:
            norm_user = self.normalize(user_input)
            norm_correct = self.normalize(correct_answer)
            if (
                norm_user != norm_correct
                and self._fold(norm_user) == self._fold(norm_correct)
                and self._typed_another_card(norm_user, norm_correct, card_context)
            ):
                return (
                    AnswerResult.WRONG_FORM,
                    f"'{norm_user}' is a different word. Expected: {correct_answer}",
                )
        if result is not AnswerResult.CORRECT or not self.leading_articles:
            return result, message
        typed = self._leading_article(user_input)
        expected = self._leading_article(correct_answer)
        # Only a disagreement counts: no article on either side, or on just
        # one, is the leniency this class exists for.
        if not typed or not expected or self._fold(typed) == self._fold(expected):
            return result, message
        if card_context and card_context.get("card_type") == "grammar":
            return (
                AnswerResult.WRONG_FORM,
                f"Wrong article — check the gender. Expected: {correct_answer}",
            )
        return (
            AnswerResult.CORRECT_SLOPPY,
            f"Right word — but check the article's gender. Expected: {correct_answer}",
        )


class SpanishNLP(AccentFoldingNLP):
    leading_articles = ("el ", "la ", "los ", "las ", "un ", "una ", "unos ", "unas ")


class RomanianNLP(AccentFoldingNLP):
    # Romanian's definite article is a suffix (casa, omul) — nothing to strip.
    leading_articles = ()


class GreekNLP(AccentFoldingNLP):
    # Accent folding is script-agnostic (NFD strips the Greek tonos too).
    leading_articles = ("ο ", "η ", "το ", "οι ", "τα ", "ένας ", "μια ", "ένα ")

    def normalize(self, text: str) -> str:
        # Final sigma ς is the POSITION of σ, not a different letter — the
        # alphabet deck's σ card and any word-final σ typed without the
        # final form were graded wrong over a rendering rule real keyboards
        # apply automatically.
        return super().normalize(text).replace("ς", "σ")


class PortugueseNLP(AccentFoldingNLP):
    leading_articles = ("o ", "a ", "os ", "as ", "um ", "uma ", "uns ", "umas ")


class DutchNLP(AccentFoldingNLP):
    leading_articles = ("de ", "het ", "een ")


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


class LatinNLP(AccentFoldingNLP):
    # No articles in Latin — puella alone can mean "girl," "a girl," or "the
    # girl." Folding still helps: macrons (ā ē ī ō ū) are usually omitted in
    # a learner's typed answer.
    leading_articles = ()


class IndonesianNLP(AccentFoldingNLP):
    leading_articles = ()


class TagalogNLP(AccentFoldingNLP):
    # ang/ng/sa are case-marking particles, not articles like Spanish "el" —
    # stripping them would eat a real word, so nothing is stripped here.
    leading_articles = ()


# Hebrew final letters → their non-final forms (ך ם ן ף ץ → כ מ נ פ צ).
_HEBREW_FINALS = str.maketrans("ךםןףץ", "כמנפצ")


class HebrewNLP(AccentFoldingNLP):
    """Folds niqqud (vowel points) — Unicode combining marks — so an answer
    typed with or without them matches. No article stripping: Hebrew's ה is
    fused onto the word itself, not a separable "the "."""
    leading_articles = ()

    def fold_lookalikes(self, text: str) -> str:
        # Final forms are worth learning (unlike niqqud, they are mandatory
        # in ordinary spelling), so they fold in the COACHING layer: שלומ
        # for שלום is accepted amber with the proper form named, not green.
        return text.translate(_HEBREW_FINALS)


class PersianNLP(AccentFoldingNLP):
    """Folds the optional Perso-Arabic vowel diacritics (harakat) the same
    way. Persian has no articles to strip.

    Persian took the worst of the typed-vs-pasted failure. iOS ships an
    Arabic keyboard and not a Persian one by default, so learners type Arabic
    kaf ك and yeh ي where Persian spells ک and ی — different codepoints,
    identical on screen, and every answer containing one was rejected. The
    ZWNJ that Persian puts inside ordinary words (می‌روم) is handled a layer
    up, in check_answer, since it is invisible rather than merely look-alike.
    """
    leading_articles = ()

    def fold_lookalikes(self, text: str) -> str:
        return fold_arabic_script(text)
