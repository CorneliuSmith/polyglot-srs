"""Tests for the Hausa and Xhosa seeders and sourcing builders."""
from collections import Counter

import pytest

from backend.services.seeder.source_data import (
    build_hausa_rows,
    build_xhosa_rows,
    plaintext_dir_counts,
)


class TestPlaintextDirCounts:
    def test_counts_txt_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("Mutum daya. Mutum biyu.", encoding="utf-8")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("mutum uku", encoding="utf-8")
        counts = plaintext_dir_counts(tmp_path)
        assert counts["mutum"] == 3

    def test_missing_dir_empty(self, tmp_path):
        assert plaintext_dir_counts(tmp_path / "nope") == Counter()


class TestBuildRows:
    def test_hausa_apostrophe_folds_onto_headword(self):
        counts = Counter({"ya’ya": 50})
        dictionary = {"ya'ya": {"pos": "n", "gloss": "children", "plural": None}}
        rows = build_hausa_rows(counts, dictionary)
        assert rows == [{"word": "ya'ya", "pos": "n", "gloss": "children"}]

    def test_xhosa_conjugation_folds_onto_stem(self):
        counts = Counter({"ndiyahamba": 30, "hamba": 5})
        dictionary = {"hamba": {"pos": "v", "gloss": "go", "plural": None}}
        rows = build_xhosa_rows(counts, dictionary)
        assert rows[0]["word"] == "hamba"

    def test_unknown_tokens_dropped(self):
        rows = build_xhosa_rows(Counter({"zzz": 99}), {"hamba": {"gloss": "go"}})
        assert rows == []


class TestHausaSeeder:
    @pytest.fixture
    async def records(self, tmp_path):
        import backend.services.seeder.seed_hausa as mod
        from backend.services.seeder.seed_hausa import HausaSeeder

        (tmp_path / "ha_frequency.tsv").write_text(
            "rank\tword\tpos\ten\tplural\n"
            "1\tda\tconj\tand\t\n"
            "2\tmutum\tnoun\tperson\tmutane\n",
            encoding="utf-8",
        )
        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            return await HausaSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original

    def test_language_code(self):
        from backend.services.seeder.seed_hausa import HausaSeeder
        assert HausaSeeder.language_code == "ha"

    def test_plural_stored_as_alternative(self, records):
        mutum = next(r for r in records if r["word"] == "mutum")
        assert mutum["answer_alternatives"] == ["mutane"]
        import json
        assert json.loads(mutum["morphology"])["plural"] == "mutane"

    def test_no_plural_no_alternatives(self, records):
        da = next(r for r in records if r["word"] == "da")
        assert "answer_alternatives" not in da

    async def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_hausa as mod
        from backend.services.seeder.seed_hausa import HausaSeeder

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            with pytest.raises(FileNotFoundError):
                await HausaSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original


class TestXhosaSeeder:
    @pytest.fixture
    async def records(self, tmp_path):
        import backend.services.seeder.seed_xhosa as mod
        from backend.services.seeder.seed_xhosa import XhosaSeeder

        (tmp_path / "xh_frequency.tsv").write_text(
            "rank\tword\tpos\ten\n"
            "1\tukuba\tconj\tthat\n"
            "2\tumntu\tnoun\tperson\n"
            "3\tumntu\tnoun\tdup\n",
            encoding="utf-8",
        )
        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            return await XhosaSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original

    def test_language_code(self):
        from backend.services.seeder.seed_xhosa import XhosaSeeder
        assert XhosaSeeder.language_code == "xh"

    def test_records_and_dedup(self, records):
        assert [r["word"] for r in records] == ["ukuba", "umntu"]

    async def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_xhosa as mod
        from backend.services.seeder.seed_xhosa import XhosaSeeder

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            with pytest.raises(FileNotFoundError):
                await XhosaSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original
