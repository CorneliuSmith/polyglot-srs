"""
Failing tests for RussianNLP backend.

Covers NLP-03, NLP-04, NLP-05:
  - NLP-03: Russian morphological analysis, lemmatization (pymorphy3)
  - NLP-04: Latin-to-Cyrillic transliteration returns CORRECT_SLOPPY
  - NLP-05: Aspect partner detection returns WRONG_FORM

All tests will FAIL with ImportError because backend/services/nlp/russian.py
does not exist yet. This is the RED phase — implementations created in plan 02-03.
"""

import pytest

from backend.services.nlp.base import AnswerResult

# These imports will fail with ImportError — that is intentional (RED phase).
from backend.services.nlp.russian import RussianNLP

# ---------------------------------------------------------------------------
# TestRussianNormalization (NLP-03)
# ---------------------------------------------------------------------------

class TestRussianNormalization:
    """Tests for RussianNLP.normalize()."""

    @pytest.fixture
    def nlp(self):
        return RussianNLP()

    def test_normalize_lowercases_cyrillic(self, nlp):
        """normalize() lowercases Cyrillic text."""
        assert nlp.normalize("Собака") == "собака"

    def test_normalize_strips_whitespace(self, nlp):
        """normalize() strips leading/trailing whitespace."""
        assert nlp.normalize("  собака  ") == "собака"

    def test_normalize_preserves_cyrillic_characters(self, nlp):
        """normalize() keeps Cyrillic characters intact."""
        result = nlp.normalize("Привет")
        assert "привет" == result

    def test_normalize_handles_mixed_case(self, nlp):
        """normalize() handles sentences with mixed case."""
        assert nlp.normalize("КОШКА") == "кошка"


# ---------------------------------------------------------------------------
# TestRussianLemmatization (NLP-03)
# ---------------------------------------------------------------------------

class TestRussianLemmatization:
    """Tests for RussianNLP.lemmatize() using pymorphy3."""

    @pytest.fixture
    def nlp(self):
        return RussianNLP()

    def test_lemmatize_accusative_noun(self, nlp):
        """lemmatize() returns nominative form for an accusative noun."""
        # "собаку" (dog, accusative) → "собака" (nominative)
        assert nlp.lemmatize("собаку") == "собака"

    def test_lemmatize_verb_conjugation(self, nlp):
        """lemmatize() returns infinitive for a conjugated verb."""
        # "пишет" (he writes, 3rd person present) → "писать" (to write)
        assert nlp.lemmatize("пишет") == "писать"

    def test_lemmatize_returns_nominative_for_genitive(self, nlp):
        """lemmatize() handles genitive case → nominative."""
        # "собаки" can be genitive singular or nominative plural of "собака"
        result = nlp.lemmatize("собаки")
        assert result == "собака"

    def test_lemmatize_infinitive_unchanged(self, nlp):
        """lemmatize() of an infinitive returns the same infinitive."""
        assert nlp.lemmatize("писать") == "писать"


# ---------------------------------------------------------------------------
# TestRussianMorphologicalFamily (NLP-03)
# ---------------------------------------------------------------------------

class TestRussianMorphologicalFamily:
    """Tests for RussianNLP.get_morphological_family()."""

    @pytest.fixture
    def nlp(self):
        return RussianNLP()

    def test_family_contains_core_noun_forms(self, nlp):
        """Morphological family of 'собака' includes core declension forms."""
        family = nlp.get_morphological_family("собака")
        required_forms = {"собака", "собаки", "собаке", "собаку"}
        assert required_forms.issubset(family), (
            f"Expected {required_forms} to be a subset of family, got {family}"
        )

    def test_family_is_a_set(self, nlp):
        """get_morphological_family returns a set."""
        result = nlp.get_morphological_family("кошка")
        assert isinstance(result, set)

    def test_family_contains_input_word(self, nlp):
        """The input word itself is in the morphological family."""
        family = nlp.get_morphological_family("собака")
        assert "собака" in family


# ---------------------------------------------------------------------------
# TestRussianTransliteration (NLP-04)
# ---------------------------------------------------------------------------

