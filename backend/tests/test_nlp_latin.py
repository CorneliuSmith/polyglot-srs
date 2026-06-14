"""Tests for the Latin-script accent-folding NLP backends."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.latin_base import (
    CatalanNLP,
    FrenchNLP,
    GermanNLP,
    ItalianNLP,
    MaoriNLP,
    SpanishNLP,
    fold_diacritics,
)


class TestFoldDiacritics:
    def test_strips_accents(self):
        assert fold_diacritics("café") == "cafe"
        assert fold_diacritics("naïve") == "naive"

    def test_strips_macrons(self):
        assert fold_diacritics("kēkē") == "keke"


class TestSpanish:
    @pytest.fixture
    def nlp(self):
        return SpanishNLP()

    def test_strips_leading_article(self, nlp):
        assert nlp.normalize("el libro") == "libro"

    def test_article_only_word_kept(self, nlp):
        assert nlp.normalize("la") == "la"

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("gato", "gato")
        assert result == AnswerResult.CORRECT

    def test_article_flexible(self, nlp):
        result, _ = nlp.check_answer("el gato", "gato")
        assert result == AnswerResult.CORRECT

    def test_missing_accent_is_sloppy_not_wrong(self, nlp):
        result, _ = nlp.check_answer("cafe", "café")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("perro", "gato")
        assert result == AnswerResult.WRONG


class TestGerman:
    @pytest.fixture
    def nlp(self):
        return GermanNLP()

    def test_eszett_folds_to_ss(self, nlp):
        # straße typed as strasse -> sloppy match (ß/ss alternation)
        result, _ = nlp.check_answer("strasse", "straße")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_umlaut_omitted_is_sloppy(self, nlp):
        result, _ = nlp.check_answer("schon", "schön")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_strips_article(self, nlp):
        assert nlp.normalize("der Hund") == "hund"


class TestMaori:
    @pytest.fixture
    def nlp(self):
        return MaoriNLP()

    def test_macron_omitted_is_sloppy(self, nlp):
        # keke vs kēkē differ only by macron -> sloppy, not wrong
        result, _ = nlp.check_answer("keke", "kēkē")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_exact_macron_is_correct(self, nlp):
        result, _ = nlp.check_answer("kēkē", "kēkē")
        assert result == AnswerResult.CORRECT


class TestOtherRomance:
    def test_french_elision_article(self):
        assert FrenchNLP().normalize("l'eau") == "eau"

    def test_italian_article(self):
        assert ItalianNLP().normalize("gli amici") == "amici"

    def test_catalan_article(self):
        assert CatalanNLP().normalize("els nens") == "nens"

    def test_no_aspect_partner(self):
        for cls in (FrenchNLP, ItalianNLP, CatalanNLP, SpanishNLP, GermanNLP, MaoriNLP):
            assert cls().get_aspect_partner("x") is None
