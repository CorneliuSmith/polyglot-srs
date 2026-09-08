"""Every paradigm cell has a drill — checked here, not only at seed time.

`seed_grammar`'s `transform` refuses a whole course when a point declares paradigm
cells and one of them has no drill: "a member the drills never test is a
member the learner never learns". That is the right rule in the wrong
place. On 7 Sep 2026 the owner's production reseed ran twenty courses and
then printed `FAIL ko: … paradigm cells with no drill: ['개월 – months
(Sino-Korean)']` — one missing drill, and Korean's 156 grammar points did
not load. The gap had been in the committed file for weeks; nothing read it
until a production run did.

So: the same rule, in CI, against the committed corpus.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

GRAMMAR = sorted((Path(__file__).resolve().parents[2] / "data" / "grammar")
                 .glob("*_grammar.json"))


def _points(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["points"] if isinstance(data, dict) else data


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_every_paradigm_cell_has_a_drill(path):
    bad = []
    for point in _points(path):
        paradigm = [str(c).strip() for c in (point.get("paradigm") or [])
                    if str(c).strip()]
        if not paradigm:
            continue
        cells = {(d.get("cell") or "").strip() for d in point.get("drills") or []}
        cells.discard("")
        missing = sorted(set(paradigm) - cells)
        if missing:
            bad.append((point["title"], missing))
    assert bad == [], (
        f"{path.name}: seed_grammar will REFUSE this whole course — a paradigm "
        f"cell with no drill is a form the learner never meets: {bad}"
    )


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_every_paradigm_cell_has_at_least_two_drills(path):
    """The seeder's density gate, and the one that actually bit: after the
    missing-cell error was fixed, the same Korean reseed failed again on
    `낫다 – to be better`, whose `past, polite ~요` cell had one drill. Two,
    so the rotation can vary the frame within a cell — one frame per form
    invites memorising the sentence instead of the form."""
    from collections import Counter
    bad = []
    for point in _points(path):
        paradigm = [str(c).strip() for c in (point.get("paradigm") or [])
                    if str(c).strip()]
        if not paradigm:
            continue
        counts = Counter((d.get("cell") or "").strip()
                         for d in point.get("drills") or [])
        thin = sorted(c for c in paradigm if counts.get(c, 0) < 2)
        if thin:
            bad.append((point["title"], thin))
    assert bad == [], (
        f"{path.name}: seed_grammar will REFUSE this whole course — a paradigm "
        f"cell with fewer than 2 drills: {bad}"
    )


@pytest.mark.parametrize("path", GRAMMAR, ids=lambda p: p.stem)
def test_no_drill_claims_a_cell_the_paradigm_does_not_have(path):
    """The other half of the seeder's rule: a typo'd cell name is a drill
    filed under a member that does not exist, so the real member reads as
    uncovered and the course still fails."""
    bad = []
    for point in _points(path):
        paradigm = {str(c).strip() for c in (point.get("paradigm") or [])
                    if str(c).strip()}
        if not paradigm:
            continue
        cells = {(d.get("cell") or "").strip() for d in point.get("drills") or []}
        cells.discard("")
        unknown = sorted(cells - paradigm)
        if unknown:
            bad.append((point["title"], unknown))
    assert bad == [], f"{path.name}: drill cells not in the paradigm: {bad}"


def test_the_rule_here_is_the_rule_the_seeder_applies():
    """If the seeder's check moves or changes shape, this file is testing
    something the production path no longer does."""
    import inspect

    from backend.services.seeder.seed_grammar import GrammarSeeder

    src = inspect.getsource(GrammarSeeder.transform)
    for phrase in ("paradigm cells with no drill",
                   "drill cells not in the paradigm",
                   "paradigm cells below 2 drills"):
        assert phrase in src, f"the seeder no longer raises {phrase!r}"
