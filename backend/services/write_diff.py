"""Which letters did the reader get wrong? (docs/plans/handwriting.md, §12)

Given the reader's transcription and what the writer says they wrote,
align the two letter by letter and name the misreads. Combining marks
ride with their base — a hamza on an alif, a tashkeel, a breve on й — so
"й read as и" is one unit, not a missing mark. This is the ground truth
the whole adaptation is built on: every entry here came from the writer,
not the model.
"""
from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher


def units(text: str) -> list[str]:
    """Letters with their combining marks attached; whitespace dropped."""
    out: list[str] = []
    for ch in unicodedata.normalize("NFC", text or ""):
        if out and unicodedata.combining(ch):
            out[-1] += ch
        elif ch.isspace():
            continue
        else:
            out.append(ch)
    return out


def same_text(a: str, b: str) -> bool:
    """Equal as writing, ignoring spacing and normalisation form."""
    return units(a) == units(b)


def misread_letters(read: str, wrote: str) -> list[dict]:
    """[{wrote, read}] for every unit the reader got wrong. `read` is ''
    where the reader missed a letter; `wrote` is '' where it invented one."""
    a, b = units(read), units(wrote)
    sm = SequenceMatcher(a=a, b=b, autojunk=False)
    out: list[dict] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ra, wb = a[i1:i2], b[j1:j2]
        for k in range(max(len(ra), len(wb))):
            out.append({"wrote": wb[k] if k < len(wb) else "",
                        "read": ra[k] if k < len(ra) else ""})
    return out
