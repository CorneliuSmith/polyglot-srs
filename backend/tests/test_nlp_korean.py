"""Tests for the Korean NLP backend (WP27)."""
from backend.services.nlp.base import AnswerResult
from backend.services.nlp.korean import KoreanNLP


class TestLemmatizer:
    def test_particle_stripping(self):
        nlp = KoreanNLP()
        assert nlp.lemmatize("학교에") == "학교"
        assert nlp.lemmatize("학교에서") == "학교"
        assert nlp.lemmatize("친구가") == "친구"
        assert nlp.lemmatize("한국어를") == "한국어"

    def test_single_syllable_noun_keeps_locative_strip(self):
        assert KoreanNLP().lemmatize("집에") == "집"

    def test_two_syllable_nouns_ending_in_particle_shapes_survive(self):
        # 종이 (paper) and 고기 (meat) merely END in particle-shaped
        # syllables — the two-syllable guard keeps them whole.
        nlp = KoreanNLP()
        assert nlp.lemmatize("종이") == "종이"
        assert nlp.lemmatize("고기") == "고기"

    def test_polite_endings_reattach_dictionary_da(self):
        nlp = KoreanNLP()
        assert nlp.lemmatize("해요") == "하다"
        assert nlp.lemmatize("공부했어요") == "공부하다"
        assert nlp.lemmatize("먹었습니다") == "먹다"

    def test_fused_bieup_nida(self):
        # 갑니다 hides its ㅂ inside the stem syllable — jamo arithmetic
        # must recover 가다.
        nlp = KoreanNLP()
        assert nlp.lemmatize("갑니다") == "가다"
        assert nlp.lemmatize("옵니다") == "오다"

    def test_non_hangul_passthrough(self):
        assert KoreanNLP().lemmatize("pizza") == "pizza"


class TestCheckAnswer:
    def test_exact(self):
        result, _ = KoreanNLP().check_answer("먹어요", "먹어요")
        assert result == AnswerResult.CORRECT

    def test_wrong(self):
        result, _ = KoreanNLP().check_answer("가요", "먹어요")
        assert result == AnswerResult.WRONG

    def test_same_lemma_different_form_is_sloppy_not_correct(self):
        # Typing the bare noun for a particled answer (or vice versa)
        # should grade as almost-right, never as fully correct.
        result, _ = KoreanNLP().check_answer("학교", "학교에")
        assert result in (AnswerResult.CORRECT_SLOPPY, AnswerResult.WRONG_FORM)

    def test_no_aspect_partner(self):
        assert KoreanNLP().get_aspect_partner("가다") is None


class TestMorphologicalFamily:
    def test_verb_family_includes_polite_forms(self):
        fam = KoreanNLP().get_morphological_family("먹다")
        assert "먹다" in fam
        assert "먹습니다" in fam

    def test_noun_family_includes_particled_forms(self):
        fam = KoreanNLP().get_morphological_family("학교")
        assert "학교" in fam
        assert "학교는" in fam
