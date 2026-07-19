"""Alphabet deck data integrity (ru + el ship; ar/hi/th are a later wave)."""

from backend.services.seeder.seed_alphabet import ALPHABETS, GREEK, RUSSIAN


class TestAlphabetData:
    def test_counts(self):
        assert len(RUSSIAN) == 33   # modern Cyrillic
        assert len(GREEK) == 24     # Greek alphabet

    def test_letters_unique(self):
        for letters in ALPHABETS.values():
            chars = [c for c, _, _ in letters]
            assert len(chars) == len(set(chars))

    def test_rows_well_formed(self):
        for code, letters in ALPHABETS.items():
            for letter, rom, sound in letters:
                assert letter.strip(), code
                assert rom.strip(), (code, letter)
                assert sound.strip(), (code, letter)

    def test_only_clean_scripts_shipped(self):
        # Arabic/Hindi/Thai deliberately excluded until verified per-letter.
        assert set(ALPHABETS) == {"ru", "el"}
