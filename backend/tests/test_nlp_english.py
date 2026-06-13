"""
Failing tests for EnglishNLP backend.

Covers NLP-09:
  - English NLP backend (spaCy + lemminflect)
  - normalize(): lowercase, strip leading articles, strip whitespace
  - lemmatize(): irregular verbs, irregular plurals via spaCy + lemminflect
  - get_morphological_family(): all inflected forms via lemminflect
  - get_aspect_partner(): always returns None
  - Full check_answer pipeline integration

All tests will FAIL with ImportError because backend/services/nlp/english.py
does not exist yet. This is the RED phase — implementations created in plan 02-02.

Note: Tests requiring spaCy model use pytest.importorskip("spacy") to skip
gracefully when spaCy is not installed.
"""

import pytest

from backend.services.nlp.base import AnswerResult

# These imports will fail with ImportError — that is intentional (RED phase).
from backend.services.nlp.english import EnglishNLP

# ---------------------------------------------------------------------------
# TestEnglishNormalization (NLP-09)
# ---------------------------------------------------------------------------

class TestEnglishNormalization:
    """Tests for EnglishNLP.normalize() — lowercase, article stripping."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("spacy")
        return EnglishNLP()

    def test_normalize_lowercases(self, nlp):
        """normalize() lowercases input text."""
        assert nlp.normalize("The Dog") == "dog"

    def test_normalize_strips_leading_a(self, nlp):
        """normalize() strips leading 'a ' article."""
        assert nlp.normalize("A cat") == "cat"

    def test_normalize_strips_leading_an(self, nlp):
        """normalize() strips leading 'an ' article."""
        assert nlp.normalize("an elephant") == "elephant"

    def test_normalize_strips_leading_the(self, nlp):
        """normalize() strips leading 'the ' article."""
        assert nlp.normalize("the dog") == "dog"

    def test_normalize_does_not_strip_the_as_full_word(self, nlp):
        """normalize() does not strip 'the' if it is the entire word."""
        # Edge case: don't strip if the entire text is the article
        result = nlp.normalize("the")
        assert result == "the"

    def test_normalize_does_not_strip_article_in_middle(self, nlp):
        """normalize() only strips articles at the START of input."""
        # "house of the dog" should not have 'the' stripped from the middle
        result = nlp.normalize("house of the dog")
        assert result == "house of the dog"

    def test_normalize_strips_whitespace(self, nlp):
        """normalize() strips leading/trailing whitespace."""
        assert nlp.normalize("  dog  ") == "dog"

    def test_normalize_case_insensitive_article_stripping(self, nlp):
        """normalize() strips 'The ', 'A ', 'An ' regardless of case."""
        assert nlp.normalize("The Dog") == "dog"
        assert nlp.normalize("THE DOG") == "dog"


# ---------------------------------------------------------------------------
# TestEnglishLemmatization (NLP-09)
# ---------------------------------------------------------------------------

class TestEnglishLemmatization:
    """Tests for EnglishNLP.lemmatize() using spaCy."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("spacy")
        return EnglishNLP()

    def test_lemmatize_irregular_verb_went(self, nlp):
        """lemmatize('went') → 'go'."""
        assert nlp.lemmatize("went") == "go"

    def test_lemmatize_irregular_plural_mice(self, nlp):
        """lemmatize('mice') → 'mouse'."""
        assert nlp.lemmatize("mice") == "mouse"

    def test_lemmatize_regular_plural(self, nlp):
        """lemmatize('dogs') → 'dog'."""
        assert nlp.lemmatize("dogs") == "dog"

    def test_lemmatize_verb_running(self, nlp):
        """lemmatize('running') → 'run'."""
        assert nlp.lemmatize("running") == "run"

    def test_lemmatize_base_form_unchanged(self, nlp):
        """lemmatize() of a base form returns the same base form."""
        assert nlp.lemmatize("go") == "go"

    def test_lemmatize_verb_gone(self, nlp):
        """lemmatize('gone') → 'go'."""
        assert nlp.lemmatize("gone") == "go"


# ---------------------------------------------------------------------------
# TestEnglishMorphologicalFamily (NLP-09)
# ---------------------------------------------------------------------------

