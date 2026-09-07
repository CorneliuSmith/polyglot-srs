#!/usr/bin/env python3
"""Gate authored definitions and write them into `data/gloss_overrides.tsv`.

A card shows the DEFINITION and asks the learner to type the word, so a
definition is the layer that decides whether the card is answerable at all.
CHECKS §28 measured that: of 128 top-band cards that fail to determine their
answer, the cheapest repair was the definition for 77 of them — more than the
hint, the sentence and the grading policy combined.

**Every rule here is one the programme has already paid for.**

*Circular* — `have` glossed "have or possess" tells a learner nothing
(CHECKS §1). The check is `audit_content.is_circular`, imported rather than
re-implemented so the gate and the audit cannot drift.

*Self-quoting, and why it is scoped to English* — the circular rule and the
"opens with its own word" rule run on the ENGLISH course only. Everywhere
else the definition is in a different language from the headword, so a match
is a coincidence or a correct translation: Catalan `ha` really does mean
"has", Spanish `me` really does mean "me", and Swahili `na` is glossed "and;
with (kuwa na, to have)" on purpose. Applied to all 27 these two rules
refused 864 shipped overrides, none of them defects — the same result
`_audit_circular_glosses` documents and scopes away. What survives
everywhere is the one rule that cannot be a coincidence: a definition that
is nothing but the headword teaches nothing.

*Not a label* — "a pronoun" is a part of speech, not a definition.

*Unchanged* — a proposal identical to what is already shown is not a fix,
and writing it would inflate the override count with nothing behind it
(quality rule 31: never let a number stand in for the work).

*Unknown word* — a definition for a headword the course does not have is
either a typo or a hallucination; it must not create a row.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
sys.path.insert(0, str(REPO))

from backend.services.quality.audit_content import is_circular  # noqa: E402

OVERRIDES = DATA / "gloss_overrides.tsv"
# Set from the shipped corpus rather than from taste: 2,699 overrides run to
# a median of 76 characters, a 95th percentile of 224 and a longest of 414
# (a Dutch entry carrying two senses and their collocations). A cap of 160
# would have refused 495 of them, none of them defects. 480 leaves headroom
# above everything written so far while still catching a runaway paste.
MAX_CHARS = 480

# A definition that is only a grammatical label leaves the learner with
# nothing to produce the word from.
LABELS = {
    "noun", "verb", "adjective", "adverb", "pronoun", "preposition",
    "conjunction", "particle", "article", "determiner", "interjection",
    "numeral", "classifier", "auxiliary", "a noun", "a verb", "an adjective",
    "an adverb", "a pronoun", "a preposition", "a conjunction", "a particle",
}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").casefold())
    return "".join(c for c in text if not unicodedata.category(c).startswith("M"))


def words_of(text: str) -> list[str]:
    out, cur = [], ""
    for ch in text or "":
        if unicodedata.category(ch).startswith(("L", "M")) or (cur and ch in "'’-"):
            cur += ch
        else:
            if cur:
                out.append(cur)
                cur = ""
    if cur:
        out.append(cur)
    return out


def read_overrides() -> list[dict]:
    if not OVERRIDES.exists():
        return []
    with OVERRIDES.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def course_words(code: str) -> dict[str, str]:
    """word -> current definition, from the frequency list."""
    path = DATA / f"{code}_frequency.tsv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return {
            (r.get("word") or "").strip(): (r.get("en") or "").strip()
            for r in csv.DictReader(fh, delimiter="\t")
            if (r.get("word") or "").strip()
        }


def check(code: str, word: str, pos: str, definition: str,
          known: dict[str, str], current: dict[str, str]) -> str | None:
    """The reason to refuse, or None to accept."""
    definition = (definition or "").strip()
    if not definition:
        return "empty"
    if word not in known:
        return "word is not in this course"
    if len(definition) > MAX_CHARS:
        return f"longer than {MAX_CHARS} characters"
    if fold(definition).strip(" .") in {fold(x) for x in LABELS}:
        return "a part-of-speech label, not a definition"
    folded_word = fold(word)
    body = words_of(fold(definition))
    if not body:
        return "no words in it"
    # A single-word gloss is fine and common — Italian `e` is "and" — so the
    # only thing a one-word definition can fail on is being the word itself.
    if len(body) == 1 and body[0] == folded_word:
        return "is the word it defines"
    if code == "en":
        # English only, for the reason in the module docstring: elsewhere the
        # definition is in another language and a match is a translation.
        if body and body[0] == folded_word:
            return "opens with the word it defines"
        if is_circular(word, pos, definition):
            return "explains the word with the word"
    was = current.get(word) or known.get(word, "")
    if fold(definition).strip(" .;:!?") == fold(was).strip(" .;:!?"):
        return "identical to the definition already shown"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results", nargs="+",
                    help="JSON: {code: [{word, pos, definition}]}")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    proposals: dict[str, list[dict]] = {}
    for path in args.results:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        for code, items in raw.items():
            proposals.setdefault(code, []).extend(items)

    rows = read_overrides()
    existing = {(r["language"], r["word"]): r for r in rows}
    accepted, rejected = [], {}
    for code, items in sorted(proposals.items()):
        known = course_words(code)
        current = {w: (existing.get((code, w)) or {}).get("en", "")
                   for w in known}
        for item in items:
            word = (item.get("word") or "").strip()
            pos = (item.get("pos") or "").strip()
            definition = (item.get("definition") or "").strip()
            why = check(code, word, pos, definition, known, current)
            if why:
                rejected.setdefault(why, []).append((code, word, definition))
                continue
            accepted.append({"language": code, "word": word, "pos": pos,
                             "en": definition})

    print(f"{len(accepted):,} definitions accepted for "
          f"{len({a['language'] for a in accepted})} courses")
    for why, items in sorted(rejected.items(), key=lambda kv: -len(kv[1])):
        print(f"   rejected {len(items):>4}  {why}")
        for code, word, definition in items[:2]:
            print(f"        {code} {word!r}: {definition[:60]}")
    if args.dry_run or not accepted:
        print("DRY RUN — nothing written." if args.dry_run else "nothing to write")
        return 0

    for a in accepted:
        key = (a["language"], a["word"])
        if key in existing:
            existing[key].update(pos=a["pos"], en=a["en"])
        else:
            rows.append(a)
            existing[key] = a
    rows.sort(key=lambda r: (r["language"], r["word"]))
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=["language", "word", "pos", "en"],
                            delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in
                         ("language", "word", "pos", "en")})
    OVERRIDES.write_text(out.getvalue(), encoding="utf-8", newline="")
    print(f"wrote {len(rows):,} rows to {OVERRIDES.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
