"""No shipped text may be an instruction ABOUT the text.

On 10 Sep 2026 a second-lens review of Korean's explanations returned its
corrections in a `fix` field, and some were phrased as instructions to an
editor rather than as replacement prose:

    "Add a third row: | ㄹ | `거예요`, with no 을 | 살다 → 살 거예요 |"

The applier pasted `fix` in verbatim. Three reached the corpus. One was
caught — it made a four-cell row in a three-cell table, so the gate in
`apply_grammar_explanations` refused it. **The other two passed, because an
instruction line does not break a table's shape**, and they shipped to
production in #450: a learner opening *Future with (으)ㄹ 거예요* read the
sentence "Add a third row:" on the card.

Worse than the stray line: in both cases the instruction REPLACED the row it
was describing, so each table lost its consonant row while its drills went on
answering consonant stems (먹을, 있을, 작은가요, 좋은가) against a table that no
longer taught them.

The lesson is about the shape of review output, not about Korean: a correction
phrased as an instruction and a correction phrased as content are not
interchangeable, and only one of them can be applied mechanically. This test
is the backstop for when that distinction is missed again.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

GRAMMAR = sorted((Path(__file__).resolve().parents[2] / "data" / "grammar")
                 .glob("*_grammar.json"))

# An editorial instruction names the DOCUMENT'S OWN STRUCTURE — a row, a cell,
# a table. That is the discriminator, and it has to be, because grammar prose
# is full of legitimate imperatives that operate on the LANGUAGE: "Replace the
# object with a short pronoun" is a function note on six courses' pronoun
# points, and "Drop the `-en` of the infinitive and add the ending" is how
# German's present tense is taught. A first draft of this pattern flagged all
# of them. Only a verb aimed at the page counts.
_STRUCTURE = r"(?:row|rows|cell|cells|table|column|columns|line|lines|bullet|paragraph)"
_INSTRUCTION = re.compile(
    r"(?im)^\s*(?:—\s*)?(?:or\s+)?(?:"
    r"add|drop|replace|delete|insert|remove|rewrite|move|keep|split|merge"
    r")\b[^.\n]{0,60}?\b" + _STRUCTURE + r"\b"
)

FIELDS = ("explanation", "culture_note", "function")


def _points(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["points"] if isinstance(data, dict) else data


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_no_shipped_text_is_an_editorial_instruction(path):
    bad = []
    for point in _points(path):
        for field in FIELDS:
            text = point.get(field) or ""
            for line in text.split("\n"):
                if _INSTRUCTION.match(line):
                    bad.append((point.get("title"), field, line.strip()[:90]))
    assert bad == [], (
        f"{path.name}: shipped text reads as an instruction to an editor, not "
        f"as content a learner should see: {bad}"
    )


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_a_table_row_is_never_left_stranded_outside_its_table(path):
    """The instruction lines landed BETWEEN table rows, which is how they
    deleted one: the line that replaced the consonant row still contained
    pipes, so nothing downstream noticed the row had gone.

    A line carrying table pipes must itself be a table row — it may not have
    prose before the first pipe.
    """
    bad = []
    for point in _points(path):
        for line in (point.get("explanation") or "").split("\n"):
            if "|" not in line:
                continue
            head = line.split("|", 1)[0].strip()
            if head and not head.startswith(("#", ">", "-", "*")):
                bad.append((point.get("title"), line.strip()[:90]))
    assert bad == [], (
        f"{path.name}: a line carries table pipes but opens with prose — it "
        f"will render as a broken row and may have displaced a real one: {bad}"
    )
