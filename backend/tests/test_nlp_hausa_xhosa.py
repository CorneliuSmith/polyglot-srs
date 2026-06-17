"""Tests for HausaNLP and XhosaNLP backends."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.hausa import HausaNLP, normalize_hausa
from backend.services.nlp.xhosa import XhosaNLP

# ── Hausa ─────────────────────────────────────────────────────────────────

@pytest.fixture
def ha():
    return HausaNLP()


class TestHausaNormalize:
    def test_lowercase_strip(self, ha):
        assert ha.normalize("  Mutum ") == "mutum"

    def test_apostrophe_variants_folded(self):
        assert normalize_hausa("yaʼya") == normalize_hausa("ya'ya") == normalize_hausa("ya’ya")

    def test_hooked_letters_preserved(self, ha):
        assert ha.normalize("ƁARNA") == "ɓarna"


class TestHausaCheckAnswer:
    def test_exact_match(self, ha):
        result, _ = ha.check_answer("mutum", "mutum")
        assert result == AnswerResult.CORRECT

    def test_apostrophe_insensitive(self, ha):
        result, _ = ha.check_answer("yaʼya", "ya'ya")
        assert result == AnswerResult.CORRECT

    def test_plural_via_alternatives(self, ha):
        # Irregular plural accepted only when stored as an alternative.
        result, _ = ha.check_answer(
            "mutane", "mutum", {"answer_alternatives": ["mutane"]}
        )
        assert result == AnswerResult.CORRECT

    def test_wrong_word(self, ha):
        result, _ = ha.check_answer("ruwa", "mutum")
        assert result == AnswerResult.WRONG

    def test_no_aspect_partner(self, ha):
        assert ha.get_aspect_partner("zo") is None


# ── Xhosa ─────────────────────────────────────────────────────────────────

@pytest.fixture
def xh():
    return XhosaNLP()


class TestXhosaLemmatize:
    def test_strips_subject_and_tense(self, xh):
        assert xh.lemmatize("ndiyahamba") == "hamba"

    def test_strips_plural_subject(self, xh):
        assert xh.lemmatize("bayadlala") == "dlala"

    def test_noun_untouched(self, xh):
        assert xh.lemmatize("umntu") == "umntu"


class TestXhosaMorphologicalFamily:
    def test_noun_class_um_aba(self, xh):
        family = xh.get_morphological_family("umntu")
        assert "abantu" in family

    def test_noun_class_isi_izi(self, xh):
        family = xh.get_morphological_family("isitya")
        assert "izitya" in family

    def test_noun_class_in_izin(self, xh):
        family = xh.get_morphological_family("inja")
        assert "izinja" in family

    def test_verb_conjugations_present(self, xh):
        family = xh.get_morphological_family("hamba")
        assert "ndiyahamba" in family


class TestXhosaCheckAnswer:
    def test_exact_match(self, xh):
        result, _ = xh.check_answer("umntu", "umntu")
        assert result == AnswerResult.CORRECT

    def test_plural_is_sloppy(self, xh):
        result, _ = xh.check_answer("abantu", "umntu")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_conjugated_for_stem_is_sloppy(self, xh):
        result, _ = xh.check_answer("ndiyahamba", "hamba")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_wrong_word(self, xh):
        result, _ = xh.check_answer("inja", "umntu")
        assert result == AnswerResult.WRONG

    def test_no_aspect_partner(self, xh):
        assert xh.get_aspect_partner("hamba") is None
