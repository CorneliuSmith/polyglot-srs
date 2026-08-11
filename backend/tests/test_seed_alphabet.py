"""Alphabet deck data integrity for the non-Latin scripts."""

import json

from backend.services.seeder import seed_alphabet
from backend.services.seeder.seed_alphabet import (
    ALPHABETS,
    ARABIC,
    GREEK,
    HANGUL,
    HEBREW,
    HINDI,
    PERSIAN,
    RUSSIAN,
    THAI,
    _letter_alternatives,
    _load_file_alphabet,
)


class TestAlphabetData:
    def test_counts(self):
        assert len(RUSSIAN) == 33   # modern Cyrillic
        assert len(GREEK) == 24     # Greek alphabet
        assert len(ARABIC) == 28    # Arabic abjad
        assert len(HINDI) == 43     # 10 vowels + 33 consonants
        assert len(THAI) == 44      # Thai consonants (incl. the 2 obsolete)
        assert len(HANGUL) == 40    # 19 consonants + 21 vowels
        assert len(HEBREW) == 27    # 22 letters + 5 final forms
        assert len(PERSIAN) == 33   # 32 letters + آ

    def test_letters_unique(self):
        for code, letters in ALPHABETS.items():
            chars = [c for c, _, _ in letters]
            assert len(chars) == len(set(chars)), code

    def test_rows_well_formed(self):
        for code, letters in ALPHABETS.items():
            for letter, rom, sound in letters:
                assert letter.strip(), code
                assert rom.strip(), (code, letter)
                assert sound.strip(), (code, letter)

    def test_every_nonlatin_course_has_a_deck(self):
        assert set(ALPHABETS) == {"ru", "el", "ar", "hi", "th", "ko", "he", "fa"}


class TestLetterAlternatives:
    def test_korean_lone_vowels_accept_their_seated_syllable(self):
        # The translit keyboard seats a bare vowel on silent ㅇ: typing "a"
        # yields 아, so the ㅏ card must accept it.
        assert _letter_alternatives("ko", "ㅏ") == ["아"]
        assert _letter_alternatives("ko", "ㅢ") == ["의"]
        assert _letter_alternatives("ko", "ㄱ") is None  # consonants type bare

    def test_every_korean_vowel_gets_exactly_its_own_seat(self):
        vowels = [ch for ch, _, _ in HANGUL if 0x314F <= ord(ch) <= 0x3163]
        assert len(vowels) == 21
        seats = [_letter_alternatives("ko", v)[0] for v in vowels]
        assert len(set(seats)) == 21  # distinct, no cross-talk

    def test_hebrew_plain_and_final_forms_accept_each_other(self):
        assert _letter_alternatives("he", "כ") == ["ך"]
        assert _letter_alternatives("he", "ך") == ["כ"]
        assert _letter_alternatives("he", "צ") == ["ץ"]
        assert _letter_alternatives("he", "א") is None

    def test_no_alternatives_leak_into_other_scripts(self):
        assert _letter_alternatives("fa", "ص") is None
        assert _letter_alternatives("ru", "а") is None


class TestFileAlphabet:
    """A checked-in data/alphabet/{code}.json (e.g. from the extractor)
    overrides / supplies an alphabet without editing this module."""

    def test_loads_from_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(seed_alphabet, "ALPHABET_DIR", tmp_path)
        (tmp_path / "zz.json").write_text(
            json.dumps({
                "language": "zz",
                "letters": [
                    {"letter": "Ɓ", "romanization": "b", "sound": "'b' as in boy"},
                    {"letter": "  ", "romanization": "x", "sound": "skip me"},  # no letter
                ],
            }),
            encoding="utf-8",
        )
        letters = _load_file_alphabet("zz")
        assert letters == [("Ɓ", "b", "'b' as in boy")]  # blank-letter row dropped

    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(seed_alphabet, "ALPHABET_DIR", tmp_path)
        assert _load_file_alphabet("nope") is None
