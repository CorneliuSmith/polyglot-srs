#!/usr/bin/env python3
"""Validate structural glosses from a workflow journal and write them in.

Workflow output arrives as a task file OR, when that comes back empty, as the
run's journal.jsonl — which has held the full result every time the task file
did not. This reads either, gates every gloss, and writes only what passes.

The gate is the point. An agent's gloss is a proposal; these are the rules a
proposal has to satisfy before it reaches a learner:

  cells == tokens     one cell per whitespace token, joined by " · ".
  one blank           exactly one "___", sitting on the {{answer}} token.
  no leak             the answer appears in no cell, compared on the FOLDED
                      form (case and combining marks stripped) at both
                      granularities — whole hyphenated tokens and their parts.
  decomposes          at least one cell differs from the token above it. A
                      line where every cell echoes its own token teaches
                      nothing; on English that is the whole failure mode.

Usage:
    python scripts/apply_drill_glosses.py <journal.jsonl|task.output> [more...]
    python scripts/apply_drill_glosses.py --dry-run <path>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GRAMMAR = REPO / "data" / "grammar"
_WORD = re.compile(r"[\w'’-]+", re.UNICODE)


def fold(text: str) -> str:
    """Case-folded, mark-stripped skeleton. Category M*, not combining()>0:
    the Devanagari vowel sign is Mc with combining class zero, and Python's
    \\w drops it — so folding on combining() lets रही through as रह."""
    text = unicodedata.normalize("NFD", (text or "").casefold())
    return "".join(c for c in text if not unicodedata.category(c).startswith("M"))


def harvest(paths: list[Path]) -> dict[str, str]:
    """{key: gloss} from journals and/or task outputs. Later fixes win."""
    glosses: dict[str, str] = {}
    fixes: dict[str, str] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        blobs = []
        if path.suffix == ".jsonl":
            blobs = [json.loads(x) for x in text.splitlines() if x.strip()]
            blobs = [b.get("result") for b in blobs if b.get("type") == "result"]
        else:
            whole = json.loads(text)
            blobs = [whole.get("result", whole)]
        for b in blobs:
            if not isinstance(b, dict):
                continue
            if isinstance(b.get("glosses"), list):
                for g in b["glosses"]:
                    glosses[g["k"]] = g["gloss"]
            if isinstance(b.get("fixes"), list):
                for f in b["fixes"]:
                    fixes[f["k"]] = f["gloss"]
            # a plain {key: gloss} map (what the workflow returns at the end)
            if not b.get("glosses") and not b.get("fixes"):
                for k, v in b.items():
                    if isinstance(v, str) and ":" in k:
                        glosses[k] = v
    glosses.update(fixes)
    return glosses


def check(gloss: str, sentence: str, answer: str) -> str | None:
    """The reason to refuse *gloss*, or None when it may be written."""
    cells = [c.strip() for c in gloss.split("·")]
    tokens = sentence.split()
    if len(cells) != len(tokens):
        return "cell count != token count"
    if gloss.count("___") != 1:
        return "not exactly one blank"
    blank = cells.index("___") if "___" in cells else -1
    if blank < 0 or "{{answer}}" not in tokens[blank]:
        return "blank is not on the answer token"
    seen: set[str] = set()
    for tok in _WORD.findall(fold(gloss)):
        seen.add(tok)
        seen.update(p for p in re.split(r"[-'’.]", tok) if p)
    if fold(answer).strip() in seen:
        return "gloss contains the answer"
    if all(c == "___" for c in cells):
        # A one-token sentence glossed as a bare blank. Structurally valid and
        # completely empty — test_gloss_layer rejects it, and so should this.
        return "the whole gloss is the blank"
    pairs = [(t, c) for t, c in zip(tokens, cells, strict=False) if c != "___"]
    if pairs and all(c.lower() == t.strip(".,!?\"'").lower() for t, c in pairs):
        return "every cell echoes its token"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    proposals = harvest([Path(p) for p in args.paths])
    print(f"harvested {len(proposals):,} proposed glosses")

    accepted: dict[str, dict] = defaultdict(dict)
    rejected: Counter = Counter()
    for key, gloss in proposals.items():
        try:
            code, pi, di = key.split(":")
            pi, di = int(pi), int(di)
        except ValueError:
            rejected["unparseable key"] += 1
            continue
        path = GRAMMAR / f"{code}_grammar.json"
        if not path.exists():
            rejected["unknown course"] += 1
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        points = data if isinstance(data, list) else data.get("points", [])
        try:
            drill = points[pi]["drills"][di]
        except (IndexError, KeyError):
            rejected["drill not found"] += 1
            continue
        why = check((gloss or "").strip(), (drill.get("sentence") or "").strip(),
                    (drill.get("answer") or "").strip())
        if why:
            rejected[why] += 1
            continue
        accepted[code][(pi, di)] = gloss.strip()

    total = sum(len(v) for v in accepted.values())
    print(f"accepted {total:,}   rejected {dict(rejected) or 'none'}")
    if args.dry_run:
        return 0

    for code, edits in sorted(accepted.items()):
        path = GRAMMAR / f"{code}_grammar.json"
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        indent_match = re.search(r"\n( +)\"", raw)
        indent = len(indent_match.group(1)) if indent_match else 2
        points = data if isinstance(data, list) else data.get("points", [])
        for (pi, di), gloss in edits.items():
            points[pi]["drills"][di]["gloss"] = gloss
        out = json.dumps(data, ensure_ascii=False, indent=indent)
        if raw.endswith("\n"):
            out += "\n"
        path.write_text(out, encoding="utf-8")
        drills = [d for p in points for d in p.get("drills") or []]
        done = sum(1 for d in drills if (d.get("gloss") or "").strip())
        print(f"  {code}: +{len(edits)} -> {done}/{len(drills)} "
              f"({100 * done / max(1, len(drills)):.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
