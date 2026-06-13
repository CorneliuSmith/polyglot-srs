"""Tests for TurkishNLP — casing, suffix stripping, and check_answer grading."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.turkish import TurkishNLP, turkish_lower


@pytest.fixture
def nlp():
    return TurkishNLP()


class TestTurkishLower:
    def test_dotless_capital_i(self):
        assert turkish_lower("IŞIK") == "ışık"

    def test_dotted_capital_i(self):
        assert turkish_lower("İstanbul") == "istanbul"

    def test_mixed(self):
        assert turkish_lower("DİL") == "dil"

    def test_plain_ascii_unaffected(self):
        assert turkish_lower("Kitap") == "kitap"


class TestNormalize:
    def test_strips_and_lowers(self, nlp):
        assert nlp.normalize("  Ev  ") == "ev"

    def test_turkish_casing(self, nlp):
        # str.lower() would produce "iyi̇" / wrong dotless mapping
        assert nlp.normalize("İyİ") == "iyi"


class TestLemmatize:
    def test_plural_stripped(self, nlp):
        assert nlp.lemmatize("evler") == "ev"

    def test_locative_stripped(self, nlp):
        assert nlp.lemmatize("okulda") == "okul"

    def test_ablative_stripped(self, nlp):
        assert nlp.lemmatize("evden") == "ev"

    def test_plural_plus_case(self, nlp):
        # evlerde -> evler -> ev (two rounds)
        assert nlp.lemmatize("evlerde") == "ev"

    def test_bare_word_unchanged(self, nlp):
        assert nlp.lemmatize("su") == "su"

    def test_short_stem_protected(self, nlp):
        # "et" must not be reduced below the minimum stem length
        assert len(nlp.lemmatize("et")) >= 2


class TestMorphologicalFamily:
    def test_includes_word_and_lemma(self, nlp):
        family = nlp.get_morphological_family("evler")
        assert "evler" in family
        assert "ev" in family

    def test_includes_plural_with_back_harmony(self, nlp):
        family = nlp.get_morphological_family("kitap")
        assert "kitaplar" in family  # back vowel -> -lar

    def test_includes_plural_with_front_harmony(self, nlp):
        family = nlp.get_morphological_family("ev")
        assert "evler" in family  # front vowel -> -ler

    def test_includes_locative(self, nlp):
        family = nlp.get_morphological_family("ev")
        assert "evde" in family


class TestCheckAnswer:
    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("ev", "ev")
        assert result == AnswerResult.CORRECT

    def test_case_insensitive_turkish(self, nlp):
        result, _ = nlp.check_answer("IŞIK", "ışık")
        assert result == AnswerResult.CORRECT

    def test_inflected_form_is_sloppy(self, nlp):
        result, _ = nlp.check_answer("evler", "ev")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("kedi", "ev")
        assert result == AnswerResult.WRONG

    def test_aspect_partner_none(self, nlp):
        assert nlp.get_aspect_partner("gitmek") is None
        assert nlp.get_aspect_partner("gitmek", {"morphology": {}}) is None