class TestEnglishMorphologicalFamily:
    """Tests for EnglishNLP.get_morphological_family() using lemminflect."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("spacy")
        return EnglishNLP()

    def test_family_of_go_contains_core_forms(self, nlp):
        """Morphological family of 'go' contains at least the core verb forms."""
        family = nlp.get_morphological_family("go")
        required = {"go", "goes", "going", "went", "gone"}
        assert required.issubset(family), (
            f"Expected {required} to be in family, got {family}"
        )

    def test_family_is_a_set(self, nlp):
        """get_morphological_family returns a set."""
        result = nlp.get_morphological_family("dog")
        assert isinstance(result, set)

    def test_family_contains_input_word(self, nlp):
        """The input word itself is in the morphological family."""
        family = nlp.get_morphological_family("dog")
        assert "dog" in family

    def test_family_of_go_contains_went(self, nlp):
        """Morphological family of 'go' includes 'went' (irregular past)."""
        family = nlp.get_morphological_family("go")
        assert "went" in family


# ---------------------------------------------------------------------------
# TestEnglishAspectPartner (NLP-09)
# ---------------------------------------------------------------------------

class TestEnglishAspectPartner:
    """Tests that English has no aspect partner system (NLP-09)."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("spacy")
        return EnglishNLP()

    def test_get_aspect_partner_returns_none(self, nlp):
        """English get_aspect_partner always returns None."""
        result = nlp.get_aspect_partner("go", card_context=None)
        assert result is None

    def test_get_aspect_partner_with_verb_returns_none(self, nlp):
        """English get_aspect_partner returns None for any verb."""
        assert nlp.get_aspect_partner("write", card_context=None) is None
        assert nlp.get_aspect_partner("run", card_context={"morphology": {}}) is None


# ---------------------------------------------------------------------------
# TestEnglishFullPipeline (NLP-09)
# ---------------------------------------------------------------------------

class TestEnglishFullPipeline:
    """Integration tests for the full check_answer pipeline with English."""

    @pytest.fixture
    def nlp(self):
        pytest.importorskip("spacy")
        return EnglishNLP()

    def test_exact_match_returns_correct(self, nlp):
        """Exact English word match → CORRECT."""
        result, msg = nlp.check_answer("dog", "dog")
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_normalized_case_match_returns_correct(self, nlp):
        """Case-insensitive match → CORRECT."""
        result, msg = nlp.check_answer("Dog", "dog")
        assert result == AnswerResult.CORRECT

    def test_article_stripping_returns_correct_or_sloppy(self, nlp):
        """'The dog' vs 'dog' → CORRECT (normalized) or CORRECT_SLOPPY (lemma)."""
        result, msg = nlp.check_answer("the dog", "dog")
        assert result in (AnswerResult.CORRECT, AnswerResult.CORRECT_SLOPPY)

    def test_irregular_verb_form_returns_correct_sloppy(self, nlp):
        """'went' when 'go' expected → CORRECT_SLOPPY (same lemma)."""
        result, msg = nlp.check_answer("went", "go")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None

    def test_lemma_match_plural_noun_returns_correct_sloppy(self, nlp):
        """'dogs' when 'dog' expected → CORRECT_SLOPPY (same lemma)."""
        result, msg = nlp.check_answer("dogs", "dog")
        assert result == AnswerResult.CORRECT_SLOPPY

    def test_wrong_word_returns_wrong(self, nlp):
        """Completely wrong English word → WRONG."""
        result, msg = nlp.check_answer("cat", "dog")
        assert result == AnswerResult.WRONG
        assert msg is None

    def test_alternatives_accepted_before_wrong(self, nlp):
        """British spelling alternative → CORRECT via alternatives list."""
        ctx = {"answer_alternatives": ["colour"]}
        result, msg = nlp.check_answer("colour", "color", card_context=ctx)
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_irregular_plural_mice_lemmatizes_to_mouse(self, nlp):
        """'mice' as answer for 'mouse' → CORRECT_SLOPPY via lemma match."""
        result, msg = nlp.check_answer("mice", "mouse")
        assert result == AnswerResult.CORRECT_SLOPPY
