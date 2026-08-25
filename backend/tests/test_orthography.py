"""A course's declared orthography, checked instead of merely declared.

`jam.md` and the `JamaicanNLP` docstring both stated Cassidy-JLU, and nothing
enforced it: 12 headwords broke the rules the doc states as a checkable list,
three of them words the doc names as drift by name. Expressing a policy as a
character set makes the violations fall out.

Measured 25 Aug 2026 across the five courses with a tight declarable
inventory: mi 0, xh 0, yo 0, ha cosmetic-only, jam 6. The class is real but
currently Jamaican-scoped, which is a measured decision, not an omission.
See docs/quality/CHECKS.md §4.
"""
import csv
import re
import unicodedata
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "data"

# Each course's letter inventory, from its own quality doc. Tone/length marks
# that the doc calls letters are included; anything else is a violation.
# Words are compared under NFD, so a mark the doc calls a LETTER is listed here
# as its combining codepoint: Māori's macron and Yoruba's underdot are letters,
# not decoration, and stripping either changes the word.
MACRON = "\u0304"        # mi: the 16th letter
DOT_BELOW = "\u0323"     # yo: distinguishes ẹ ọ ṣ from e o s
GRAVE, ACUTE = "\u0300", "\u0301"  # yo: low and high tone

INVENTORIES = {
    "mi": set("aeiouhkmnprtwg") | {MACRON},
    "yo": set("abdefghijklmnoprstuwy") | {DOT_BELOW, GRAVE, ACUTE},
    # xh.md: basic Latin, no diacritics at all.
    "xh": set("abcdefghijklmnopqrstuvwxyz"),
}
ALLOWED_PUNCT = set(" -'’ʼ")


def _rows(code):
    path = DATA / f"{code}_frequency.tsv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [r for r in csv.DictReader(handle, delimiter="\t") if (r.get("word") or "").strip()]


def _norm(text):
    return unicodedata.normalize("NFC", (text or "").strip()).lower()


@pytest.mark.parametrize("code", sorted(INVENTORIES))
def test_headwords_use_only_the_declared_inventory(code):
    inventory = INVENTORIES[code] | ALLOWED_PUNCT
    offenders = []
    for row in _rows(code):
        word = unicodedata.normalize("NFD", row["word"]).lower()
        bad = {c for c in word if c not in inventory and not c.isspace()}
        if bad:
            offenders.append(f"{row['word']} ({''.join(sorted(bad))})")
    assert not offenders, (
        f"{code}: headwords outside the declared inventory: {offenders[:10]}"
    )


# ── Cassidy-JLU, as jam.md states it ─────────────────────────────────────────

_BAD_DIGRAPH = re.compile(r"ea|ei|oo|ay|ey|oa|ck|ph|th")
_BAD_LETTER = re.compile(r"x|q|c(?!h)")
_DOUBLE_CONS = re.compile(r"([bcdfgjklmnpqrstvwxyz])\1")
_FINAL_Y = re.compile(r"y$")

# `gg` in these is `ng` + `g` — the /ŋ/+/ɡ/ of [maŋɡuus], two sounds — not a
# geminate spelling one, which is what the rule and all three of its worked
# examples (likkle, granny, riddim) target. The corpus is inconsistent about
# /ŋɡ/ (finga, ongri, jongl use one g) and jam.md states no rule on it, so
# settling all five is a JLU-reviewer question rather than an extrapolation.
CASSIDY_EXEMPT = {"mangguus", "onggl"}


def _breaks_cassidy(word):
    for pattern, why in (
        (_BAD_DIGRAPH, "non-Cassidy digraph"),
        (_BAD_LETTER, "letter outside the inventory"),
        (_DOUBLE_CONS, "doubled consonant"),
        (_FINAL_Y, "final -y"),
    ):
        found = pattern.search(word)
        if found:
            return f'{why} "{found.group(0)}"'
    return None


def test_jamaican_headwords_are_cassidy_jlu():
    offenders = [
        f"{r['word']}: {_breaks_cassidy(_norm(r['word']))}"
        for r in _rows("jam")
        if _norm(r["word"]) not in CASSIDY_EXEMPT and _breaks_cassidy(_norm(r["word"]))
    ]
    assert not offenders, (
        "jam headwords outside Cassidy-JLU: " + "; ".join(offenders)
        + " — respell and put the old spelling FIRST in `alt`, or add a "
        "reasoned exemption here. This gate is necessary, not sufficient: "
        "`friend` broke no letter rule and was still the English spelling."
    )


def test_no_alt_spelling_is_another_words_headword():
    """The alt column is deliberate leniency — typing `him` for `im` passes.
    But when the alt is another row's HEADWORD it stops excusing a spelling
    and starts laundering a word (the fold rule), and the collision ratchet cannot
    see it: _collision_surfaces() reads only the `word` column. `di` (the)
    claimed `de` (to be at); `nuo` (know) claimed `no` (the negator)."""
    rows = _rows("jam")
    heads = {_norm(r["word"]): r["word"] for r in rows}
    clashes = [
        f"{r['word']} lists alt '{alt.strip()}', which is headword {heads[_norm(alt)]}"
        for r in rows
        for alt in (r.get("alt") or "").split(";")
        if alt.strip() and _norm(alt) in heads and _norm(alt) != _norm(r["word"])
    ]
    assert not clashes, "alt-column laundering: " + "; ".join(clashes)
