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
# Letters only. The Arabic block contains its own PUNCTUATION — ، ؛ ؟ ٪ ۔ —
# and a range-based test swallows them, so `؟` was looked up as if it were a
# word and failed 18 Persian drills on its own.
SCRIPT = re.compile(
    "[^\u0620-\u064A\u066E-\u06D3\u06D5\u06E5-\u06EF\u06FA-\u06FF"
    "\u0620-\u063F\u0641-\u064A\u05D0-\u05EA\u05EF-\u05F4]"
)

# (prefix, what it contributes to the reading). Longest first at match time.
CLITICS = {
    "ar": [("وال", "wa-al-"), ("بال", "bi-al-"), ("فال", "fa-al-"),
           ("كال", "ka-al-"), ("لل", "li-l-"), ("ال", "al-"),
           ("و", "wa-"), ("ف", "fa-"), ("ب", "bi-"), ("ل", "li-"),
           ("ك", "ka-"), ("س", "sa-")],
    # HEBREW AND PERSIAN PEEL NOTHING. Both lists were removed on 26 Aug 2026
    # after a verification pass judged 22 of 108 Hebrew peeled forms wrong and
    # 10 of 11 Persian ones — and the errors were not near-misses:
    #
    #   מחברות  peeled to mi-ḥaverót, "from friends". It is makhbarót,
    #           notebooks. A different word entirely.
    #   הילדות  peeled to ha-yaldút, "childhood". It is ha-yeladót, the girls.
    #   בבית    peeled to be-báyit. Hebrew FUSES the preposition with the
    #           definite article — ba-báyit — and a peeler cannot see an
    #           article that is no longer written.
    #   بچهها   peeled to be-če-hâ by stripping a ب that is part of the stem;
    #           بچه is one word, bačče.
    #
    # Unvocalised Hebrew is genuinely ambiguous and its prefixes change the
    # vowel of what follows, so a mechanical split is guessing. Arabic keeps
    # its list: ال is a clean, unambiguous prefix that does not reshape the
    # stem, and its peeled forms verified sound.
    "he": [],
    "fa": [],
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


# Persian marks the plural and the possessive with SUFFIXES, which no prefix
# peeler can reach: بچه‌ها is بچه + ها. Hebrew stacks its prefixes instead —
# מהעבודה is מ + ה + עבודה — so that side needs a second pass, not a longer list.
SUFFIXES = {
    "fa": [("ها", "-hâ"), ("های", "-hâ-ye"), ("ان", "-ân"),
           ("ام", "-am"), ("ات", "-at"), ("اش", "-aš")],
}


def _peel(t: str, code: str, table: dict[str, str], depth: int = 0) -> str | None:
    """Strip one clitic and look the rest up; recurse so stacked prefixes work."""
    if depth > 2:
        return None
    for prefix, latin in CLITICS.get(code, []):
        # A one-letter prefix needs a real word behind it. Without this,
        # بچه (child) peels its ب and matches چه, giving be-če-hâ for بچه‌ها
        # where the answer is bače-hâ — a false reading, which is worse than
        # none because the learner cannot tell.
        if t.startswith(prefix) and len(t) - len(prefix) >= 3:
            rest = t[len(prefix):]
            if rest in table:
                return latin + table[rest]
            deeper = _peel(rest, code, table, depth + 1)
            if deeper:
                return latin + deeper
    for suffix, latin in SUFFIXES.get(code, []):
        if t.endswith(suffix) and len(t) > len(suffix) + 1:
            stem = t[: -len(suffix)]
            if stem in table:
                return table[stem] + latin
            # Persian writes the plural with a zero-width non-joiner as often
            # as not, and the stem may still carry its own prefix.
            deeper = _peel(stem, code, table, depth + 1)
            if deeper:
                return deeper + latin
    return None


def _one(token: str, code: str) -> str | None:
    table = _table(code)
    if not table:
        return None
    t = bare(SCRIPT.sub("", token))
    if not t:
        return None
    t = t.replace("\u200c", "")          # Persian zero-width non-joiner
    if t in table:
        return table[t]
    peeled = _peel(t, code, table)
    if peeled:
        return peeled
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
