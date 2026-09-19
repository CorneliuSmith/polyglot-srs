"""What the Content Health endpoints read that `repositories/quality.py` does
not: the table probes, the open verdicts and their counts, the disposition
write, and the last reconcile survey per course (migration 20261107000000).

The same two rules as quality.py: every reader degrades on an absent table
under a savepoint, because the router holds one privileged transaction and
a failed statement would poison every read after it; and the one writer
here says so when the table is absent instead of pretending, so the router
can answer 503 naming the migration (the plan-limits precedent in
`routers/contribute.py`).

The probe is `to_regclass`, not a failing SELECT: it never raises, so four
tables cost one statement and no savepoint (`admins.digest_log_present`,
`trials.trials_table_present`, `contributor._present`).
"""
from __future__ import annotations

from decimal import Decimal

import asyncpg

from backend.repositories.pool import savepoint

_MISSING = (asyncpg.exceptions.UndefinedTableError, asyncpg.exceptions.UndefinedColumnError)

# The four tables of migration 20261107000000, in the order the panel's
# `available` block names them.
TABLES = ("quality_runs", "content_verdicts", "quality_settings", "language_quality_targets")

# What `dispose_verdict` returns when content_verdicts is not there: distinct
# from None (no open row with that id) so the router can tell 503 from 404.
TABLE_ABSENT = object()

VERDICT_COLUMNS = (
    "id", "judged_at", "entity_type", "entity_id", "field", "question", "verdict",
    "category", "evidence", "confidence", "expected", "note", "judge", "disposition", "locale",
)


def _num(value):
    """NUMERIC arrives as Decimal; an integral value stays an int (quality._number)."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _sid(value) -> str | None:
    return str(value) if value is not None else None


async def list_languages(conn: asyncpg.Connection) -> list[dict]:
    """Every language, by code — the panel lists all of them, measured or
    not, so a course the loop skipped shows as grey rather than vanishing."""
    rows = await conn.fetch("SELECT id, code, name FROM languages ORDER BY code")
    return [{"id": str(r["id"]), "code": r["code"], "name": r["name"]} for r in rows]


async def table_flags(conn: asyncpg.Connection) -> dict[str, bool]:
    """{table: present} for the four telemetry tables, in one statement."""
    rows = await conn.fetch(
        """
        SELECT t AS name, to_regclass(t) IS NOT NULL AS present
          FROM unnest($1::text[]) AS t
        """,
        list(TABLES),
    )
    found = {r["name"]: bool(r["present"]) for r in rows}
    return {table: found.get(table, False) for table in TABLES}


async def open_flag_counts(
    conn: asyncpg.Connection,
    positives: dict[str, frozenset[str] | set[str]],
    min_confidence: Decimal,
) -> dict[str, dict[str, int]]:
    """{language_id: {question: n}} — open verdicts whose verdict is one of
    that question's positive set, at or above the confidence floor.

    The (question, verdict) pairs travel as two parallel arrays and are
    joined through unnest, so a verdict word one question uses for a
    finding (`rare`) can never count under a question that does not
    (`register`) — `question = ANY(..) AND verdict = ANY(..)` would.

    It counts DISTINCT ROWS OF CONTENT, not verdict rows, because it is the
    numerator of a rate whose denominator (`verdicts.judged_count`) counts
    the same identity — `(entity_type, entity_id, field, locale)`, folded the
    way the unique index folds it. A row judged on two nights with both
    verdicts still open is two verdict rows and one flagged card; counting
    `*` here made the panel able to print a flag rate above 100%."""
    questions: list[str] = []
    verdicts: list[str] = []
    for question, words in sorted(positives.items()):
        for word in sorted(words):
            questions.append(question)
            verdicts.append(word)
    if not questions:
        return {}
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT v.language_id, v.question,
                       count(DISTINCT (v.entity_type, v.entity_id, v.field,
                                       COALESCE(v.locale, ''))) AS flagged
                  FROM content_verdicts v
                  JOIN unnest($1::text[], $2::text[]) AS p(question, verdict)
                    ON p.question = v.question AND p.verdict = v.verdict
                 WHERE v.disposition = 'open'
                   AND v.confidence >= $3::numeric
                 GROUP BY v.language_id, v.question
                """,
                questions, verdicts, min_confidence,
            )
    except _MISSING:
        return {}
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        out.setdefault(_sid(r["language_id"]), {})[r["question"]] = int(r["flagged"])
    return out


async def open_verdicts(
    conn: asyncpg.Connection, language_id, limit: int = 200
) -> list[dict]:
    """The open queue for one course, newest first, capped: the drill-down
    is a list to work through, not an export."""
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                f"""
                SELECT {", ".join(VERDICT_COLUMNS)}
                  FROM content_verdicts
                 WHERE language_id = $1::uuid
                   AND disposition = 'open'
                 ORDER BY judged_at DESC
                 LIMIT $2
                """,
                _sid(language_id), int(limit),
            )
    except _MISSING:
        return []
    out = []
    for r in rows:
        row = {col: r[col] for col in VERDICT_COLUMNS}
        row["id"] = _sid(row["id"])
        row["entity_id"] = _sid(row["entity_id"])
        row["judged_at"] = row["judged_at"].isoformat() if row["judged_at"] else None
        row["evidence"] = list(row["evidence"] or [])
        row["confidence"] = _num(row["confidence"])
        out.append(row)
    return out


async def dispose_verdict(
    conn: asyncpg.Connection, verdict_id: str, disposition: str, disposed_by: str
):
    """Mark one OPEN verdict accepted or rejected, by this admin, now.

    Returns {id, disposition, disposed_at}; None when no open row has that
    id (already disposed, or never existed — the router 404s either way);
    TABLE_ABSENT when content_verdicts is not there (503). Touches nothing
    but the verdict row: what a person agreed with is recorded, and nothing
    is applied to content until decision #5 says what "accept" does."""
    try:
        async with savepoint(conn):
            row = await conn.fetchrow(
                """
                UPDATE content_verdicts
                   SET disposition = $2, disposed_by = $3::uuid, disposed_at = now()
                 WHERE id = $1::uuid AND disposition = 'open'
                RETURNING id, disposition, disposed_at
                """,
                verdict_id, disposition, disposed_by,
            )
    except _MISSING:
        return TABLE_ABSENT
    if row is None:
        return None
    return {
        "id": _sid(row["id"]),
        "disposition": row["disposition"],
        "disposed_at": row["disposed_at"].isoformat() if row["disposed_at"] else None,
    }


async def latest_reconcile(conn: asyncpg.Connection) -> dict[str, dict]:
    """{language_id: {metrics: {metric: value}, run_at, build_sha}} from the
    newest kind='reconcile' row per metric; run_at and build_sha are the
    newest row's. Only courses with a survey appear — the deploy panel lists
    what reconcile measured, not every language."""
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (language_id, metric)
                       language_id, metric, value, run_at, build_sha
                  FROM quality_runs
                 WHERE kind = 'reconcile' AND locale IS NULL
                 ORDER BY language_id, metric, run_at DESC
                """
            )
    except _MISSING:
        return {}
    out: dict[str, dict] = {}
    for r in rows:
        entry = out.setdefault(
            _sid(r["language_id"]), {"metrics": {}, "run_at": None, "build_sha": None},
        )
        entry["metrics"][r["metric"]] = _num(r["value"])
        if entry["run_at"] is None or r["run_at"] > entry["run_at"]:
            entry["run_at"] = r["run_at"]
            entry["build_sha"] = r["build_sha"]
    return out
