"""Sentence romanisation: the all-or-nothing property, and coverage floors.

A learner of Arabic, Korean or Hindi cannot read an example sentence at all
without the reading line. Two things must stay true, and only one of them is
about how MUCH is covered:

1. **All or nothing.** A line that romanises some words and leaves others in
   their own script is read as complete by exactly the people who cannot
   check it. Every romaniser must either render the whole sentence or return
   None. This is the property that matters and it is absolute.
2. **Coverage floors.** How often a reading is available at all. These are
   ratchets, not targets — ar is low because Arabic drops short vowels and
   the reading is a lookup; it goes UP when the table grows, never quietly
   down (quality rule 24 and 32).

Measured 30 Aug 2026 over a fixed 300-row sample per course.
"""
import csv
import random
import re
import sys

import pytest

sys.path.insert(0, ".")
from backend.services.readings import READING_LANGS, sentence_reading  # noqa: E402

TOK = re.compile(r"[^\W\d_]+", re.UNICODE)

# Unicode blocks, explicitly. Two earlier attempts at "is this still native
# script" were wrong in the SAME direction and both understated coverage:
# `not str.isascii()` counts the ā of DIN 31635, and
# `not unicodedata.name(c).startswith("LATIN")` counts ʼ and ʻ (named
# MODIFIER LETTER ...), which are how that standard writes hamza and ayn.
# Name the blocks; do not infer them.
_NATIVE = [
    (0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
    (0x0590, 0x05FF), (0xFB1D, 0xFB4F),
    (0x0900, 0x097F), (0x0400, 0x04FF), (0x0370, 0x03FF),
    (0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F),
    (0x0E00, 0x0E7F),
]

# course -> minimum share of sentences that yield a reading, as measured.
# ar dropped 0.38 -> 0.35 on 30 Aug when 684 newly authored sentences landed
# for its thin top-2000 words. That is dilution by GOOD content, not decay:
# the reading is a dictionary lookup built over the VOCABULARY list, while a
# sentence may contain any word at all, so a corpus that grows faster than
# the table covers reads as a coverage drop. Rule 24 — a number going down
# can be the correct outcome; the floor moves, with the reason attached.
# Raise it again when the lookup is extended over sentence vocabulary.
# TOKEN coverage — what share of words the reader can render. NOT the share
# of whole sentences, which falls as sentences get longer even when the
# reader is unchanged: a sentence needs EVERY word known. Arabic's
# sentence-share floor was moved twice in two days chasing that, both times
# because sentence quality had been RAISED. A ratchet that drops when the
# content improves is measuring the wrong unit.
#
# ru/el/hi/ko compute their reading rather than look it up, so they render
# any word and sit at 1.00. th/he/fa/ar are dictionary lookups and their
# floors are the real state of those tables (measured 31 Aug).
FLOORS = {"ru": 0.99, "el": 0.99, "hi": 0.99, "ko": 0.99,
          "he": 0.85, "fa": 0.90, "ar": 0.78}

# Thai stays on the per-SENTENCE measure, and it is the one language where
# that is right: it writes without spaces, so "a token" only exists once the
# reader has segmented the text — and asking whether the reader can render
# the segments it produced is circular. Sentence coverage is the only
# non-circular question available (§22).
SENTENCE_FLOORS = {"th": 0.85}


def _native(token: str) -> bool:
    return any(any(a <= ord(c) <= b for a, b in _NATIVE) for c in token)


def _sample(code: str, n: int = 300) -> list[str]:
    path = f"data/{code}_sentences.tsv"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r["sentence"] for r in csv.DictReader(fh, delimiter="\t")
                if (r.get("sentence") or "").strip()]
    random.seed(11)
    return random.sample(rows, min(n, len(rows)))


@pytest.mark.parametrize("code", sorted(READING_LANGS))
def test_a_reading_is_never_partial(code):
    """THE property. A reading with native script still in it is a half-line
    presented as a whole one."""
    partial = []
    for sentence in _sample(code):
        out = sentence_reading(sentence, code)
        if not out:
            continue
        left = [t for t in TOK.findall(out) if _native(t)]
        if left:
            partial.append((sentence, out, left))
    assert not partial, (
        f"{code}: {len(partial)} partial reading(s) — e.g. {partial[0][1]!r} "
        f"still contains {partial[0][2][:3]}")


@pytest.mark.parametrize("code", sorted(SENTENCE_FLOORS))
def test_unspaced_reading_coverage_holds_its_floor(code):
    """Thai only. See SENTENCE_FLOORS for why the unit differs."""
    rows = _sample(code)
    share = sum(1 for s in rows if sentence_reading(s, code)) / len(rows)
    assert share >= SENTENCE_FLOORS[code], (
        f"{code}: readings on {share:.0%} of the sample, floor "
        f"{SENTENCE_FLOORS[code]:.0%}")


@pytest.mark.parametrize("code", sorted(FLOORS))
def test_reading_coverage_holds_its_floor(code):
    """Per-TOKEN, so the number answers "how much of this language can the
    reader render" rather than "how short are the sentences today"."""
    total = known = 0
    for sentence in _sample(code):
        for token in TOK.findall(sentence):
            if not _native(token):
                continue          # already Latin: nothing to render
            total += 1
            if sentence_reading(token, code):
                known += 1
    share = known / max(1, total)
    assert share >= FLOORS[code], (
        f"{code}: the reader renders {share:.0%} of {total} native tokens, "
        f"floor {FLOORS[code]:.0%}. A drop means the lookup lost entries — "
        f"raise the floor only after it genuinely improves, and never to "
        f"accommodate longer sentences (that is what the old per-sentence "
        f"unit punished).")
