"""Tests for YorubaNLP — tone marks, underdots, and check_answer grading."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.yoruba import YorubaNLP, ascii_fold, strip_tones


@pytest.fixture
def nlp():
    return YorubaNLP()


class TestStripTones:
    def test_removes_tone_marks(self):
        assert strip_tones("ọkọ̀") == "ọkọ"
        assert strip_tones("àti") == "ati"

    def test_keeps_underdots(self):
        assert strip_tones("ṣé") == "ṣe"
        assert "ọ" in strip_tones("ọmọ")

    def test_result_is_nfc(self):
        import unicodedata
        out = strip_tones("ẹ̀kọ́")
        assert out == unicodedata.normalize("NFC", out)


class TestAsciiFold:
    def test_removes_everything(self):
        assert ascii_fold("ọkọ̀") == "oko"
        assert ascii_fold("ṣé") == "se"


class TestLemmatize:
    def test_strips_tone_keeps_quality(self, nlp):
        assert nlp.lemmatize("ọkọ̀") == "ọkọ"

    def test_untoned_word_unchanged(self, nlp):
        assert nlp.lemmatize("oko") == "oko"


class TestMorphologicalFamily:
    def test_includes_all_three_levels(self, nlp):
        family = nlp.get_morphological_family("ọkọ̀")
        assert "ọkọ̀" in family   # exact
        assert "ọkọ" in family    # tone-stripped
        assert "oko" in family    # ascii-folded


class TestCheckAnswer:
    def test_fully_diacritized_is_correct(self, nlp):
        result, _ = nlp.check_answer("ọkọ̀", "ọkọ̀")
        assert result == AnswerResult.CORRECT

    def test_missing_tones_is_sloppy_not_wrong(self, nlp):
        """The tashkeel principle: diacritics coach, they don't fail you."""
        result, _ = nlp.check_answer("ọkọ", "ọkọ̀")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_bare_qwerty_is_sloppy_not_wrong(self, nlp):
        result, _ = nlp.check_answer("oko", "ọkọ̀")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_different_word_is_wrong(self, nlp):
        result, _ = nlp.check_answer("ilé", "ọkọ̀")
        assert result == AnswerResult.WRONG

    def test_case_insensitive(self, nlp):
        result, _ = nlp.check_answer("Àti", "àti")
        assert result == AnswerResult.CORRECT

    def test_decomposed_input_matches_composed(self, nlp):
        """NFD input (as mobile keyboards often produce) matches NFC answers."""
        decomposed = "ọkọ̀"  # ọkọ̀ fully decomposed
        result, _ = nlp.check_answer(decomposed, "ọkọ̀")
        assert result == AnswerResult.CORRECT

    def test_aspect_partner_none(self, nlp):
        assert nlp.get_aspect_partner("lọ") is None
        assert nlp.get_aspect_partner("lọ", {"morphology": {}}) is None
