"""Tests for the Hindi NLP backend: romanizer, lemmatizer, answer checking."""
import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.hindi import HindiNLP, devanagari_to_roman


class TestRomanizer:
    def test_basic_words(self):
        assert devanagari_to_roman("किताब") == "kitaab"
        assert devanagari_to_roman("पानी") == "paanii"
        assert devanagari_to_roman("हिंदी") == "hindii"

    def test_word_final_schwa_deleted(self):
        # राम is written राम but read "raam", not "raama"
        assert devanagari_to_roman("राम") == "raam"
        assert devanagari_to_roman("समझ") == "samajh"

    def test_medial_schwa_deletion(self):
        # लड़का → laṛkā, not laṛakā
        assert devanagari_to_roman("लड़का") == "larkaa"
        # the matlab class: right-to-left rule, following schwa counts as V
        assert devanagari_to_roman("मतलब") == "matlab"
        assert devanagari_to_roman("जनता") == "jantaa"
        # but kamal keeps its medial schwa (final deletion starves the rule)
        assert devanagari_to_roman("कमल") == "kamal"

    def test_punctuation_does_not_block_final_deletion(self):
        assert devanagari_to_roman("मतलब?") == "matlab?"

    def test_nukta_loan_sounds(self):
        assert devanagari_to_roman("ज़रूर") == "zaruur"
        assert devanagari_to_roman("खिड़की") == "khirkii"

    def test_anusvara_becomes_n(self):
        assert "n" in devanagari_to_roman("हिंदी")

    def test_multiword(self):
        assert devanagari_to_roman("मैं आप") == "main aap"


class TestLemmatizer:
    @pytest.fixture
    def nlp(self):
        return HindiNLP()

    def test_habitual_participle_folds_to_infinitive(self, nlp):
        assert nlp.lemmatize("करता") == "करना"
        assert nlp.lemmatize("करती") == "करना"
        assert nlp.lemmatize("करते") == "करना"

    def test_oblique_plural_folds(self, nlp):
        assert nlp.lemmatize("बच्चों") == "बच्चा"
        assert nlp.lemmatize("लड़के") == "लड़का"

    def test_unknown_word_unchanged(self, nlp):
        assert nlp.lemmatize("पानी") == "पानी"


class TestAnswerChecking:
    @pytest.fixture
    def nlp(self):
        return HindiNLP()

    def test_exact_match(self, nlp):
        result, _ = nlp.check_answer("नमस्ते", "नमस्ते")
        assert result == AnswerResult.CORRECT

    def test_whitespace_tolerant(self, nlp):
        result, _ = nlp.check_answer("  हैं ", "हैं")
        assert result == AnswerResult.CORRECT

    def test_wrong_answer(self, nlp):
        result, _ = nlp.check_answer("नहीं", "हाँ")
        assert result == AnswerResult.WRONG

    def test_inflected_form_is_wrong_form(self, nlp):
        # right verb, wrong inflection → WRONG_FORM, not a hard WRONG
        result, _ = nlp.check_answer("करती", "करता")
        assert result in (AnswerResult.WRONG_FORM, AnswerResult.CORRECT_SLOPPY)
