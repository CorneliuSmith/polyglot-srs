"""Tests for EnglishSeeder — uses fixture TSV files, no network calls."""
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.seeder.seed_english import EnglishSeeder

from .conftest import requires_wordnet

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

@requires_wordnet
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


# ── hand-authored overrides ───────────────────────────────────────────────────

@requires_wordnet
class TestEnglishSeederGlossOverrides:
    """data/gloss_overrides.tsv is the one place a bad definition gets fixed.

    English used to be the only course it could not reach: its definitions come
    from WordNet at seed time rather than from a gloss column, so nothing read
    the file. WordNet's own senses are what defined `be` as beryllium.
    """

    async def test_override_replaces_the_wordnet_definition(self, seeder):
        rows = {"book": {"pos": "noun", "en": "a written work bound between covers"}}
        with fixture_patch(), patch(
            "backend.services.seeder.seed_english.load_gloss_overrides", return_value=rows
        ):
            records = await seeder.transform()
        book = next(r for r in records if r["word"] == "book")
        assert book["translations"]["en"] == "a written work bound between covers"
        assert book["pos"] == "noun"

    async def test_override_beats_the_builtin_function_gloss(self, seeder):
        """'the' has a hard-coded gloss; the file still wins, or it cannot fix one."""
        rows = {"the": {"pos": "article", "en": "marks a specific, already-known thing"}}
        with fixture_patch(), patch(
            "backend.services.seeder.seed_english.load_gloss_overrides", return_value=rows
        ):
            records = await seeder.transform()
        the = next(r for r in records if r["word"] == "the")
        assert the["translations"]["en"] == "marks a specific, already-known thing"

    async def test_blank_override_does_not_erase_the_definition(self, seeder):
        rows = {"water": {"pos": "noun", "en": ""}}
        with fixture_patch(), patch(
            "backend.services.seeder.seed_english.load_gloss_overrides", return_value=rows
        ):
            records = await seeder.transform()
        water = next(r for r in records if r["word"] == "water")
        assert water["translations"]["en"].strip()

    async def test_untouched_words_keep_their_wordnet_definition(self, seeder):
        rows = {"book": {"pos": "noun", "en": "a written work bound between covers"}}
        with fixture_patch(), patch(
            "backend.services.seeder.seed_english.load_gloss_overrides", return_value=rows
        ):
            overridden = await seeder.transform()
        with fixture_patch():
            plain = await seeder.transform()
        by_word = {r["word"]: r["translations"]["en"] for r in plain}
        for r in overridden:
            if r["word"] != "book":
                assert r["translations"]["en"] == by_word[r["word"]]


# ── committed definitions ─────────────────────────────────────────────────────

@requires_wordnet
class TestEnglishSeederCommittedGlosses:
    """data/en_frequency.tsv carries `pos` and `en` like the other 26 courses.

    English used to resolve its definitions from WordNet at seed time and
    commit nothing, so no audit could see them — which is how rank 3 `be`
    shipped defined as beryllium.
    """

    def freq_file(self, tmp_path, rows):
        path = tmp_path / "en_freq.tsv"
        lines = ["rank\tword\tpos\ten"]
        lines += ["\t".join(r) for r in rows]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def patched(self, path):
        stack = ExitStack()
        stack.enter_context(patch("backend.services.seeder.seed_english.DATA_DIR", path.parent))
        stack.enter_context(patch("backend.services.seeder.seed_english.FREQ_FILENAME", path.name))
        return stack

    async def test_committed_definition_is_used(self, seeder, tmp_path):
        path = self.freq_file(tmp_path, [("1", "book", "noun", "a thing you read")])
        with self.patched(path):
            records = await seeder.transform()
        assert records[0]["translations"]["en"] == "a thing you read"

    async def test_blank_column_falls_back_to_wordnet(self, seeder, tmp_path):
        path = self.freq_file(tmp_path, [("1", "book", "", "")])
        with self.patched(path):
            records = await seeder.transform()
        assert records[0]["translations"]["en"]
        assert records[0]["translations"]["en"] != "a thing you read"

    async def test_overrides_still_win_over_the_committed_column(self, seeder, tmp_path):
        path = self.freq_file(tmp_path, [("1", "book", "noun", "a thing you read")])
        rows = {"book": {"pos": "noun", "en": "a written work bound between covers"}}
        with self.patched(path), patch(
            "backend.services.seeder.seed_english.load_gloss_overrides", return_value=rows
        ):
            records = await seeder.transform()
        assert records[0]["translations"]["en"] == "a written work bound between covers"

    async def test_regenerating_ignores_what_is_on_disk(self, tmp_path):
        """The emitter that writes the column must not read it back, or
        regeneration is a no-op that silently preserves the bad gloss."""
        from backend.services.seeder.emit_english_glosses import _Regenerating

        path = self.freq_file(tmp_path, [("1", "book", "noun", "a thing you read")])
        with self.patched(path):
            records = await _Regenerating("postgresql://localhost/test").transform()
        assert records[0]["translations"]["en"] != "a thing you read"
