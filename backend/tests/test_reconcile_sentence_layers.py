"""The backfill that makes the romanisation and gloss layers reachable.

`load_example_sentences` inserts with `ON CONFLICT ... DO NOTHING`. Adding
`transliteration` and `gloss` to that INSERT only helps rows created after the
change — the ~28,000 sentences already in the database never gain the columns
on a re-seed. So a layer can be fully authored, committed, guarded, and still
show a learner nothing. This is the only path that fills them, which makes its
two failure modes worth pinning: writing over a value that is already there,
and writing a value the committed bank does not actually contain.
"""
import asyncio

import pytest

from backend.services.seeder import reconcile


class FakeConn:
    """Just enough asyncpg to drive the survey."""

    def __init__(self, rows):
        self.rows = rows
        self.writes = []

    async def fetch(self, _sql, *args):
        wanted = set(args[1])
        return [r for r in self.rows if r["sentence"] in wanted]

    async def execute(self, sql, *args):
        self.writes.append((sql, args))


def _bank(tmp_path, monkeypatch, body):
    monkeypatch.setattr(reconcile, "DATA", tmp_path)
    (tmp_path / "xx_sentences.tsv").write_text(body, encoding="utf-8")


HEADER = "word\tsentence\ttranslation\ttransliteration\tgloss\n"


def test_the_backfill_fills_a_column_that_is_empty(tmp_path, monkeypatch):
    _bank(tmp_path, monkeypatch, HEADER + "a\tмир\tpeace\tmir\tpeace.N\n")
    conn = FakeConn([{"id": 1, "sentence": "мир", "transliteration": None,
                      "gloss": None}])
    fills = asyncio.run(reconcile.survey_sentence_layers(conn, "xx", 7))
    assert len(fills) == 1
    assert fills[0]["transliteration"] == "mir"
    assert fills[0]["gloss"] == "peace.N"


def test_the_backfill_never_overwrites_a_value_that_is_already_there():
    """The reason `apply` can use a plain SET: survey has already proved the
    column is empty. If survey ever returned a populated row, the rollback
    would restore NULL over a real value and the loss would be silent."""
    conn = FakeConn([{"id": 1, "sentence": "мир", "transliteration": "MIR",
                      "gloss": "already here"}])
    fills = asyncio.run(reconcile.survey_sentence_layers(conn, "xx", 7))
    assert fills == []


def test_a_column_the_database_has_and_one_it_lacks_are_decided_separately(
        tmp_path, monkeypatch):
    _bank(tmp_path, monkeypatch, HEADER + "a\tмир\tpeace\tmir\tpeace.N\n")
    conn = FakeConn([{"id": 1, "sentence": "мир", "transliteration": "MIR",
                      "gloss": ""}])
    fills = asyncio.run(reconcile.survey_sentence_layers(conn, "xx", 7))
    assert fills[0]["transliteration"] is None, "would have stomped MIR"
    assert fills[0]["gloss"] == "peace.N"


def test_a_sentence_the_bank_does_not_carry_is_left_alone(tmp_path, monkeypatch):
    """A row with neither layer must not appear as work. Otherwise every
    unromanised sentence in the corpus reads as a pending write forever."""
    _bank(tmp_path, monkeypatch, HEADER + "a\tмир\tpeace\t\t\n")
    conn = FakeConn([{"id": 1, "sentence": "мир", "transliteration": None,
                      "gloss": None}])
    assert asyncio.run(reconcile.survey_sentence_layers(conn, "xx", 7)) == []


def test_whitespace_is_not_a_value(tmp_path, monkeypatch):
    _bank(tmp_path, monkeypatch, HEADER + "a\tмир\tpeace\tmir\t\n")
    conn = FakeConn([{"id": 1, "sentence": "мир", "transliteration": "   ",
                      "gloss": None}])
    fills = asyncio.run(reconcile.survey_sentence_layers(conn, "xx", 7))
    assert fills[0]["transliteration"] == "mir"


def test_the_rollback_restores_exactly_the_columns_that_were_written(tmp_path,
                                                                    monkeypatch):
    """Nothing is written until a replayable undo exists on disk — the property
    the whole reconciler rests on. A backfill that only rolls back one of its
    two columns leaves the other unrecoverable."""
    monkeypatch.setattr(reconcile, "ROLLBACK_DIR", tmp_path)
    reports = [{"code": "xx", "sentence_layers": [
        {"id": "abc", "sentence": "мир", "transliteration": "mir", "gloss": None},
        {"id": "def", "sentence": "дом", "transliteration": None, "gloss": "house.N"},
    ]}]
    sql = reconcile.write_rollback(reports, "test").read_text(encoding="utf-8")
    assert "SET transliteration = NULL WHERE id = 'abc'" in sql
    assert "SET gloss = NULL WHERE id = 'def'" in sql
    assert "gloss = NULL WHERE id = 'abc'" not in sql, "would blank an untouched column"


@pytest.mark.parametrize("code", ["he", "fa"])
def test_the_committed_banks_the_backfill_exists_to_carry_are_readable(code):
    """Guards the file contract: these two are the only banks that carry any
    sentence romanisation at all. If a column is renamed or the bank moves,
    the backfill goes quietly to zero rather than failing."""
    rows = reconcile.read_sentences(code)
    assert rows, f"{code} bank carries no transliteration or gloss at all"
    assert all(r["sentence"] for r in rows)


# Banks with no transliteration column whatsoever. ru/hi are covered live by
# the computed reading on the card (backend/services/readings.py); el, ko, th
# and ar are not covered by anything, and ar is deliberately excluded because
# unvocalized script drops the short vowels a romanization needs.
NO_ROMANISATION_YET = {"ko", "th", "ru", "ar", "hi", "el"}


@pytest.mark.parametrize("code", sorted(NO_ROMANISATION_YET))
def test_the_gap_is_the_gap_we_think_it_is(code):
    """A ratchet, not a wish. When a bank gains romanisation this fails and
    tells whoever added it to move the code out of the set — which is how the
    coverage number in docs/quality/card-layers.md stays true. A gap nobody
    is forced to look at is a gap that gets reported as done."""
    assert not reconcile.read_sentences(code), (
        f"{code} now carries a layer — drop it from NO_ROMANISATION_YET "
        "and update docs/quality/card-layers.md")
