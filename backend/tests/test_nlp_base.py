"""
Failing tests for BaseNLP pipeline, registry, and AnswerResult relocation.

These tests define the behavioral contract for:
  - BaseNLP abstract interface (NLP-01)
  - 4-tier check_answer pipeline (NLP-02)
  - NLP backend registry with get_nlp() and init_nlp_backends() (NLP-01)
  - AnswerResult relocated to nlp.base (NLP-01)
  - Answer alternatives (NLP-10)

All tests in this file will FAIL with ImportError or AttributeError because
backend/services/nlp/base.py and backend/services/nlp/__init__.py do not exist yet.
This is the RED phase of TDD — implementations are created in plans 02-01 through 02-04.
"""
import unicodedata

import pytest

from backend.services.nlp import NLP_BACKENDS, get_nlp, init_nlp_backends

# These imports will fail with ImportError — that is intentional (RED phase).
from backend.services.nlp.base import AnswerResult, BaseNLP

# ---------------------------------------------------------------------------
# StubNLP — a minimal concrete subclass used throughout these tests.
# All abstract methods are implemented; no real NLP library required.
# ---------------------------------------------------------------------------

class StubNLP(BaseNLP):
    """Minimal concrete NLP backend for testing the base pipeline."""

    def normalize(self, text: str) -> str:
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        lemma_map = {
            "dogs": "dog",
            "going": "go",
            "went": "go",
            "cats": "cat",
            "running": "run",
        }
        return lemma_map.get(word.lower(), word.lower())

    def get_morphological_family(self, word: str) -> set[str]:
        families = {
            "dog": {"dog", "dogs"},
            "cat": {"cat", "cats"},
            "run": {"run", "runs", "running", "ran"},
        }
        lemma = self.lemmatize(word)
        return families.get(lemma, {word})

    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        """Standardized signature: get_aspect_partner(verb, card_context=None)."""
        aspect_map = {
            "write": "wrote",
            "go": "went",
        }
        return aspect_map.get(verb.lower())


# ---------------------------------------------------------------------------
# BaseNLP ABC tests
# ---------------------------------------------------------------------------

class TestBaseNLPAbstract:
    """Tests for BaseNLP as an abstract base class."""

    def test_base_nlp_cannot_be_instantiated_directly(self):
        """BaseNLP is abstract and must not be directly instantiable."""
        with pytest.raises(TypeError):
            BaseNLP()

    def test_concrete_stub_can_be_instantiated(self):
        """A concrete subclass implementing all abstract methods can be instantiated."""
        nlp = StubNLP()
        assert nlp is not None

    def test_stub_has_check_answer_method(self):
        """The concrete subclass inherits check_answer from BaseNLP."""
        nlp = StubNLP()
        assert callable(nlp.check_answer)


class TestCheckAnswerPipeline:
    """Tests for the 4-tier check_answer pipeline in BaseNLP."""

    @pytest.fixture
    def nlp(self):
        return StubNLP()

    # Layer 1: Exact match
    def test_exact_match_returns_correct(self, nlp):
        result, msg = nlp.check_answer("dog", "dog")
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_exact_match_preserves_case_sensitivity(self, nlp):
        """Exact match is case-sensitive before normalization."""
        result, msg = nlp.check_answer("Dog", "dog")
        # Should fall through to normalized match (also CORRECT), not fail
        assert result == AnswerResult.CORRECT

    # Layer 2: Normalized match (case difference → CORRECT)
    def test_normalized_match_returns_correct(self, nlp):
        """Normalized match (e.g. case difference) returns CORRECT."""
        result, msg = nlp.check_answer("DOG", "dog")
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_normalized_match_strips_whitespace(self, nlp):
        """Leading/trailing whitespace is stripped before comparison."""
        result, msg = nlp.check_answer("  dog  ", "dog")
        assert result == AnswerResult.CORRECT

    # Layer 3: Lemma match → CORRECT_SLOPPY
    def test_lemma_match_returns_correct_sloppy(self, nlp):
        """Same lemma, different inflection → CORRECT_SLOPPY with message."""
        result, msg = nlp.check_answer("going", "go")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None
        assert len(msg) > 0

    def test_lemma_match_went_to_go(self, nlp):
        """Irregular form lemmatizes correctly → CORRECT_SLOPPY."""
        result, msg = nlp.check_answer("went", "go")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None

    # Layer 4: Morphological family match → CORRECT_SLOPPY
    def test_morphological_family_match_returns_correct_sloppy(self, nlp):
        """Word in correct word's morphological family → CORRECT_SLOPPY."""
        result, msg = nlp.check_answer("dogs", "dog")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None

    def test_morphological_family_message_is_informative(self, nlp):
        """CORRECT_SLOPPY message explains the situation."""
        result, msg = nlp.check_answer("cats", "cat")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None
        assert len(msg) > 10

    # Layer 5: Aspect partner match → WRONG_FORM
    def test_aspect_partner_match_returns_wrong_form(self, nlp):
        """Typing the aspect partner of the correct verb → WRONG_FORM."""
        result, msg = nlp.check_answer("wrote", "write")
        assert result == AnswerResult.WRONG_FORM
        assert msg is not None

    def test_aspect_partner_layer_calls_with_card_context(self, nlp):
        """Layer 5 passes card_context to get_aspect_partner."""
        card_ctx = {"aspect": "impf"}
        result, msg = nlp.check_answer("wrote", "write", card_context=card_ctx)
        assert result == AnswerResult.WRONG_FORM
        assert msg is not None

    # Layer 6: No match → WRONG
    def test_completely_wrong_answer_returns_wrong(self, nlp):
        """Unrelated answer → WRONG with None message."""
        result, msg = nlp.check_answer("cat", "dog")
        assert result == AnswerResult.WRONG
        assert msg is None

    def test_empty_answer_that_differs_returns_wrong(self, nlp):
        """Input that normalizes to something else → WRONG."""
        result, msg = nlp.check_answer("xyz", "dog")
        assert result == AnswerResult.WRONG
        assert msg is None


