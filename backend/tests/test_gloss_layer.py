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
import unicodedata

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



# Scripts written without spaces between words. Counting whitespace there is
# meaningless — a whole Thai sentence is ONE token, so the correct three-cell
# gloss of ผม{{answer}}ข้าว reads as three invented cells. Borrow the reading
# pipeline's segmentation, which is how the learner sees the sentence divided
# (CHECKS.md §22).
UNSPACED = {"th"}


def _tokens(sentence: str, code: str) -> list[str]:
    if code in UNSPACED:
        try:
            from backend.services.readings import sentence_reading

            reading = sentence_reading(sentence, code)
            if reading and reading.split():
                return reading.split()
        except Exception:  # noqa: BLE001 — a missing reader must not fail a gloss
            pass
    return sentence.split()


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
    code = os.path.basename(path).split("_")[0]
    bad = []
    for drill in _drills(path):
        gloss = (drill.get("gloss") or "").strip()
        if not gloss or "·" not in gloss:
            continue  # self-labelling format, checked by the tests above
        cells = [c for c in gloss.split("·") if c.strip()]
        tokens = _tokens(drill.get("sentence") or "", code)
        if len(cells) > len(tokens):
            bad.append((drill.get("sentence"), gloss, len(tokens), len(cells)))
    assert not bad, f"{len(bad)} gloss(es) with more cells than tokens: {bad[:2]}"


# Courses whose glosses were authored to the strict positional contract: one
# cell per whitespace token, no multi-word cells.
#
# `mi` joined on 26 Aug. It had used multi-word cells (`Kei te` as one tense
# marker) on 24 lines; those now split, with each token of a two-word marker
# glossed and split the SAME way every time.
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
                    "sw_grammar.json", "mi_grammar.json"]


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


def test_english_glosses_are_structural_not_translational():
    """Owner decision, 27 Aug 2026: ALL courses transition to STRUCTURAL
    glosses — Leipzig decomposition, metalanguage English everywhere, en
    included. An earlier tripwire here blocked en glosses as "circular"; that
    analysis treated the layer as a translation, and it is not. The value of
    an en gloss is the decomposition — have.NEG, bark.3SG, child.PL — which
    is precisely what a Spanish learner of English needs made visible.

    What WOULD be a defect on en is a gloss that only echoes its own tokens:
    a line where no cell decomposes anything teaches nothing. Once en glosses
    exist, at least the inflected cells must differ from the token above."""
    drills = [d for d in _drills("data/grammar/en_grammar.json")
              if (d.get("gloss") or "").strip()]
    echo_only = []
    for d in drills:
        cells = [c.strip() for c in (d.get("gloss") or "").split("·")]
        tokens = (d.get("sentence") or "").split()
        if len(cells) != len(tokens):
            continue  # the strict-alignment test reports this separately
        pairs = [(t, c) for t, c in zip(tokens, cells) if c != "___"]
        if pairs and all(
            c.lower() == t.strip(".,!?\"'").lower() for t, c in pairs
        ):
            echo_only.append((d.get("sentence"), d.get("gloss")))
    assert not echo_only, (
        f"{len(echo_only)} en gloss(es) only echo their tokens — no cell "
        f"decomposes anything, e.g. {echo_only[:2]}")


# ── Example-sentence floor (CHECKS §23) ────────────────────────────────────
def _sentence_tokens(sentence: str) -> list[str]:
    out: list[str] = []
    cur = ""
    for ch in sentence or "":
        if unicodedata.category(ch).startswith(("L", "M")) or (cur and ch in "'’-"):
            cur += ch
        else:
            if cur:
                out.append(cur)
                cur = ""
    if cur:
        out.append(cur)
    return out


@pytest.mark.parametrize(
    "path",
    [p for p in glob.glob("data/*_sentences.tsv") if "/th_" not in p],
    ids=lambda p: os.path.basename(p),
)
def test_a_word_with_a_real_sentence_keeps_no_fragments(path):
    """CHECKS §23. A word that HAS a sentence of five tokens or more must not
    also carry ones below that: the card draws by difficulty_rank, appended
    rows sort last, and the fragments win. The owner's `мне` card showed
    "Это мне?", "Это не мне." and "Это мне." while three authored sentences
    of ten and eleven words sat unseen behind them.

    Words whose every sentence is thin are exempt — nothing better exists
    yet, and an empty card is worse. Thai is excluded (§22): it writes
    without spaces, so a token count says nothing.
    """
    import csv as _csv
    from collections import defaultdict

    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in _csv.DictReader(fh, delimiter="\t")
                if (r.get("sentence") or "").strip()]
    by_word = defaultdict(list)
    for r in rows:
        by_word[(r.get("word") or "").strip()].append(r.get("sentence") or "")
    bad = []
    for word, group in by_word.items():
        lens = [len(_sentence_tokens(s)) for s in group]
        if max(lens) >= 5 and min(lens) < 5:
            bad.append((word, [s for s, n in zip(group, lens, strict=False) if n < 5][:2]))
    assert not bad, (
        f"{len(bad)} word(s) keep a fragment despite having a real sentence, "
        f"e.g. {bad[:2]}")
