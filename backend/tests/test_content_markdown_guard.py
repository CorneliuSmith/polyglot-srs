"""The seed corpus carries no markdown — and after 4 Sep 2026 that is a
guard, not an observation.

Explanations, culture notes and function notes now RENDER markdown when
they carry it (a block with bold, a list, a table, code or a link goes
through react-markdown; plain blocks keep the typesetter). A backtick or a
pair of asterisks that lands in the seed therefore changes what every
learner sees, where before it printed literally. This pins the corpus at
zero for the markers that flip a block into markdown, so a new one is a
deliberate choice made in this file, not an accident in a data pass.

Glosses are never markdown-rendered (docs/quality/jam.md reasons from that)
— they are held to the same zero for backticks so the reasoning stays true.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GRAMMAR = sorted((REPO / "data" / "grammar").glob("*_grammar.json"))
VOCAB = sorted((REPO / "data").glob("*_vocabulary.csv"))

# The same signals components/ExplanationView.tsx uses to route a block to
# the markdown renderer. Keep the two in step.
MARKERS = {
    "backtick": re.compile(r"`[^`\n]+`"),
    # Asterisks only: "___" is how the cards write a blank ("I live in
    # ___"), and it must not flip a card into markdown.
    "bold": re.compile(r"\*\*[^*\n]+\*\*"),
    "list": re.compile(r"(^|\n)\s*([-*+]|\d+\.)\s+"),
    "table": re.compile(r"(^|\n)\s*\|.*\|"),
    "heading": re.compile(r"(^|\n)#{1,3}\s"),
    "link": re.compile(r"\[[^\]]+\]\([^)]+\)"),
}

# Rows that carry a marker on purpose: (file stem, point title, marker).
# Add here, deliberately, when an explanation is meant to render as
# markdown. Empty today.
ALLOWED: set[tuple[str, str, str]] = set()


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_seed_explanations_carry_no_markdown_markers(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    points = data["points"] if isinstance(data, dict) else data
    found = []
    for p in points:
        for field in ("explanation", "culture_note", "function_note"):
            text = p.get(field) or ""
            for name, rx in MARKERS.items():
                if rx.search(text) and (path.stem, p["title"], name) not in ALLOWED:
                    found.append((p["title"], field, name))
    assert found == [], (
        f"{path.name}: markdown markers in the seed — these blocks now RENDER "
        f"as markdown for every learner. Either strip them or list them in "
        f"ALLOWED on purpose: {found[:10]}"
    )


@pytest.mark.parametrize("path", VOCAB, ids=lambda p: p.stem)
def test_seed_glosses_carry_no_backticks(path):
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    bad = [
        (r.get("word"), k) for r in rows for k, v in r.items()
        if k and k.startswith("definition") and v and "`" in v
    ]
    assert bad == [], f"{path.name}: backticks in glosses print literally on the card: {bad[:10]}"
