#!/usr/bin/env python3
"""Measure the generated stroke library against a per-letter rules table.

The library is a typeface's centreline with order and direction guessed by
rule (`docs/plans/letterform-quality.md`). A rules table — one row per
(script, style, glyph, form), sourced from a teaching model — is the first
yardstick that is not another guess. This prints, per letter, where the
two disagree on the two things a rule can settle: how many strokes, and
where the first one starts.

    python3 scripts/strokes/check_rules.py latin print
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# "baseline-left" and "bottom-left" are the same place to a learner.
ALIAS = {"baseline-left": "bottom-left", "baseline-right": "bottom-right",
         "baseline": "bottom", "bottom": "bottom", "top": "top", "centre": "centre"}


def zone_of(p, box) -> str:
    """Which ninth of the glyph's own ink box a point falls in."""
    x0, y0, x1, y1 = box
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    col = int(min(2, max(0, (p[0] - x0) * 3 // w)))
    row = int(min(2, max(0, (p[1] - y0) * 3 // h)))
    names = [["top-left", "top", "top-right"],
             ["left", "centre", "right"],
             ["bottom-left", "bottom", "bottom-right"]]
    return names[row][col]


def near(a: str, b: str) -> bool:
    """Zones agree if they are the same, or adjacent on one axis — a rule
    says 'top-left' where the ink starts a few units into the middle band
    often enough that exact equality would be noise, not signal."""
    a, b = ALIAS.get(a, a), ALIAS.get(b, b)
    if a == b:
        return True
    grid = {"top-left": (0, 0), "top": (1, 0), "top-right": (2, 0),
            "left": (0, 1), "centre": (1, 1), "right": (2, 1),
            "bottom-left": (0, 2), "bottom": (1, 2), "bottom-right": (2, 2)}
    if a not in grid or b not in grid:
        return False
    (ax, ay), (bx, by) = grid[a], grid[b]
    return abs(ax - bx) + abs(ay - by) <= 1


def main() -> int:
    script = sys.argv[1] if len(sys.argv) > 1 else "latin"
    style = sys.argv[2] if len(sys.argv) > 2 else "print"
    rules_path = ROOT / "scripts" / "strokes" / "rules" / f"{script}-{style}.jsonl"
    if not rules_path.exists():
        print(f"no rules table at {rules_path}")
        return 1
    rules = [json.loads(line) for line in rules_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = json.loads((ROOT / "data" / "strokes" / f"{script}.json").read_text(encoding="utf-8"))
    have = {(g["glyph"], g["form"], g["style"]): g for g in data["glyphs"]}

    count_ok = start_ok = missing = 0
    rows = []
    for r in rules:
        key = (r["glyph"], r["form"], style)
        g = have.get(key)
        if not g:
            missing += 1
            rows.append((r["glyph"], r["form"], "—", len(r["strokes"]), "not in the library", ""))
            continue
        want_n = len(r["strokes"])
        got_n = len(g["strokes"])
        pts = [p for s in g["strokes"] for p in s]
        box = (min(p[0] for p in pts), min(p[1] for p in pts),
               max(p[0] for p in pts), max(p[1] for p in pts))
        got_zone = zone_of(g["strokes"][0][0], box)
        want_zone = r["strokes"][0]["from"]
        n_ok = want_n == got_n
        z_ok = near(want_zone, got_zone)
        count_ok += n_ok
        start_ok += z_ok
        if not (n_ok and z_ok):
            rows.append((r["glyph"], r["form"], got_n, want_n,
                         "" if n_ok else f"strokes {got_n} vs {want_n} taught",
                         "" if z_ok else f"starts {got_zone}, taught {want_zone}"))

    total = len(rules)
    print(f"{script}/{style}: {total} letters with a sourced rule\n")
    print(f"  stroke count agrees : {count_ok}/{total}")
    print(f"  first stroke starts in the taught place : {start_ok}/{total}")
    if missing:
        print(f"  not in the library at all : {missing}")
    if rows:
        print("\n  disagreements:")
        for glyph, form, got, want, a, b in rows:
            print(f"    {glyph} {form:<6} {a}{'; ' if a and b else ''}{b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
