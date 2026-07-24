"""Tests for CSVImporter and the validators module."""
import csv
import io
import json
import textwrap
from pathlib import Path

import pytest

from backend.services.seeder.csv_importer import CSVImporter
from backend.services.seeder.validators import (
    VALID_LEVELS,
    VALID_POS,
    ValidationError,
    validate_script,
)

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_importer(language_code: str = "en", file_path: str = "dummy.csv") -> CSVImporter:
    """Return a CSVImporter wired to a fake DB URL (no connection needed for unit tests)."""
    return CSVImporter("postgresql://localhost/test", language_code, file_path)


def rows_from_csv(text: str) -> list[dict]:
    """Parse a CSV string into a list of row dicts (like DictReader)."""
    reader = csv.DictReader(io.StringIO(textwrap.dedent(text).strip()))
    return list(reader)


# ---------------------------------------------------------------------------
# Script validation — unit tests for validators.validate_script
# ---------------------------------------------------------------------------

class TestValidateScript:
    def test_arabic_accepts_arabic(self):
        assert validate_script("كتاب", "ar") is None

    def test_arabic_accepts_arabic_with_tashkeel(self):
        # Tashkeel / harakat are in the Arabic Unicode block
        assert validate_script("كَتَبَ", "ar") is None

    def test_arabic_accepts_arabic_with_spaces(self):
        assert validate_script("مدرسة الملك", "ar") is None

    def test_arabic_rejects_latin(self):
        err = validate_script("hello", "ar")
        assert err is not None
        assert "non-Arabic" in err

    def test_arabic_rejects_cyrillic(self):
        err = validate_script("кот", "ar")
        assert err is not None

    def test_cyrillic_accepts_russian(self):
        assert validate_script("кошка", "ru") is None

    def test_cyrillic_accepts_hyphenated(self):
        assert validate_script("что-то", "ru") is None

    def test_cyrillic_rejects_latin(self):
        err = validate_script("cat", "ru")
        assert err is not None
        assert "non-Cyrillic" in err

    def test_cyrillic_rejects_arabic(self):
        err = validate_script("كتاب", "ru")
        assert err is not None

    def test_latin_accepts_english(self):
        assert validate_script("hello", "en") is None

    def test_latin_accepts_hyphen_and_apostrophe(self):
        assert validate_script("mother-in-law", "en") is None
        assert validate_script("it's", "en") is None

    def test_latin_rejects_cyrillic(self):
        err = validate_script("кот", "en")
        assert err is not None
        assert "non-Latin" in err

    def test_latin_rejects_arabic(self):
        err = validate_script("مرحبا", "en")
        assert err is not None

    def test_unknown_language_always_passes(self):
        assert validate_script("anything123!@#", "zh") is None

    def test_empty_word_returns_error(self):
        err = validate_script("   ", "ru")
        assert err is not None
        assert "empty" in err


# ---------------------------------------------------------------------------
# ValidationError __str__
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_str_format(self):
        ve = ValidationError(5, "word", "hello", "some problem")
        s = str(ve)
        assert "Row 5" in s
        assert "word" in s
        assert "some problem" in s
        assert "hello" in s


# ---------------------------------------------------------------------------
# CSVImporter.validate — unit tests (no I/O)
# ---------------------------------------------------------------------------

