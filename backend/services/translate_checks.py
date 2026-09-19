"""Mechanical gates for the translation pipeline.

The maker-checker (translate.py) grades MEANING; these functions catch the
failure classes a semantic grader misses, each one already paid for elsewhere
in this program:

* A translated HINT that contains the drill's answer. The label/prose
  charters correctly instruct that quoted course-language material be copied
  unchanged — which means an English hint that quotes its own answer
  ("be — bare") keeps the leak verbatim in every locale. The render guard
  (safePrompt) blanks it, so the learner sees NO hint, and the stored row
  reads as done forever because the write path COALESCEs. Catching it here
  leaves the row unfilled so a later sweep can retry once the source is fixed.
* An IDENTITY rendering — the model echoing the English back — stored as if
  it were the locale. The checker sometimes accepts these ("that is how
  speakers say it"), and example-sentence renderings land reviewed=true, so
  nothing downstream would ever question them.
* A model-controlled INDEX used to file the result. rows[res["i"]] with
  i = -1 silently files a translation under the LAST row — the same class as
  the rank drift that nearly filed luna's gloss under stella. Out-of-range
  crashes the batch; negative misfiles it, which is worse because nothing
  errors.
* A lost cloze BLANK. No current source string carries {{answer}}, and the
  cheapest way to keep that true of every kind anyone adds later is to
  enforce it: a rendering must carry the same blanks its source did.
* Locale punctuation a grader shrugs at: a Spanish question without its
  opening question mark. Wrong in every schoolbook the learner owns.
* A gloss in the wrong PART OF SPEECH. The maker charter asks for a rendering
  that matches the row's part of speech and the checker is meant to hold it
  to that; measured on 18 Sep 2026, 23% of the Arabic divergences a reviewer
  reported were a noun standing on a verb row. Only Arabic, only verbs:
  that is the one class with a measured predicate (`nominal_gloss_on_a_verb`,
  76% precision), and at 76% the gate WITHHOLDS the rendering for another
  attempt rather than filing a rejection a human has to clear.

All pure functions — no client, no settings — so the tests exercise them
without touching a model (quality rule 15).
"""
from __future__ import annotations

import re
import unicodedata

BLANKS = ("{{answer}}", "___")

# Locale -> (closing mark, required opening mark). Spanish-family locales
# open questions and exclamations with inverted marks; a rendering that
# closes one without ever opening it is wrong in a way every textbook the
# learner owns agrees on.
_INVERTED = {"es": [("?", "¿"), ("!", "¡")]}

_WORD = re.compile(r"[\w'’-]+", re.UNICODE)


def _fold(text: str) -> str:
    """Case-folded, accent-insensitive, joiner-free form for comparison.
    Combining marks are STRIPPED for comparison only — \\p{L}-style tokenizing
    silently dropped Devanagari vowel signs once (रही tokenized as रह), so the
    fold errs the other way: compare skeletons, never report on them."""
    text = unicodedata.normalize("NFD", (text or "").casefold())
    # Category M*, not combining()>0: the Devanagari vowel sign ी is Mc with
    # combining class ZERO, so combining() keeps it — and Python's \w drops
    # it, exactly the mismatch that let रही slip past the frontend guard as
    # रह. Stripping every mark on BOTH sides makes the skeletons agree.
    text = "".join(c for c in text
                   if not unicodedata.category(c).startswith("M"))
    return text.replace("‌", "")


def leaks_answer(rendering: str, answer: str) -> bool:
    """True when *rendering* hands over *answer* as a readable token.

    Tokens at BOTH granularities — whole words including internal apostrophes
    and hyphens (so buku-buku matches), and their split pieces (so Man still
    matches inside man-passive). Taking only one of the two regressed real
    cases each way in the render guard; see hintLayers.test.ts."""
    target = _fold(answer).strip(" .,!?\"'")
    if not target:
        return False
    tokens: set[str] = set()
    for tok in _WORD.findall(_fold(rendering)):
        tokens.add(tok)
        tokens.update(p for p in re.split(r"[-'’]", tok) if p)
    if target in tokens:
        return True
    # a multi-word answer leaks as a phrase even when no single token is it
    return " " in answer.strip() and target in _fold(rendering)


