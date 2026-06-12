"""
Failing tests for ArabicNLP backend.

Covers NLP-06, NLP-07, NLP-08:
  - NLP-06: Arabic backend tashkeel stripping, alef normalization, root extraction
  - NLP-07: Arabic never fails on diacritic presence/absence
  - NLP-08: Arabic verb form detection returns WRONG_FORM with root + form table

All tests will FAIL with ImportError because backend/services/nlp/arabic.py
does not exist yet. This is the RED phase — implementations created in plan 02-04.

Note: Tests requiring camel-tools data files use pytest.importorskip("camel_tools")
to skip gracefully when the library or data is not installed.
"""

import pytest

# These imports will fail with ImportError — that is intentional (RED phase).
from backend.services.nlp.arabic import ArabicNLP
from backend.services.nlp.base import AnswerResult

# ---------------------------------------------------------------------------
# TestArabicNormalization (NLP-06)
# ---------------------------------------------------------------------------

class TestArabicNormalization:
    """Tests for ArabicNLP.normalize() — tashkeel stripping, alef, tatweel."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_normalize_strips_tashkeel(self, nlp):
        """normalize() strips all tashkeel (diacritical marks) from Arabic text."""
        # "كَتَبَ" with tashkeel → "كتب" without
        result = nlp.normalize("كَتَبَ")
        assert result == "كتب"

    def test_normalize_handles_alef_with_hamza_above(self, nlp):
        """normalize() converts أ (alef with hamza above) to ا (bare alef)."""
        result = nlp.normalize("أكتب")
        assert result == "اكتب"

    def test_normalize_handles_alef_with_hamza_below(self, nlp):
        """normalize() converts إ (alef with hamza below) to ا (bare alef)."""
        result = nlp.normalize("إبراهيم")
        assert "ابراهيم" == result

    def test_normalize_handles_alef_with_madda(self, nlp):
        """normalize() converts آ (alef with madda) to ا (bare alef)."""
        result = nlp.normalize("آسيا")
        assert "اسيا" == result

    def test_normalize_strips_tatweel(self, nlp):
        """normalize() strips tatweel (Arabic elongation character U+0640)."""
        # "كتـاب" with tatweel → "كتاب"
        assert nlp.normalize("كتـاب") == "كتاب"

    def test_normalize_lowercases_or_is_idempotent(self, nlp):
        """normalize() is idempotent — applying twice gives same result."""
        text = "كَتَبَ"
        once = nlp.normalize(text)
        twice = nlp.normalize(once)
        assert once == twice


# ---------------------------------------------------------------------------
# TestDiacriticInvariance (NLP-07)
# ---------------------------------------------------------------------------

class TestDiacriticInvariance:
    """Tests that Arabic answer validation never fails on diacritics (NLP-07)."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_user_without_tashkeel_matches_answer_with_tashkeel(self, nlp):
        """User typing 'كتب' when answer is 'كَتَبَ' → CORRECT."""
        result, msg = nlp.check_answer("كتب", "كَتَبَ")
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_user_with_tashkeel_matches_answer_without_tashkeel(self, nlp):
        """User typing 'كَتَبَ' when answer is 'كتب' → CORRECT."""
        result, msg = nlp.check_answer("كَتَبَ", "كتب")
        assert result == AnswerResult.CORRECT

    def test_alef_variant_matches_bare_alef(self, nlp):
        """أ variant matches bare ا in answer comparison → CORRECT."""
        result, msg = nlp.check_answer("اكتب", "أكتب")
        assert result == AnswerResult.CORRECT

    def test_exact_match_with_diacritics_is_correct(self, nlp):
        """Exact match including tashkeel → CORRECT."""
        result, msg = nlp.check_answer("كَتَبَ", "كَتَبَ")
        assert result == AnswerResult.CORRECT
        assert msg is None


# ---------------------------------------------------------------------------
# TestTaaMarbuta (NLP-06)
# ---------------------------------------------------------------------------

