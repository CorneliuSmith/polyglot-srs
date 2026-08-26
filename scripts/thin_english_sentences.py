"""Thin the English example-sentence bank to the best few per word, with variety.

English carries 202,772 rows over 125,387 distinct (word, sentence) pairs — a
median of 13 different sentences per headword, against 2 to 3 in every other
course. That surplus costs more than it earns: a learner sees one example per
card, and glossing the unthinned set would cost more than the other 26 courses
combined.

Owner decision, 26 Aug 2026: reduce to the best few per word, selected FOR
VARIETY rather than by taking the first N.

What "best with variety" means here, in order of what the selection actually
optimises:

* **A usable length.** Fragments teach nothing — the bank contains "I am." and
  "I am!" as separate examples of *I*. Sentences of 5 to 14 words score
  highest; 1 to 2 words score near zero.
* **Different shapes.** After the first pick, each further sentence is scored
  down for resembling one already chosen: same length band, same opening word,
  same final punctuation. This is what stops four declaratives of identical
  length being "the best four".
* **Translation reach.** A pair already rendered into several locales serves
  more learners than one rendered into none.
* **The word must actually appear.** A few rows list a headword the sentence
  does not contain; those are dropped rather than kept as filler.

Rows for a kept sentence are kept in EVERY locale — the thinning removes
sentences, never translations.

    python scripts/thin_english_sentences.py            # report only
    python scripts/thin_english_sentences.py --apply
"""
from __future__ import annotations

import collections
import csv
import io
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
SRC = DATA / "en_sentences.tsv"
KEEP_PER_WORD = 4

WORDS = re.compile(r"[A-Za-z']+")


def _tokens(text: str) -> list[str]:
    return WORDS.findall(text or "")


def _length_score(n: int) -> float:
    if n <= 2:
        return 0.05
    if n <= 4:
        return 0.45
    if n <= 14:
        return 1.0
    if n <= 20:
        return 0.6
    return 0.25


def _band(n: int) -> int:
    return min(n // 3, 6)


def choose(word: str, options: list[tuple[str, int]]) -> list[str]:
    """options: (sentence, locale_count) -> the sentences to keep."""
    scored = []
    for sentence, locales in options:
        toks = _tokens(sentence)
        if not any(t.lower() == word.lower() for t in toks):
            continue                        # headword absent: not an example of it
        scored.append((sentence, toks, locales))
    if not scored:
        # keep the single longest so the word is never left with nothing
        return [max(options, key=lambda o: len(_tokens(o[0])))[0]] if options else []

    picked: list[str] = []
    picked_tokens: list[set[str]] = []
    used_bands: set[int] = set()
    used_openers: set[str] = set()
    used_endings: set[str] = set()
    while scored and len(picked) < KEEP_PER_WORD:
        # -inf, not a fixed floor: the overlap penalty can drive every
        # candidate below any constant, which left best as None.
        best, best_score = None, float("-inf")
        for sentence, toks, locales in scored:
            score = _length_score(len(toks)) + min(locales, 4) * 0.12
            if _band(len(toks)) in used_bands:
                score -= 0.35
            if toks and toks[0].lower() in used_openers:
                score -= 0.30
            if sentence[-1:] in used_endings:
                score -= 0.12
            # Word-overlap, because the opener check only sees one token:
            # "I think he did it." and "I think he has done it." both survived
            # it while being the same example twice.
            lowered = {t.lower() for t in toks}
            for other in picked_tokens:
                overlap = len(lowered & other) / max(1, len(lowered | other))
                if overlap > 0.5:
                    score -= 1.2 * overlap
            if score > best_score:
                best, best_score = (sentence, toks), score
        sentence, toks = best
        picked.append(sentence)
        picked_tokens.append({t.lower() for t in toks})
        used_bands.add(_band(len(toks)))
        if toks:
            used_openers.add(toks[0].lower())
        used_endings.add(sentence[-1:])
        scored = [s for s in scored if s[0] != sentence]
    return picked


def main(apply: bool) -> int:
    raw = SRC.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in raw[:4000] else "\n"
    rows = list(csv.DictReader(io.StringIO(raw), delimiter="\t"))
    fields = list(rows[0].keys())

    locales: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for r in rows:
        locales[((r.get("word") or "").strip(), (r.get("sentence") or "").strip())].add(
            r.get("translation_locale") or "")
    by_word: dict[str, list[tuple[str, int]]] = collections.defaultdict(list)
    for (word, sentence), locs in locales.items():
        by_word[word].append((sentence, len(locs)))

    keep: set[tuple[str, str]] = set()
    for word, options in by_word.items():
        for sentence in choose(word, options):
            keep.add((word, sentence))

    kept = [r for r in rows
            if ((r.get("word") or "").strip(), (r.get("sentence") or "").strip()) in keep]
    print(f"words              {len(by_word):,}")
    print(f"(word, sentence)   {len(locales):,} -> {len(keep):,}")
    print(f"rows               {len(rows):,} -> {len(kept):,}")
    print(f"sentences per word {len(locales) / len(by_word):.1f} -> {len(keep) / len(by_word):.1f}")
    if not apply:
        print("\n(report only — pass --apply to write)")
        return 0
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, delimiter="\t", lineterminator=newline)
    writer.writeheader()
    writer.writerows(kept)
    SRC.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"\nwrote {SRC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
