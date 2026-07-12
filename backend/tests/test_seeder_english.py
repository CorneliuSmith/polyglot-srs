"""Tests for EnglishSeeder — uses fixture TSV files, no network calls."""
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.seeder.seed_english import EnglishSeeder

FIXTURES_DIR = Path(__file__).parent / "fixtures"

VALID_CEFR = {"A1", "A2", "B1", "B2", "C1", None}


def fixture_patch():
    """ExitStack context manager that patches seeder to use fixture file."""
    stack = ExitStack()
    stack.enter_context(patch("backend.services.seeder.seed_english.DATA_DIR", FIXTURES_DIR))
    stack.enter_context(patch("backend.services.seeder.seed_english.FREQ_FILENAME", "en_frequency_sample.tsv"))
    return stack


@pytest.fixture
def seeder():
    return EnglishSeeder("postgresql://localhost/test")


# ── language_code ─────────────────────────────────────────────────────────────

class TestEnglishSeederLanguageCode:
    def test_language_code_is_en(self, seeder):
        assert seeder.language_code == "en"


# ── transform with fixture data ───────────────────────────────────────────────

class TestEnglishSeederTransform:
    async def test_returns_list_of_dicts(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        assert isinstance(records, list)
        assert len(records) > 0
        assert all(isinstance(r, dict) for r in records)

    async def test_content_words_present(self, seeder):
        """Common content words should appear in the output."""
        with fixture_patch():
            records = await seeder.transform()
        words = {r["word"] for r in records}
        # These words all have WordNet synsets
        assert "book" in words
        assert "water" in words
        assert "music" in words

    async def test_function_words_get_grammar_glosses(self, seeder):
        """'the', 'of', 'and' have no useful WordNet synsets — they carry
        hand-written grammar glosses instead of being skipped (or worse,
        wearing WordNet's iodine-for-'i' style junk)."""
        with fixture_patch():
            records = await seeder.transform()
        by_word = {r["word"]: r for r in records}
        assert "article" in by_word["the"]["translations"]["en"]
        assert by_word["of"]["translations"]["en"]  # a real gloss, present
        assert by_word["and"]["translations"]["en"]
        # pinned POS survives (spaCy mislabels bare tokens)
        assert by_word["the"]["pos"] == "article"

    async def test_morphology_includes_lemma(self, seeder):
        """Every record's morphology JSON must contain a 'lemma' key."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            morph = json.loads(r["morphology"])
            assert "lemma" in morph, f"Missing 'lemma' in morphology for word '{r['word']}'"
            assert isinstance(morph["lemma"], str)
            assert morph["lemma"]  # non-empty

    async def test_morphology_is_valid_json_string(self, seeder):
        """morphology field must be a JSON-serializable string."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            morph_str = r.get("morphology", "{}")
            assert isinstance(morph_str, str), f"Expected str, got {type(morph_str)}"
            parsed = json.loads(morph_str)
            assert isinstance(parsed, dict)

    async def test_pos_from_wordnet_synset(self, seeder):
        """POS should be populated (non-null) for words with WordNet synsets."""
        with fixture_patch():
            records = await seeder.transform()
        # Check that at least the clear content nouns get a pos tag
        nouns = [r for r in records if r["word"] in {"music", "family", "school", "water"}]
        assert len(nouns) > 0, "Expected at least one common noun in fixture"
        for r in nouns:
            assert r["pos"] is not None, f"Expected non-null POS for word '{r['word']}'"
            # POS value is a non-empty lowercase string
            assert isinstance(r["pos"], str)
            assert r["pos"].strip()

    async def test_rank_to_level_applied(self, seeder):
        """frequency_rank and level should be correctly derived."""
        with fixture_patch():
            records = await seeder.transform()
        # rank 1 → A1
        r1 = next((r for r in records if r["frequency_rank"] == 1), None)
        assert r1 is not None
        assert r1["level"] == "A1"

    async def test_level_is_valid_cefr_or_none(self, seeder):
        """Every record's level should be a valid CEFR string or None."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            assert r["level"] in VALID_CEFR, f"Invalid level '{r['level']}' for word '{r['word']}'"

    async def test_translations_dict_has_en_key(self, seeder):
        """Every record should have an 'en' key in translations from WordNet."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            assert "en" in r["translations"], f"Missing 'en' in translations for '{r['word']}'"
            assert isinstance(r["translations"]["en"], str)
            assert r["translations"]["en"]  # non-empty definition

    async def test_reading_is_none(self, seeder):
        """English words have no reading field (no accent marks)."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            assert r["reading"] is None

    async def test_frequency_rank_is_positive_int(self, seeder):
        """frequency_rank should be a positive integer."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            assert isinstance(r["frequency_rank"], int)
            assert r["frequency_rank"] > 0

    async def test_word_is_non_empty_string(self, seeder):
        """Every record's word should be a non-empty string."""
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            assert isinstance(r["word"], str)
            assert r["word"].strip()

    async def test_missing_freq_file_raises_error(self, seeder):
        """FileNotFoundError should be raised when the frequency file is missing."""
        with ExitStack() as stack:
            stack.enter_context(patch("backend.services.seeder.seed_english.DATA_DIR", FIXTURES_DIR))
            stack.enter_context(patch("backend.services.seeder.seed_english.FREQ_FILENAME", "nonexistent_file.tsv"))
            with pytest.raises(FileNotFoundError):
                await seeder.transform()
