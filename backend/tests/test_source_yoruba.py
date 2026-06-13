"""Tests for the Yoruba sourcing builders and seeder — fixtures, no network."""
from collections import Counter

import pytest

from backend.services.seeder.source_data import (
    build_yoruba_rows,
    yoruba_corpus_counts,
)


class TestYorubaCorpusCounts:
    def test_counts_nfc_tokens_across_dirs(self, tmp_path):
        blog = tmp_path / "TheYorubaBlog"
        blog.mkdir()
        (blog / "post.txt").write_text("Ọmọ wá. Ọmọ lọ!", encoding="utf-8")
        news = tmp_path / "Iroyin"
        news.mkdir()
        (news / "a.txt").write_text("ọmọ kan", encoding="utf-8")

        counts = yoruba_corpus_counts(tmp_path)
        assert counts["ọmọ"] == 3
        assert counts["wá"] == 1

    def test_missing_dirs_skipped(self, tmp_path):
        assert yoruba_corpus_counts(tmp_path) == Counter()


class TestBuildYorubaRows:
    def test_exact_headword_match(self):
        counts = Counter({"àti": 100})
        dictionary = {"àti": {"pos": "conj", "gloss": "and", "plural": None}}
        rows = build_yoruba_rows(counts, dictionary)
        assert rows == [{"word": "àti", "pos": "conj", "gloss": "and"}]

    def test_toneless_corpus_token_folds_onto_diacritized_headword(self):
        counts = Counter({"ati": 50, "àti": 10})
        dictionary = {"àti": {"pos": "conj", "gloss": "and", "plural": None}}
        rows = build_yoruba_rows(counts, dictionary)
        assert rows[0]["word"] == "àti"

    def test_unknown_tokens_dropped(self):
        counts = Counter({"zzz": 1000})
        rows = build_yoruba_rows(counts, {"àti": {"pos": None, "gloss": "and"}})
        assert rows == []

    def test_orders_by_aggregated_count(self):
        counts = Counter({"ọmọ": 5, "ati": 50})
        dictionary = {
            "àti": {"pos": "conj", "gloss": "and", "plural": None},
            "ọmọ": {"pos": "noun", "gloss": "child", "plural": None},
        }
        rows = build_yoruba_rows(counts, dictionary)
        assert [r["word"] for r in rows] == ["àti", "ọmọ"]


class TestYorubaSeeder:
    @pytest.fixture
    async def records(self, tmp_path):
        import backend.services.seeder.seed_yoruba as mod
        from backend.services.seeder.seed_yoruba import YorubaSeeder

        (tmp_path / "yo_frequency.tsv").write_text(
            "rank\tword\tpos\ten\n"
            "1\tàti\tconj\tand\n"
            "2\tọmọ\tnoun\tchild\n"
            "3\tọmọ\tnoun\tduplicate skipped\n",
            encoding="utf-8",
        )
        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            return await YorubaSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original

    def test_language_code(self):
        from backend.services.seeder.seed_yoruba import YorubaSeeder
        assert YorubaSeeder.language_code == "yo"

    def test_diacritics_preserved(self, records):
        words = [r["word"] for r in records]
        assert "àti" in words and "ọmọ" in words

    def test_duplicates_skipped(self, records):
        assert len(records) == 2

    async def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_yoruba as mod
        from backend.services.seeder.seed_yoruba import YorubaSeeder

        original = mod.DATA_DIR
        mod.DATA_DIR = tmp_path
        try:
            with pytest.raises(FileNotFoundError):
                await YorubaSeeder("fake://db").transform()
        finally:
            mod.DATA_DIR = original
