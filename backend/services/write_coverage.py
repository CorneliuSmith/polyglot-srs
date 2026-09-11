"""The baseline's coverage set (docs/plans/handwriting.md, §12.2).

A baseline session asks the writer for eight short sentences that, between
them, show every letter of the script — and for the Arabic script every
positional form, since ب alone, at the start, in the middle and at the end
are four different things to write. Until a script has a speaker-reviewed
exemplar set (§5), the sentences are picked greedily from the course's own
beginner lines: each pick is the sentence that adds the most still-uncovered
units. Worse than an authored set; never absent.

Units are what a hand has to form:
  * a letter (case-folded for the cased scripts, so Ф covers ф);
  * for Arabic and Persian, letter + form, decided by whether the
    neighbours join — the six right-joining-only letters and hamza forms
    never take an initial or medial form;
  * for Hangul, the conjoining jamo of each syllable block.
"""
from __future__ import annotations

import unicodedata

from backend.services.seeder.seed_alphabet import ALPHABETS

ARABIC_SCRIPT = frozenset({"ar", "fa"})
# Letters of the Arabic script that never join to the letter after them.
NON_JOINING_LEFT = frozenset("اأإآدذرزوةىءؤژ")
CASED = frozenset({"ru", "el"})
BASELINE_SIZE = 8


def letters_of(code: str) -> list[str]:
    """The script's letter inventory as the alphabet decks know it; empty
    for a Latin-script course, whose targets come from the pool itself."""
    return [letter for letter, _, _ in ALPHABETS.get(code, [])]


def _cells(text: str) -> list[str]:
    """Letters with their combining marks; anything else is a break."""
    out: list[str] = []
    for ch in unicodedata.normalize("NFC", text or ""):
        if out and out[-1] != " " and unicodedata.combining(ch):
            out[-1] += ch
        elif unicodedata.category(ch).startswith("L"):
            out.append(ch)
        elif not out or out[-1] != " ":
            out.append(" ")
    return out


def _jamo_key(ch: str) -> str:
    """One name for a jamo whatever its position: the conjoining lead ᄂ,
    the trailing ᆫ and the compat letter ㄴ are all NIEUN — the same shape
    a hand forms, at the top or the bottom of a block."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return ch
    parts = name.split(" ", 2)
    return parts[2] if len(parts) == 3 and parts[0] == "HANGUL" else ch


def _jamo(ch: str) -> list[str]:
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        i = code - 0xAC00
        lead, vowel, tail = i // (21 * 28), (i % (21 * 28)) // 28, i % 28
        out = [chr(0x1100 + lead), chr(0x1161 + vowel)]
        if tail:
            out.append(chr(0x11A7 + tail))
        return [_jamo_key(j) for j in out]
    return [_jamo_key(ch)]


def units_shown(code: str, text: str) -> set[str]:
    """Everything a hand forms writing *text*, as coverage units."""
    cells = _cells(text)
    if code in ARABIC_SCRIPT:
        base = [c[0] if c != " " else " " for c in cells]
        out: set[str] = set()
        for i, ch in enumerate(base):
            if ch == " ":
                continue
            prev_joins = i > 0 and base[i - 1] != " " and base[i - 1] not in NON_JOINING_LEFT
            joins_next = i + 1 < len(base) and base[i + 1] != " " and ch not in NON_JOINING_LEFT
            form = ("medial" if prev_joins and joins_next else "final" if prev_joins
                    else "initial" if joins_next else "isolated")
            out.add(f"{ch}:{form}")
        return out
    if code == "ko":
        return {j for c in cells if c != " " for j in _jamo(c[0])}
    if code in CASED or code not in ALPHABETS:
        return {c[0].lower() for c in cells if c != " "}
    return {c[0] for c in cells if c != " "}


def targets(code: str, pool: list[str] = ()) -> set[str]:
    """The units a complete baseline must show. Scripts the alphabet decks
    know are enumerated; anything else (a Latin-script course) is covered
    by whatever letters its own pool uses."""
    letters = letters_of(code)
    if code in ARABIC_SCRIPT:
        out: set[str] = set()
        for ch in letters:
            out |= {f"{ch}:isolated", f"{ch}:final"}
            if ch not in NON_JOINING_LEFT:
                out |= {f"{ch}:initial", f"{ch}:medial"}
        return out
    if code == "ko":
        return {_jamo_key(ch) for ch in letters}
    if letters:
        return {ch.lower() for ch in letters} if code in CASED else set(letters)
    seen: set[str] = set()
    for s in pool:
        seen |= units_shown(code, s)
    return seen


def pick_coverage(code: str, sentences: list[dict], n: int = BASELINE_SIZE) -> dict:
    """Greedy set cover over *sentences* ({answer, ...}): each pick adds the
    most still-uncovered units; ties go to the shorter sentence (a beginner
    writes eight of these by hand). Returns {items, covered, total}."""
    want = targets(code, [s["answer"] for s in sentences])
    total = len(want)
    pool = [(s, units_shown(code, s["answer"]) & want) for s in sentences]
    chosen: list[dict] = []
    while len(chosen) < n and want and pool:
        best = max(pool, key=lambda p: (len(p[1] & want), -len(p[0]["answer"])))
        gain = best[1] & want
        if not gain:
            break
        chosen.append(best[0])
        want -= gain
        pool.remove(best)
    # Short of coverage but short of eight too: fill with the shortest
    # remaining lines so the session still has its eight samples.
    for s, _ in sorted(pool, key=lambda p: len(p[0]["answer"])):
        if len(chosen) >= n:
            break
        chosen.append(s)
    return {"items": chosen, "covered": total - len(want), "total": total}
