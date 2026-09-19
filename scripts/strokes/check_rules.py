#!/usr/bin/env python3
"""Measure the generated stroke library against a per-letter rules table.

The library is a typeface's centreline with order and direction set by
rule (`docs/plans/letterform-quality.md`). A rules table — one row per
(script, style, glyph, form), written by `ingest_rules.py` from teaching
sources — is the yardstick that is not another guess.

**This scores every stroke of every letter.** The first version scored
only the first stroke, and the owner found three letters it could not
see: uppercase B drawn bowls-first (both orders start top-left, so the
first stroke looked right), lowercase a ending mid-letter going up, and
d starting at the stem instead of the bowl. One stroke out of N, with a
tolerance wide enough to hide a wrong one, is not a check.

Per stroke it asks three things — does it start where the source says,
end where the source says, and run that way round — and the headline
number is **letters where every stroke is right**, because that is the
only figure that means what it sounds like.

    python3 scripts/strokes/check_rules.py latin print
    python3 scripts/strokes/check_rules.py --all
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "scripts" / "strokes" / "rules"

# "baseline-left" and "bottom-left" are the same place to a learner.
ALIAS = {"baseline-left": "bottom-left", "baseline-right": "bottom-right",
         "baseline": "bottom", "bottom": "bottom", "top": "top", "centre": "centre"}

GRID = {"top-left": (0, 0), "top": (1, 0), "top-right": (2, 0),
        "left": (0, 1), "centre": (1, 1), "right": (2, 1),
        "bottom-left": (0, 2), "bottom": (1, 2), "bottom-right": (2, 2)}


def zone_of(p, box) -> str:
    """Which ninth of the glyph's own ink box a point falls in."""
    x0, y0, x1, y1 = box
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    col = int(min(2, max(0, (p[0] - x0) * 3 // w)))
    row = int(min(2, max(0, (p[1] - y0) * 3 // h)))
    names = [["top-left", "top", "top-right"],
             ["left", "centre", "right"],
             ["bottom-left", "bottom", "bottom-right"]]
    return names[row][col]


def near(a: str, b: str) -> bool:
    """Zones agree if they are the same or adjacent on one axis. A rule
    says 'top-left' where the ink starts a few units into the middle band
    often enough that exact equality would be noise, not signal."""
    a, b = ALIAS.get(a, a), ALIAS.get(b, b)
    if a == b:
        return True
    if a not in GRID or b not in GRID:
        return False
    (ax, ay), (bx, by) = GRID[a], GRID[b]
    return abs(ax - bx) + abs(ay - by) <= 1


def heading(a: str, b: str):
    """The direction a taught stroke runs, from its zone names, or None
    when it starts and ends in the same zone (a closed loop says nothing
    about direction)."""
    a, b = ALIAS.get(a or "", a or ""), ALIAS.get(b or "", b or "")
    if a not in GRID or b not in GRID or a == b:
        return None
    (ax, ay), (bx, by) = GRID[a], GRID[b]
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def runs_the_taught_way(stroke, want) -> bool | None:
    """Whether our stroke runs the way the source says. None when the
    source's own zones do not pin a direction down."""
    if want is None:
        return None
    dx, dy = stroke[-1][0] - stroke[0][0], stroke[-1][1] - stroke[0][1]
    n = math.hypot(dx, dy)
    if n < 1:
        return None                      # a closed loop: no direction to judge
    return (dx / n) * want[0] + (dy / n) * want[1] > 0


def judge(glyph: dict, rule: dict) -> dict:
    """Score one letter, stroke by stroke."""
    ours, taught = glyph["strokes"], rule["strokes"]
    pts = [p for s in ours for p in s]
    box = (min(p[0] for p in pts), min(p[1] for p in pts),
           max(p[0] for p in pts), max(p[1] for p in pts))
    out = {"count": len(ours) == len(taught), "strokes": [], "notes": []}
    for i, want in enumerate(taught):
        if i >= len(ours):
            out["strokes"].append(False)
            continue
        s = ours[i]
        a, b = zone_of(s[0], box), zone_of(s[-1], box)
        s_ok = near(want["from"], a)
        e_ok = want.get("to") is None or near(want["to"], b)
        d = runs_the_taught_way(s, heading(want["from"], want.get("to")))
        d_ok = d is not False
        out["strokes"].append(bool(s_ok and e_ok and d_ok))
        if not s_ok:
            out["notes"].append(f"{i + 1} starts {a}, taught {want['from']}")
        if not e_ok:
            out["notes"].append(f"{i + 1} ends {b}, taught {want['to']}")
        if not d_ok:
            out["notes"].append(f"{i + 1} runs the wrong way")
    if not out["count"]:
        out["notes"].insert(0, f"strokes {len(ours)} vs {len(taught)} taught")
    out["all"] = out["count"] and all(out["strokes"])
    return out


def run(script: str, style: str, quiet: bool = False) -> tuple:
    path = RULES / f"{script}-{style}.jsonl"
    if not path.exists():
        print(f"no rules table at {path}")
        return (0, 0, 0, 0, 0)
    rules = [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines() if row.strip()]
    data = json.loads((ROOT / "data" / "strokes" / f"{script}.json").read_text(encoding="utf-8"))
    have = {(g["glyph"], g["form"]): g for g in data["glyphs"] if g["style"] == style}

    n = whole = count_ok = st_ok = st_all = missing = 0
    rows = []
    for r in rules:
        g = have.get((r["glyph"], r["form"]))
        if not g:
            missing += 1
            rows.append((r["glyph"], r["form"], ["not in the library"]))
            continue
        n += 1
        v = judge(g, r)
        count_ok += v["count"]
        whole += v["all"]
        st_ok += sum(v["strokes"])
        st_all += len(r["strokes"])
        if not v["all"]:
            rows.append((r["glyph"], r["form"], v["notes"]))

    if not quiet:
        print(f"{script}/{style}: {n} letters with a sourced rule\n")
        print(f"  every stroke right      : {whole}/{n}")
        print(f"  strokes right           : {st_ok}/{st_all}")
        print(f"  stroke count agrees     : {count_ok}/{n}")
        if missing:
            print(f"  not in the library      : {missing}")
        if rows:
            print("\n  disagreements:")
            for glyph, form, notes in rows:
                print(f"    {glyph} {form:<8} {'; '.join(notes)}")
    return (whole, n, st_ok, st_all, count_ok)


def disagreements() -> int:
    """Print every row where the source itself said the teaching models
    disagree. 216 of the 661 rows carry one and nothing read them until
    the owner queried a letter the note had already explained: d's row
    says, in the model's own words, that it is taught as one continuous
    stroke "to prevent b/d reversal". A rule with a footnote is a rule
    to look at before trusting the number it produced."""
    for f in sorted(RULES.glob("*.jsonl")):
        rows = [json.loads(row) for row in f.read_text(encoding="utf-8").splitlines() if row.strip()]
        flagged = [r for r in rows if (r.get("disagreement") or "").strip()]
        low = [r for r in rows if r.get("confidence") not in ("high", None)]
        print(f"\n{f.stem}: {len(flagged)} of {len(rows)} rows carry a "
              f"disagreement, {len(low)} are not high confidence")
        for r in flagged:
            mark = "" if r.get("confidence") in ("high", None) else f" [{r['confidence']}]"
            print(f"  {r['glyph']} {r['form']:<9}{mark} {r['disagreement']}")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--disagreements" in sys.argv[1:]:
        return disagreements()
    if "--all" in sys.argv[1:]:
        tw = tn = ts = tsa = tc = 0

        def line(table, right, strokes, count):
            print(f"{table:<22} {right:<12} {strokes:<14} {count}")

        line("table", "all right", "strokes", "count")
        for f in sorted(RULES.glob("*.jsonl")):
            script, style = f.stem.rsplit("-", 1)
            w, n, s, sa, c = run(script, style, quiet=True)
            tw += w
            tn += n
            ts += s
            tsa += sa
            tc += c
            line(f"{script} {style}", f"{w}/{n}", f"{s}/{sa}", f"{c}/{n}")
        line("TOTAL", f"{tw}/{tn}", f"{ts}/{tsa}", f"{tc}/{tn}")
        return 0
    run(args[0] if args else "latin", args[1] if len(args) > 1 else "print")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
