"""Tests for the personal-text extraction helpers."""
from backend.services.extract import (
    classify_words,
    make_cloze,
    split_sentences,
    tokenize,
)


class TestSplitSentences:
    def test_splits_on_punctuation(self):
        assert split_sentences("Hola. ¿Qué tal? Bien!") == ["Hola.", "¿Qué tal?", "Bien!"]

    def test_ignores_blank(self):
        assert split_sentences("   ") == []


class TestTokenize:
    def test_words_only(self):
        assert tokenize("El gato, 3 veces!") == ["El", "gato", "veces"]

    def test_keeps_diacritics_and_apostrophe(self):
        assert tokenize("l'eau café") == ["l'eau", "café"]


class TestMakeCloze:
    def test_blanks_whole_word(self):
        assert make_cloze("El gato duerme.", "gato") == "El {{answer}} duerme."

    def test_case_insensitive(self):
        assert make_cloze("Gato negro", "gato") == "{{answer}} negro"

    def test_only_whole_word(self):
        # 'at' should not match inside 'gato'
        assert make_cloze("El gato", "at") is None

    def test_missing_word(self):
        assert make_cloze("El gato", "perro") is None

    def test_first_occurrence_only(self):
        assert make_cloze("sí sí", "sí") == "{{answer}} sí"


class TestClassifyWords:
    def test_known_vs_new_and_dedup(self):
        words = classify_words(
            ["El", "gato", "gato", "xyzzy"],
            known_words={"el", "gato"},
            normalize=str.lower,
        )
        assert [w["word"] for w in words] == ["El", "gato", "xyzzy"]
        assert words[0]["known"] and words[1]["known"]
        assert words[2]["known"] is False
