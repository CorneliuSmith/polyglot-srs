"""A headword rename in a file is an add plus an orphan — and the reconcile
now says so instead of leaving it for the owner to read out of `gone`.

Quality rule 73: the database has no rename. When a tone repair turns `ati`
into `àti`, the seeder INSERTs `àti` and this tool reports `ati` as "in no
committed source" — never deleted — so the course teaches the word twice.
The 874 Yoruba tone repairs would have shipped every one of them doubled;
what caught it was a person reading a list. The rank is the field a
respelling does not change, so a departed word and a new word at the same
rank are paired, and `--apply` refuses the course until the old spelling is
in `vocab_exclusions.tsv`. Plan `quality-guardrails-telemetry`, A3.
"""
from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stdout

import pytest

from backend.services.seeder import gloss_overrides, reconcile

FILE = ("rank\tword\tpos\ten\n"
        "10\tàti\tconj\tand\n"
        "11\tkí\tpron\twhat\n")


@pytest.fixture
def data(tmp_path, monkeypatch):
    (tmp_path / "yo_frequency.tsv").write_text(FILE, encoding="utf-8")
    (tmp_path / "gloss_overrides.tsv").write_text("language\tword\tpos\ten\n",
                                                  encoding="utf-8")
    monkeypatch.setattr(reconcile, "DATA", tmp_path)
    monkeypatch.setattr(reconcile, "ROLLBACK_DIR", tmp_path / "out")
    monkeypatch.setattr(gloss_overrides, "GLOSS_OVERRIDES_PATH",
                        tmp_path / "gloss_overrides.tsv")
    return tmp_path


TSV = {"àti": {"rank": "10", "en": "and"}, "kí": {"rank": "11", "en": "what"}}


class TestDetectRenames:
    def test_a_departed_and_an_absent_word_at_one_rank_are_a_rename(self):
        renames = reconcile.detect_renames(
            [{"id": "1", "word": "ati", "cards": 2, "rank": 10}], ["àti"], TSV, set())
        assert renames == [{"from": "ati", "to": "àti", "rank": 10, "cards": 2,
                            "excluded": False}]

    def test_the_exclusion_file_is_consulted(self):
        renames = reconcile.detect_renames(
            [{"id": "1", "word": "ati", "cards": 0, "rank": 10}], ["àti"], TSV, {"ati"})
        assert renames[0]["excluded"] is True

    def test_different_ranks_are_not_a_rename(self):
        assert reconcile.detect_renames(
            [{"id": "1", "word": "ati", "cards": 0, "rank": 12}], ["àti"], TSV, set()) == []

    def test_a_rank_shared_by_two_words_on_one_side_is_not_guessed(self):
        """A re-ranked list can put two unrelated words at one rank; pairing
        one of them would send the operator to exclude the wrong word."""
        assert reconcile.detect_renames(
            [{"id": "1", "word": "ati", "cards": 0, "rank": 10},
             {"id": "2", "word": "atì", "cards": 0, "rank": 10}], ["àti"], TSV, set()) == []

    def test_a_row_without_a_rank_pairs_with_nothing(self):
        assert reconcile.detect_renames(
            [{"id": "1", "word": "ati", "cards": 0, "rank": None}], ["àti"], TSV, set()) == []
        assert reconcile.detect_renames(
            [{"id": "1", "word": "ati", "cards": 0, "rank": 10}], ["àti"],
            {"àti": {"rank": "", "en": "and"}}, set()) == []


def _survey(db_rows, monkeypatch, excluded=frozenset()):
    async def _layers(conn, code, lang_id):
        return []
    monkeypatch.setattr(reconcile, "survey_sentence_layers", _layers)
    monkeypatch.setattr(reconcile, "excluded_words", lambda code: set(excluded))

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
                wanted = set(a[1])
                return [{"id": r["id"], "word": r["word"], "cards": r.get("cards", 0),
                         "frequency_rank": r.get("rank")}
                        for r in db_rows if r["word"] in wanted]
            return [{"morphology": None, "part_of_speech": "conj", "curated": False, **r}
                    for r in db_rows]
    return asyncio.run(reconcile.survey(_Conn(), "yo"))


