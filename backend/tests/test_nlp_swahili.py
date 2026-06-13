"""Tests for SwahiliNLP — verb prefix stripping, noun classes, check_answer."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.swahili import SwahiliNLP


@pytest.fixture
def nlp():
    return SwahiliNLP()


class TestNormalize:
    def test_lowercase_strip(self, nlp):
        assert nlp.normalize("  Kitabu ") == "kitabu"


class TestLemmatize:
    def test_present_tense_first_person(self, nlp):
        assert nlp.lemmatize("ninasoma") == "soma"

    def test_past_tense_third_person(self, nlp):
        assert nlp.lemmatize("alisoma") == "soma"

    def test_future_plural(self, nlp):
        assert nlp.lemmatize("watasoma") == "soma"

    def test_perfect(self, nlp):
        assert nlp.lemmatize("nimesoma") == "soma"

    def test_noun_untouched(self, nlp):
        # "kitabu" starts with no subject+tense sequence — must not be stripped
        assert nlp.lemmatize("kitabu") == "kitabu"

    def test_short_stem_protected(self, nlp):
        # stripping that would leave fewer than 3 chars must not fire
        assert nlp.lemmatize("una") == "una"


class TestMorphologicalFamily:
    def test_verb_conjugations_included(self, nlp):
        family = nlp.get_morphological_family("soma")
        assert "ninasoma" in family
        assert "alisoma" in family
        assert "watasoma" in family

    def test_noun_class_ki_vi(self, nlp):
        family = nlp.get_morphological_family("kitabu")
        assert "vitabu" in family

    def test_noun_class_vi_ki_reverse(self, nlp):
        family = nlp.get_morphological_family("vitabu")
        assert "kitabu" in family

    def test_noun_class_m_wa(self, nlp):
        family = nlp.get_morphological_family("mtu")
        assert "watu" in family


class TestCheckAnswer:
    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("soma", "soma")
        assert result == AnswerResult.CORRECT

    def test_case_insensitive(self, nlp):
        result, _ = nlp.check_answer("Soma", "soma")
        assert result == AnswerResult.CORRECT

    def test_conjugated_for_stem_is_sloppy(self, nlp):
        result, _ = nlp.check_answer("ninasoma", "soma")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_plural_noun_class_is_sloppy(self, nlp):
        result, _ = nlp.check_answer("vitabu", "kitabu")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_wrong_word(self, nlp):
        result, _ = nlp.check_answer("maji", "kitabu")
        assert result == AnswerResult.WRONG

    def test_aspect_partner_none(self, nlp):
        assert nlp.get_aspect_partner("soma") is None
        assert nlp.get_aspect_partner("soma", {"morphology": {}}) is None
