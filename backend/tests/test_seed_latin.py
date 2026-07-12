"""Tests for the Latin-script frequency-TSV seeders."""
import json

import pytest

from backend.services.seeder.seed_latin import SEEDERS, SpanishSeeder


class TestSpanishSeeder:
    @pytest.fixture
    async def records(self, tmp_path):
        import backend.services.seeder.seed_latin as mod

        (tmp_path / "es_frequency.tsv").write_text(
            "rank\tword\tpos\ten\n"
            "1\tde\tprep\tof\n"
            "2\tCasa\tnoun\thouse\n"
            "3\tcasa\tnoun\tduplicate\n"
            "4\t\t\tempty skipped\n",
            encoding="utf-8",
        )
        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            return await SpanishSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original

    def test_language_code(self):
        assert SpanishSeeder.language_code == "es"

    def test_all_registered(self):
        assert set(SEEDERS) == {"es", "it", "fr", "de", "ca", "mi", "ro", "el", "pt"}

    def test_records_lowercased_and_deduped(self, records):
        words = [r["word"] for r in records]
        assert words == ["de", "casa"]  # 'Casa' lowercased, duplicate dropped

    def test_fields(self, records):
        casa = next(r for r in records if r["word"] == "casa")
        assert casa["translations"]["en"] == "house"
        assert casa["level"] == "A1"
        assert json.loads(casa["morphology"])["lemma"] == "casa"

    async def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_latin as mod

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            with pytest.raises(FileNotFoundError):
                await SpanishSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original
