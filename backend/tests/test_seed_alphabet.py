"""Alphabet deck data integrity for the five non-Latin scripts."""

from backend.services.seeder.seed_alphabet import (
    ALPHABETS,
    ARABIC,
    GREEK,
    HINDI,
    RUSSIAN,
    THAI,
)


class TestAlphabetData:
    def test_counts(self):
        assert len(RUSSIAN) == 33   # modern Cyrillic
        assert len(GREEK) == 24     # Greek alphabet
        assert len(ARABIC) == 28    # Arabic abjad
        assert len(THAI) == 44      # Thai consonants (incl. the 2 obsolete)

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

    def test_all_five_scripts(self):
        assert set(ALPHABETS) == {"ru", "el", "ar", "hi", "th"}