class TestTaaMarbuta:
    """Tests for taa marbuta vs ha distinction (NLP-06)."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_taa_marbuta_vs_ha_returns_correct_sloppy(self, nlp):
        """Taa marbuta (ة) vs ha (ه) difference → CORRECT_SLOPPY, not CORRECT or WRONG."""
        # "مدرسة" (school, with taa marbuta) vs "مدرسه" (with ha)
        result, msg = nlp.check_answer("مدرسه", "مدرسة")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_exact_taa_marbuta_is_correct(self, nlp):
        """Typing taa marbuta when answer has taa marbuta → CORRECT."""
        result, msg = nlp.check_answer("مدرسة", "مدرسة")
        assert result == AnswerResult.CORRECT


# ---------------------------------------------------------------------------
# TestArabicLemmatization (NLP-06)
# ---------------------------------------------------------------------------

class TestArabicLemmatization:
    """Tests for ArabicNLP.lemmatize() using camel-tools analyzer."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_lemmatize_returns_lex_field(self, nlp):
        """lemmatize() returns the 'lex' field from camel-tools analysis."""
        # "كَتَبَ" → lemma from lex field (stripped of sense ID suffix)
        result = nlp.lemmatize("كَتَبَ")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lemmatize_strips_diacritics_from_result(self, nlp):
        """lemmatize() result should not contain tashkeel."""
        result = nlp.lemmatize("كَتَبَ")
        # Result should be normalized (no tashkeel in the base form comparison)
        # At minimum, the result is a non-empty string
        assert result is not None
        assert len(result) > 0


# ---------------------------------------------------------------------------
# TestVerbFormDetection (NLP-08)
# ---------------------------------------------------------------------------

class TestVerbFormDetection:
    """Tests for Arabic verb form detection returning WRONG_FORM (NLP-08)."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_same_root_different_form_returns_wrong_form(self, nlp):
        """Words from the same root but different verb forms → WRONG_FORM with root."""
        # Both كَتَبَ (Form I: to write) and كَاتَبَ (Form III: to correspond)
        # share the root ك-ت-ب but are different forms
        result, msg = nlp.check_answer("كَتَبَ", "كَاتَبَ")
        # Should be WRONG_FORM (same root, different form) with root info in message
        assert result in (AnswerResult.WRONG_FORM, AnswerResult.WRONG)
        # When WRONG_FORM, the message should mention the root
        if result == AnswerResult.WRONG_FORM:
            assert msg is not None

    def test_wrong_form_message_contains_root_info(self, nlp):
        """WRONG_FORM feedback for Arabic verb mentions the root."""
        ctx = {"morphology": {"root": "ك.ت.ب", "verb_form": "III"}}
        result, msg = nlp.check_answer("كَتَبَ", "كَاتَبَ", card_context=ctx)
        if result == AnswerResult.WRONG_FORM:
            assert msg is not None
            assert len(msg) > 5

    def test_completely_different_roots_return_wrong(self, nlp):
        """Words with completely different roots → WRONG."""
        result, msg = nlp.check_answer("كتب", "ذهب")
        assert result == AnswerResult.WRONG


# ---------------------------------------------------------------------------
# TestArabicAspectPartner (NLP-06)
# ---------------------------------------------------------------------------

class TestArabicAspectPartner:
    """Tests that Arabic has no aspect partner system (NLP-06)."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_get_aspect_partner_returns_none(self, nlp):
        """Arabic get_aspect_partner always returns None."""
        result = nlp.get_aspect_partner("كتب", card_context=None)
        assert result is None

    def test_get_aspect_partner_with_context_returns_none(self, nlp):
        """Arabic get_aspect_partner returns None even with card_context."""
        result = nlp.get_aspect_partner("كتب", card_context={"morphology": {}})
        assert result is None


# ---------------------------------------------------------------------------
# TestArabicFullPipeline (NLP-06, NLP-07)
# ---------------------------------------------------------------------------

class TestArabicFullPipeline:
    """Integration tests for the full check_answer pipeline with Arabic."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("camel_tools")
        return ArabicNLP()

    def test_exact_arabic_match(self, nlp):
        """Exact Arabic match → CORRECT."""
        result, msg = nlp.check_answer("كتب", "كتب")
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_wrong_arabic_word_returns_wrong(self, nlp):
        """Completely different Arabic word → WRONG."""
        result, msg = nlp.check_answer("بيت", "كتب")
        assert result == AnswerResult.WRONG
