"""Arabic, Hebrew and Persian readings — looked up, with the clitics peeled.

These scripts write consonants and leave the short vowels to the reader. `كتاب`
carries no more information about its vowels than `ktb` does in English, so no
rule can romanise them and the reading has to be a LOOKUP. That is the same
answer Thai reached (`thai_reading.py`) after a computed romanizer failed
adversarial verification, and it is the same source: the Wiktionary extracts
already on disk.

`data/{ar,he,fa}_readings.tsv` are those tables, built by
`scripts/build_semitic_readings.py`, which also names the standard each course
follows and the two substitutions made for readability.

**The clitics are what makes it work.** Arabic glues the article, conjunctions
and prepositions onto the following word, so a sentence token frequently is not
a dictionary headword: `والكتاب` is و + ال + كتاب. Looking up bare tokens covered
65% of Arabic sentence tokens and left only 15% of sentences fully covered.
Peeling the clitics and re-looking-up takes that to 99% and 97%. Hebrew and
Persian get the same treatment for their own prefix sets.

**Full coverage or no reading.** If any token of a sentence has no entry, this
returns "" rather than a partial line — a line with a hole in it is read as a
whole by someone who cannot see the hole.

**The honest limit: homographs.** An unvocalised word with two readings still
has two. Hebrew `ספר` is séfer (a book) or sapár (a barber), and the table
takes Wiktionary's first listing without knowing which the sentence means. A
lookup cannot resolve that, and it is the part that wants a native reviewer.
"""
from __future__ import annotations

import csv
import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

DATA = Path(__file__).resolve().parents[3] / "data"
LANGS = ("ar", "he", "fa")

# Diacritics only, by CODEPOINT. Writing these ranges with literal characters
# got them wrong in a way that looked plausible: [ؐ-ً] swallows the entire
# Arabic alphabet, so bare("كتاب") returned "" and every Arabic lookup missed.
#   U+064B-U+065F, U+0670, U+06D6-U+06ED  Arabic harakat and Quranic marks
#   U+0640                                tatweel (a stretch, not a letter)
#   U+0591-U+05BD, U+05BF, U+05C1-2, U+05C4-5, U+05C7  Hebrew points
MARKS = re.compile(
    "[\\u064B-\\u065F\\u0670\\u06D6-\\u06ED\\u0640"
    "\\u0591-\\u05BD\\u05BF\\u05C1-\\u05C2\\u05C4-\\u05C5\\u05C7]"
)
SCRIPT = re.compile(r"[^؀-ۿ֐-׿]")

# (prefix, what it contributes to the reading). Longest first at match time.
CLITICS = {
    "ar": [("وال", "wa-al-"), ("بال", "bi-al-"), ("فال", "fa-al-"),
           ("كال", "ka-al-"), ("لل", "li-l-"), ("ال", "al-"),
           ("و", "wa-"), ("ف", "fa-"), ("ب", "bi-"), ("ل", "li-"),
           ("ك", "ka-"), ("س", "sa-")],
    # Hebrew's one-letter particles: the definite ה, and ו ב ל כ ש מ.
    "he": [("ה", "ha-"), ("ו", "ve-"), ("ב", "be-"), ("ל", "le-"),
           ("כ", "ke-"), ("ש", "she-"), ("מ", "mi-")],
    # Persian keeps most particles separate; the productive bound ones are the
    # verbal مى/نمى and the conjunction و.
    "fa": [("نمی", "nemi-"), ("می", "mi-"), ("و", "va-"), ("ب", "be-")],
}


def bare(text: str) -> str:
    return MARKS.sub("", text or "")


@lru_cache(maxsize=8)
def _table(code: str) -> dict[str, str]:
    path = DATA / f"{code}_readings.tsv"
    table: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                w = (row.get("word") or "").strip()
                r = (row.get("reading") or "").strip()
                if w and r:
                    table[w] = r
    except OSError as exc:  # noqa: BLE001 — a missing table must never 500
        logger.warning("%s readings table unavailable: %s", code, exc)
    return table


def _one(token: str, code: str) -> str | None:
    table = _table(code)
    if not table:
        return None
    t = bare(SCRIPT.sub("", token))
    if not t:
        return None
    if t in table:
        return table[t]
    for prefix, latin in CLITICS.get(code, []):
        if t.startswith(prefix) and len(t) > len(prefix) + 1:
            rest = table.get(t[len(prefix):])
            if rest:
                return latin + rest
    # Arabic ta marbuta alternates with ha in the headword.
    if t.endswith("ة") and (t[:-1] + "ه") in table:
        return table[t[:-1] + "ه"]
    return None


def semitic_reading(text: str, code: str) -> str:
    """A romanised reading of *text*, or "" when the tables do not cover it.
    Non-script runs pass through verbatim, which is what keeps a cloze blank a
    blank — romanising the raw sentence would print the hidden word in Latin
    letters above its own gap (CHECKS.md §11)."""
    if not text or code not in LANGS:
        return ""
    out: list[str] = []
    for token in text.split():
        if not SCRIPT.sub("", token):
            out.append(token)      # punctuation, {{answer}}, Latin, digits
            continue
        reading = _one(token, code)
        if reading is None:
            return ""
        # keep whatever punctuation hung off the token
        trail = "".join(c for c in token if c in ".,!?؟،;:\"')]}")
        out.append(reading + trail)
    return " ".join(out).strip()
