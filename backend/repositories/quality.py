"""Content-quality telemetry: the rows the nightly loop writes, the switches
the judge reads (migration 20261029).

Why this exists: nothing in the repo stored a quality number with a date on
it. `data/quality/baseline.json` is a current-state ratchet, `reconcile`'s
survey is printed and discarded, `db_snapshot` overwrites one file. So "is
Arabic getting better or worse since the gloss pass" had no answer, and
"the judge flagged 4 percent of Korean" could not be told apart from "the
judge flagged 4 percent of Korean last month too". `quality_runs` is one
row per (run, language, locale, metric); everything the Content Health
panel plots comes from it.

Two rules shape every function here:

* **Every reader degrades on an absent table.** Migrations are the owner's
  to apply and the code deploys first (CLAUDE.md), so a deploy ahead of
  20261029 must write nothing and read empty, not 500 — and must do it under
  a savepoint, because the loop runs inside one privileged transaction and
  a failed statement there poisons every statement after it (LEARN.md,
  "try/except a SQL error inside a transaction is a no-op").
* **The judge's switch fails CLOSED.** `quality_settings` is the owner's
  cost control: their condition for a nightly judge was that how much it
  spends is theirs to set, in the admin panel, because it can be a lot of
  money. So `get_quality_settings` answers OFF with a zero budget whenever
  it cannot read the row — absent table, absent row, any database error.
  A judge that runs because its switch was unreadable is the one outcome
  this table exists to prevent.
"""
from __future__ import annotations

import json
from decimal import Decimal

import asyncpg

from backend.repositories.pool import savepoint

_MISSING = (asyncpg.exceptions.UndefinedTableError,)

# What the judge reads when it cannot read its switch. Off, and a budget of
# nothing — not the migration's defaults, which are what an admin gets AFTER
# they can see and change them.
SETTINGS_OFF: dict = {
    "judge_enabled": False,
    "judge_rows_per_cycle": 0,
    "judge_daily_token_cap": 0,
    "judge_model": None,
}
# The only columns an admin may write; the CHECK ranges from the migration.
SETTINGS_FIELDS = ("judge_enabled", "judge_rows_per_cycle", "judge_daily_token_cap", "judge_model")
ROWS_PER_CYCLE_MAX = 10_000

# A language with no row in language_quality_targets: not judged, and red
# at the thresholds the plan chose (15 percent bad cards, 5 percent judge
# flags) — the same values the migration defaults a new row to.
TARGET_DEFAULTS: dict = {
    "judge_enabled": False,
    "max_bad_card_pct": 15,
    "max_judge_flag_pct": 5,
}
TARGET_FIELDS = tuple(TARGET_DEFAULTS)


def _number(value):
    """NUMERIC comes back as Decimal, which JSON cannot carry. An integral
    value stays an int so a count reads as a count, not as 12.0."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _sid(value) -> str | None:
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# quality_runs — the trend source
# ---------------------------------------------------------------------------


async def record_run(
    conn: asyncpg.Connection,
    *,
    kind: str,
    language_id,
    metric: str,
    value,
    population: int | None = None,
    locale: str | None = None,
    build_sha: str | None = None,
    meta: dict | None = None,
) -> str | None:
    """One measurement. Returns the row id, or None when quality_runs is not
    there yet — the caller counts those so the heartbeat can say "ran, wrote
    nothing, migration 20261029 missing" instead of looking healthy."""
    try:
        async with savepoint(conn):
            row = await conn.fetchrow(
                """
                INSERT INTO quality_runs
                    (kind, language_id, locale, metric, value, population, build_sha, meta)
                VALUES ($1, $2::uuid, $3, $4, $5::numeric, $6, $7, $8::jsonb)
                RETURNING id
                """,
                kind, _sid(language_id), locale, metric, value, population, build_sha,
                json.dumps(meta or {}),
            )
    except _MISSING:
        return None
    return _sid(row["id"])


async def record_runs(conn: asyncpg.Connection, rows: list[dict]) -> list[str | None]:
    """Many at once — one INSERT each. The volume is a few hundred rows a
    night, and a per-row statement keeps the degrade path identical to
    record_run's rather than a second copy of it."""
    return [await record_run(conn, **row) for row in rows]


