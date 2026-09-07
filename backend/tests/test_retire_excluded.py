"""Retiring a word the courses no longer teach, without orphaning a learner.

`data/vocab_exclusions.tsv` holds 858 headwords that must not be taught, and
until migration 20261016 every one of them was still SERVED: the file is
applied by the loader and no seeder deletes a vocabulary row — nor may it,
because `user_cards.card_id` references it and the review draw INNER JOINs,
so a delete empties a learner's session (CHECKS §12).

The owner met this twice on one card: English `em` (a printer's quad, matched
by WordNet) survived its exclusion, and the Spanish UI showed its gloss
faithfully translated to "eme".
"""

import csv

from backend.services.seeder import reconcile


class TestTheFileIsTheSourceOfTruth:
    def test_it_reads_only_this_language_s_exclusions(self, tmp_path, monkeypatch):
        (tmp_path / "vocab_exclusions.tsv").write_text(
            "language\tword\treason\n"
            "en\tem\ta printer's quad, not the word\n"
            "en\ter\terbium\n"
            "fr\tabby\ta given name\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(reconcile, "DATA", tmp_path)
        assert reconcile.excluded_words("en") == {"em", "er"}
        assert reconcile.excluded_words("fr") == {"abby"}
        assert reconcile.excluded_words("ru") == set()

    def test_a_missing_file_excludes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(reconcile, "DATA", tmp_path)
        assert reconcile.excluded_words("en") == set()

    def test_the_shipped_file_parses_and_covers_the_em_card(self):
        """The owner's card. If this stops being excluded, the card returns."""
        assert "em" in reconcile.excluded_words("en")


class TestSurveyRetirements:
    """Both directions, so deleting a line from the file restores the card
    rather than needing a second tool."""

    def _survey(self, rows, excluded, monkeypatch, column=True):
        monkeypatch.setattr(reconcile, "excluded_words", lambda code: excluded)

        class _Conn:
            async def fetch(self, *a, **k):
                if not column:
                    import asyncpg
                    raise asyncpg.exceptions.UndefinedColumnError(
                        "column does not exist")
                return rows
        import asyncio
        return asyncio.run(reconcile.survey_retirements(_Conn(), "en", "lang"))

    def test_an_excluded_word_is_retired(self, monkeypatch):
        rows = [{"id": "1", "word": "em", "retired_at": None},
                {"id": "2", "word": "hello", "retired_at": None}]
        rep = self._survey(rows, {"em"}, monkeypatch)
        assert [r["word"] for r in rep["retire"]] == ["em"]
        assert rep["unretire"] == []

    def test_a_word_that_leaves_the_file_comes_back(self, monkeypatch):
        rows = [{"id": "1", "word": "em", "retired_at": "2026-09-07"}]
        rep = self._survey(rows, set(), monkeypatch)
        assert [r["word"] for r in rep["unretire"]] == ["em"]
        assert rep["retire"] == []

    def test_an_already_retired_word_is_not_retired_twice(self, monkeypatch):
        rows = [{"id": "1", "word": "em", "retired_at": "2026-09-07"}]
        rep = self._survey(rows, {"em"}, monkeypatch)
        assert rep["retire"] == [] and rep["unretire"] == []

    def test_a_database_without_the_column_is_not_an_error(self, monkeypatch):
        """A deploy ahead of its schema serves the old behaviour rather than
        failing the reconcile (CLAUDE.md)."""
        rep = self._survey([], {"em"}, monkeypatch, column=False)
        assert rep == {"retire": [], "unretire": [],
                       "retire_skipped": "no retired_at column"}


class TestTheRollbackUndoesBothDirections:
    def test_it_writes_the_inverse_of_each_change(self, tmp_path, monkeypatch):
        monkeypatch.setattr(reconcile, "ROLLBACK_DIR", tmp_path)
        reports = [{
            "code": "en",
            "retire": [{"id": "11111111-1111-1111-1111-111111111111", "word": "em"}],
            "unretire": [{"id": "22222222-2222-2222-2222-222222222222", "word": "ya"}],
        }]
        sql = reconcile.write_rollback(reports, "TESTSTAMP").read_text(encoding="utf-8")
        assert "SET retired_at = NULL" in sql       # undoes the retire
        assert "SET retired_at = now()" in sql      # undoes the un-retire
        assert sql.rstrip().endswith("COMMIT;")


def test_every_exclusion_row_is_well_formed():
    """A malformed row silently excludes nothing, which is the failure mode
    that hides worst — the word keeps being taught and the file looks right."""
    with open("data/vocab_exclusions.tsv", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert rows, "the exclusions file is empty"
    bad = [r for r in rows
           if not (r.get("language") or "").strip()
           or not (r.get("word") or "").strip()
           or not (r.get("reason") or "").strip()]
    assert not bad, f"{len(bad)} exclusion rows missing a field: {bad[:3]}"
    seen = set()
    dupes = []
    for r in rows:
        key = (r["language"].strip(), r["word"].strip())
        if key in seen:
            dupes.append(key)
        seen.add(key)
    assert not dupes, f"duplicate exclusions: {dupes[:5]}"
