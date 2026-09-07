#!/usr/bin/env python3
"""Gate rewritten drill hints and write them into `data/grammar/*_grammar.json`.

A hint narrows the answer without supplying it. Two ways of failing that are
counted by the audit and repaired by this script's input:

`giveaway_by_gloss` — a hint of three words or fewer that already sits inside
the drill's own translation. "she" under "She sings very well." adds nothing
the learner cannot read one line up, and for a closed-class answer it settles
the question outright.

`agreement_feature` — a hint that is EXCLUSIVELY the agreement features the
drill exists to make the learner derive. "feminine singular" under
"___ casa és gran." picks `La` out of {el, la, els, les} without the learner
ever having to know that casa is feminine, which is the whole exercise.

The gate re-runs the audit's own predicates rather than reimplementing them,
so a hint this script accepts is one `audit_content` will not flag. It also
refuses the two failures that would be worse than the defect being fixed: a
hint containing its answer, and a hint that is merely the old one reworded
into another rule's violation.

    python scripts/apply_drill_hints.py results.json [--dry-run]

where results.json is {code: [{point, sentence, hint}]}.
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
sys.path.insert(0, str(REPO))

from backend.services.quality.audit_content import (  # noqa: E402
    _is_agreement_feature_only,
    _whole_word,
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
MAX_CHARS = 120


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").casefold())
    return "".join(c for c in text if not unicodedata.category(c).startswith("M"))


def check(hint: str, answer: str, translation: str, was: str) -> str | None:
    """The reason to refuse *hint*, or None when it may be written."""
    hint = (hint or "").strip()
    if not hint:
        return "empty"
    if len(hint) > MAX_CHARS:
        return f"longer than {MAX_CHARS} characters"
    if fold(hint) == fold(was or ""):
        return "identical to the hint it replaces"
    # The defect this whole phase exists to remove must not be reintroduced.
    if answer and _whole_word(answer).search(hint):
        return "contains its own answer"
    words = _WORD_RE.findall(hint)
    if translation and 1 <= len(words) <= 3 and _whole_word(hint).search(translation):
        return "still sits inside the drill's translation"
    if _is_agreement_feature_only(hint):
        return "still only the agreement features"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    proposals: dict[str, list[dict]] = defaultdict(list)
    for path in args.results:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        for code, items in raw.items():
            proposals[code].extend(items)

    accepted: dict[str, dict] = defaultdict(dict)
    rejected: Counter = Counter()
    for code, items in sorted(proposals.items()):
        path = GRAMMAR / f"{code}_grammar.json"
        if not path.exists():
            rejected["unknown course"] += len(items)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        points = data.get("points", [])
        index = {
            (p["title"], d.get("sentence", "")): (pi, di, d)
            for pi, p in enumerate(points)
            for di, d in enumerate(p.get("drills", []))
        }
        for item in items:
            key = (item.get("point", ""), item.get("sentence", ""))
            found = index.get(key)
            if not found:
                rejected["drill not found"] += 1
                continue
            pi, di, drill = found
            why = check(item.get("hint", ""), (drill.get("answer") or "").strip(),
                        (drill.get("translation") or "").strip(),
                        (drill.get("hint") or "").strip())
            if why:
                rejected[why] += 1
                continue
            accepted[code][(pi, di)] = item["hint"].strip()

    total = sum(len(v) for v in accepted.values())
    print(f"accepted {total:,}   rejected {dict(rejected) or 'none'}")
    if args.dry_run or not total:
        return 0

    for code, edits in sorted(accepted.items()):
        path = GRAMMAR / f"{code}_grammar.json"
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        for (pi, di), hint in edits.items():
            data["points"][pi]["drills"][di]["hint"] = hint
        indent = 1 if raw.startswith("{\n ") and not raw.startswith("{\n  ") else 2
        path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n",
                        encoding="utf-8")
        print(f"  {code}: {len(edits)} hints rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
