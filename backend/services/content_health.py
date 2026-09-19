"""Content Health: turn the quality loop's rows into one course row the panel
can colour (docs/plans/quality-guardrails-telemetry.md §6, phase B).

Everything here is arithmetic over dicts and is deliberately free of the
database and the router, so the status rules can be tested one branch at a
time without a client. The router (`routers/contribute.py`, the
`/admin/content-health*` family) fetches `latest_metrics`, the targets, the
baseline and the open-verdict counts and hands them in; this module says
what they mean.

Two things worth knowing before changing a number:

* **None is a value, not a zero.** A course the loop has never measured has
  no bad-card share, not a share of zero, and a judge that has judged
  nothing has no flag rate. Every percentage here is None when its
  population is missing or zero, and every comparison against a target
  tests for None first — a `0 > 15` that reads as green for an unmeasured
  course is the false comfort the panel exists to remove.
* **"Audit fails" means the fail-level rules only.** The loop writes every
  rule in `audit_content.ALL_RULES`, but `data/quality/baseline.json` only
  ratchets `FAIL_RULES`; summing warn and report counts against a baseline
  of zero would paint every course red for having a gender-marking
  statistic. The per-rule list in the drill-down carries the others with
  `baseline: null`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from backend.services.quality.audit_content import FAIL_RULES

# A verdict counts as a flag at this confidence and above (plan §6: "judge-
# flagged, per question, confidence >= 0.7"). The same threshold J5 uses to
# route a verdict into a queue, so the panel and the queue agree on what a
# flag is.
# A Decimal, not the float 0.7: asyncpg encodes a float bound to `numeric` as
# Decimal(float), so `>= 0.7` would reach Postgres as 0.69999999999999995559…
# `judge_step.FLAG_CONFIDENCE` is the same value for the same reason, and
# test_content_health pins the two together — the panel's SQL and the ledger's
# Python must call the same rows flagged.
FLAG_CONFIDENCE = Decimal("0.7")

# The metric the coverage step writes: value = words in the top band with a
# blankable sentence, population = the band.
COVERAGE_METRIC = "blankable_top_band"
# Below this share of the top band covered a course is amber (plan §6,
# "Top-1,000 covered: >= 95 green").
COVERED_AMBER_PCT = 95

STATUS_ORDER = ("red", "amber", "green", "grey")

# The reconcile survey's columns, in the order the deploy panel shows them.
# Pinned to `quality_loop.RECONCILE_METRICS` plus `gone_with_cards` by
# test_content_health; written out here so the deploy endpoint's shape is
# the contract's and not whatever the loop happens to write.
RECONCILE_FIELDS = (
    "gone", "gone_with_cards", "new", "gloss", "pos",
    "retire", "unretire", "gp_retire", "no_translation",
)

# "Calibrated" has exactly one definition, and it is the one the judge spends
# on: `data/eval/calibrated.json`, read by `content_judge.calibrated_pairs()`,
# which the nightly step gates every (question, course) pair against. The panel
# must not have a second opinion — a constant here read `false` for
# `register`/`ar`, the one pair being judged and billed, which is the worst
# possible row to label "not calibrated".
#
# It is a PAIR, not a question: a gold set is labelled in one course, and
# `register` being calibrated on Arabic says nothing about Persian. The status
# rule still does NOT consult it — an uncalibrated flag rate above the target
# reads red, because the owner switches the judge on per course and sets that
# target themselves; `calibrated` is the label that tells them how to read the
# number.


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def pct(part, whole) -> float | None:
    """100 * part / whole, or None when there is nothing to divide by.
    Never 0.0 for an empty population: that would read as "measured, and
    perfect"."""
    if part is None or not whole:
        return None
    return 100.0 * float(part) / float(whole)


def _latest(dt_a, dt_b):
    if dt_a is None:
        return dt_b
    if dt_b is None:
        return dt_a
    return max(dt_a, dt_b)


def question_positives(questions: dict) -> dict[str, frozenset[str]]:
    """{question name: the verdicts that count as a finding}, from the judge's
    registry — so the flagged count uses the same definition of "positive"
    the gold-set gates do."""
    return {name: frozenset(q.positive) for name, q in questions.items()}


