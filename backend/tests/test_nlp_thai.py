"""Tests for the Thai NLP backend and lexicon segmenter."""
from backend.services.nlp.base import AnswerResult
from backend.services.nlp.thai import ThaiNLP, segment


class TestSegmenter:
    LEX = {"ผม", "กิน", "ข้าว", "ไม่", "ชอบ", "อาหาร", "เผ็ด", "ที่", "บ้าน"}

    def test_greedy_longest_match(self):
        assert segment("ผมกินข้าว", self.LEX) == ["ผม", "กิน", "ข้าว"]

    def test_spaces_and_latin_ignored(self):
        assert segment("ผมกิน pizza ที่บ้าน", self.LEX) == ["ผม", "กิน", "ที่", "บ้าน"]

    def test_unknown_span_groups_into_one_chunk(self):
        # ทุเรียน is not in the lexicon — comes back as ONE unknown token,
        # so the difficulty scorer counts one unknown, not five characters.
        out = segment("ผมกินทุเรียน", self.LEX)
        assert out == ["ผม", "กิน", "ทุเรียน"]

    def test_longest_wins_over_prefix(self):
        lex = {"ไป", "ไปรษณีย์"}
        assert segment("ไปรษณีย์", lex) == ["ไปรษณีย์"]


class TestThaiNLP:
    def test_identity_lemmatizer(self):
        nlp = ThaiNLP()
        assert nlp.lemmatize("กิน") == "กิน"

    def test_exact_answer(self):
        nlp = ThaiNLP()
        result, _ = nlp.check_answer("ครับ", "ครับ")
        assert result == AnswerResult.CORRECT

    def test_wrong_answer(self):
        nlp = ThaiNLP()
        result, _ = nlp.check_answer("ค่ะ", "ครับ")
        assert result == AnswerResult.WRONG
