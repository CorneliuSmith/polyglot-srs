"""Schema-drift detection: does the running code's DB actually have the
columns and tables the code expects?

Written after a live incident: the Gym returned a bare `500` on
`/api/review/cram` for days because the deploy shipped code that reads
`drill_sentences.lemma` while the migration adding that column
(20260829000000_drill_lemma) had not been applied. Nothing in the app said
so — the only clue was an asyncpg `UndefinedColumnError` buried in the logs.

This module derives the expectation set from the migration files themselves
(no hand-maintained list to fall out of date), diffs it against
`information_schema`, and names the migration that would fix each gap. It is
diagnostic only: it never blocks startup and never mutates anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import asyncpg

# Repo root: backend/services/schema_check.py -> ../../
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"

# `CREATE TABLE [IF NOT EXISTS] name (`  — public schema only; the auth shim
# and Supabase-managed schemas are not ours to check.
_CREATE_TABLE = re.compile(
    r"^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:public\.)?([a-z_][a-z0-9_]*)",
    re.IGNORECASE | re.MULTILINE,
)
# `ALTER TABLE [IF EXISTS] name ... ADD COLUMN [IF NOT EXISTS] col` — the
# statement often wraps across lines, so match the pair non-greedily.
_ADD_COLUMN = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?([a-z_][a-z0-9_]*)"
    r"(.*?)(?=;)",
    re.IGNORECASE | re.DOTALL,
)
_COLUMN_NAME = re.compile(
    r"ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Expectation:
    """One database object a migration promises to have created."""

    migration: str
    table: str
    column: str | None = None  # None = the table itself

    def describe(self) -> str:
        target = self.table if self.column is None else f"{self.table}.{self.column}"
        return f"{target} (from {self.migration})"


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def expected_objects(migrations_dir: Path | None = None) -> list[Expectation]:
    """Parse the migration files into the set of tables/columns they create.

    Deliberately conservative: only plain `CREATE TABLE` and `ADD COLUMN`
    forms are recognised, because a false "missing!" report is worse than a
    quiet miss for a diagnostic. Later migrations that DROP an object are
    also honoured, so a renamed column doesn't linger as a phantom.
    """
    directory = migrations_dir or MIGRATIONS_DIR
    if not directory.is_dir():
        return []
    out: list[Expectation] = []
    dropped: set[tuple[str, str | None]] = set()
    for path in sorted(directory.glob("*.sql")):
        sql = _strip_comments(path.read_text(encoding="utf-8"))
        for table in _CREATE_TABLE.findall(sql):
            out.append(Expectation(path.name, table.lower()))
        for table, body in _ADD_COLUMN.findall(sql):
            for column in _COLUMN_NAME.findall(body):
                out.append(Expectation(path.name, table.lower(), column.lower()))
        for table, column in re.findall(
            r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?([a-z_][a-z0-9_]*)"
            r"[^;]*?DROP\s+COLUMN\s+(?:IF\s+EXISTS\s+)?([a-z_][a-z0-9_]*)",
            sql, re.IGNORECASE | re.DOTALL,
        ):
            dropped.add((table.lower(), column.lower()))
        for table in re.findall(
            r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?([a-z_][a-z0-9_]*)",
            sql, re.IGNORECASE,
        ):
            dropped.add((table.lower(), None))
    return [
        e for e in out
        if (e.table, e.column) not in dropped and (e.table, None) not in dropped
    ]


async def find_schema_drift(
    conn: asyncpg.Connection, migrations_dir: Path | None = None
) -> dict:
    """Compare the live schema against what the migrations promise.

    Returns {"ok", "initialized", "missing_migrations", "missing"} where
    `missing` names each absent object and the migration that adds it. On a
    completely empty database `initialized` is False and the per-object list
    is suppressed — "run the migrations" is the whole message there.
    """
    expectations = expected_objects(migrations_dir)
    if not expectations:
        return {"ok": True, "initialized": True, "missing_migrations": [], "missing": []}

    rows = await conn.fetch(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    live_columns = {(r["table_name"], r["column_name"]) for r in rows}
    live_tables = {r["table_name"] for r in rows}

    if not live_tables:
        return {
            "ok": False,
            "initialized": False,
            "missing_migrations": sorted({e.migration for e in expectations}),
            "missing": [],
        }

    missing: list[Expectation] = []
    for e in expectations:
        if e.column is None:
            if e.table not in live_tables:
                missing.append(e)
        elif (e.table, e.column) not in live_columns:
            # A column can only be missing meaningfully when its table exists;
            # otherwise the table's own entry already reports the gap.
            if e.table in live_tables:
                missing.append(e)
    return {
        "ok": not missing,
        "initialized": True,
        "missing_migrations": sorted({e.migration for e in missing}),
        "missing": [e.describe() for e in missing],
    }