def baseline_for(baseline: dict[str, int], code: str) -> dict[str, int]:
    """This course's ratchet, one entry per fail-level rule. A missing key is
    zero, as `audit_content.load_baseline` documents — a rule the baseline
    has never recorded has no debt to forgive."""
    return {rule: int(baseline.get(f"{code}.{rule}", 0)) for rule in FAIL_RULES}


def _own(metrics: dict) -> list[dict]:
    """The course's own rows: `latest_metrics` keys a support-locale row as
    "<locale>:<metric>" and marks it with `locale`; the course row is built
    from the unmarked ones only (plan §3, principle 6)."""
    return [m for m in metrics.values() if m.get("locale") is None]


def derive_course(
    metrics: dict,
    targets: dict,
    baseline_for_course: dict[str, int],
    flagged_by_question: dict[str, int],
    questions: dict,
    code: str = "",
    calibrated: set[tuple[str, str]] | None = None,
) -> dict:
    """One course's row, minus its identity (the router adds code, name and
    language_id).

    `metrics` is `latest_metrics(conn)[language_id]` — the newest row per
    metric with its kind, value, population and run_at. `targets` is the
    course's `language_quality_targets` row or the defaults.
    `flagged_by_question` is the open, confident, positive verdict count per
    question. `questions` is `content_judge.QUESTIONS`, so the judge block
    always has one entry per question, judged or not. `code` and `calibrated`
    are the course's code and `content_judge.calibrated_pairs()`; without them
    every question reads uncalibrated, which is the safe direction for a label
    that tells a reader how much to trust a rate.
    """
    pairs = calibrated or set()
    own = _own(metrics)
    coverage = next(
        (m for m in own if m["kind"] == "coverage" and m["metric"] == COVERAGE_METRIC), None,
    )
    bad_card_pct = top_band_covered_pct = None
    if coverage is not None and coverage.get("population"):
        population = coverage["population"]
        bad_card_pct = pct(population - coverage["value"], population)
        top_band_covered_pct = pct(coverage["value"], population)

    audit = {m["metric"]: m for m in own if m["kind"] == "audit"}
    fail_rows = [audit[rule] for rule in FAIL_RULES if rule in audit]
    audit_fails = audit_fail_delta = None
    if fail_rows:
        audit_fails = sum(int(m["value"]) for m in fail_rows)
        audit_fail_delta = sum(
            int(m["value"]) - baseline_for_course.get(m["metric"], 0) for m in fail_rows
        )

    judge: dict[str, dict] = {}
    for name in questions:
        cov = next(
            (m for m in own if m["kind"] == "coverage" and m["metric"] == f"judge.{name}"),
            None,
        )
        judged = int(cov["value"]) if cov is not None else 0
        population = int(cov["population"] or 0) if cov is not None else 0
        flagged = int(flagged_by_question.get(name, 0))
        judge[name] = {
            "judged": judged,
            "population": population,
            "judged_pct": pct(judged, population),
            "flagged": flagged,
            "flag_pct": pct(flagged, judged),
            "calibrated": (name, code) in pairs,
        }

    queues = {m["metric"]: int(m["value"]) for m in own if m["kind"] == "queues"}

    reconcile_rows = [m for m in own if m["kind"] == "reconcile"]
    reconcile: dict = {m["metric"]: int(m["value"]) for m in reconcile_rows}
    reconcile_at = None
    for m in reconcile_rows:
        reconcile_at = _latest(reconcile_at, m.get("run_at"))
    reconcile["run_at"] = _iso(reconcile_at)

    last_audited = last_judged = None
    for m in own:
        if m["kind"] == "audit":
            last_audited = _latest(last_audited, m.get("run_at"))
        elif m["kind"] == "judge":
            last_judged = _latest(last_judged, m.get("run_at"))

    course = {
        "targets": {
            "judge_enabled": bool(targets.get("judge_enabled", False)),
            "max_bad_card_pct": targets.get("max_bad_card_pct"),
            "max_judge_flag_pct": targets.get("max_judge_flag_pct"),
        },
        "bad_card_pct": bad_card_pct,
        "top_band_covered_pct": top_band_covered_pct,
        "audit_fail_delta": audit_fail_delta,
        "audit_fails": audit_fails,
        "judge": judge,
        "queues": queues,
        "reconcile": reconcile,
        "last_audited": _iso(last_audited),
        "last_judged": _iso(last_judged),
    }
    course["status"] = status_of(course, measured=bool(metrics))
    return course


