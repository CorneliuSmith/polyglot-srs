"""Tests for RussianSeeder — uses fixture TSV files, no network calls."""
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.seeder.seed_russian import RussianSeeder

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fixture_patch():
    """ExitStack context manager that patches seeder to use sample fixture files."""
    stack = ExitStack()
    stack.enter_context(patch("backend.services.seeder.seed_russian.DATA_DIR", FIXTURES_DIR))
    stack.enter_context(patch("backend.services.seeder.seed_russian.WORDS_FILENAME", "ru_words_sample.tsv"))
    stack.enter_context(patch("backend.services.seeder.seed_russian.TRANSLATIONS_FILENAME", "ru_translations_sample.tsv"))
    return stack


@pytest.fixture
def seeder():
    return RussianSeeder("postgresql://localhost/test")


# ── language_code ─────────────────────────────────────────────────────────────

class TestRussianSeederLanguageCode:
    def test_language_code_is_ru(self, seeder):
        assert seeder.language_code == "ru"


# ── transform with fixture data ───────────────────────────────────────────────

class TestRussianSeederTransform:
    async def test_returns_list_of_dicts(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        assert isinstance(records, list)
        assert len(records) > 0
        assert all(isinstance(r, dict) for r in records)

    async def test_disabled_words_are_skipped(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        words = [r["word"] for r in records]
        assert "disabled_word" not in words

    async def test_all_enabled_words_present(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        words = [r["word"] for r in records]
        # 9 enabled rows in the fixture (1 disabled)
        assert len(records) == 9
        assert "я" in words
        assert "быть" in words
        assert "студент" in words

    async def test_accented_form_used_as_reading(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        book = next(r for r in records if r["word"] == "книга")
        assert book["reading"] == "кни́га"

    async def test_reading_is_none_when_same_as_bare(self, seeder):
        """When accented == bare, reading should be None (no accent info)."""
        with fixture_patch():
            records = await seeder.transform()
        # "быть" has accented="быть" (same as bare)
        byt = next(r for r in records if r["word"] == "быть")
        assert byt["reading"] is None

    async def test_frequency_rank_populated(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        ya = next(r for r in records if r["word"] == "я")
        assert ya["frequency_rank"] == 1

    async def test_level_derived_from_rank(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        ya = next(r for r in records if r["word"] == "я")
        assert ya["level"] == "A1"      # rank 1 → A1
        book = next(r for r in records if r["word"] == "книга")
        assert book["level"] == "B1"    # rank 1600 → B1 (> 1500)
        student = next(r for r in records if r["word"] == "студент")
        assert student["level"] == "C1"  # rank 5100 → C1

    async def test_translations_mapped_by_locale(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        ya = next(r for r in records if r["word"] == "я")
        assert "en" in ya["translations"]
        assert ya["translations"]["en"] == "I, me"
        # Russian translation also present in fixture
        assert "ru" in ya["translations"]

    async def test_multiple_locales_for_book(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        book = next(r for r in records if r["word"] == "книга")
        assert "en" in book["translations"]
        assert "de" in book["translations"]
        assert book["translations"]["en"] == "book"
        assert book["translations"]["de"] == "Buch"

    async def test_morphology_is_valid_json_string(self, seeder):
        with fixture_patch():
            records = await seeder.transform()
        for r in records:
            morph = r.get("morphology", "{}")
            assert isinstance(morph, str), f"morphology should be str, got {type(morph)}"
            parsed = json.loads(morph)
            assert isinstance(parsed, dict)

    async def test_word_with_no_translations_has_empty_dict(self, seeder):
        """Words with no translation entries should have empty translations."""
        with fixture_patch():
            records = await seeder.transform()
        # работать has no translation in fixture (word_id=8, not in translations)
        rabotat = next((r for r in records if r["word"] == "работать"), None)
        assert rabotat is not None
        assert rabotat["translations"] == {}


# ── pymorphy3 morphology enrichment ──────────────────────────────────────────

class TestRussianSeederMorphology:
    async def test_morphology_populated_when_pymorphy3_available(self, seeder):
        pytest.importorskip("pymorphy3")
        with fixture_patch():
            records = await seeder.transform()
        # книга is a noun — should have gender
        book = next(r for r in records if r["word"] == "книга")
        morph = json.loads(book.get("morphology", "{}"))
        # pymorphy3 should provide gender for книга (feminine)
        assert "gender" in morph
        assert morph["gender"] is not None

    async def test_pos_populated_when_pymorphy3_available(self, seeder):
        pytest.importorskip("pymorphy3")
        with fixture_patch():
            records = await seeder.transform()
        # быть is a verb
        byt = next(r for r in records if r["word"] == "быть")
        assert byt["pos"] is not None
        # книга is a noun
        book = next(r for r in records if r["word"] == "книга")
        assert book["pos"] is not None
