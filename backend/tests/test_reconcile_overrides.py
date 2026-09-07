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
import json
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
    monkeypatch.setattr(reconcile, "ROLLBACK_DIR", tmp_path / "out")
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
                return [{"morphology": None, **r} for r in db_rows]
        return asyncio.run(reconcile.survey(_Conn(), "tr"))

    def test_a_pos_change_out_of_the_nominal_set_strips_the_chips(self, data, monkeypatch):
        """Review of #431: 23 words the override moves from noun to det/adv/verb
        would have kept 'Gender / Plural' chips — the reconcile is how those
        pos changes reach production first, so it strips them too."""
        _write(data, "tr_frequency.tsv", "rank\tword\tpos\ten\n1\tson\tdet\this\n")
        rep = self._survey([{"id": "1", "word": "son", "part_of_speech": "noun",
                             "definition": "his",
                             "morphology": {"lemma": "son", "chips": [
                                 {"label": "Gender", "value": "m"},
                                 {"label": "Stem", "value": "s-"}]}}], monkeypatch)
        assert [c["new"] for c in rep["pos_changes"]] == ["det"]
        assert len(rep["morphology_changes"]) == 1
        new = json.loads(rep["morphology_changes"][0]["new"])
        assert [c["label"] for c in new["chips"]] == ["Stem"]
        sql = reconcile.write_rollback([{"code": "tr", **rep}], "T").read_text(encoding="utf-8")
        assert "SET morphology = " in sql and "Gender" in sql

    def test_a_pos_change_that_stays_nominal_leaves_the_chips(self, data, monkeypatch):
        _write(data, "tr_frequency.tsv", "rank\tword\tpos\ten\n1\tev\tadj\thouse\n")
        rep = self._survey([{"id": "1", "word": "ev", "part_of_speech": "noun",
                             "definition": "house",
                             "morphology": {"chips": [{"label": "Gender", "value": "m"}]}}],
                           monkeypatch)
        assert rep["pos_changes"] and rep["morphology_changes"] == []

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

    def test_the_overlay_runs_before_the_chart_merge(self):
        """`strip_nominal_chips` judges with the record's pos; the override
        can move a word out of the nominal set, so it must be laid over
        first. Checked on the source of `load`, the only place the order lives."""
        import inspect
        src = inspect.getsource(BaseSeeder.load)
        assert src.index("self.prepare_records(") < src.index("self._merge_morphology_charts(")

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


class TestGoneMeansUngoverned:
    """`gone` used to mean "not in the frequency file", which is not the same
    as "nothing owns it". 166 of the 40,861 rows it reported on 7 Sep 2026
    were alphabet-deck cards (`seed_alphabet`, 8 courses, 17 of them held by
    learners) and 12 were curated starter words. A plan to retire "the
    letters and digits nothing governs" would have deleted seven alphabet
    decks.
    """

    def _survey(self, db_rows, monkeypatch, code="tr"):
        async def _layers(conn, code, lang_id):
            return []
        monkeypatch.setattr(reconcile, "survey_sentence_layers", _layers)
        monkeypatch.setattr(reconcile, "excluded_words", lambda c: set())

        class _Conn:
            async def fetchval(self, *a, **k):
                return "lang"

            async def fetch(self, sql, *a, **k):
                if "retired_at" in sql:
                    return [{"id": r["id"], "word": r["word"], "retired_at": None}
                            for r in db_rows]
                if "user_cards" in sql:
                    # honour the word list the survey passes, as Postgres would
                    wanted = set(a[1]) if len(a) > 1 else None
                    return [{"id": r["id"], "word": r["word"], "cards": 0}
                            for r in db_rows
                            if wanted is None or r["word"] in wanted]
                return [{"morphology": None, **r} for r in db_rows]
        return asyncio.run(reconcile.survey(_Conn(), code))

    def test_an_alphabet_letter_is_not_ungoverned(self, data, monkeypatch):
        rep = self._survey([
            {"id": "1", "word": "ㄱ", "part_of_speech": "letter", "definition": "giyeok"},
            {"id": "2", "word": "junk", "part_of_speech": "noun", "definition": "debris"},
        ], monkeypatch)
        assert rep["owned_elsewhere"] == ["ㄱ"]
        assert [d["word"] for d in rep["departed"]] == ["junk"]

    def test_a_curated_starter_word_is_not_ungoverned(self, data, monkeypatch, tmp_path):
        (tmp_path / "ar_seed.json").write_text(
            '[{"word": "\\u0625\\u0646 \\u0634\\u0627\\u0621 \\u0627\\u0644\\u0644\\u0647"}]',
            encoding="utf-8")
        (tmp_path / "ar_frequency.tsv").write_text("rank\tword\tpos\ten\n1\tبيت\tnoun\thouse\n",
                                                   encoding="utf-8")
        rep = self._survey([
            {"id": "1", "word": "إن شاء الله", "part_of_speech": "phrase", "definition": "God willing"},
            {"id": "2", "word": "خرابة", "part_of_speech": "noun", "definition": "ruin"},
        ], monkeypatch, code="ar")
        assert rep["owned_elsewhere"] == ["إن شاء الله"]
        assert [d["word"] for d in rep["departed"]] == ["خرابة"]

    def test_a_missing_starter_file_governs_nothing(self, data):
        assert reconcile.words_from_other_sources("tr") == set()

    def test_the_report_prints_the_other_column(self, data, monkeypatch):
        rep = self._survey([
            {"id": "1", "word": "ㄱ", "part_of_speech": "letter", "definition": "giyeok"},
        ], monkeypatch)
        out = io.StringIO()
        with redirect_stdout(out):
            reconcile.print_report([rep], detail=False)
        header = out.getvalue().splitlines()[0]
        assert "other" in header and "gone" in header

    def test_the_shipped_sources_are_readable(self):
        """Each named starter file parses and yields words — an unreadable one
        silently widens `gone` back to the old, wrong number."""
        for code in reconcile.OTHER_SOURCES:
            assert reconcile.words_from_other_sources(code), code
