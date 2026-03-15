"""Integration tests validating all three seeders + CSV importer produce correct schema."""
import json
import pytest

from backend.services.seeder.base import BaseSeeder

VALID_LEVELS = {None, "A1", "A2", "B1", "B2", "C1", "C2"}
REQUIRED_RECORD_KEYS = {"word", "translations", "morphology"}


class TestSeederImports:
    """All seeder classes can be imported and have correct language codes."""

    def test_russian_seeder_importable(self):
        from backend.services.seeder.seed_russian import RussianSeeder
        assert RussianSeeder.language_code == "ru"

    def test_arabic_seeder_importable(self):
        from backend.services.seeder.seed_arabic import ArabicSeeder
        assert ArabicSeeder.language_code == "ar"

    def test_english_seeder_importable(self):
        from backend.services.seeder.seed_english import EnglishSeeder
        assert EnglishSeeder.language_code == "en"

    def test_csv_importer_importable(self):
        from backend.services.seeder.csv_importer import CSVImporter
        importer = CSVImporter("fake://db", "ar", "/fake/path.csv")
        assert importer.language_code == "ar"

    def test_all_seeders_extend_base(self):
        from backend.services.seeder.seed_russian import RussianSeeder
        from backend.services.seeder.seed_arabic import ArabicSeeder
        from backend.services.seeder.seed_english import EnglishSeeder
        from backend.services.seeder.csv_importer import CSVImporter

        for cls in (RussianSeeder, ArabicSeeder, EnglishSeeder, CSVImporter):
            assert issubclass(cls, BaseSeeder), f"{cls.__name__} must extend BaseSeeder"


class TestCliRunnerImport:
    """CLI runner module can be imported without errors."""

    def test_run_module_importable(self):
        import backend.services.seeder.run  # noqa: F401


def _validate_record(rec: dict, index: int):
    """Validate a single transform() output record matches vocabulary schema."""
    # Required keys
    for key in REQUIRED_RECORD_KEYS:
        assert key in rec, f"Record {index}: missing required key '{key}'"

    # word: non-empty string
    assert isinstance(rec["word"], str) and rec["word"].strip(), \
        f"Record {index}: word must be non-empty string, got {rec['word']!r}"

    # translations: dict with at least one entry
    assert isinstance(rec["translations"], dict), \
        f"Record {index}: translations must be dict, got {type(rec['translations'])}"
    assert len(rec["translations"]) > 0, \
        f"Record {index}: translations must have at least one entry"

    # morphology: valid JSON string
    morph_str = rec.get("morphology", "{}")
    assert isinstance(morph_str, str), \
        f"Record {index}: morphology must be JSON string, got {type(morph_str)}"
    try:
        json.loads(morph_str)
    except (json.JSONDecodeError, TypeError):
        pytest.fail(f"Record {index}: morphology is not valid JSON: {morph_str!r}")

    # level: None or valid CEFR
    level = rec.get("level")
    assert level in VALID_LEVELS, \
        f"Record {index}: level must be None or valid CEFR, got {level!r}"

    # frequency_rank: None or positive int
    rank = rec.get("frequency_rank")
    if rank is not None:
        assert isinstance(rank, int) and rank > 0, \
            f"Record {index}: frequency_rank must be positive int, got {rank!r}"


class TestRussianTransformSchema:
    """Russian seeder transform() output matches vocabulary schema."""

    @pytest.fixture
    def records(self, tmp_path):
        import asyncio
        from backend.services.seeder.seed_russian import RussianSeeder
        import backend.services.seeder.seed_russian as mod

        # Create fixture TSV files
        words_tsv = tmp_path / "ru_words.tsv"
        trans_tsv = tmp_path / "ru_translations.tsv"

        words_tsv.write_text(
            "id\tposition\tbare\taccented\trank\tdisabled\n"
            "1\t1\tбыть\tбы́ть\t1\t0\n"
            "2\t2\tмочь\tмо́чь\t5\t0\n"
            "3\t3\tдом\tдо́м\t42\t0\n",
            encoding="utf-8"
        )
        trans_tsv.write_text(
            "id\tword_id\tlang\ttl\texample\tinfo\tposition\n"
            "1\t1\ten\tto be\t\t\t1\n"
            "2\t2\ten\tto be able\t\t\t1\n"
            "3\t3\ten\thouse\t\t\t1\n",
            encoding="utf-8"
        )

        # Patch DATA_DIR
        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            seeder = RussianSeeder("fake://db")
            return asyncio.get_event_loop().run_until_complete(seeder.transform())
        finally:
            mod.DATA_DIR = original

    def test_records_not_empty(self, records):
        assert len(records) > 0

    def test_all_records_valid_schema(self, records):
        for i, rec in enumerate(records):
            _validate_record(rec, i)

    def test_no_duplicate_words(self, records):
        words = [r["word"] for r in records]
        assert len(words) == len(set(words)), "Duplicate words found in transform output"


class TestArabicTransformSchema:
    """Arabic seeder transform() output matches vocabulary schema."""

    @pytest.fixture
    def records(self, tmp_path):
        import asyncio
        import json as json_mod
        from backend.services.seeder.seed_arabic import ArabicSeeder
        import backend.services.seeder.seed_arabic as mod

        # Create fixture seed file
        seed_file = tmp_path / "ar_seed.json"
        seed_file.write_text(json_mod.dumps([
            {"word": "كتب", "reading": "كَتَبَ", "pos": "verb", "rank": 15,
             "root": "كتب", "form": "I", "translations": {"en": "to write"}},
            {"word": "بيت", "reading": "بَيْت", "pos": "noun", "rank": 50,
             "root": "بيت", "gender": "m", "translations": {"en": "house"}},
        ], ensure_ascii=False), encoding="utf-8")

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            seeder = ArabicSeeder("fake://db")
            return asyncio.get_event_loop().run_until_complete(seeder.transform())
        finally:
            mod.DATA_DIR = original

    def test_records_not_empty(self, records):
        assert len(records) > 0

    def test_all_records_valid_schema(self, records):
        for i, rec in enumerate(records):
            _validate_record(rec, i)

    def test_no_duplicate_words(self, records):
        words = [r["word"] for r in records]
        assert len(words) == len(set(words))


class TestEnglishTransformSchema:
    """English seeder transform() output matches vocabulary schema."""

    @pytest.fixture
    def records(self, tmp_path):
        import asyncio
        from backend.services.seeder.seed_english import EnglishSeeder
        import backend.services.seeder.seed_english as mod

        # Create small fixture frequency file
        freq_file = tmp_path / "en_frequency.tsv"
        freq_file.write_text(
            "rank\tword\n1\ttime\n2\tyear\n3\tpeople\n4\tway\n5\tday\n",
            encoding="utf-8"
        )

        original_dir = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            seeder = EnglishSeeder("fake://db")
            return asyncio.get_event_loop().run_until_complete(seeder.transform())
        finally:
            mod.DATA_DIR = original_dir

    def test_records_not_empty(self, records):
        assert len(records) > 0

    def test_all_records_valid_schema(self, records):
        for i, rec in enumerate(records):
            _validate_record(rec, i)

    def test_no_duplicate_words(self, records):
        words = [r["word"] for r in records]
        assert len(words) == len(set(words))
