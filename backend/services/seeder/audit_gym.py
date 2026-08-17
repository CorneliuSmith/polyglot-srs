"""How full the Gym actually is, per language, on three axes.

The complaint this answers is that the English Gym reads as poor "by name and
by fullness" beside Portuguese. Measured, the diagnosis inverts the obvious
fix: the biggest gap is not missing content, it is existing content the Gym
never shows. English drills 43 grammar points and its picker offers 12, and the
31 it hides are the passive, do-support, relative clauses, reported speech, the
conditionals, inversion and cleft sentences — precisely the forms whose absence
makes the menu look shallow. Nothing measured that drift, so it accumulated
quietly as manifests were authored at different moments with different ambition.

Three axes:

  BREADTH — a grammar point that has drills but no manifest entry is invisible.
            A deliberate omission is fine, but it has to be a decision: put
            {"point": "...", "excluded": "reason"} in the manifest and it stops
            counting as hidden.
  DEPTH   — drills per exposed form against a floor. Ten is one full default
            session on a single form with no repeats; A1 forms take the most
            traffic and get twelve.
  COPY    — an entry with no label, usage or example is a picker row that
            cannot say what it is. Plus dangling entries, whose "point" matches
            no grammar point at all: those resolve to nothing at request time
            and silently show the learner an empty form.

Usage:
    python -m backend.services.seeder.audit_gym
    python -m backend.services.seeder.audit_gym --language en --detail
    python -m backend.services.seeder.audit_gym --json out.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# backend/services/seeder/audit_gym.py -> repo root.
REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
GRAMMAR_DIR = DATA / "grammar"
GYM_DIR = DATA / "gym"

LANGUAGES = tuple(
    "ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko "
    "la id tl he fa".split()
)

# A form with fewer drills than this cannot fill one session without repeating.
FLOOR = 10
FLOOR_A1 = 12
# Below this a point is a stub rather than a drillable form, so its absence from
# the picker is not the drift this module is looking for.
DRILLED_AT_LEAST = 6


def load_grammar(code: str) -> list[dict] | None:
    path = GRAMMAR_DIR / f"{code}_grammar.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("points", []) if isinstance(data, dict) else data


def load_manifest(code: str) -> dict | None:
    path = GYM_DIR / f"{code}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _entries(manifest: dict | None):
    """(column_kind, entry) for every row in the picker."""
    for column in (manifest or {}).get("columns", []) or []:
        for entry in column.get("entries", []) or []:
            yield column.get("kind"), entry


def audit_language(code: str) -> dict:
    points = load_grammar(code)
    manifest = load_manifest(code)

    if points is None:
        return {"code": code, "state": "no grammar file"}
    by_title = {(p.get("title") or "").strip(): p for p in points}
    drill_counts = {
        title: len(point.get("drills") or []) for title, point in by_title.items()
    }
    levels = {title: point.get("level") for title, point in by_title.items()}

    if manifest is None:
        # Distinct from "a manifest that shows nothing": seven languages have no
        # Gym at all, and reporting them as 0% coverage would read as a
        # regression rather than a feature that was never switched on.
        drilled = [t for t, n in drill_counts.items() if n >= DRILLED_AT_LEAST]
        return {
            "code": code,
            "state": "no manifest",
            "points": len(points),
            "drilled_points": len(drilled),
            "shown": 0,
            "hidden": sorted(drilled),
            "excluded": [],
            "dangling": [],
            "thin_forms": [],
            "incomplete_copy": [],
            "deficit": 0,
        }

    shown, excluded, dangling, thin, incomplete = [], [], [], [], []
    for kind, entry in _entries(manifest):
        title = (entry.get("point") or "").strip()
        if entry.get("excluded"):
            excluded.append({"point": title, "reason": entry["excluded"]})
            continue
        if title not in by_title:
            # Resolved to ids at request time, so a title that matches nothing
            # is not a typo the learner never sees — it is an empty picker row.
            dangling.append({"point": title, "column": kind})
            continue
        shown.append(title)
        n = drill_counts[title]
        floor = FLOOR_A1 if levels.get(title) == "A1" else FLOOR
        if n < floor:
            thin.append(
                {"point": title, "level": levels.get(title), "drills": n, "floor": floor}
            )
        missing = [f for f in ("label", "usage", "example") if not (entry.get(f) or "").strip()]
        if missing:
            incomplete.append({"point": title, "missing": missing})

    exposed = set(shown)
    excluded_titles = {e["point"] for e in excluded}
    hidden = sorted(
        title
        for title, n in drill_counts.items()
        if n >= DRILLED_AT_LEAST and title not in exposed and title not in excluded_titles
    )

    return {
        "code": code,
        "state": "ok",
        "points": len(points),
        "drilled_points": sum(1 for n in drill_counts.values() if n >= DRILLED_AT_LEAST),
        "shown": len(shown),
        "hidden": hidden,
        "excluded": excluded,
        "dangling": dangling,
        "thin_forms": thin,
        "incomplete_copy": incomplete,
        "deficit": sum(row["floor"] - row["drills"] for row in thin),
    }


def audit_all(codes=LANGUAGES) -> list[dict]:
    return [audit_language(code) for code in codes]


def print_report(reports: list[dict]) -> None:
    print("Gym fullness. A hidden point has drills but no picker entry;")
    print(f"a thin form has fewer than {FLOOR} drills ({FLOOR_A1} at A1).\n")
    print(
        f"{'lang':<6}{'state':<14}{'shown':>7}{'hidden':>8}{'dangling':>10}"
        f"{'thin':>7}{'no copy':>9}{'deficit':>9}"
    )
    print("-" * 70)
    for report in sorted(reports, key=lambda r: -len(r.get("hidden", []))):
        if report["state"] == "no grammar file":
            print(f"{report['code']:<6}{'no grammar':<14}")
            continue
        print(
            f"{report['code']:<6}{report['state']:<14}{report['shown']:>7}"
            f"{len(report['hidden']):>8}{len(report['dangling']):>10}"
            f"{len(report['thin_forms']):>7}{len(report['incomplete_copy']):>9}"
            f"{report['deficit']:>9}"
        )
    usable = [r for r in reports if r["state"] != "no grammar file"]
    print("-" * 70)
    print(
        f"{'all':<6}{'':<14}{sum(r['shown'] for r in usable):>7}"
        f"{sum(len(r['hidden']) for r in usable):>8}"
        f"{sum(len(r['dangling']) for r in usable):>10}"
        f"{sum(len(r['thin_forms']) for r in usable):>7}"
        f"{sum(len(r['incomplete_copy']) for r in usable):>9}"
        f"{sum(r['deficit'] for r in usable):>9}"
    )
    missing = [r["code"] for r in usable if r["state"] == "no manifest"]
    if missing:
        print(
            f"\nNo Gym manifest at all: {', '.join(missing)}."
            "\nThat is a feature never switched on, not a regression — but for a"
            "\nlanguage whose whole difficulty is paradigms it is the first thing"
            "\na learner goes looking for."
        )


def print_language_detail(report: dict, limit: int = 40) -> None:
    print(f"\n=== {report['code']} ===")
    for label, rows in (
        ("hidden (drilled, not in the picker)", report.get("hidden", [])),
        ("dangling (entry resolves to no point)", report.get("dangling", [])),
        ("thin (below floor)", report.get("thin_forms", [])),
        ("incomplete copy", report.get("incomplete_copy", [])),
        ("excluded on purpose", report.get("excluded", [])),
    ):
        if not rows:
            continue
        print(f"\n  {label}: {len(rows)}")
        for row in rows[:limit]:
            print(f"    {row}" if not isinstance(row, str) else f"    {row}")
        if len(rows) > limit:
            print(f"    … {len(rows) - limit} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m backend.services.seeder.audit_gym",
        description="Report Gym breadth, depth and picker copy per language.",
    )
    parser.add_argument("--language", "-l", help="audit one language instead of all 27")
    parser.add_argument("--json", dest="json_out", help="write the full report to this path")
    parser.add_argument("--detail", action="store_true", help="list the findings for --language")
    args = parser.parse_args(argv)

    if args.language and args.language not in LANGUAGES:
        parser.error(f"unknown language {args.language!r}; known: {' '.join(LANGUAGES)}")

    codes = (args.language,) if args.language else LANGUAGES
    reports = audit_all(codes)
    print_report(reports)
    if args.detail and args.language:
        print_language_detail(reports[0])

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(reports, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {args.json_out}")

    # Reporting only for now. The gym-coverage plan turns the floor into a CI
    # gate once the exposure pass has landed; failing today would just wall off
    # the languages this is meant to help.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