class TestCSVImporterValidate:
    def _imp(self, language_code: str = "en") -> CSVImporter:
        return make_importer(language_code)

    # --- required fields ---

    def test_valid_row_passes(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition
            cat,a small mammal
        """)
        valid, errors = imp.validate(rows)
        assert errors == []
        assert len(valid) == 1

    def test_missing_word_field(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition
            ,no word here
        """)
        valid, errors = imp.validate(rows)
        assert len(valid) == 0
        assert any(e.column == "word" for e in errors)
        # Row 2 (header is row 1)
        assert errors[0].row == 2

    def test_missing_definition_field(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition
            dog,
        """)
        valid, errors = imp.validate(rows)
        assert any(e.column == "definition" for e in errors)

    # --- duplicate detection ---

    def test_duplicate_word_within_file(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition
            book,a written work
            book,another definition
        """)
        valid, errors = imp.validate(rows)
        dup_errors = [e for e in errors if "duplicate" in e.message]
        assert len(dup_errors) == 1
        assert dup_errors[0].column == "word"
        # First occurrence is valid, duplicate triggers on row 3
        assert dup_errors[0].row == 3

    # --- script validation ---

    def test_arabic_word_with_latin_fails(self):
        imp = make_importer("ar")
        rows = rows_from_csv("""
            word,definition
            hello,a greeting
        """)
        valid, errors = imp.validate(rows)
        assert any(e.column == "word" for e in errors)

    def test_russian_word_with_latin_fails(self):
        imp = make_importer("ru")
        rows = rows_from_csv("""
            word,definition
            hello,a greeting
        """)
        valid, errors = imp.validate(rows)
        assert any(e.column == "word" for e in errors)

    def test_english_word_with_cyrillic_fails(self):
        imp = make_importer("en")
        rows = rows_from_csv("""
            word,definition
            кошка,a cat
        """)
        valid, errors = imp.validate(rows)
        assert any(e.column == "word" for e in errors)

    # --- POS validation ---

    def test_invalid_pos_value(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition,pos
            cat,a small mammal,animal
        """)
        valid, errors = imp.validate(rows)
        assert any(e.column == "pos" for e in errors)

    def test_all_valid_pos_values_accepted(self):
        imp = self._imp()
        for pos in VALID_POS:
            rows = [{"word": "cat", "definition": "a mammal", "pos": pos}]
            _, errors = imp.validate(rows)
            assert not any(e.column == "pos" for e in errors), f"Valid POS '{pos}' was rejected"

    # --- CEFR level validation ---

    def test_invalid_cefr_level(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition,level
            cat,a small mammal,D1
        """)
        valid, errors = imp.validate(rows)
        assert any(e.column == "level" for e in errors)

    def test_all_valid_levels_accepted(self):
        imp = self._imp()
        for level in VALID_LEVELS:
            rows = [{"word": "cat", "definition": "a mammal", "level": level}]
            _, errors = imp.validate(rows)
            assert not any(e.column == "level" for e in errors), f"Valid level '{level}' was rejected"

    # --- level_source validation (optional column) ---

    def test_invalid_level_source_rejected(self):
        imp = self._imp()
        rows = [{"word": "cat", "definition": "a mammal", "level_source": "guess"}]
        _, errors = imp.validate(rows)
        assert any(e.column == "level_source" for e in errors)

    def test_valid_level_sources_accepted(self):
        imp = self._imp()
        for src in ("frequency", "curated", "ai"):
            rows = [{"word": "cat", "definition": "a mammal", "level_source": src}]
            _, errors = imp.validate(rows)
            assert not any(e.column == "level_source" for e in errors), src

    def test_absent_level_source_is_fine(self):
        imp = self._imp()
        rows = [{"word": "cat", "definition": "a mammal"}]
        _, errors = imp.validate(rows)
        assert not any(e.column == "level_source" for e in errors)

    # --- frequency_rank validation ---

    def test_negative_frequency_rank_fails(self):
        imp = self._imp()
        rows = [{"word": "cat", "definition": "a mammal", "frequency_rank": "-5"}]
        valid, errors = imp.validate(rows)
        assert any(e.column == "frequency_rank" for e in errors)

    def test_zero_frequency_rank_fails(self):
        imp = self._imp()
        rows = [{"word": "cat", "definition": "a mammal", "frequency_rank": "0"}]
        valid, errors = imp.validate(rows)
        assert any(e.column == "frequency_rank" for e in errors)

    def test_positive_frequency_rank_passes(self):
        imp = self._imp()
        rows = [{"word": "cat", "definition": "a mammal", "frequency_rank": "1"}]
        valid, errors = imp.validate(rows)
        assert not any(e.column == "frequency_rank" for e in errors)

    # --- mixed valid/invalid rows → no partial load ---

    def test_mixed_rows_only_invalid_reported(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition,pos
            cat,a small mammal,noun
            ,missing word,noun
            dog,a loyal pet,noun
        """)
        valid, errors = imp.validate(rows)
        # Only the invalid row produces errors
        assert len(errors) == 1
        # Valid rows are returned
        assert len(valid) == 2

    def test_error_includes_row_number(self):
        imp = self._imp()
        rows = rows_from_csv("""
            word,definition
            ,no word
        """)
        _, errors = imp.validate(rows)
        assert errors[0].row == 2  # header=1, first data row=2


# ---------------------------------------------------------------------------
# CSVImporter.transform — file parsing tests (uses actual fixture files)
# ---------------------------------------------------------------------------

class TestCSVImporterTransform:
    @pytest.mark.asyncio
    async def test_valid_csv_produces_correct_record_count(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        assert len(records) == 10

    @pytest.mark.asyncio
    async def test_valid_csv_word_and_definition_present(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        words = {r["word"] for r in records}
        assert "cat" in words
        assert "dog" in words

    @pytest.mark.asyncio
    async def test_invalid_csv_raises_value_error(self):
        imp = make_importer("en", str(FIXTURES / "invalid_vocab.csv"))
        with pytest.raises(ValueError, match="CSV validation failed"):
            await imp.transform()

    @pytest.mark.asyncio
    async def test_invalid_csv_no_partial_load(self):
        """Errors populated means no records returned — ValueError is raised."""
        imp = make_importer("en", str(FIXTURES / "invalid_vocab.csv"))
        with pytest.raises(ValueError):
            await imp.transform()
        # errors list should be populated
        assert len(imp.errors) > 0

    @pytest.mark.asyncio
    async def test_error_messages_include_row_numbers(self):
        imp = make_importer("en", str(FIXTURES / "invalid_vocab.csv"))
        with pytest.raises(ValueError):
            await imp.transform()
        for err in imp.errors:
            assert err.row >= 2, "Row numbers should start at 2 (header=1)"

    @pytest.mark.asyncio
    async def test_error_messages_include_column_names(self):
        imp = make_importer("en", str(FIXTURES / "invalid_vocab.csv"))
        with pytest.raises(ValueError):
            await imp.transform()
        columns = {e.column for e in imp.errors}
        # The invalid fixture has errors in: word, definition, pos, level, frequency_rank
        assert columns, "Should have at least one column identified in errors"

    # --- morphology mapping ---

    @pytest.mark.asyncio
    async def test_morphology_columns_populate_jsonb(self):
        imp = make_importer("ar", str(FIXTURES / "arabic_vocab_sample.csv"))
        records = await imp.transform()
        # كتب has root and form
        ktb = next(r for r in records if r["word"] == "كتب")
        morph = json.loads(ktb["morphology"])
        assert morph.get("root") == "ك ت ب"
        assert morph.get("form") == "I"

    @pytest.mark.asyncio
    async def test_morphology_gender_stored(self):
        imp = make_importer("ar", str(FIXTURES / "arabic_vocab_sample.csv"))
        records = await imp.transform()
        madrasa = next(r for r in records if r["word"] == "مدرسة")
        morph = json.loads(madrasa["morphology"])
        assert morph.get("gender") == "feminine"

    @pytest.mark.asyncio
    async def test_empty_morphology_columns_not_stored(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        # English fixture has no morphology columns
        for rec in records:
            morph = json.loads(rec["morphology"])
            assert morph == {}

    # --- translation columns ---

    @pytest.mark.asyncio
    async def test_definition_locale_columns_populate_translations(self):
        imp = make_importer("ar", str(FIXTURES / "arabic_vocab_sample.csv"))
        records = await imp.transform()
        # كتاب has definition_ru
        kitab = next(r for r in records if r["word"] == "كتاب")
        assert "ru" in kitab["translations"]
        assert kitab["translations"]["ru"] == "книга"

    @pytest.mark.asyncio
    async def test_english_always_in_translations(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        for rec in records:
            assert "en" in rec["translations"]

    # --- alternatives ---

    @pytest.mark.asyncio
    async def test_pipe_separated_alternatives_parsed(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        run_rec = next(r for r in records if r["word"] == "run")
        assert "walk" in run_rec["alternatives"]
        assert "jog" in run_rec["alternatives"]

    @pytest.mark.asyncio
    async def test_empty_alternatives_is_empty_list(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        cat_rec = next(r for r in records if r["word"] == "cat")
        assert cat_rec["alternatives"] == []

    # --- optional columns produce None not errors ---

    @pytest.mark.asyncio
    async def test_empty_optional_columns_produce_none(self):
        imp = make_importer("en", str(FIXTURES / "valid_vocab.csv"))
        records = await imp.transform()
        # cat has no reading, pos is populated but some have no level override
        cat_rec = next(r for r in records if r["word"] == "cat")
        assert cat_rec["reading"] is None

    # --- delimiter detection ---

    @pytest.mark.asyncio
    async def test_tsv_file_parsed_correctly(self, tmp_path):
        tsv = tmp_path / "vocab.tsv"
        tsv.write_text(
            "word\tdefinition\tpos\tlevel\n"
            "hello\ta greeting\tinterjection\tA1\n",
            encoding="utf-8",
        )
        imp = make_importer("en", str(tsv))
        records = await imp.transform()
        assert len(records) == 1
        assert records[0]["word"] == "hello"
        assert records[0]["pos"] == "interjection"

    @pytest.mark.asyncio
    async def test_csv_file_parsed_correctly(self, tmp_path):
        csv_file = tmp_path / "vocab.csv"
        csv_file.write_text(
            "word,definition,pos,level\n"
            "world,the earth,noun,A1\n",
            encoding="utf-8",
        )
        imp = make_importer("en", str(csv_file))
        records = await imp.transform()
        assert len(records) == 1
        assert records[0]["word"] == "world"

    # --- Arabic fixture end-to-end ---

    @pytest.mark.asyncio
    async def test_arabic_fixture_all_valid(self):
        imp = make_importer("ar", str(FIXTURES / "arabic_vocab_sample.csv"))
        records = await imp.transform()
        assert len(records) == 5

    @pytest.mark.asyncio
    async def test_arabic_fixture_words_are_arabic_script(self):
        imp = make_importer("ar", str(FIXTURES / "arabic_vocab_sample.csv"))
        records = await imp.transform()
        words = {r["word"] for r in records}
        assert "كتاب" in words
        assert "مدرسة" in words

    # --- file-not-found ---

    @pytest.mark.asyncio
    async def test_missing_file_raises_file_not_found(self):
        imp = make_importer("en", "/nonexistent/path/vocab.csv")
        with pytest.raises(FileNotFoundError):
            await imp.download()

    # --- rank_to_level fallback ---

    @pytest.mark.asyncio
    async def test_freq_rank_drives_level_when_level_empty(self, tmp_path):
        csv_file = tmp_path / "vocab.csv"
        csv_file.write_text(
            "word,definition,frequency_rank\n"
            "apple,a fruit,100\n",
            encoding="utf-8",
        )
        imp = make_importer("en", str(csv_file))
        records = await imp.transform()
        # rank 100 → A1
        assert records[0]["level"] == "A1"

    @pytest.mark.asyncio
    async def test_explicit_level_overrides_rank_to_level(self, tmp_path):
        csv_file = tmp_path / "vocab.csv"
        csv_file.write_text(
            "word,definition,level,frequency_rank\n"
            "apple,a fruit,C2,100\n",
            encoding="utf-8",
        )
        imp = make_importer("en", str(csv_file))
        records = await imp.transform()
        assert records[0]["level"] == "C2"

    @pytest.mark.asyncio
    async def test_level_source_passes_through_and_defaults_none(self, tmp_path):
        csv_file = tmp_path / "vocab.csv"
        csv_file.write_text(
            "word,definition,level,level_source\n"
            "casa,house,A1,\n"          # stated level, no source → None (loader defaults to 'frequency')
            "rareza,rarity,C1,ai\n",   # provisional AI-estimated level
            encoding="utf-8",
        )
        imp = make_importer("en", str(csv_file))
        by_word = {r["word"]: r for r in await imp.transform()}
        assert by_word["casa"]["level_source"] is None
        assert by_word["rareza"]["level_source"] == "ai"
