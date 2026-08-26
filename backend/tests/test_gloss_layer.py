"""The interlinear gloss must not hand the learner the answer.

Every one of Swahili's 134 glossed drills did. The card asks for the word
behind `{{answer}}` and printed the answer in the gloss line directly beneath
it — `Utarudi {{answer}} kutoka safari?` glossed
`u-ta-rudi (2SG-FUT-return) lini (when) ...`, where `lini` IS the answer.

It hid in two forms, and the second is why a first pass under-counted:

1. Plain, 71 drills — the answer appears verbatim as a gloss head.
2. **Segmented, 62 drills** — the head is written with morpheme boundaries
   (`i-ko`) while the answer is not (`iko`). A word-boundary regex does not
   match it; a learner reads it off without effort.
3. Spanning two cells, 1 drill — `ku-to-kata tamaa` for `kutokata tamaa`.

This is the third instance of one defect class in this program: a support
layer that spells out what the card is testing. The romanisation did it on
926 rows (CHECKS.md §11) and the Hebrew hint did it on 191 of 191. Every new
layer gets this test before it gets content.
"""
import glob
import json
import os
import re

import pytest

FILES = sorted(glob.glob("data/grammar/*_grammar.json"))


def _drills(path):
    data = json.load(open(path, encoding="utf-8"))
    points = data if isinstance(data, list) else (
        data.get("points") or data.get("grammar_points") or [])
    for point in points:
        yield from point.get("drills", [])


def _norm(text: str) -> str:
    """Fold the morpheme boundaries away. `i-ko` and `iko` are the same word
    to a learner, and treating them as different is exactly how 62 of these
    survived the first audit."""
    return re.sub(r"[-\s]", "", (text or "").lower().strip("()?.,!¿¡\"'"))


@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(p) for p in FILES])
def test_a_gloss_never_spells_out_the_answer(path):
    """Scoped to the SELF-LABELLING format (`word (GLOSS) word (GLOSS)`), the
    only one that carries target-language words in the gloss line.

    A positional gloss (`CONT · live · ___ · to · Wellington`) holds nothing
    but English glosses and category labels, so there is no target word in it
    to leak — and comparing a Māori answer against English cells finds
    phantoms: `I` is the Māori past marker AND the English pronoun glossing
    `au`, which flagged 4 correct Māori lines. Positional glosses are covered
    by the blank test below, which is the check that actually applies to them.
    """
    leaks = []
    for drill in _drills(path):
        gloss = (drill.get("gloss") or "").strip()
        answer = (drill.get("answer") or "").strip()
        if not gloss or not answer or "·" in gloss:
            continue
        target = _norm(answer)
        if not target:
            continue
        # Compare whole gloss TOKENS, not substrings: a two-letter answer like
        # `na` occurs inside `ni-na` in an unrelated cell, and substring
        # matching reports 32 such phantoms across mi and sw.
        heads = [t for t in gloss.split() if not t.startswith("(")]
        if any(_norm(t) == target for t in heads):
            leaks.append((answer, drill.get("sentence", ""), gloss))
        # ...and the multi-word case, where the answer spans consecutive heads.
        joined = ""
        for head in heads:
            joined += _norm(head)
            if joined == target and len(target) > len(_norm(head)):
                leaks.append((answer, drill.get("sentence", ""), gloss))
                break
            if not target.startswith(joined):
                joined = ""
    assert not leaks, (
        f"{len(leaks)} gloss(es) spell out the answer, e.g. "
        f"answer={leaks[0][0]!r} sentence={leaks[0][1]!r} gloss={leaks[0][2]!r}")


@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(p) for p in FILES])
def test_a_gloss_marks_the_blank_exactly_once(path):
    """Rule 4 of the Leipzig spec (docs/quality/card-layers.md §1): `___` sits
    where `{{answer}}` sits, exactly one per line. Without it the gloss either
    spells the answer or silently omits the cell the learner needs."""
    bad = [
        (d.get("sentence", ""), d.get("gloss"))
        for d in _drills(path)
        if (d.get("gloss") or "").strip()
        and "{{answer}}" in (d.get("sentence") or "")
        and (d.get("gloss") or "").count("___") != 1
    ]
    assert not bad, f"{len(bad)} gloss(es) without exactly one ___, e.g. {bad[0]}"


@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(p) for p in FILES])
def test_a_gloss_never_invents_a_cell(path):
    """Rule 1: a cell may cover a genuine multi-word unit, so cells <= tokens.
    MORE cells than tokens means a cell was invented, and every position after
    it teaches the wrong word — the shifted Māori line the owner caught by
    reading one card."""
    bad = []
    for drill in _drills(path):
        gloss = (drill.get("gloss") or "").strip()
        if not gloss or "·" not in gloss:
            continue  # self-labelling format, checked by the tests above
        cells = [c for c in gloss.split("·") if c.strip()]
        tokens = (drill.get("sentence") or "").split()
        if len(cells) > len(tokens):
            bad.append((drill.get("sentence"), gloss, len(tokens), len(cells)))
    assert not bad, f"{len(bad)} gloss(es) with more cells than tokens: {bad[:2]}"


# Courses whose glosses were authored to the strict positional contract: one
# cell per whitespace token, no multi-word cells. mi predates it and uses
# multi-word cells (`Kei te` is one tense marker), so it is not listed yet.
#
# `sw` converted TO this contract on 26 Aug. Its old self-labelling form
# (`u-ta-rudi (2SG-FUT-return)`) carried the morpheme split, which positional
# cells cannot show — but the gloss renders as FLAT TEXT, where
# `u-ta-rudi (2SG-FUT-return) ___ kutoka (from)` is markedly harder to read
# than `2SG.FUT.return · ___ · from`, and xh proves the positional form works
# for a Bantu language with the same noun-class machinery. 107 of the 131
# converted mechanically; the other 24 had multi-word cells and were
# re-authored along with the 311 that had no gloss at all.
STRICTLY_ALIGNED = ["yo_grammar.json", "xh_grammar.json", "ha_grammar.json",
                    "sw_grammar.json"]


@pytest.mark.parametrize("name", STRICTLY_ALIGNED)
def test_an_authored_gloss_has_exactly_one_cell_per_token(name):
    """`cells <= tokens` cannot catch a SHIFT — the failure the owner found by
    reading one Māori card, where every position after the shift taught the
    wrong word. Requiring exact equality makes alignment mechanically provable
    for the courses authored under it, which is the only reason to accept a
    positional format over a self-labelling one."""
    bad = []
    for drill in _drills(f"data/grammar/{name}"):
        gloss = (drill.get("gloss") or "").strip()
        if not gloss:
            continue
        cells = [c for c in gloss.split("·") if c.strip()]
        tokens = (drill.get("sentence") or "").split()
        if len(cells) != len(tokens):
            bad.append((drill.get("sentence"), gloss, len(tokens), len(cells)))
    assert not bad, f"{len(bad)} misaligned, e.g. {bad[:2]}"


@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(p) for p in FILES])
def test_a_gloss_says_something(path):
    """A gloss whose only cell is the blank renders as a hint layer reading
    `___`. It is not wrong — the sentence really is one token — but it occupies
    a disclosure step and tells the learner nothing, so it should be absent
    rather than empty."""
    empty = [
        (d.get("sentence"), d.get("gloss"))
        for d in _drills(path)
        if (d.get("gloss") or "").strip()
        and len([c for c in (d.get("gloss") or "").split("·") if c.strip()]) == 1
        and (d.get("gloss") or "").strip() == "___"
    ]
    assert not empty, f"{len(empty)} gloss(es) that say nothing, e.g. {empty[0]}"
