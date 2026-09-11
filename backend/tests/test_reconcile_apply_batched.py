"""`reconcile --apply` sends arrays, not one statement per row.

The 7 Sep 2026 production apply — about 6,000 changed rows — ran as ~6,000
single-row UPDATEs inside one transaction over the Supabase pooler and took
twenty minutes, printing nothing after the rollback line. The owner asked
whether it was stuck. `BaseSeeder.load` had already learned this ("one round
trip per row over a pooled connection turns a seed into hours"); this is the
same fix for the other write path, plus a progress line per kind.
"""
from __future__ import annotations

import asyncio

from backend.services.seeder import reconcile


class _Conn:
    """Records every statement and its arguments; no database."""

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    def transaction(self):
        conn = self

        class _Txn:
            async def __aenter__(self):
                conn.calls.append(("BEGIN", ()))
                return conn

            async def __aexit__(self, *exc):
                conn.calls.append(("COMMIT", ()))
                return False
        return _Txn()

    async def execute(self, sql, *args):
        self.calls.append((" ".join(sql.split()), args))


def _report(**kw):
    base = {"code": "tr", "gloss_changes": [], "pos_changes": [],
            "morphology_changes": [], "missing_translation": [],
            "sentence_layers": [], "retire": [], "unretire": [],
            "retire_points": [], "unretire_points": []}
    base.update(kw)
    return base


def _run(reports, progress=None):
    conn = _Conn()
    counts = asyncio.run(reconcile.apply(conn, reports, progress=progress))
    return conn, counts


class TestOneStatementPerChunk:
    def test_a_thousand_glosses_are_two_statements_not_a_thousand(self):
        rows = [{"id": f"{i:032x}", "word": f"w{i}", "old": "x", "new": f"d{i}"}
                for i in range(1000)]
        conn, counts = _run([_report(gloss_changes=rows)])
        updates = [c for c in conn.calls if c[0].startswith("UPDATE translations")]
        assert len(updates) == 2                      # 500 + 500
        assert counts["gloss"] == 1000                # the counter still counts ROWS
        definitions, ids = updates[0][1]
        assert len(definitions) == len(ids) == 500
        assert definitions[0] == "d0" and ids[0] == rows[0]["id"]

    def test_every_kind_is_batched(self):
        n = reconcile.APPLY_CHUNK + 1
        def rows():
            return [{"id": f"{i:032x}", "word": "w", "old": None, "new": "v",
                     "transliteration": "t", "gloss": "g"} for i in range(n)]

        conn, counts = _run([_report(
            gloss_changes=rows(), pos_changes=rows(),
            morphology_changes=rows(), missing_translation=rows(),
            sentence_layers=rows(), retire=rows(), unretire=rows(),
            retire_points=rows(), unretire_points=rows())])
        statements = [c for c in conn.calls if c[0] not in ("BEGIN", "COMMIT")]
        # 9 kinds, 2 chunks each — sentence layers write two columns
        assert len(statements) == 20
        assert counts == {"gloss": n, "pos": n, "morphology": n,
                          "added_translation": n, "sentence_layers": n,
                          "retired": n, "unretired": n,
                          "points_retired": n, "points_unretired": n}

    def test_nothing_to_do_sends_nothing(self):
        conn, counts = _run([_report()])
        assert [c[0] for c in conn.calls] == ["BEGIN", "COMMIT"]
        assert set(counts.values()) == {0}

    def test_it_all_happens_in_one_transaction(self):
        conn, _ = _run([_report(retire=[{"id": "a"}])])
        assert conn.calls[0][0] == "BEGIN" and conn.calls[-1][0] == "COMMIT"


class TestSentenceLayers:
    def test_a_row_with_only_a_gloss_does_not_null_its_transliteration(self):
        conn, counts = _run([_report(sentence_layers=[
            {"id": "1", "transliteration": None, "gloss": "g"},
            {"id": "2", "transliteration": "t", "gloss": None},
        ])])
        translit = [c for c in conn.calls if "SET transliteration" in c[0]]
        gloss = [c for c in conn.calls if "SET gloss" in c[0]]
        assert translit[0][1] == (["t"], ["2"])
        assert gloss[0][1] == (["g"], ["1"])
        assert counts["sentence_layers"] == 2

    def test_no_layer_row_sends_no_layer_statement(self):
        conn, _ = _run([_report(sentence_layers=[])])
        assert not [c for c in conn.calls if "example_sentences" in c[0]]


class TestProgress:
    def test_each_kind_reports_as_it_lands(self):
        seen = []
        _run([_report(gloss_changes=[{"id": "1", "word": "w", "old": None, "new": "d"}],
                      retire=[{"id": "2"}, {"id": "3"}])],
             progress=lambda kind, n: seen.append((kind, n)))
        assert seen == [("tr glosses", 1), ("tr retired", 2)]

    def test_an_empty_kind_is_silent(self):
        seen = []
        _run([_report()], progress=lambda kind, n: seen.append((kind, n)))
        assert seen == []

    def test_the_runner_passes_a_progress_printer(self):
        import inspect
        src = inspect.getsource(reconcile.main)
        assert "progress=" in src, "the apply would run silent again"


def test_the_chunk_size_is_sane():
    assert 50 <= reconcile.APPLY_CHUNK <= 5000
