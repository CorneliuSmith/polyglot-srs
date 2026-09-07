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

# Fields that render PLAIN wherever they appear (`GrammarPathPage.tsx`,
# `LearnPage.tsx`, `ReviewDetail.tsx` all put them in a bare <p>), so a
# marker in one prints literally. `explanation` is not among them: it is
# the one field that reaches `ExplanationView` -> `CardMarkdown`.
#
# The seed key is `function`, not `function_note`. This guard named the
# latter for months and was therefore vacuous on that field — the plan
# `docs/plans/markdown-explanations.md` (correction 1) found it, and
# `function` is what REFERENCE.md renders from, so it matters.
PLAIN_FIELDS = ("culture_note", "function", "function_note")


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_plain_fields_carry_no_markdown_markers(path):
    """A marker in a field nothing routes to the renderer prints literally."""
    data = json.loads(path.read_text(encoding="utf-8"))
    points = data["points"] if isinstance(data, dict) else data
    found = [
        (p["title"], field, name)
        for p in points
        for field in PLAIN_FIELDS
        for name, rx in MARKERS.items()
        if rx.search(p.get(field) or "")
    ]
    assert found == [], (
        f"{path.name}: markdown markers in a field that renders PLAIN — these "
        f"print literally on the card. Strip them: {found[:10]}"
    )


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_explanations_only_carry_markdown_the_renderer_supports(path):
    """`explanation` MAY carry markdown — since 4 Sep 2026 the card renders
    it, and the editorial pass in `docs/plans/markdown-explanations.md` is
    filling it in course by course. What it may not carry is a construct
    `CardMarkdown`'s sanitiser drops: a heading (no h1-h6 in `tagNames`), an
    image, a rule, raw HTML, a non-http link, a table whose rows disagree
    with its header, or a `___` blank inside a markdown block.

    This replaced a rule that forbade markdown outright and kept an ALLOWED
    set of exceptions. That shape could not survive the pass: 1,378 texts
    would each need a line in it, and a list that long is not read.
    """
    from scripts.apply_grammar_explanations import check

    data = json.loads(path.read_text(encoding="utf-8"))
    points = data["points"] if isinstance(data, dict) else data
    bad = [
        (p["title"], why)
        for p in points
        if (p.get("explanation") or "").strip()
        and (why := check(p["explanation"], p["explanation"]))
    ]
    assert bad == [], (
        f"{path.name}: an explanation carries markdown the card cannot "
        f"render — it is dropped or printed literally: {bad[:5]}"
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