def status_of(course: dict, *, measured: bool = True) -> str:
    """grey: never measured. red: bad cards over target, any judge flag rate
    over target, or audit fails above the baseline. amber: under 95 percent
    of the top band covered. green otherwise — including a course whose
    numbers are all None but which has SOME row, because "measured, nothing
    wrong yet" is what a fresh course looks like on its first night."""
    if not measured:
        return "grey"
    targets = course.get("targets") or {}
    bad = course.get("bad_card_pct")
    max_bad = targets.get("max_bad_card_pct")
    if bad is not None and max_bad is not None and bad > max_bad:
        return "red"
    max_flag = targets.get("max_judge_flag_pct")
    for entry in (course.get("judge") or {}).values():
        rate = entry.get("flag_pct")
        if rate is not None and max_flag is not None and rate > max_flag:
            return "red"
    delta = course.get("audit_fail_delta")
    if delta is not None and delta > 0:
        return "red"
    covered = course.get("top_band_covered_pct")
    if covered is not None and covered < COVERED_AMBER_PCT:
        return "amber"
    return "green"


def sort_key(course: dict) -> tuple[int, str]:
    """Worst first, then by code — the order the owner's course table reads in."""
    status = course.get("status", "grey")
    rank = STATUS_ORDER.index(status) if status in STATUS_ORDER else len(STATUS_ORDER)
    return (rank, course.get("code") or "")


# ---------------------------------------------------------------------------
# The drill-down
# ---------------------------------------------------------------------------


def audit_rows(metrics: dict, baseline_for_course: dict[str, int]) -> list[dict]:
    """Every audit rule the loop last wrote for this course, with its
    baseline and delta where the rule is ratcheted (fail-level) and null
    where it is only counted (warn and report)."""
    out = []
    for m in _own(metrics):
        if m["kind"] != "audit":
            continue
        rule = m["metric"]
        value = int(m["value"])
        base = baseline_for_course.get(rule) if rule in FAIL_RULES else None
        out.append({
            "rule": rule,
            "value": value,
            "baseline": base,
            "delta": (value - base) if base is not None else None,
            "population": m.get("population"),
        })
    out.sort(key=lambda r: r["rule"])
    return out


def bad_card_trend(rows: list[dict]) -> list[dict]:
    """`trend()` rows for the coverage metric as a bad-card share over time.
    A row without a population has no share and is left out rather than
    plotted as null."""
    out = []
    for r in rows:
        share = pct((r["population"] or 0) - r["value"], r["population"]) \
            if r.get("population") else None
        if share is not None:
            out.append({"run_at": _iso(r["run_at"]), "value": share})
    return out


def flag_trend(rows: list[dict]) -> list[dict]:
    """`trend()` rows for a `flagged.<question>` metric as a flag rate:
    value flagged out of population judged."""
    out = []
    for r in rows:
        rate = pct(r["value"], r.get("population"))
        if rate is not None:
            out.append({"run_at": _iso(r["run_at"]), "value": rate})
    return out


def deploy_row(language: dict, latest: dict) -> dict:
    """One course's line in the deployment panel's Content section: the last
    reconcile survey's counts, every field present (0 when the survey did
    not write that metric), with when it ran and against which build."""
    counts = latest.get("metrics") or {}
    row = {
        "code": language["code"],
        "name": language["name"],
        "run_at": _iso(latest.get("run_at")),
        "build_sha": latest.get("build_sha"),
    }
    for field in RECONCILE_FIELDS:
        row[field] = int(counts.get(field, 0))
    return row
