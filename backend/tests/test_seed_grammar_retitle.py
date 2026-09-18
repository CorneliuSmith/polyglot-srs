"""A grammar point retitled in the Workshop is not re-inserted beside itself
— as of 18 Sep 2026.

`seed_grammar` found a course's curated points by title and upserts
`ON CONFLICT (language_id, title)`. A reviewer who retitles a point leaves
the file carrying the OLD title, no curated row has it, so the next re-seed
saw a new point and inserted it — the original text and drills, beside the
one the reviewer had just fixed — and nothing reported the double. Plan
`quality-guardrails-telemetry`, A2.

Two halves: the seeder indexes a curated point under every title the audit
log says it has had, and the Workshop's title edit marks the point curated
so it is in that index at all. Fake connections throughout; the audit table
may also be absent (a database behind migration 20260823).
"""
from __future__ import annotations

import inspect
import json

import asyncpg

from backend.repositories.contributor import _edit_grammar_card
from backend.services.seeder import seed_grammar
from backend.services.seeder.seed_grammar import GrammarSeeder, curated_points_by_title
from backend.tests.fakes import mock_conn

P1 = {"id": "p1", "title": "New title", "function_note": None,
      "explanation": "e1", "culture_note": None}
P2 = {"id": "p2", "title": "Other point", "function_note": None,
      "explanation": "e2", "culture_note": None}


class _Conn:
    """Answers the curated-rows query and the audit query; counts the calls."""

    def __init__(self, curated, history=None, *, table=True):
        self.curated, self.history, self.table = curated, history or [], table
        self.fetches = 0

    async def fetch(self, sql, *args):
        self.fetches += 1
        if "content_change_log" in sql:
            if not self.table:
                raise asyncpg.exceptions.UndefinedTableError("no table")
            assert "field = 'title'" in sql and "grammar_point" in sql
            return self.history
        return self.curated


def _index(*a, **k):
    import asyncio
    return asyncio.run(curated_points_by_title(_Conn(*a, **k), "lang"))


class TestFormerTitlesFindTheLiveRow:
    def test_the_file_s_old_title_finds_the_retitled_point(self):
        by_title = _index([P1], [{"entity_id": "p1",
                                  "before": json.dumps({"title": "Old title"})}])
        assert by_title["Old title"] is by_title["New title"] is P1

    def test_a_decoded_json_snapshot_works_too(self):
        # asyncpg hands jsonb back as text unless a codec is set; a caller
        # that set one hands a dict. Both shapes are the same fact.
        by_title = _index([P1], [{"entity_id": "p1", "before": {"title": "Old title"}}])
        assert by_title["Old title"] is P1

    def test_a_current_title_wins_over_a_former_one(self):
        """Two points may have swapped names; the row that carries a title
        NOW is the one the file means by it."""
        by_title = _index([P1, P2], [{"entity_id": "p1",
                                      "before": json.dumps({"title": "Other point"})}])
        assert by_title["Other point"] is P2

    def test_history_of_an_uncurated_point_is_not_an_index_entry(self):
        by_title = _index([P1], [{"entity_id": "p9",
                                  "before": json.dumps({"title": "Old title"})}])
        assert "Old title" not in by_title

    def test_a_snapshot_without_a_title_is_skipped(self):
        by_title = _index([P1], [{"entity_id": "p1", "before": None},
                                 {"entity_id": "p1", "before": "not json"},
                                 {"entity_id": "p1", "before": json.dumps({"x": 1})}])
        assert set(by_title) == {"New title"}

    def test_a_database_behind_the_audit_migration_has_no_history(self):
        by_title = _index([P1], table=False)
        assert set(by_title) == {"New title"}

    def test_a_course_with_no_curated_points_asks_no_history(self):
        conn = _Conn([], [{"entity_id": "p1", "before": "{}"}])
        import asyncio
        assert asyncio.run(curated_points_by_title(conn, "lang")) == {}
        assert conn.fetches == 1

    def test_load_uses_the_index(self):
        """Checked on the source of `load`, the only place the lookup lives:
        the inline SELECT that knew only current titles is gone."""
        src = inspect.getsource(GrammarSeeder.load)
        assert "curated_points_by_title(" in src
        assert "curated = true\"" not in src


class TestTheWorkshopRetitleIsAHumanEdit:
    def _prev(self, curated=False):
        return {"language_id": "lang-1", "title": "Old title", "explanation": "e",
                "culture_note": None, "reference_links": "[]", "curated": curated}

    async def test_a_retitle_marks_the_point_curated_and_logs_the_former_title(self):
        conn = mock_conn()
        conn.fetchrow.return_value = self._prev()
        assert await _edit_grammar_card(conn, "p1", {"sentence": "New title"}, "ed") == "ok"
        statements = [c.args[0] for c in conn.execute.call_args_list]
        assert any("SET title = $2, curated = true" in s for s in statements)
        log = next(c.args for c in conn.execute.call_args_list
                   if "content_change_log" in c.args[0])
        assert log[6] == "title"
        assert json.loads(log[7]) == {"title": "Old title", "curated": False}
        assert json.loads(log[8]) == {"title": "New title", "curated": True}

    async def test_the_same_title_again_writes_nothing(self):
        conn = mock_conn()
        conn.fetchrow.return_value = self._prev()
        await _edit_grammar_card(conn, "p1", {"sentence": "Old title"}, "ed")
        assert conn.execute.call_args_list == []


def test_the_lookup_needs_no_repository():
    """The seeder's one other use of the audit table (`log_change`) is a
    deferred import, so a seeder never imports a repository at module load.
    The lookup reads the table with plain SQL in the seeder itself and adds
    no import of any kind — `audit.py`'s own comment keeps the same wall
    from the other side ("so a repository does not import from a seeder")."""
    src = inspect.getsource(seed_grammar.curated_points_by_title)
    assert "content_change_log" in src and "import" not in src