async def latest_metrics(conn: asyncpg.Connection, language_id=None) -> dict:
    """The most recent value of every metric, per language.

    Shape: {language_id: {key: {kind, metric, locale, value, population,
    run_at}}} where key is the metric name for the course's own content and
    "<locale>:<metric>" for a support-locale measurement — the support
    locale is a corpus of its own (plan §3, principle 6), and a panel that
    merged the two would report the Arabic course healthy on the strength
    of its English hints.
    """
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (language_id, locale, metric)
                       language_id, locale, metric, kind, value, population, run_at
                  FROM quality_runs
                 WHERE ($1::uuid IS NULL OR language_id = $1::uuid)
                 ORDER BY language_id, locale, metric, run_at DESC
                """,
                _sid(language_id),
            )
    except _MISSING:
        return {}
    out: dict = {}
    for r in rows:
        key = r["metric"] if r["locale"] is None else f"{r['locale']}:{r['metric']}"
        out.setdefault(_sid(r["language_id"]), {})[key] = {
            "kind": r["kind"],
            "metric": r["metric"],
            "locale": r["locale"],
            "value": _number(r["value"]),
            "population": r["population"],
            "run_at": r["run_at"],
        }
    return out


async def trend(
    conn: asyncpg.Connection,
    language_id,
    metric: str,
    days: int = 30,
    locale: str | None = None,
) -> list[dict]:
    """One metric's history for one language, oldest first: what a sparkline
    plots. `locale` NULL means the course's own content, so the predicate
    has to say IS NOT DISTINCT FROM — `locale = NULL` matches nothing."""
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT run_at, value, population
                  FROM quality_runs
                 WHERE language_id = $1::uuid
                   AND metric = $2
                   AND locale IS NOT DISTINCT FROM $3
                   AND run_at >= now() - make_interval(days => $4)
                 ORDER BY run_at
                """,
                _sid(language_id), metric, locale, int(days),
            )
    except _MISSING:
        return []
    return [
        {"run_at": r["run_at"], "value": _number(r["value"]), "population": r["population"]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# quality_settings — the judge's spend controls (a singleton, id = 1)
# ---------------------------------------------------------------------------


async def get_quality_settings(conn: asyncpg.Connection) -> dict:
    """The judge's switch and budget. OFF, with a zero budget, whenever the
    row cannot be read: table absent, row absent, or any other database
    error. Catches wider than the other readers here on purpose — this is
    the one read where "I don't know" must mean "spend nothing"."""
    try:
        async with savepoint(conn):
            row = await conn.fetchrow(
                """
                SELECT judge_enabled, judge_rows_per_cycle, judge_daily_token_cap, judge_model
                  FROM quality_settings
                 WHERE id = 1
                """
            )
    except asyncpg.PostgresError:
        return dict(SETTINGS_OFF)
    if row is None:
        return dict(SETTINGS_OFF)
    return {
        "judge_enabled": bool(row["judge_enabled"]),
        "judge_rows_per_cycle": int(row["judge_rows_per_cycle"] or 0),
        "judge_daily_token_cap": int(row["judge_daily_token_cap"] or 0),
        "judge_model": row["judge_model"] or None,
    }


def _clamp_settings(fields: dict) -> dict:
    """Only the four settable columns, each inside its CHECK range, so a
    panel that sends -1 or a stray key gets a stored value rather than a
    constraint error that reads as a broken panel."""
    out: dict = {}
    if "judge_enabled" in fields:
        out["judge_enabled"] = bool(fields["judge_enabled"])
    if "judge_rows_per_cycle" in fields:
        out["judge_rows_per_cycle"] = max(
            0, min(ROWS_PER_CYCLE_MAX, int(fields["judge_rows_per_cycle"] or 0))
        )
    if "judge_daily_token_cap" in fields:
        out["judge_daily_token_cap"] = max(0, int(fields["judge_daily_token_cap"] or 0))
    if "judge_model" in fields:
        model = (fields["judge_model"] or "").strip()
        out["judge_model"] = model or None
    return out


async def update_quality_settings(
    conn: asyncpg.Connection, *, updated_by: str | None, **fields
) -> dict | None:
    """Admin-only (the router enforces). Writes only the fields given and
    returns the whole row as get_quality_settings would. Returns None when
    the table is absent so the router can say 503 — an admin's write failing
    silently is worse than a read degrading (repositories/flags.py)."""
    clean = _clamp_settings(fields)
    try:
        async with savepoint(conn):
            # The singleton is seeded by the migration; re-seed it here so a
            # row somebody deleted by hand cannot make every save a no-op.
            await conn.execute(
                "INSERT INTO quality_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
            )
            if clean:
                sets = ", ".join(f"{name} = ${i}" for i, name in enumerate(clean, start=1))
                await conn.execute(
                    f"""
                    UPDATE quality_settings
                       SET {sets}, updated_at = now(), updated_by = ${len(clean) + 1}::uuid
                     WHERE id = 1
                    """,
                    *clean.values(), _sid(updated_by),
                )
    except _MISSING:
        return None
    return await get_quality_settings(conn)


# ---------------------------------------------------------------------------
# language_quality_targets — per-course judge opt-in and red thresholds
# ---------------------------------------------------------------------------


async def get_language_targets(conn: asyncpg.Connection) -> dict:
    """{language_id: {judge_enabled, max_bad_card_pct, max_judge_flag_pct}}
    for EVERY language, defaults filled in for those with no row — so a
    panel can list all 27 courses, and the judge can ask "is this course
    on" without a second query. Without the table every course reads as
    the defaults, which means not judged."""
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT l.id, t.judge_enabled, t.max_bad_card_pct, t.max_judge_flag_pct
                  FROM languages l
                  LEFT JOIN language_quality_targets t ON t.language_id = l.id
                """
            )
    except _MISSING:
        rows = await conn.fetch("SELECT id FROM languages")
        return {_sid(r["id"]): dict(TARGET_DEFAULTS) for r in rows}
    out: dict = {}
    for r in rows:
        out[_sid(r["id"])] = {
            "judge_enabled": (
                TARGET_DEFAULTS["judge_enabled"]
                if r["judge_enabled"] is None else bool(r["judge_enabled"])
            ),
            "max_bad_card_pct": (
                TARGET_DEFAULTS["max_bad_card_pct"]
                if r["max_bad_card_pct"] is None else _number(r["max_bad_card_pct"])
            ),
            "max_judge_flag_pct": (
                TARGET_DEFAULTS["max_judge_flag_pct"]
                if r["max_judge_flag_pct"] is None else _number(r["max_judge_flag_pct"])
            ),
        }
    return out


def _pct(value) -> float | None:
    if value is None:
        return None
    return max(0.0, min(100.0, float(value)))


async def set_language_target(
    conn: asyncpg.Connection, language_id, *, updated_by: str | None, **fields
) -> dict | None:
    """Upsert one course's row, touching only the fields given: a NULL
    parameter means "leave it" on the update path and "the default" on the
    insert path, so flipping the judge on does not reset the thresholds.
    Returns the stored row, or None when the table is absent (503, as with
    update_quality_settings)."""
    judge_enabled = fields.get("judge_enabled")
    judge_enabled = None if judge_enabled is None else bool(judge_enabled)
    bad = _pct(fields.get("max_bad_card_pct"))
    flag = _pct(fields.get("max_judge_flag_pct"))
    try:
        async with savepoint(conn):
            row = await conn.fetchrow(
                """
                INSERT INTO language_quality_targets
                    (language_id, judge_enabled, max_bad_card_pct, max_judge_flag_pct,
                     updated_by, updated_at)
                VALUES ($1::uuid, COALESCE($2, false), COALESCE($3, 15), COALESCE($4, 5),
                        $5::uuid, now())
                ON CONFLICT (language_id) DO UPDATE SET
                    judge_enabled      = COALESCE($2, language_quality_targets.judge_enabled),
                    max_bad_card_pct   = COALESCE($3, language_quality_targets.max_bad_card_pct),
                    max_judge_flag_pct = COALESCE($4, language_quality_targets.max_judge_flag_pct),
                    updated_by = $5::uuid, updated_at = now()
                RETURNING judge_enabled, max_bad_card_pct, max_judge_flag_pct
                """,
                _sid(language_id), judge_enabled, bad, flag, _sid(updated_by),
            )
    except _MISSING:
        return None
    return {
        "judge_enabled": bool(row["judge_enabled"]),
        "max_bad_card_pct": _number(row["max_bad_card_pct"]),
        "max_judge_flag_pct": _number(row["max_judge_flag_pct"]),
    }


# ---------------------------------------------------------------------------
# tutor_usage — what the judge has already spent today
# ---------------------------------------------------------------------------


async def judge_tokens_spent_today(conn: asyncpg.Connection) -> int:
    """Tokens the judge has burned since UTC midnight, from the cost ledger
    every model call writes (tutor_usage, kind='judge'). The loop reads
    this before every batch and stops at judge_daily_token_cap. The day
    boundary is UTC in both directions: `now() AT TIME ZONE 'UTC'` drops
    the zone, so the truncated midnight has to be re-tagged as UTC before
    it can be compared with a timestamptz — otherwise the comparison
    silently adopts the session's time zone. Degrades to 0: no ledger, no
    spend recorded, and the cap check is the judge's problem to fail on."""
    try:
        async with savepoint(conn):
            total = await conn.fetchval(
                """
                SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0)
                  FROM tutor_usage
                 WHERE kind = 'judge'
                   AND created_at >= (date_trunc('day', now() AT TIME ZONE 'UTC')
                                      AT TIME ZONE 'UTC')
                """
            )
    except (asyncpg.exceptions.UndefinedTableError, asyncpg.exceptions.UndefinedColumnError):
        return 0
    return int(total or 0)
