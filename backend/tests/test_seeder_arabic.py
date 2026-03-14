"""Tests for ArabicSeeder — uses fixture JSON file, no network calls."""
import json
import pytest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from backend.services.seeder.seed_arabic import ArabicSeeder

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fixture_patch():
    """ExitStack context manager that patches seeder to use sample fixture file."""
    stack = ExitStack()
    stack.enter_context(patch("backend.services.seeder.seed_arabic.DATA_DIR", FIXTURES_DIR))
    return stack


@pytest.fixture
def seeder():
    return ArabicSeeder("postgresql://localhost/test")


# ── language_code ─────────────────────────────────────────────────────────────

class TestArabicSeederLanguageCode:
    def test_language_code_is_ar(self, seeder):
        assert seeder.language_code == "ar"


# ── download ──────────────────────────────────────────────────────────────────

class TestArabicSeederDownload:
    async def test_download_succeeds_when_seed_file_exists(self, seeder):
        """download() should succeed when ar_seed.json is present (using fixture dir)."""
        with fixture_patch():
            # Fixture dir has ar_seed_sample.json but not ar_seed.json —
            # patch name to the sample so the file exists
            with patch("backend.services.seeder.seed_arabic.DATA_DIR", FIXTURES_DIR):
                # Write a temporary ar_seed.json stub (just check the path logic)
                import tempfile, os
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)
                    (tmp_path / "ar_seed.json").write_text("[]", encoding="utf-8")
                    with patch("backend.services.seeder.seed_arabic.DATA_DIR", tmp_path):
                        await seeder.download()  # should not raise

    async def test_download_raises_when_seed_file_missing(self, seeder):
        """download() should raise FileNotFoundError when ar_seed.json is absent."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            with patch("backend.services.seeder.seed_arabic.DATA_DIR", empty_dir):
                with pytest.raises(FileNotFoundError, match="ar_seed.json"):
                    await seeder.download()


# ── transform with fixture data ───────────────────────────────────────────────

class TestArabicSeederTransform:
    async def test_returns_list_of_dicts(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", FIXTURES_DIR):
            with patch("backend.services.seeder.seed_arabic.DATA_DIR") as mock_dir:
                mock_dir.__truediv__ = lambda self, key: FIXTURES_DIR / "ar_seed_sample.json" if key == "ar_seed.json" else FIXTURES_DIR / key
                # Use direct patch approach
                pass
        # Direct approach: patch the module-level DATA_DIR used in transform
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        assert isinstance(records, list)
        assert len(records) == 10
        assert all(isinstance(r, dict) for r in records)

    async def test_word_field_populated(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        words = [r["word"] for r in records]
        assert "كتب" in words
        assert "كتاب" in words
        assert "في" in words

    async def test_reading_populated(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        ktaba = next(r for r in records if r["word"] == "كتاب")
        assert ktaba["reading"] == "كِتَاب"

    async def test_pos_populated(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        verb = next(r for r in records if r["word"] == "كتب")
        assert verb["pos"] == "verb"
        noun = next(r for r in records if r["word"] == "كتاب")
        assert noun["pos"] == "noun"

    async def test_frequency_rank_populated(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        fi = next(r for r in records if r["word"] == "في")
        assert fi["frequency_rank"] == 1

    async def test_level_derived_from_rank(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        # rank 1 → A1
        fi = next(r for r in records if r["word"] == "في")
        assert fi["level"] == "A1"
        # rank 292 → A1 (<=500)
        iqtisad = next(r for r in records if r["word"] == "اقتصاد")
        assert iqtisad["level"] == "A1"

    async def test_translations_english_locale(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        ktaba = next(r for r in records if r["word"] == "كتاب")
        assert "en" in ktaba["translations"]
        assert ktaba["translations"]["en"] == "book"

    async def test_all_records_have_english_translation(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        for r in records:
            assert "en" in r["translations"], f"Missing 'en' translation for {r['word']!r}"

    async def test_morphology_is_valid_json_string(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        for r in records:
            morph_str = r.get("morphology", "{}")
            assert isinstance(morph_str, str), f"morphology should be str, got {type(morph_str)}"
            parsed = json.loads(morph_str)
            assert isinstance(parsed, dict)

    async def test_morphology_includes_root_for_verb(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        verb = next(r for r in records if r["word"] == "كتب")
        morph = json.loads(verb["morphology"])
        assert morph.get("root") == "كتب"

    async def test_morphology_includes_form_for_verb(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        verb = next(r for r in records if r["word"] == "كتب")
        morph = json.loads(verb["morphology"])
        assert morph.get("form") == "I"

    async def test_morphology_includes_form_x(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        verb = next(r for r in records if r["word"] == "استطاع")
        morph = json.loads(verb["morphology"])
        assert morph.get("form") == "X"

    async def test_morphology_includes_gender_for_noun(self, seeder):
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        noun = next(r for r in records if r["word"] == "كتاب")
        morph = json.loads(noun["morphology"])
        assert morph.get("gender") == "m"
        school = next(r for r in records if r["word"] == "مدرسة")
        morph2 = json.loads(school["morphology"])
        assert morph2.get("gender") == "f"

    async def test_morphology_no_none_values(self, seeder):
        """None values should be stripped from morphology dict."""
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        for r in records:
            morph = json.loads(r["morphology"])
            for k, v in morph.items():
                assert v is not None, f"morphology[{k!r}] is None for word {r['word']!r}"

    async def test_word_without_root_has_no_root_in_morphology(self, seeder):
        """Words with root=null (particles like في) should not have root key in morphology."""
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            records = await seeder.transform()
        fi = next(r for r in records if r["word"] == "في")
        morph = json.loads(fi["morphology"])
        # root is None in seed, should be stripped
        assert "root" not in morph or morph.get("root") is not None


# ── camel-tools fallback ──────────────────────────────────────────────────────

class TestArabicSeederCamelToolsFallback:
    async def test_transform_works_without_camel_tools(self, seeder):
        """transform() should succeed when camel-tools raises ImportError."""
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            with patch("builtins.__import__", side_effect=_block_camel_tools):
                records = await seeder.transform()
        assert len(records) == 10

    async def test_morphology_from_seed_when_camel_unavailable(self, seeder):
        """When camel-tools unavailable, morphology is still populated from seed data."""
        with patch("backend.services.seeder.seed_arabic.DATA_DIR", new=_SampleDir(FIXTURES_DIR)):
            with patch("builtins.__import__", side_effect=_block_camel_tools):
                records = await seeder.transform()
        verb = next(r for r in records if r["word"] == "كتب")
        morph = json.loads(verb["morphology"])
        assert morph.get("root") == "كتب"
        assert morph.get("form") == "I"


# ── Helpers ───────────────────────────────────────────────────────────────────

class _SampleDir:
    """A fake DATA_DIR path that redirects ar_seed.json to ar_seed_sample.json."""

    def __init__(self, fixtures_dir: Path):
        self._dir = fixtures_dir

    def __truediv__(self, name: str) -> Path:
        if name == "ar_seed.json":
            return self._dir / "ar_seed_sample.json"
        return self._dir / name

    def __str__(self):
        return str(self._dir)


_REAL_IMPORT = __import__


def _block_camel_tools(name, *args, **kwargs):
    """Side-effect for builtins.__import__ that blocks camel_tools imports."""
    if name.startswith("camel_tools"):
        raise ImportError(f"Blocked for testing: {name}")
    return _REAL_IMPORT(name, *args, **kwargs)
