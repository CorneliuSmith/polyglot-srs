"""A grammar point can be retired — the gap Korean's duplicates exposed.

`seed_grammar` is add-only for points: it updates what the file has and
inserts what is new, and a point the file stops mentioning stays in
production for ever. Vocabulary had the same gap until migration 20261016.
Two readers of Korean judged four topics taught twice (8 Sep 2026); five
points lose, and without this path they could not leave.

Same shape as vocabulary: a file (`data/grammar_exclusions.tsv`) is the
source of truth in both directions, the reconcile sets and clears
`grammar_points.retired_at`, every place a point is OFFERED filters on it,
and a database behind the migration degrades to "nothing retired".
"""
from __future__ import annotations

import asyncio
import csv
import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from backend.services.seeder import reconcile

REPO = Path(__file__).resolve().parents[2]


class TestTheFile:
    def test_it_parses_and_names_only_korean_today(self):
        with (REPO / "data" / "grammar_exclusions.tsv").open(
                encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        assert rows, "the five Korean duplicates should be listed"
        assert {r["language"] for r in rows} == {"ko"}
        assert all(r["title"].strip() and r["reason"].strip() for r in rows)

    def test_every_retired_title_has_left_the_grammar_file(self):
        """The file is the record; the grammar JSON no longer carries the
        loser, so `seed_grammar` stops touching it and the reconcile hides it."""
        import json
        titles = reconcile.excluded_points("ko")
        data = json.loads((REPO / "data" / "grammar" / "ko_grammar.json")
                          .read_text(encoding="utf-8"))
        still = titles & {p["title"] for p in data["points"]}
        assert still == set(), f"retired but still in the file: {still}"

    def test_every_keeper_named_in_a_reason_is_still_in_the_file(self):
        import json
        import re
        data = json.loads((REPO / "data" / "grammar" / "ko_grammar.json")
                          .read_text(encoding="utf-8"))
        titles = {p["title"] for p in data["points"]}
        with (REPO / "data" / "grammar_exclusions.tsv").open(
                encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                m = re.search(r"duplicate of “(.+?)”", r["reason"])
                assert m, r["reason"]
                assert m.group(1) in titles, f"keeper {m.group(1)!r} is gone too"


class TestSurvey:
    def _survey(self, rows, excluded, monkeypatch, column=True):
        monkeypatch.setattr(reconcile, "excluded_points", lambda code: excluded)

        class _Conn:
            async def fetch(self, *a, **k):
                if not column:
                    import asyncpg
                    raise asyncpg.exceptions.UndefinedColumnError("no column")
                return rows
        return asyncio.run(reconcile.survey_point_retirements(_Conn(), "ko", "lang"))

    def test_a_listed_point_is_retired(self, monkeypatch):
        rep = self._survey([{"id": "1", "title": "dup", "retired_at": None},
                            {"id": "2", "title": "keep", "retired_at": None}],
                           {"dup"}, monkeypatch)
        assert [r["title"] for r in rep["retire_points"]] == ["dup"]
        assert rep["unretire_points"] == []

    def test_a_point_that_leaves_the_file_comes_back(self, monkeypatch):
        rep = self._survey([{"id": "1", "title": "dup", "retired_at": "2026-09-08"}],
                           set(), monkeypatch)
        assert [r["title"] for r in rep["unretire_points"]] == ["dup"]

    def test_an_already_retired_point_is_not_retired_twice(self, monkeypatch):
        rep = self._survey([{"id": "1", "title": "dup", "retired_at": "2026-09-08"}],
                           {"dup"}, monkeypatch)
        assert rep["retire_points"] == [] and rep["unretire_points"] == []

    def test_a_database_behind_the_migration_is_not_an_error(self, monkeypatch):
        rep = self._survey([], {"dup"}, monkeypatch, column=False)
        assert rep["retire_points"] == [] and rep["point_retire_skipped"]


class TestRollbackAndReport:
    def test_the_rollback_undoes_both_directions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(reconcile, "ROLLBACK_DIR", tmp_path)
        sql = reconcile.write_rollback([{
            "code": "ko",
            "retire_points": [{"id": "11111111-1111-1111-1111-111111111111", "title": "a"}],
            "unretire_points": [{"id": "22222222-2222-2222-2222-222222222222", "title": "b"}],
        }], "T").read_text(encoding="utf-8")
        assert "UPDATE grammar_points SET retired_at = NULL" in sql
        assert "UPDATE grammar_points SET retired_at = now()" in sql

    def test_the_report_prints_the_point_column(self):
        rep = {"code": "ko", "db_rows": 1, "tsv_rows": 1, "gloss_changes": [],
               "pos_changes": [], "missing_translation": [], "departed": [],
               "owned_elsewhere": [], "absent_from_db": [], "sentence_layers": [],
               "retire": [], "unretire": [], "retire_skipped": None,
               "retire_points": [{"id": "1", "title": "dup"}] * 5,
               "unretire_points": [], "point_retire_skipped": None}
        out = io.StringIO()
        with redirect_stdout(out):
            reconcile.print_report([rep], detail=False)
        table = out.getvalue()
        assert "gp-ret" in table.splitlines()[0]
        row = next(line for line in table.splitlines() if line.startswith("ko "))
        assert row.split()[-1] == "5"

    def test_the_apply_counts_and_names_the_kind(self):
        import inspect
        src = inspect.getsource(reconcile.apply)
        assert "retire_points" in src and "unretire_points" in src
        summary = inspect.getsource(reconcile.main)
        assert "points_retired" in summary


class TestTheCardLayerProbes:
    @pytest.mark.parametrize("module,name", [
        ("backend.repositories.cards", "_point_retired_clause"),
        ("backend.repositories.curriculum", "_point_retired_clause"),
    ])
    def test_the_clause_is_empty_without_the_column(self, module, name, monkeypatch):
        import importlib
        mod = importlib.import_module(module)
        fn = getattr(mod, name)

        async def absent(conn, table, column):
            return False

        async def present(conn, table, column):
            return table == "grammar_points" and column == "retired_at"
        import backend.services.auto_translate as at
        monkeypatch.setattr(at, "column_present", absent)
        if module.endswith("cards"):
            monkeypatch.setattr(mod, "column_present", absent)
        assert asyncio.run(fn(None)) == ""
        monkeypatch.setattr(at, "column_present", present)
        if module.endswith("cards"):
            monkeypatch.setattr(mod, "column_present", present)
        assert asyncio.run(fn(None)) == "AND gp.retired_at IS NULL"

    def test_every_offer_path_carries_the_clause_and_no_lookup_does(self):
        """Offered: Learn candidates, the next-level peek, deck counts, the
        two path listings. Not filtered: fetch-by-id, so a learner who was
        part-way through a retired point can still open their card."""
        cards = (REPO / "backend" / "repositories" / "cards.py").read_text(encoding="utf-8")
        curriculum = (REPO / "backend" / "repositories" / "curriculum.py").read_text(encoding="utf-8")
        assert cards.count("{point_retired}") == 3
        assert curriculum.count("{point_retired}") == 2
        by_id = cards[cards.index("WHERE gp.id = ANY($1::uuid[])") - 400:
                      cards.index("WHERE gp.id = ANY($1::uuid[])") + 60]
        assert "point_retired" not in by_id
