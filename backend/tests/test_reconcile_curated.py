"""A Workshop definition fix survives the reconcile — as of 18 Sep 2026.

`_edit_vocab_card` updated `translations` and never set `vocabulary.curated`;
`reconcile --apply` computes a gloss correction as "database differs from
the file" and writes the file's wording back. So every definition a
reviewer fixed in the Workshop was reverted on the owner's next apply,
silently, with a rollback line nobody would think to look for. Grammar had
the protection (`save_explanation` sets `curated`); vocabulary did not.
Plan `quality-guardrails-telemetry`, A1.

Two halves, one defect: the write path that now marks the row human-owned,
and the reconcile that now reports such a row under `kept` and never writes
it. No database — the connections are fakes, as in
`test_reconcile_overrides.py`.
"""
from __future__ import annotations

import asyncio
import io
import json
from contextlib import redirect_stdout

import asyncpg
import pytest

from backend.repositories.contributor import _edit_vocab_card
from backend.services.seeder import gloss_overrides, reconcile
from backend.tests.fakes import mock_conn

FILE = ("rank\tword\tpos\ten\n"
        "1\tmi\tparticle\tthe yes/no question particle\n"
        "2\tev\tnoun\thouse\n"
        "3\tsu\tnoun\twater\n")


@pytest.fixture
def data(tmp_path, monkeypatch):
    (tmp_path / "tr_frequency.tsv").write_text(FILE, encoding="utf-8")
    # A header-only override file: the shipped one carries a Turkish `mi`
    # row that would lay itself over the fixture.
    (tmp_path / "gloss_overrides.tsv").write_text("language\tword\tpos\ten\n",
                                                  encoding="utf-8")
    monkeypatch.setattr(reconcile, "DATA", tmp_path)
    monkeypatch.setattr(reconcile, "ROLLBACK_DIR", tmp_path / "out")
    monkeypatch.setattr(gloss_overrides, "GLOSS_OVERRIDES_PATH",
                        tmp_path / "gloss_overrides.tsv")
    return tmp_path


def _survey(db_rows, monkeypatch, *, column=True):
    """Run `survey` over fake rows. *column* False makes the database one
    without `vocabulary.curated` — the first fetch fails, the fallback
    serves the rows with the flag read as false."""
    async def _layers(conn, code, lang_id):
        return []
    monkeypatch.setattr(reconcile, "survey_sentence_layers", _layers)
    monkeypatch.setattr(reconcile, "excluded_words", lambda code: set())

    class _Conn:
        async def fetchval(self, *a, **k):
            return "lang"

        async def fetch(self, sql, *a, **k):
            if "grammar_points" in sql:
                return []
            if "retired_at" in sql:
                return [{"id": r["id"], "word": r["word"], "retired_at": None}
                        for r in db_rows]
            if "user_cards" in sql:
                return []
            if "v.curated" in sql and not column:
                raise asyncpg.exceptions.UndefinedColumnError("no column")
            rows = [{"morphology": None, "part_of_speech": "noun", **r}
                    for r in db_rows]
            if "false AS curated" in sql:
                # what the fallback query selects, as Postgres would
                rows = [{**r, "curated": False} for r in rows]
            return rows
    return asyncio.run(reconcile.survey(_Conn(), "tr"))


class TestTheSurveyKeepsAHumanEdit:
    def test_a_curated_row_that_differs_is_kept_not_corrected(self, data, monkeypatch):
        rep = _survey([
            {"id": "1", "word": "mi", "definition": "the question particle mi/mı/mu/mü",
             "curated": True},
            {"id": "2", "word": "ev", "definition": "a house", "curated": False},
        ], monkeypatch)
        assert [(c["word"], c["old"]) for c in rep["curated_differs"]] == [
            ("mi", "the question particle mi/mı/mu/mü")]
        # the uncurated row is still a correction, exactly as before
        assert [(c["word"], c["new"]) for c in rep["gloss_changes"]] == [("ev", "house")]

    def test_a_curated_row_that_agrees_is_nothing(self, data, monkeypatch):
        rep = _survey([{"id": "1", "word": "mi", "curated": True,
                        "definition": "the yes/no question particle"}], monkeypatch)
        assert rep["curated_differs"] == [] and rep["gloss_changes"] == []

    def test_a_curated_row_with_no_definition_is_still_filled(self, data, monkeypatch):
        """`curated` protects a human's definition; a row that has none has
        nothing to protect, and filling an empty is not an overwrite."""
        rep = _survey([{"id": "3", "word": "su", "definition": None, "curated": True}],
                      monkeypatch)
        assert [c["word"] for c in rep["missing_translation"]] == ["su"]
        assert rep["curated_differs"] == []

    def test_a_database_without_the_column_reads_every_row_as_machine_owned(
            self, data, monkeypatch):
        rep = _survey([{"id": "1", "word": "mi", "definition": "x", "curated": True}],
                      monkeypatch, column=False)
        # the fallback query says `false AS curated`; the fixture's flag is
        # what the failing query would have returned, so it is ignored
        assert [c["word"] for c in rep["gloss_changes"]] == ["mi"]
        assert rep["curated_differs"] == []


