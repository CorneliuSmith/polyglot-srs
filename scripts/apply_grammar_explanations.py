#!/usr/bin/env python3
"""Export grammar explanations for an editorial pass, and apply what comes back.

`docs/plans/markdown-explanations.md` is the brief. Since PR #394 an
explanation that carries markdown RENDERS as markdown on the card
(`ExplanationView` routes a block with bold, a list, a table, code or a
link through `CardMarkdown`); the 1,378 texts in `data/grammar/*.json`
carry none. Turning them into good markdown is not a migration — nothing
mechanical decides what deserves bold — so it is an editorial read, one
course at a time, done in-session (the programme never spends the API key).

This script is the two halves around that read, the same shape as
`apply_drill_glosses.py` and `apply_authored_sentences.py`:

    python -m scripts.apply_grammar_explanations --export tr --out tr.json
    python -m scripts.apply_grammar_explanations --apply tr.edited.json

The apply half is a GATE, not a writer that trusts its input. What it
refuses, and why each rule exists rather than being obvious:

- **A heading.** `CardMarkdown`'s sanitiser has no `h1`-`h6` in `tagNames`,
  so `## Forms` reaches the renderer, flips the block to markdown, and then
  loses its own tag. The card title is the heading (house style).
- **An image, a rule, raw HTML, a non-http link.** Same reason: not in the
  allow-list, so it is silently dropped or printed literally. `clean_markdown`
  (the server's cleaner, which runs on the way in) must be a no-op on the
  text, or the text is carrying something production would strip anyway.
- **A malformed table.** A GFM table whose rows disagree with its header
  renders as a paragraph of pipes — worse than the plain text it replaced.
- **`___` inside a markdown block.** That is how cards write a blank
  ("I live in ___"). Outside a markdown block it is literal; inside one GFM
  reads it as emphasis and the blank disappears.
- **A text that shares nothing with the one it replaces.** An editorial pass
  rewrites; it does not swap one point's explanation for another's, which is
  what an off-by-one in the export/apply round trip looks like.
- **A text that grew past 3x or shrank below 40%.** Formatting does not
  triple a paragraph, and a truncation is silent otherwise.

Nothing here decides taste. It decides that what came back can be rendered.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.services.markdown import clean_markdown  # noqa: E402

GRAMMAR = REPO / "data" / "grammar"

# Mirrors `hasMarkdown` in frontend/src/components/ExplanationView.tsx — the
# signals that flip a block from the typesetter to the markdown renderer.
MARKDOWN = (
    re.compile(r"`[^`\n]+`"),
    re.compile(r"\*\*[^*\n]+\*\*"),
    re.compile(r"(^|\n)\s*([-*+]|\d+\.)\s+"),
    re.compile(r"(^|\n)\s*\|.*\|"),
    re.compile(r"(^|\n)#{1,3}\s"),
    re.compile(r"\[[^\]]+\]\([^)]+\)"),
)
_HEADING = re.compile(r"(^|\n)\s*#{1,6}\s")
_IMAGE = re.compile(r"!\[[^\]]*\]\(")
_RULE = re.compile(r"(^|\n)\s*([-*_])\s*\2\s*\2[\s\2]*(\n|$)")
_BLANK = re.compile(r"_{2,}")
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)

MAX_GROWTH = 3.0
MIN_SHRINK = 0.4


def has_markdown(text: str) -> bool:
    """Would the card render this block as markdown?"""
    return any(rx.search(text) for rx in MARKDOWN)


def _blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]


def _table_is_well_formed(block: str) -> bool:
    rows = [ln for ln in block.split("\n") if ln.strip().startswith("|")]
    if not rows:
        return True
    if len(rows) < 3:
        return False                      # header, separator, at least one row
    widths = {len(ln.strip().strip("|").split("|")) for ln in rows}
    return len(widths) == 1


def check(old: str, new: str) -> str | None:
    """Why *new* cannot replace *old*, or None when it can."""
    new = (new or "").strip()
    old = (old or "").strip()
    if not new:
        return "empty"
    if clean_markdown(new) != new:
        return "raw HTML or an unsafe link destination"
    if _HEADING.search(new):
        return "a heading — the renderer has no heading tag; the title is the heading"
    if _IMAGE.search(new):
        return "an image — a card never fetches from elsewhere"
    if _RULE.search(new):
        return "a horizontal rule — not in the renderer's allow-list"
    for block in _blocks(new):
        if not _table_is_well_formed(block):
            return "a table whose rows disagree with its header"
        if has_markdown(block) and _BLANK.search(block):
            return "a ___ blank inside a markdown block — GFM reads it as emphasis"
    if old:
        if len(new) > len(old) * MAX_GROWTH:
            return f"{len(new) / len(old):.1f}x longer than the text it replaces"
        if len(new) < len(old) * MIN_SHRINK:
            return f"{len(new) / len(old):.0%} of the text it replaces — truncated?"
        if not (set(_WORD.findall(old.lower())) & set(_WORD.findall(new.lower()))):
            return "shares no word with the text it replaces — wrong point?"
    return None


def load(code: str) -> tuple[Path, dict | list, list[dict]]:
    path = GRAMMAR / f"{code}_grammar.json"
    if not path.exists():
        raise SystemExit(f"no grammar file for {code!r}")
    data = json.loads(path.read_text(encoding="utf-8"))
    points = data["points"] if isinstance(data, dict) else data
    return path, data, points


def export(code: str, out: Path | None) -> int:
    _, _, points = load(code)
    tasks = [
        {
            "code": code,
            "index": i,
            "title": p.get("title"),
            "level": p.get("level"),
            "function": p.get("function"),
            "explanation": p.get("explanation") or "",
        }
        for i, p in enumerate(points)
        if (p.get("explanation") or "").strip()
    ]
    blob = json.dumps({"code": code, "points": tasks}, ensure_ascii=False, indent=1)
    if out:
        out.write_text(blob + "\n", encoding="utf-8")
        print(f"{code}: {len(tasks)} explanations -> {out}")
    else:
        print(blob)
    return 0


def apply(paths: list[Path], dry_run: bool) -> int:
    edits: dict[str, dict[int, str]] = {}
    rejected: Counter = Counter()
    seen = 0
    for path in paths:
        blob = json.loads(path.read_text(encoding="utf-8"))
        code = blob["code"]
        _, _, points = load(code)
        for task in blob.get("points", []):
            seen += 1
            i = task.get("index")
            if not isinstance(i, int) or not 0 <= i < len(points):
                rejected["index out of range"] += 1
                continue
            point = points[i]
            if task.get("title") and task["title"] != point.get("title"):
                rejected["title does not match the point at that index"] += 1
                continue
            old = point.get("explanation") or ""
            new = (task.get("explanation") or "").strip()
            if new == old.strip():
                continue                       # nothing to do, not a rejection
            why = check(old, new)
            if why:
                rejected[why] += 1
                continue
            edits.setdefault(code, {})[i] = new

    total = sum(len(v) for v in edits.values())
    print(f"read {seen:,} · accepted {total:,} · "
          f"rejected {dict(rejected) or 'none'}")
    if dry_run or not total:
        if dry_run:
            print("DRY RUN — nothing written.")
        return 0

    for code, per_point in sorted(edits.items()):
        path, data, points = load(code)
        raw = path.read_text(encoding="utf-8")
        indent_match = re.search(r"\n( +)\"", raw)
        indent = len(indent_match.group(1)) if indent_match else 2
        for i, text in per_point.items():
            points[i]["explanation"] = text
        out = json.dumps(data, ensure_ascii=False, indent=indent)
        if raw.endswith("\n"):
            out += "\n"
        path.write_text(out, encoding="utf-8")
        formatted = sum(
            1 for p in points if has_markdown(p.get("explanation") or "")
        )
        print(f"  {code}: {len(per_point)} rewritten, "
              f"{formatted}/{len(points)} explanations now render as markdown")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", metavar="CODE")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--apply", nargs="+", type=Path, default=[])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.export:
        return export(args.export, args.out)
    if args.apply:
        return apply(args.apply, args.dry_run)
    ap.error("give --export CODE or --apply FILE…")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
