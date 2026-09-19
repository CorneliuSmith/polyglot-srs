#!/usr/bin/env python3
"""Merge a run of handwriting rules into the per-script rules tables.

The teaching model answers one run at a time (docs/quality/letterforms/
gemini-brief.md) and its rows arrive as pasted JSONL. This normalises a
paste and merges it into `rules/{script}-{style}.jsonl`, then says what
changed. Each run is a few dozen rows and there are ten of them, so this
is a command rather than a fresh throwaway script per paste.

    python3 scripts/strokes/ingest_rules.py <paste.jsonl> [--force]

What it normalises, all of it drift the model has actually produced:

- `letter` -> `glyph`, the key the brief asks for and the library uses.
- Sources wrapped as `[real](google-redirect?utm_source=gemini)`: the
  real URL is kept and the tracking parameter dropped.
- An uppercase row is filed under its lowercase glyph plus form "upper",
  because the library keys a form on the lowercase letter.
- The summary line (`summary`, or the `run_complete` shape the model
  emits instead) is not a rule and is reported, not stored.

What it refuses rather than guesses:

- A row with no source. The brief says a rule with no source is worthless
  and should be omitted; storing it anyway would launder a guess.
- A row that would overwrite an existing one *from a different source*.
  This is not hypothetical: a Turkish row for "I" is the capital of
  DOTLESS ı — Turkish pairs i-İ and ı-I, everyone else i-I — and filing
  it under i/upper silently replaced the row for the letter every other
  Latin course writes. A same-source replacement is a correction and goes
  through; a cross-source one stops and asks. `--force` takes the new row.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "scripts" / "strokes" / "rules"
HEAD = ("script", "style", "glyph", "form")


def clean_source(s: str | None) -> str | None:
    if not s:
        return None
    m = re.match(r"^\[(.+?)\]\((.*)\)$", s.strip())
    if m:
        s = m.group(1)
    s = re.sub(r"[?&]utm_source=[^&\s]*", "", s)
    return s.strip() or None


def domain(url: str | None) -> str:
    return urlsplit(url or "").netloc.lower().removeprefix("www.")


def order(r: dict):
    g = r["glyph"]
    return (0 if g.isascii() else 1, unicodedata.normalize("NFD", g)[0], g,
            r.get("form") != "lower")


def normalise(raw: dict) -> dict | None:
    r = dict(raw)
    g = r.pop("letter", None) or r.pop("glyph", None)
    if not g:
        return None
    form = r.get("form") or "letter"
    if form == "upper" and len(g.lower()) == 1:
        g = g.lower()
    r["glyph"], r["form"] = g, form
    r["source"] = clean_source(r.get("source"))
    rest = {k: v for k, v in r.items() if k not in HEAD}
    return {**{k: r.get(k) for k in HEAD}, **rest}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    lines = Path(args[0]).read_text(encoding="utf-8").splitlines()

    rows, summaries, bad = [], [], []
    for n, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            bad.append(f"line {n}: not JSON ({e.msg})")
            continue
        if "summary" in raw or "run_complete" in raw:
            summaries.append(raw)
            continue
        r = normalise(raw)
        if r is None:
            bad.append(f"line {n}: no glyph")
        elif not r.get("source"):
            bad.append(f"line {n}: {raw.get('letter') or raw.get('glyph')} has no source — dropped")
        elif not r.get("strokes"):
            bad.append(f"line {n}: {r['glyph']} has no strokes — dropped")
        else:
            rows.append(r)

    by_table: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_table.setdefault((r["script"], r["style"]), []).append(r)

    held = []
    for (script, style), new in sorted(by_table.items()):
        path = RULES / f"{script}-{style}.jsonl"
        have = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    old = json.loads(line)
                    have[(old["glyph"], old["form"])] = old
        added = replaced = same = 0
        for r in new:
            key = (r["glyph"], r["form"])
            old = have.get(key)
            if old is None:
                have[key] = r
                added += 1
            elif old == r:
                same += 1
            elif domain(old.get("source")) != domain(r.get("source")) and not force:
                held.append((script, style, key, domain(old.get("source")), domain(r.get("source"))))
            else:
                have[key] = r
                replaced += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(have[k], ensure_ascii=False) + "\n"
                                for k in sorted(have, key=lambda k: order(have[k]))),
                        encoding="utf-8")
        print(f"{script}/{style}: +{added} new, {replaced} replaced, {same} unchanged"
              f" — {len(have)} rows in {path.relative_to(ROOT)}")

    if bad:
        print("\ndropped:")
        for b in bad:
            print("  " + b)
    if held:
        print("\nheld back — same letter, a different source (pass --force to take the new row):")
        for script, style, (g, form), a, b in held:
            print(f"  {script}/{style} {g} {form}: have {a}, offered {b}")
    for s in summaries:
        print("\nthe run said:", json.dumps(s, ensure_ascii=False)[:400])

    # One URL standing in for dozens of letters is the model falling back on
    # a publisher's front page; the brief asks for the page that shows the
    # letter being written.
    per = Counter(r["source"] for r in rows)
    for url, n in per.most_common(3):
        if n >= 10:
            print(f"\nthin sourcing: {n} rows cite {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