class TestTheReportAndTheApply:
    def _rep(self, **kw):
        base = {"code": "tr", "db_rows": 3, "tsv_rows": 3, "gloss_changes": [],
                "pos_changes": [], "morphology_changes": [],
                "missing_translation": [], "sentence_layers": [], "departed": [],
                "owned_elsewhere": [], "absent_from_db": [], "renames": [],
                "retire": [], "unretire": [], "retire_points": [],
                "unretire_points": [], "curated_differs": []}
        base.update(kw)
        return base

    def test_kept_is_its_own_column_between_gloss_and_pos(self):
        rep = self._rep(curated_differs=[{"id": "1", "word": "mi", "old": "a", "new": "b"}],
                        gloss_changes=[{"id": "2", "word": "ev", "old": "c", "new": "d"}])
        out = io.StringIO()
        with redirect_stdout(out):
            reconcile.print_report([rep], detail=True)
        lines = out.getvalue().splitlines()
        header = lines[0].split()
        assert header.index("gloss") + 1 == header.index("kept") == header.index("pos") - 1
        row = next(line for line in lines if line.startswith("tr ")).split()
        assert row[header.index("gloss")] == "1" and row[header.index("kept")] == "1"
        total = next(line for line in lines if line.startswith("all ")).split()
        assert total[1] == "1" and total[2] == "1"           # gloss, kept
        legend = out.getvalue()
        assert "LEFT ALONE" in legend and "human-edited definitions" in legend
        assert "human-edited definitions kept (file differs)" in legend   # --detail

    def test_apply_never_writes_a_kept_definition(self):
        class _Conn:
            def __init__(self):
                self.calls = []

            def transaction(self):
                conn = self

                class _Txn:
                    async def __aenter__(self):
                        return conn

                    async def __aexit__(self, *exc):
                        return False
                return _Txn()

            async def execute(self, sql, *args):
                self.calls.append((" ".join(sql.split()), args))

        conn = _Conn()
        rep = self._rep(curated_differs=[{"id": "1", "word": "mi", "old": "a", "new": "b"}])
        counts = asyncio.run(reconcile.apply(conn, [rep]))
        assert not any("UPDATE translations" in c[0] for c in conn.calls)
        assert counts["kept"] == 1 and counts["gloss"] == 0

    def test_the_rollback_has_nothing_to_undo_for_a_kept_row(self, data):
        rep = self._rep(curated_differs=[{"id": "1", "word": "mi", "old": "a", "new": "b"}])
        sql = reconcile.write_rollback([rep], "T").read_text(encoding="utf-8")
        assert "mi" not in sql


class TestTheWorkshopEditOwnsTheRow:
    def _prev(self, definition="old", curated=False):
        return {"language_id": "lang-1", "reading": None, "curated": curated,
                "definition": definition}

    def _log_rows(self, conn):
        """The content_change_log INSERTs, as (field, before, after)."""
        out = []
        for call in conn.execute.call_args_list:
            sql, args = call.args[0], call.args[1:]
            if "content_change_log" in sql:
                out.append((args[5], json.loads(args[6]), json.loads(args[7])))
        return out

    async def test_a_definition_edit_marks_the_row_curated_and_says_so(self):
        conn = mock_conn()
        conn.fetchrow.return_value = self._prev()
        assert await _edit_vocab_card(conn, "v1", {"translation": "new"}, "ed") == "ok"
        statements = [c.args[0] for c in conn.execute.call_args_list]
        assert any("SET curated = true" in s for s in statements)
        assert self._log_rows(conn) == [
            ("definition", {"definition": "old", "curated": False},
             {"definition": "new", "curated": True})]

    async def test_an_unchanged_definition_changes_no_ownership(self):
        conn = mock_conn()
        conn.fetchrow.return_value = self._prev(definition="same")
        await _edit_vocab_card(conn, "v1", {"translation": "same"}, "ed")
        assert not any("curated" in c.args[0] for c in conn.execute.call_args_list)

    async def test_a_reading_edit_alone_does_not_claim_the_definition(self):
        """`curated` is what the seeder and the reconcile consult before
        touching the DEFINITION; a reading is neither's business."""
        conn = mock_conn()
        conn.fetchrow.return_value = self._prev()
        await _edit_vocab_card(conn, "v1", {"hint": "mee"}, "ed")
        assert not any("curated" in c.args[0] for c in conn.execute.call_args_list)