def is_identity(source: str, rendering: str) -> bool:
    """True when the rendering is just the source handed back. Whitespace,
    case and terminal punctuation are not a translation."""
    a = " ".join(_fold(source).split()).strip(" .,!?¿¡\"'")
    b = " ".join(_fold(rendering).split()).strip(" .,!?¿¡\"'")
    return bool(a) and a == b


def blanks_intact(source: str, rendering: str) -> bool:
    """Every cloze blank in the source must survive, verbatim and in equal
    number. A rendering that spells the blank prints the hidden answer in the
    learner's own language above its gap (CHECKS.md §11)."""
    return all(source.count(b) == rendering.count(b) for b in BLANKS)


def locale_punctuation_ok(locale: str, rendering: str) -> bool:
    """Locale-specific marks a semantic grader lets slide."""
    for closing, opening in _INVERTED.get((locale or "").split("-")[0], []):
        if closing in rendering and opening not in rendering:
            return False
    return True


def safe_row(rows: list, i) -> object | None:
    """rows[i] with the model-controlled index VALIDATED. i = -1 would file
    the result under the last row without an error; anything not an int in
    [0, len) returns None and the result is dropped instead of misfiled."""
    if isinstance(i, bool) or not isinstance(i, int):
        return None
    if 0 <= i < len(rows):
        return rows[i]
    return None


# Where the part-of-speech predicate has been MEASURED. A locale is added
# here after its own 200-row gold set, the way `ar` got one (quality rule 1:
# a class, not an Arabic quirk — but the instrument is per language).
_POS_CHECKED_LOCALES = {"ar"}


def pos_mismatch(word: str, pos: str | None, definition: str | None,
                 rendering: str, *, locale: str = "") -> str | None:
    """Why *rendering* is in the wrong part of speech for its row, or None.

    Arabic verb rows only: `nominal_gloss_on_a_verb` is the predicate the
    18 Sep 2026 measurement stands behind (76% precision, 86% recall on 120
    judged rows), and it is imported lazily so this module stays free of
    the audit script's database imports. *word* is the course headword — the
    predicate needs it to spare an English `-ing` word, which a masdar
    glosses correctly. Any other locale or part of speech is not judged:
    a heuristic that was measured on one language and applied to nine is
    the kind of guard this program has already paid for once.
    """
    if (locale or "").split("-")[0] not in _POS_CHECKED_LOCALES:
        return None
    if (pos or "").strip() != "verb":
        return None
    from backend.services.quality.audit_locale_rows import (  # noqa: PLC0415
        nominal_gloss_on_a_verb,
    )
    if nominal_gloss_on_a_verb(word or "", pos, definition, rendering or ""):
        return "noun where the row needs a verb"
    return None


def gate(source: str, rendering: str, *, locale: str = "",
         answer: str = "", pos: str = "", word: str = "") -> str | None:
    """The reason to withhold *rendering*, or None when it may be stored.
    Order is severity: a leak is worse than an echo is worse than a mark.

    *pos* and *word* are the row's part of speech and headword, for a
    vocabulary gloss; a sentence or a label has neither and is not judged
    for part of speech (`pos_mismatch`)."""
    if not (rendering or "").strip():
        return "empty"
    if answer and leaks_answer(rendering, answer):
        return "contains the answer"
    if not blanks_intact(source, rendering):
        return "cloze blank altered"
    if is_identity(source, rendering):
        return "identical to the source"
    if not locale_punctuation_ok(locale, rendering):
        return "missing inverted punctuation"
    return pos_mismatch(word, pos, source, rendering, locale=locale)
