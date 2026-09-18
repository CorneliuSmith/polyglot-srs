"""The nightly quality cycle: persist what the repo's checks already compute.

Why this exists. Every quality instrument in this repo produced a number and
threw it away. `audit_content` prints counts and gates CI on a ratchet file;
`reconcile --report` prints drift and exits; `db_snapshot` overwrites one
JSON file; the review inbox counts its queues on every page load and keeps
none of it. So the program could say "Korean has 82 percent sentence
coverage today" and never "and it was 70 percent before the authoring pass"
— and the owner's condition for ever running a paid judge was that coverage
is tracked first, with the spend theirs to set. This loop is the tracking
half: once a day it runs the mechanical checks that cost nothing and writes
one `quality_runs` row per (language, metric), so the Content Health panel
has a trend to plot and a judge, when one is switched on, has a baseline to
be measured against.

What it does per course, in order: the content audit (every rule in
`audit_content.ALL_RULES`, run in a worker thread because it parses the
frequency and sentence files and would stall every request for the duration
if it ran on the event loop); the reconcile survey (how far production has
drifted from the committed files — the 25 Aug gap, measured nightly instead
of once); the snapshot counts (what production actually serves); and the
sentence-layer coverage of the top band. Then, once, the review-queue depths
for every language.

Then, still free, how much of each judge question's scope has a verdict —
the coverage the owner asked to see tracked before any judge runs, written
for every course whether or not the judge is on.

The judge itself is `quality/judge_step.py`: the one paid step, run by
`quality_loop()` after `run_quality_cycle` has written every mechanical
row, behind `get_quality_settings()['judge_enabled']` (fails closed), the
daily token cap, the per-course opt-in and `data/eval/calibrated.json`.
Its stats land under `stats["judge"]`; its failure is one line in the
cycle's failures, never a lost cycle.

Failure shape. Each step runs under its own savepoint and its own
try/except, so one broken course — a missing grammar file, a survey that
hits a column the database does not have yet — loses that one step's rows
and nothing else. Failures are counted in the cycle's stats and logged at
warning, and the stats land in `QUALITY_HEARTBEAT`, because every failure
mode of a background loop looks the same from outside ("no new rows") and
the first question is always whether it ran at all.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from backend.repositories import quality as quality_repo
from backend.repositories import verdicts as verdicts_repo
from backend.repositories.contributor import review_inbox_by_language
from backend.repositories.pool import savepoint
from backend.services.build_info import build_info
from backend.services.quality import audit_content, content_judge, db_snapshot
from backend.services.quality.judge_step import judge_step
from backend.services.seeder import reconcile

logger = logging.getLogger(__name__)

SWEEP_SECONDS = 24 * 60 * 60
# Let the pool and the schema check settle before the first pass — and keep
# the first audit (a minute of file parsing across 27 courses) away from
# the cold-start window the platform's health check watches.
FIRST_SWEEP_DELAY_SECONDS = 120

# Rules whose count is "drills out of this many": population = the course's
# drill count. The others count points (structural), frequency rows
# (wrong_sense_gloss, circular_gloss, relation_only_gloss), sentence-bank
# words (unclozable_rows, frame_collision) or are one summary line
# (gender_marking), and get no population rather than a wrong one.
DRILL_RULES = frozenset((
    "leak_hard", "self_answering", "giveaway_by_gloss", "agreement_feature",
    "duplicate_hint", "empty", "ar_register", "construction_quote",
    "vague_translation", "hint_language", "stem_in_hint",
))

# quality_runs metric -> key in reconcile.survey's report. Each is a list;
# the metric is its length.
RECONCILE_METRICS = (
    ("gloss", "gloss_changes"),
    ("pos", "pos_changes"),
    ("no_translation", "missing_translation"),
    ("gone", "departed"),
    ("new", "absent_from_db"),
    ("retire", "retire"),
    ("unretire", "unretire"),
    ("gp_retire", "retire_points"),
)

# Proof of life for the cycle, in this process — the auto-translate loop's
# shape. "Ran and wrote nothing" (table absent), "ran and every course
# failed" and "never ran" are three different repairs, and a panel that
# only sees the rows table cannot tell them apart.
QUALITY_HEARTBEAT: dict = {
    "started": False,
    "cycles": 0,
    "last_cycle_at": None,
    "last_error": None,
    "last_stats": None,
}


def quality_heartbeat() -> dict:
    """What the loop has done in THIS process. Copied, not shared."""
    return dict(QUALITY_HEARTBEAT)


def _new_stats() -> dict:
    return {
        "languages": 0,   # courses that were in the database and were processed
        "rows": 0,        # quality_runs rows written
        "dropped": 0,     # measurements record_run could not store (table absent)
        "skipped": [],    # "<code>: <why>" — not in the DB, no frequency file
        "failures": [],   # "<code>.<step>: <error>" — one broken step, counted
    }


async def _write(conn, stats: dict, sha: str | None, **row) -> None:
    """One measurement, counted as written or dropped."""
    row_id = await quality_repo.record_run(conn, build_sha=sha, **row)
    stats["rows" if row_id is not None else "dropped"] += 1


async def _step(conn, stats: dict, code: str, name: str, fn, *args):
    """Run one step under its own savepoint. A failure rolls that step's
    statements back — a failed one would otherwise poison the transaction
    for every course after it — and is counted, never raised."""
    try:
        async with savepoint(conn):
            return await fn(conn, stats, *args)
    except Exception as exc:  # noqa: BLE001 — one course must not stop the cycle
        logger.warning("quality cycle: %s %s failed: %s", code, name, exc)
        stats["failures"].append(f"{code}.{name}: {type(exc).__name__}: {exc}")
        return None


async def _language_ids(conn) -> dict[str, str]:
    rows = await conn.fetch(
        "SELECT id, code FROM languages WHERE code = ANY($1::text[])",
        list(db_snapshot.LANGUAGES),
    )
    return {r["code"]: str(r["id"]) for r in rows}


# ---------------------------------------------------------------------------
# The steps. Each takes (conn, stats, ...) and writes its own rows.
# ---------------------------------------------------------------------------


async def _audit_step(conn, stats: dict, code: str, lang_id: str, sha: str | None) -> dict:
    # In a thread, always: audit_language parses the frequency file (up to
    # 200k rows), the sentence bank and the grammar JSON, and on the event
    # loop that is seconds during which no request is served.
    report = await asyncio.to_thread(audit_content.audit_language, code)
    meta = {"drills": report["drills"], "points": report["points"]}
    for rule in audit_content.ALL_RULES:
        await _write(
            conn, stats, sha,
            kind="audit", language_id=lang_id, metric=rule,
            value=report["counts"].get(rule, 0),
            population=report["drills"] if rule in DRILL_RULES else None,
            meta=meta,
        )
    return report


async def _reconcile_step(conn, stats: dict, code: str, lang_id: str, sha: str | None) -> None:
    rep = await reconcile.survey(conn, code)
    if rep.get("skipped"):
        stats["skipped"].append(f"{code}: {rep['skipped']}")
        return
    population = rep.get("db_rows")
    for metric, key in RECONCILE_METRICS:
        await _write(
            conn, stats, sha,
            kind="reconcile", language_id=lang_id, metric=metric,
            value=len(rep.get(key) or []), population=population,
        )
    # The number that decides whether "gone" is a chore or a learner-facing
    # loss: rows that left the file while somebody still holds a card on them.
    await _write(
        conn, stats, sha,
        kind="reconcile", language_id=lang_id, metric="gone_with_cards",
        value=sum(1 for d in rep.get("departed") or [] if d.get("cards")),
        population=population,
    )


async def _snapshot_step(conn, stats: dict, code: str, lang_id: str, sha: str | None) -> None:
    # samples=0: the counts only. Sample rows are card text, and this table
    # is a ledger of numbers, not a second copy of the corpus.
    snap = await db_snapshot.snapshot_language(conn, code, samples=0)
    if not snap.get("present"):
        return
    for key, val in (snap.get("counts") or {}).items():
        if isinstance(val, bool) or not isinstance(val, int | float):
            continue
        await _write(
            conn, stats, sha,
            kind="snapshot", language_id=lang_id, metric=key, value=val,
        )


async def _coverage_step(
    conn, stats: dict, code: str, lang_id: str, sha: str | None, report: dict | None
) -> None:
    """How much of the top band a card can actually blank.

    `unclozable_rows` (already written under kind='audit') counts the words
    in the top CARD_RULE_BAND whose every sentence the card cannot cloze.
    The complement, out of the band, is the coverage number the owner asked
    to see tracked — with the band capped at the course's own row count,
    because a 1,200-row course is not 60 percent covered for being short.
    """
    if report is None:
        return  # the audit failed; there is no count to complement
    rows = await asyncio.to_thread(reconcile.expected_rows, code)
    band = min(audit_content.CARD_RULE_BAND, len(rows))
    if band <= 0:
        stats["skipped"].append(f"{code}: no frequency file, no coverage")
        return
    unclozable = int(report["counts"].get("unclozable_rows", 0))
    await _write(
        conn, stats, sha,
        kind="coverage", language_id=lang_id, metric="blankable_top_band",
        value=max(band - unclozable, 0), population=band,
        meta={"unclozable_rows": unclozable, "band": audit_content.CARD_RULE_BAND},
    )


async def _judge_coverage_step(
    conn, stats: dict, code: str, lang_id: str, sha: str | None, calibrated: set
) -> None:
    """How much of each judge question's scope has ever had a verdict.

    Written for every course and every question whether or not the judge
    is on — it costs two counts — because the owner's condition for
    running a paid judge was that its coverage is tracked from day one,
    and a course the judge has never read must show 0 of N, not nothing.
    `calibrated` in the meta says whether the pair could be judged at all
    (`data/eval/calibrated.json`), so the panel can tell "not yet read"
    from "cannot be read yet".
    """
    for question in content_judge.QUESTIONS.values():
        judged = await verdicts_repo.judged_count(conn, question, lang_id)
        scope = await verdicts_repo.scope_size(conn, question, lang_id)
        await _write(
            conn, stats, sha,
            kind="coverage", language_id=lang_id, metric=f"judge.{question.name}",
            value=judged, population=scope,
            meta={"calibrated": (question.name, code) in calibrated},
        )


async def _queues_step(conn, stats: dict, sha: str | None) -> None:
    # One query for every language (the inbox's own roll-up), not one per
    # course: it probes for every table it needs and folds the queues the
    # way the panel shows them, so the trend matches what the reviewer saw.
    rows = await review_inbox_by_language(conn, include_empty=True)
    for row in rows:
        for key, count in row["counts"].items():
            await _write(
                conn, stats, sha,
                kind="queues", language_id=row["id"], metric=key, value=count,
            )


# ---------------------------------------------------------------------------
# The cycle and the loop
# ---------------------------------------------------------------------------


async def run_quality_cycle(conn) -> dict:
    """Every mechanical measurement for every course, once. Returns the
    stats the heartbeat keeps; never raises for a single course."""
    stats = _new_stats()
    sha = build_info().get("sha")
    ids = await _language_ids(conn)
    calibrated = content_judge.calibrated_pairs()
    for code in db_snapshot.LANGUAGES:
        lang_id = ids.get(code)
        if lang_id is None:
            stats["skipped"].append(f"{code}: not in the database")
            continue
        report = await _step(conn, stats, code, "audit", _audit_step, code, lang_id, sha)
        await _step(conn, stats, code, "reconcile", _reconcile_step, code, lang_id, sha)
        await _step(conn, stats, code, "snapshot", _snapshot_step, code, lang_id, sha)
        await _step(conn, stats, code, "coverage", _coverage_step, code, lang_id, sha, report)
        await _step(conn, stats, code, "judge_coverage", _judge_coverage_step,
                    code, lang_id, sha, calibrated)
        stats["languages"] += 1
    await _step(conn, stats, "*", "queues", _queues_step, sha)
    if stats["dropped"] and not stats["rows"]:
        logger.warning(
            "quality cycle: quality_runs is absent (migration 20261029 not applied); "
            "%d measurements dropped", stats["dropped"],
        )
    return stats


def _summary(stats: dict) -> str:
    line = (
        f"{stats.get('languages', 0)} courses, {stats.get('rows', 0)} rows"
        f", {stats.get('dropped', 0)} dropped, {len(stats.get('skipped', ()))} skipped"
        f", {len(stats.get('failures', ()))} failures"
    )
    judge = stats.get("judge")
    if judge is None:
        return line
    if not judge.get("enabled"):
        return line + "; judge off"
    line += (
        f"; judge: {judge.get('judged', 0)} judged, {judge.get('flagged', 0)} flagged"
        f", {judge.get('tokens', 0)} tokens over {judge.get('calls', 0)} calls"
    )
    if judge.get("cap_reached"):
        line += ", cap reached"
    return line


async def quality_loop() -> None:
    """Background task started from the app lifespan. Never raises."""
    from backend.repositories.pool import privileged_connection

    logger.info("quality loop started (every %ds)", SWEEP_SECONDS)
    QUALITY_HEARTBEAT["started"] = True
    await asyncio.sleep(FIRST_SWEEP_DELAY_SECONDS)
    while True:
        stats: dict = {}
        try:
            async with privileged_connection() as conn:
                stats = await run_quality_cycle(conn)
                # The judge (quality/judge_step.py) runs after every
                # mechanical row is written, so a judge that crashes or
                # overspends cannot cost the free measurements; its gates
                # are its own and fail closed. Its failure is one line in
                # the stats: the heartbeat still says the cycle ran.
                try:
                    stats["judge"] = await judge_step(conn, build_info().get("sha"))
                except Exception as exc:  # noqa: BLE001 — never costs the cycle
                    logger.warning("quality cycle: judge failed: %s", exc)
                    stats["judge"] = None
                    stats.setdefault("failures", []).append(
                        f"*.judge: {type(exc).__name__}: {exc}")
            logger.info("quality cycle: %s", _summary(stats))
            if stats.get("failures"):
                logger.warning("quality cycle failures: %s", stats["failures"])
            QUALITY_HEARTBEAT["last_error"] = None
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("quality cycle failed: %s", exc)
            QUALITY_HEARTBEAT["last_error"] = f"{type(exc).__name__}: {exc}"
        # Stamped whether or not anything was written: "ran and found the
        # table missing" and "never ran" are different answers.
        QUALITY_HEARTBEAT["last_cycle_at"] = datetime.now(UTC).isoformat()
        QUALITY_HEARTBEAT["last_stats"] = stats or None
        QUALITY_HEARTBEAT["cycles"] += 1
        await asyncio.sleep(SWEEP_SECONDS)
