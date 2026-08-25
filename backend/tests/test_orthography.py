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


# ── interlinear glosses ──────────────────────────────────────────────────────
# The `gloss` field on a drill is the word-by-word line printed UNDER the
# sentence, so cell N is read as the meaning of token N. Two mechanical faults
# were found on 25 Aug 2026 and both are checkable; the third — whether each
# cell sits under the right token — is judgement and is not gated here.

def _drills(code):
    import json
    path = DATA / "grammar" / f"{code}_grammar.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    points = doc if isinstance(doc, list) else (doc.get("points") or doc.get("grammar_points"))
    return [d for p in (points or []) for d in p.get("drills", [])]


# mi separates cells with " · "; sw writes `word (GLOSS)` instead. Only the
# dot-separated convention is checked — see docs/quality/CHECKS.md.
DOT_GLOSS_LANGS = ["mi"]


@pytest.mark.parametrize("code", DOT_GLOSS_LANGS)
def test_interlinear_gloss_is_not_truncated(code):
    """Nine Māori glosses stopped mid-sentence with an ellipsis, leaving the
    rest of the tokens unglossed — and the "..." was glued onto the last cell,
    so `toa` read as meaning "shop..."."""
    truncated = [
        d["sentence"] for d in _drills(code)
        if (d.get("gloss") or "").strip().endswith(("...", "…"))
    ]
    assert not truncated, (
        f"{code}: interlinear gloss stops mid-sentence: {truncated[:5]} — "
        "every token needs a cell, or the line shifts under the learner."
    )


@pytest.mark.parametrize("code", DOT_GLOSS_LANGS)
def test_interlinear_gloss_never_invents_cells(code):
    """A gloss may COLLAPSE a multi-word unit into one cell (`Kei te` is one
    tense marker), so cells < tokens is fine. More cells than tokens is not:
    it means a cell was invented and everything after it is shifted."""
    offenders = []
    for drill in _drills(code):
        gloss = (drill.get("gloss") or "").strip()
        if not gloss:
            continue
        sentence = drill.get("sentence") or ""
        tokens = [t for t in re.split(r"\s+", re.sub(r"[.,!?;:]", "", sentence)) if t]
        cells = gloss.split("·")
        if len(cells) > len(tokens):
            offenders.append(f"{sentence!r}: {len(cells)} cells for {len(tokens)} tokens")
    assert not offenders, f"{code}: " + "; ".join(offenders[:5])


@pytest.mark.parametrize("code", DOT_GLOSS_LANGS)
def test_interlinear_gloss_has_exactly_one_blank(code):
    """The blank is what the learner is answering; two or none is incoherent."""
    offenders = [
        f"{d['sentence']!r}: {sum('___' in c for c in (d.get('gloss') or '').split('·'))} blanks"
        for d in _drills(code)
        if (d.get("gloss") or "").strip()
        and "{{answer}}" in (d.get("sentence") or "")
        and sum("___" in c for c in (d.get("gloss") or "").split("·")) != 1
    ]
    assert not offenders, f"{code}: " + "; ".join(offenders[:5])