class TestTransliteration:
    """Tests for Latin-to-Cyrillic transliteration pre-check (NLP-04)."""

    @pytest.fixture
    def nlp(self):
        return RussianNLP()

    def test_latin_sobaka_returns_correct_sloppy(self, nlp):
        """Typing 'sobaka' when correct is 'собака' → CORRECT_SLOPPY."""
        result, msg = nlp.check_answer("sobaka", "собака")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None
        assert "Cyrillic" in msg or "cyrillic" in msg.lower() or "кириллиц" in msg.lower() or len(msg) > 0

    def test_latin_da_returns_correct_sloppy(self, nlp):
        """Typing 'da' when correct is 'да' → CORRECT_SLOPPY with keyboard nudge."""
        result, msg = nlp.check_answer("da", "да")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None

    def test_transliteration_message_encourages_cyrillic(self, nlp):
        """Transliteration feedback message mentions Cyrillic keyboard."""
        result, msg = nlp.check_answer("sobaka", "собака")
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None and len(msg) > 5

    def test_wrong_latin_returns_wrong(self, nlp):
        """A wrong Latin string that doesn't transliterate to the answer → WRONG."""
        result, msg = nlp.check_answer("koshka", "собака")
        assert result == AnswerResult.WRONG


# ---------------------------------------------------------------------------
# TestAspectPartner (NLP-05)
# ---------------------------------------------------------------------------

class TestAspectPartner:
    """Tests for Russian aspect partner detection (NLP-05)."""

    @pytest.fixture
    def nlp(self):
        return RussianNLP()

    def test_get_aspect_partner_from_card_context(self, nlp):
        """get_aspect_partner reads from card_context morphology JSONB."""
        ctx = {"morphology": {"aspect_partner": "написать"}}
        partner = nlp.get_aspect_partner("писать", card_context=ctx)
        assert partner == "написать"

    def test_get_aspect_partner_returns_none_without_context(self, nlp):
        """get_aspect_partner returns None when no card_context provided."""
        partner = nlp.get_aspect_partner("писать", card_context=None)
        assert partner is None

    def test_get_aspect_partner_returns_none_without_morphology_key(self, nlp):
        """get_aspect_partner returns None when card_context lacks morphology key."""
        partner = nlp.get_aspect_partner("писать", card_context={})
        assert partner is None

    def test_check_answer_aspect_wrong_returns_wrong_form(self, nlp):
        """Typing perfective when imperfective expected → WRONG_FORM."""
        ctx = {"morphology": {"aspect_partner": "писать"}}
        result, msg = nlp.check_answer("писать", "написать", card_context=ctx)
        assert result == AnswerResult.WRONG_FORM
        assert msg is not None

    def test_aspect_partner_wrong_form_has_explanation(self, nlp):
        """WRONG_FORM message for aspect error provides explanation."""
        ctx = {"morphology": {"aspect_partner": "писать"}}
        result, msg = nlp.check_answer("писать", "написать", card_context=ctx)
        assert result == AnswerResult.WRONG_FORM
        assert len(msg) > 10


# ---------------------------------------------------------------------------
# TestRussianFullPipeline (NLP-03)
# ---------------------------------------------------------------------------

class TestRussianFullPipeline:
    """Integration tests for the full check_answer pipeline with Russian."""

    @pytest.fixture
    def nlp(self):
        return RussianNLP()

    def test_exact_cyrillic_match(self, nlp):
        """Exact Cyrillic match returns CORRECT."""
        result, msg = nlp.check_answer("собака", "собака")
        assert result == AnswerResult.CORRECT
        assert msg is None

    def test_normalized_case_match(self, nlp):
        """Case-insensitive Cyrillic match returns CORRECT."""
        result, msg = nlp.check_answer("Собака", "собака")
        assert result == AnswerResult.CORRECT

    def test_lemma_match_returns_correct_sloppy(self, nlp):
        """Different inflection of same lemma → CORRECT_SLOPPY."""
        result, msg = nlp.check_answer("собаку", "собака")
        # "собаку" lemmatizes to "собака" == lemma of "собака"
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg is not None

    def test_wrong_word_returns_wrong(self, nlp):
        """Completely wrong word → WRONG."""
        result, msg = nlp.check_answer("кошка", "собака")
        assert result == AnswerResult.WRONG
        assert msg is None
