"""One word, several spellings: the `alt` column of a frequency file.

Turkish writes its yes/no particle mi, mı, mu or mü according to the vowel
before it — one word, four shapes. Jamaican writes `likkle` or `little` —
one word, two conventions. Both courses carry the extra shapes in an `alt`
column (semicolon-separated) that the seeder writes to
`vocabulary.alternatives`, and everything that asks "is this word in this
sentence?" has to ask about every shape, or a sentence written with the
second shape counts as one the card cannot blank (quality rule 46) while a
learner reading it sees the word plainly.

This module is the file-side reader of that column, so the audit, the
authored-sentence gate and the prune agree with the card about which rows
teach the word. The card itself reads the database column
(`repositories/cards.py`), which the seeder filled from the same file.
"""
from __future__ import annotations

import csv
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@cache
def linked_forms(code: str) -> dict[str, tuple[str, ...]]:
    """word -> its other spellings, for every headword whose row has an `alt`.

    Words without an `alt` are absent, so `forms_of` is the accessor to use.
    """
    path = DATA_DIR / f"{code}_frequency.tsv"
    if not path.exists():
        return {}
    out: dict[str, tuple[str, ...]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip()
            alts = tuple(
                a.strip() for a in (row.get("alt") or "").split(";") if a.strip()
            )
            if word and alts:
                out[word] = alts
    return out


def forms_of(word: str, code: str) -> list[str]:
    """Every shape of *word* that a sentence may carry, headword first."""
    return [word, *[a for a in linked_forms(code).get(word, ()) if a != word]]
