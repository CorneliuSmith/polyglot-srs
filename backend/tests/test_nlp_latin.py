"""Tests for the Latin-script accent-folding NLP backends."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.latin_base import (
    CatalanNLP,
    FrenchNLP,
    GermanNLP,
    HebrewNLP,
    IndonesianNLP,
    ItalianNLP,
    LatinNLP,
    MaoriNLP,
    PersianNLP,
    SpanishNLP,
    TagalogNLP,
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


class TestLatin:
    @pytest.fixture
    def nlp(self):
        return LatinNLP()

    def test_macron_omitted_is_sloppy(self, nlp):
        result, _ = nlp.check_answer("regina", "rēgīna")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("puella", "puella")
        assert result == AnswerResult.CORRECT

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("puer", "puella")
        assert result == AnswerResult.WRONG

    def test_no_article_stripped(self, nlp):
        assert nlp.normalize("puella") == "puella"


class TestIndonesian:
    @pytest.fixture
    def nlp(self):
        return IndonesianNLP()

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("rumah", "rumah")
        assert result == AnswerResult.CORRECT

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("mobil", "rumah")
        assert result == AnswerResult.WRONG

    def test_case_insensitive(self, nlp):
        result, _ = nlp.check_answer("Rumah", "rumah")
        assert result == AnswerResult.CORRECT


class TestTagalog:
    @pytest.fixture
    def nlp(self):
        return TagalogNLP()

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("bahay", "bahay")
        assert result == AnswerResult.CORRECT

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("aso", "bahay")
        assert result == AnswerResult.WRONG

    def test_particle_not_stripped(self, nlp):
        # ang/ng/sa are case markers, not articles — must NOT be eaten
        assert nlp.normalize("ang bahay") == "ang bahay"


class TestHebrew:
    @pytest.fixture
    def nlp(self):
        return HebrewNLP()

    def test_niqqud_omitted_is_sloppy(self, nlp):
        # בַּיִת (bayit, "house") with niqqud vs. plain בית
        result, _ = nlp.check_answer("בית", "בַּיִת")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("שלום", "שלום")
        assert result == AnswerResult.CORRECT

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("ספר", "בית")
        assert result == AnswerResult.WRONG

    def test_no_article_stripped(self, nlp):
        # the ה is fused onto the word, not a separable "the "
        assert nlp.normalize("הבית") == "הבית"


class TestPersian:
    @pytest.fixture
    def nlp(self):
        return PersianNLP()

    def test_harakat_omitted_is_sloppy(self, nlp):
        # سَلام (salām with a fatha) vs. plain سلام
        result, _ = nlp.check_answer("سلام", "سَلام")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("کتاب", "کتاب")
        assert result == AnswerResult.CORRECT

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("خانه", "کتاب")
        assert result == AnswerResult.WRONG