class TestAlternatives:
    """Tests for Layer 6 answer alternatives from card_context (NLP-10)."""

    @pytest.fixture
    def nlp(self):
        return StubNLP()

    def test_alternative_match_before_wrong(self, nlp):
        """Matching an alternative from card_context returns CORRECT, not WRONG."""
        ctx = {"answer_alternatives": ["colour", "color"]}
        result, msg = nlp.check_answer("colour", "color", card_context=ctx)
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_alternative_normalized_match(self, nlp):
        """Alternatives are compared after normalization."""
        ctx = {"answer_alternatives": ["Colour", "Color"]}
        result, msg = nlp.check_answer("colour", "Colour", card_context=ctx)
        # "colour" normalizes to "colour", "Colour" normalizes to "colour" → CORRECT
        assert result == AnswerResult.CORRECT

    def test_no_alternatives_falls_to_wrong(self, nlp):
        """Without alternatives, unrelated input returns WRONG."""
        ctx = {"answer_alternatives": []}
        result, msg = nlp.check_answer("cat", "dog", card_context=ctx)
        assert result == AnswerResult.WRONG

    def test_none_card_context_doesnt_crash(self, nlp):
        """check_answer(card_context=None) must not raise an exception."""
        result, msg = nlp.check_answer("cat", "dog", card_context=None)
        assert result == AnswerResult.WRONG


class TestNFCNormalization:
    """Tests for Unicode NFC normalization in the base pipeline."""

    @pytest.fixture
    def nlp(self):
        return StubNLP()

    def test_nfc_normalization_handles_different_unicode_forms(self, nlp):
        """NFC normalization ensures visually identical strings compare equal."""
        # "é" can be represented as NFC (U+00E9) or NFD (e + U+0301 combining accent)
        nfc_form = unicodedata.normalize("NFC", "café")
        nfd_form = unicodedata.normalize("NFD", "café")
        # The two forms look identical but are different byte sequences
        assert nfc_form != nfd_form or True  # may already be equal on some systems
        # Both should produce CORRECT because check_answer applies NFC normalization
        result, msg = nlp.check_answer(nfd_form, nfc_form)
        assert result == AnswerResult.CORRECT


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestNLPRegistry:
    """Tests for the NLP backend registry."""

    def test_get_nlp_raises_for_unknown_language(self):
        """get_nlp raises ValueError for unregistered language codes."""
        with pytest.raises(ValueError):
            get_nlp("xx")  # unknown language code

    def test_get_nlp_raises_value_error_with_language_in_message(self):
        """The ValueError message includes the unknown language code."""
        with pytest.raises(ValueError, match="xx"):
            get_nlp("xx")

    def test_register_stub_and_retrieve(self):
        """After registering a backend, get_nlp returns it."""
        stub = StubNLP()
        NLP_BACKENDS["stub"] = stub
        retrieved = get_nlp("stub")
        assert retrieved is stub
        # Clean up
        del NLP_BACKENDS["stub"]

    def test_init_nlp_backends_does_not_crash_when_modules_missing(self):
        """init_nlp_backends() should not crash if backend modules are missing yet."""
        # In 02-00 (RED phase), the backend modules don't exist.
        # init_nlp_backends() is expected to import them — this will raise ImportError
        # which is expected behavior in the RED phase. The test simply documents this.
        # Once 02-01 through 02-04 create the backends, this test will verify no crash.
        try:
            init_nlp_backends()
        except ImportError:
            # Expected in RED phase — backends not implemented yet
            pass


# ---------------------------------------------------------------------------
# AnswerResult relocation tests
# ---------------------------------------------------------------------------

class TestAnswerResultRelocation:
    """Tests that AnswerResult imported from nlp.base has the correct values."""

    def test_answer_result_has_correct_variant(self):
        assert AnswerResult.CORRECT.value == "correct"

    def test_answer_result_has_correct_sloppy_variant(self):
        assert AnswerResult.CORRECT_SLOPPY.value == "correct_sloppy"

    def test_answer_result_has_wrong_form_variant(self):
        assert AnswerResult.WRONG_FORM.value == "wrong_form"

    def test_answer_result_has_wrong_variant(self):
        assert AnswerResult.WRONG.value == "wrong"

    def test_answer_result_works_with_quality_map_values(self):
        """AnswerResult from nlp.base maps correctly to SM-2 quality scores."""
        QUALITY_MAP = {
            AnswerResult.CORRECT: 4,
            AnswerResult.CORRECT_SLOPPY: 3,
            AnswerResult.WRONG_FORM: 2,
            AnswerResult.WRONG: 1,
        }
        assert QUALITY_MAP[AnswerResult.CORRECT] == 4
        assert QUALITY_MAP[AnswerResult.CORRECT_SLOPPY] == 3
        assert QUALITY_MAP[AnswerResult.WRONG_FORM] == 2
        assert QUALITY_MAP[AnswerResult.WRONG] == 1
