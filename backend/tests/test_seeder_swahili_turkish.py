"""Tests for the Swahili and Turkish seeders — fixture TSVs, no network calls."""
import json

import pytest


def _write_tsv(path, rows):
    lines = ["rank\tword\tpos\ten"] + [
        f"{r['rank']}\t{r['word']}\t{r['pos']}\t{r['en']}" for r in rows
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestSwahiliSeeder:
    @pytest.fixture
    async def records(self, tmp_path):
        import backend.services.seeder.seed_swahili as mod
        from backend.services.seeder.seed_swahili import SwahiliSeeder

        _write_tsv(tmp_path / "sw_frequency.tsv", [
            {"rank": 1, "word": "na", "pos": "conj", "en": "and, with"},
            {"rank": 2, "word": "Kitabu", "pos": "noun", "en": "book"},
            {"rank": 3, "word": "soma", "pos": "verb", "en": "to read"},
            {"rank": 4, "word": "kitabu", "pos": "noun", "en": "book duplicate"},
            {"rank": 5, "word": "", "pos": "", "en": "empty word skipped"},
        ])

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            return await SwahiliSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original

    def test_language_code(self):
        from backend.services.seeder.seed_swahili import SwahiliSeeder
        assert SwahiliSeeder.language_code == "sw"

    def test_records_parsed(self, records):
        words = [r["word"] for r in records]
        assert "na" in words and "kitabu" in words and "soma" in words

    def test_duplicates_and_empties_skipped(self, records):
        words = [r["word"] for r in records]
        assert len(words) == len(set(words))
        assert "" not in words

    def test_level_from_rank(self, records):
        assert all(r["level"] == "A1" for r in records)

    def test_morphology_valid_json(self, records):
        for r in records:
            assert "lemma" in json.loads(r["morphology"])

    def test_translations_have_en(self, records):
        for r in records:
            assert r["translations"]["en"]

    async def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_swahili as mod
        from backend.services.seeder.seed_swahili import SwahiliSeeder

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path  # empty dir
        try:
            with pytest.raises(FileNotFoundError):
                await SwahiliSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original


class TestTurkishSeeder:
    @pytest.fixture
    async def records(self, tmp_path):
        import backend.services.seeder.seed_turkish as mod
        from backend.services.seeder.seed_turkish import TurkishSeeder

        _write_tsv(tmp_path / "tr_frequency.tsv", [
            {"rank": 1, "word": "bir", "pos": "det", "en": "a, one"},
            {"rank": 2, "word": "Işık", "pos": "noun", "en": "light"},
            {"rank": 3, "word": "İyi", "pos": "adj", "en": "good"},
        ])

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            return await TurkishSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original

    def test_language_code(self):
        from backend.services.seeder.seed_turkish import TurkishSeeder
        assert TurkishSeeder.language_code == "tr"

    def test_turkish_casing_applied(self, records):
        words = {r["word"] for r in records}
        # 'Işık' must lower to 'ışık' (dotless), 'İyi' to 'iyi' (dotted)
        assert "ışık" in words
        assert "iyi" in words

    def test_records_have_required_fields(self, records):
        for r in records:
            assert r["word"] and r["translations"]["en"]
            assert isinstance(r["frequency_rank"], int)
            assert "lemma" in json.loads(r["morphology"])

    async def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_turkish as mod
        from backend.services.seeder.seed_turkish import TurkishSeeder

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            with pytest.raises(FileNotFoundError):
                await TurkishSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original
