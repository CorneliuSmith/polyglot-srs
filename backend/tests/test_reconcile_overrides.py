"""The override file is a layer with a write path — as of 7 Sep 2026.

The Phase 2d pass wrote 1,611 definitions into `gloss_overrides.tsv` for
25 courses. The reconcile compared production against the frequency file's
`en` column, the seeders (all but English) read that column as written, and
the override file reached the column only when `source_data` rebuilt the
file. So the owner's dry run said `gloss 0` for every course but English
while every corrected definition sat unshipped, and production still taught
Turkish `mi` as "Used to form interrogatives." Quality rule 13.
"""
from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stdout

import pytest

from backend.services.seeder import gloss_overrides, reconcile
from backend.services.seeder.base import BaseSeeder


def _write(tmp_path, name, text):
    (tmp_path / name).write_text(text, encoding="utf-8")


@pytest.fixture
def data(tmp_path, monkeypatch):
    _write(tmp_path, "tr_frequency.tsv",
           "rank\tword\tpos\ten\n6\tmi\tparticle\tUsed to form interrogatives.\n"
           "7\tde\tconj\ttoo\n8\tev\tnoun\thouse\n9\tsu\tnoun\t\n")
    _write(tmp_path, "gloss_overrides.tsv",
           "language\tword\tpos\ten\ntr\tmi\tparticle\tthe yes/no question particle\n"
           "tr\tyok\t\tnever invented\nen\tmi\t\tnot this course\n")
    monkeypatch.setattr(reconcile, "DATA", tmp_path)
    monkeypatch.setattr(gloss_overrides, "GLOSS_OVERRIDES_PATH", tmp_path / "gloss_overrides.tsv")
    return tmp_path


class TestExpectedRows:
    def test_the_override_wins_over_the_file_column(self, data):
        rows = reconcile.expected_rows("tr")
        assert rows["mi"]["en"] == "the yes/no question particle"
        assert rows["de"]["en"] == "too"

    def test_an_override_never_invents_a_word(self, data):
        assert "yok" not in reconcile.expected_rows("tr")

    def test_another_course_s_override_is_not_read(self, data):
        assert reconcile.expected_rows("tr")["mi"]["en"] != "not this course"


class TestSurveySeesTheOverride:
    def _survey(self, db_rows, monkeypatch, column=True):
        async def _layers(conn, code, lang_id):
            return []
        monkeypatch.setattr(reconcile, "survey_sentence_layers", _layers)
        monkeypatch.setattr(reconcile, "excluded_words", lambda code: {"su"})

        class _Conn:
            async def fetchval(self, *a, **k):
                return "lang"

            async def fetch(self, sql, *a, **k):
                if "retired_at" in sql:
                    if not column:
                        import asyncpg
                        raise asyncpg.exceptions.UndefinedColumnError("no column")
                    return [{"id": r["id"], "word": r["word"], "retired_at": None}
                            for r in db_rows]
                if "user_cards" in sql:
                    return []
                return db_rows
        return asyncio.run(reconcile.survey(_Conn(), "tr"))

    def test_the_dry_run_reports_the_override_as_a_correction(self, data, monkeypatch):
        rep = self._survey([{"id": "1", "word": "mi", "part_of_speech": "particle",
                             "definition": "Used to form interrogatives."}], monkeypatch)
        assert [(c["word"], c["new"]) for c in rep["gloss_changes"]] == [
            ("mi", "the yes/no question particle")]

    def test_a_definition_already_right_is_not_a_change(self, data, monkeypatch):
        rep = self._survey([{"id": "1", "word": "mi", "part_of_speech": "particle",
                             "definition": "the yes/no question particle"}], monkeypatch)
        assert rep["gloss_changes"] == []

    def test_new_counts_only_words_a_seeder_would_create(self, data, monkeypatch):
        """`su` has no gloss anywhere; every seeder skips it, so it is not
        "new" — English's dry run said 1,267 where the seeder would add 66."""
        rep = self._survey([{"id": "1", "word": "mi", "part_of_speech": "particle",
                             "definition": "x"}], monkeypatch)
        assert rep["absent_from_db"] == ["de", "ev"]

    def test_the_report_prints_the_retire_column(self, data, monkeypatch):
        rep = self._survey([{"id": "1", "word": "su", "part_of_speech": "noun",
                             "definition": "water"}], monkeypatch)
        assert [r["word"] for r in rep["retire"]] == ["su"]
        out = io.StringIO()
        with redirect_stdout(out):
            reconcile.print_report([rep], detail=False)
        table = out.getvalue()
        assert "retire" in table.splitlines()[0]
        row = next(line for line in table.splitlines() if line.startswith("tr "))
        assert row.split()[-2:] == ["1", "0"]

    def test_a_database_behind_the_migration_keeps_its_row_in_the_table(self, data, monkeypatch):
        rep = self._survey([{"id": "1", "word": "mi", "part_of_speech": "particle",
                             "definition": "x"}], monkeypatch, column=False)
        assert rep["retire_skipped"]
        out = io.StringIO()
        with redirect_stdout(out):
            reconcile.print_report([rep], detail=False)
        row = next(line for line in out.getvalue().splitlines() if line.startswith("tr "))
        assert row.split()[-2:] == ["-", "-"]


class TestEverySeederOverlaysTheOverrides:
    class _Seeder(BaseSeeder):
        language_code = "tr"

        async def download(self):
            pass

        async def transform(self):
            return []

    def test_prepare_records_applies_the_override(self, data):
        seeder = self._Seeder("fake://db")
        records = seeder.prepare_records([
            {"word": "mi", "pos": "particle",
             "translations": {"en": "Used to form interrogatives."}},
            {"word": "ev", "pos": "noun", "translations": {"en": "house"}},
        ])
        by_word = {r["word"]: r for r in records}
        assert by_word["mi"]["translations"]["en"] == "the yes/no question particle"
        assert by_word["ev"]["translations"]["en"] == "house"

    def test_the_helper_touches_only_matching_records(self, data):
        records = [{"word": "ev", "translations": {"en": "house"}}]
        assert gloss_overrides.apply_gloss_overrides_to_records("tr", records) == 0
        assert records[0]["translations"]["en"] == "house"

    def test_the_helper_never_adds_a_record(self, data):
        records = [{"word": "ev", "translations": {"en": "house"}}]
        gloss_overrides.apply_gloss_overrides_to_records("tr", records)
        assert [r["word"] for r in records] == ["ev"]

    def test_the_shipped_override_file_has_the_turkish_particle(self):
        """The row that started this: production taught it as 'Used to form
        interrogatives.' after the override was written, because nothing
        carried the override."""
        hit = gloss_overrides.load_gloss_overrides("tr")["mi"]["en"]
        assert "harmonis" in hit and "mü" in hit