class TestTheSurveyPairsThem:
    def test_the_yoruba_shape(self, data, monkeypatch):
        rep = _survey([{"id": "1", "word": "ati", "definition": "and", "rank": 10,
                        "cards": 3}], monkeypatch)
        assert [d["word"] for d in rep["departed"]] == ["ati"]      # still reported
        assert rep["absent_from_db"] == ["kí", "àti"]                # still new
        assert rep["renames"] == [{"from": "ati", "to": "àti", "rank": 10, "cards": 3,
                                   "excluded": False}]
        assert reconcile.rename_blockers(rep) == rep["renames"]

    def test_an_excluded_old_spelling_blocks_nothing(self, data, monkeypatch):
        rep = _survey([{"id": "1", "word": "ati", "definition": "and", "rank": 10}],
                      monkeypatch, excluded={"ati"})
        assert rep["renames"][0]["excluded"] is True
        assert reconcile.rename_blockers(rep) == []

    def test_the_report_has_the_column_and_the_rule(self, data, monkeypatch):
        rep = _survey([{"id": "1", "word": "ati", "definition": "and", "rank": 10}],
                      monkeypatch)
        out = io.StringIO()
        with redirect_stdout(out):
            reconcile.print_report([rep], detail=False)
        text = out.getvalue()
        header = text.splitlines()[0].split()
        assert header.index("gone") + 1 == header.index("rename")
        row = next(line for line in text.splitlines() if line.startswith("yo ")).split()
        assert row[header.index("rename")] == "1"
        assert "ati -> àti" in text and "NOT EXCLUDED" in text
        assert reconcile.RENAME_RULE in text
        assert reconcile.RENAME_RULE == (
            "A rename in a file is an add plus an orphan in production (quality "
            "rule 73): add the old spelling to vocab_exclusions.tsv before seeding")


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


def _report(**kw):
    base = {"code": "yo", "gloss_changes": [], "pos_changes": [],
            "morphology_changes": [], "missing_translation": [],
            "sentence_layers": [], "retire": [], "unretire": [],
            "retire_points": [], "unretire_points": [], "curated_differs": [],
            "renames": []}
    base.update(kw)
    return base


class TestApplyRefusesTheCourse:
    GLOSS = [{"id": "1", "word": "kí", "old": "which", "new": "what"}]

    def test_an_unexcluded_rename_skips_the_whole_course(self):
        conn = _Conn()
        rep = _report(gloss_changes=self.GLOSS,
                      renames=[{"from": "ati", "to": "àti", "rank": 10, "cards": 0,
                                "excluded": False}])
        counts = asyncio.run(reconcile.apply(conn, [rep]))
        # not even the unrelated gloss correction: a half-applied course
        # would read as reconciled while the double card was still coming
        assert not any("UPDATE translations" in c[0] for c in conn.calls)
        assert counts["gloss"] == 0
        assert counts["rename_blocked"] == {"yo": rep["renames"]}

    def test_with_the_old_spelling_excluded_apply_proceeds(self):
        conn = _Conn()
        rep = _report(gloss_changes=self.GLOSS,
                      renames=[{"from": "ati", "to": "àti", "rank": 10, "cards": 0,
                                "excluded": True}])
        counts = asyncio.run(reconcile.apply(conn, [rep]))
        assert any("UPDATE translations" in c[0] for c in conn.calls)
        assert counts["gloss"] == 1 and counts["rename_blocked"] == {}

    def test_other_courses_are_not_held_hostage(self):
        conn = _Conn()
        blocked = _report(renames=[{"from": "ati", "to": "àti", "rank": 10, "cards": 0,
                                    "excluded": False}])
        other = _report(code="tr", gloss_changes=self.GLOSS)
        counts = asyncio.run(reconcile.apply(conn, [blocked, other]))
        assert counts["gloss"] == 1 and list(counts["rename_blocked"]) == ["yo"]
