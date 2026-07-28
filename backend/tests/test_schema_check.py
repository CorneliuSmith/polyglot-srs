"""Schema-drift detection: parse the migrations, diff against the live
schema, name the migration that fixes each gap.

Regression cover for a live incident — the Gym 500'd for days because a
deploy shipped code reading `drill_sentences.lemma` without applying
20260829000000_drill_lemma, and nothing in the app said so.
"""

from __future__ import annotations

from pathlib import Path

from backend.services.schema_check import expected_objects


def _write(tmp_path: Path, name: str, sql: str) -> None:
    (tmp_path / name).write_text(sql, encoding="utf-8")


class TestExpectedObjects:
    def test_parses_create_table_and_add_column(self, tmp_path):
        _write(tmp_path, "0001_init.sql", """
            CREATE TABLE drill_sentences (
                id UUID PRIMARY KEY,
                sentence TEXT NOT NULL
            );
        """)
        _write(tmp_path, "0002_lemma.sql", """
            ALTER TABLE drill_sentences
                ADD COLUMN IF NOT EXISTS lemma TEXT;
        """)
        found = {(e.table, e.column, e.migration) for e in expected_objects(tmp_path)}
        assert ("drill_sentences", None, "0001_init.sql") in found
        assert ("drill_sentences", "lemma", "0002_lemma.sql") in found

    def test_multiple_columns_in_one_statement(self, tmp_path):
        _write(tmp_path, "0001.sql", "CREATE TABLE t (id UUID);")
        _write(tmp_path, "0002.sql", """
            ALTER TABLE t
                ADD COLUMN a TEXT,
                ADD COLUMN IF NOT EXISTS b BOOLEAN NOT NULL DEFAULT false;
        """)
        cols = {e.column for e in expected_objects(tmp_path) if e.column}
        assert cols == {"a", "b"}

    def test_comments_never_create_expectations(self, tmp_path):
        # A commented-out DDL (or prose mentioning it) must not become an
        # expectation — a false "missing!" is worse than a quiet miss.
        _write(tmp_path, "0001.sql", """
            -- ALTER TABLE ghost ADD COLUMN nope TEXT;
            /* CREATE TABLE also_ghost (id UUID); */
            CREATE TABLE real_one (id UUID);
        """)
        tables = {e.table for e in expected_objects(tmp_path)}
        assert tables == {"real_one"}

    def test_dropped_objects_are_not_expected(self, tmp_path):
        _write(tmp_path, "0001.sql", "CREATE TABLE t (id UUID);")
        _write(tmp_path, "0002.sql", "ALTER TABLE t ADD COLUMN temp TEXT;")
        _write(tmp_path, "0003.sql", "ALTER TABLE t DROP COLUMN IF EXISTS temp;")
        _write(tmp_path, "0004.sql", "CREATE TABLE gone (id UUID);")
        _write(tmp_path, "0005.sql", "DROP TABLE IF EXISTS gone;")
        objs = {(e.table, e.column) for e in expected_objects(tmp_path)}
        assert ("t", "temp") not in objs
        assert ("gone", None) not in objs
        assert ("t", None) in objs

    def test_every_column_of_a_multi_column_drop_is_honoured(self, tmp_path):
        """One ALTER can retire several columns. The first version of this
        parser caught only the first, so the second lingered as a phantom
        expectation and the drift detector reported a column a later
        migration had deliberately removed — CI caught it against a real
        fully-migrated database."""
        _write(tmp_path, "0001.sql", "CREATE TABLE t (id UUID);")
        _write(tmp_path, "0002.sql", """
            ALTER TABLE t
                ADD COLUMN IF NOT EXISTS keep TEXT,
                ADD COLUMN IF NOT EXISTS a UUID[],
                ADD COLUMN IF NOT EXISTS b UUID[];
        """)
        _write(tmp_path, "0003.sql", """
            ALTER TABLE t
                DROP COLUMN IF EXISTS a,
                DROP COLUMN IF EXISTS b;
        """)
        objs = {(e.table, e.column) for e in expected_objects(tmp_path)}
        assert ("t", "a") not in objs
        assert ("t", "b") not in objs
        # The column the migration kept is still expected.
        assert ("t", "keep") in objs

    def test_a_drop_does_not_retire_a_same_named_column_elsewhere(self, tmp_path):
        _write(tmp_path, "0001.sql", "CREATE TABLE t (id UUID);")
        _write(tmp_path, "0002.sql", "CREATE TABLE u (id UUID);")
        _write(tmp_path, "0003.sql", "ALTER TABLE t ADD COLUMN note TEXT;")
        _write(tmp_path, "0004.sql", "ALTER TABLE u ADD COLUMN note TEXT;")
        _write(tmp_path, "0005.sql", "ALTER TABLE t DROP COLUMN IF EXISTS note;")
        objs = {(e.table, e.column) for e in expected_objects(tmp_path)}
        assert ("t", "note") not in objs
        assert ("u", "note") in objs

    def test_missing_directory_is_not_an_error(self, tmp_path):
        assert expected_objects(tmp_path / "nope") == []

    def test_real_migrations_include_the_incident_column(self):
        # The actual repo: the column whose absence caused the Gym 500 must
        # be part of the expectation set.
        objs = {(e.table, e.column) for e in expected_objects()}
        assert ("drill_sentences", "lemma") in objs
        assert ("grammar_point_overlaps", None) in objs
