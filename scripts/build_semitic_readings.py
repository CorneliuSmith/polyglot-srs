"""Regenerate data/{ar,he,fa}_readings.tsv from the Wiktionary extracts.

These three scripts cannot be romanised by rule: Arabic and Hebrew write
consonants and leave the short vowels to the reader, and Persian inherits the
Arabic script with the same gap. `كتاب` carries no more information about its
vowels than `ktb` does in English. So the reading is a LOOKUP, exactly as Thai
turned out to be — see backend/services/nlp/thai_reading.py for why that was
the answer there too.

Needs the gitignored kaikki extracts:
    python scripts/build_semitic_readings.py

THE STANDARD, named per the owner's decision of 26 Aug 2026:

* **Arabic** — Wiktionary's Arabic transliteration, which is DIN 31635 with
  three departures it makes deliberately: `j` for ج (DIN has ǧ), `ḵ` for خ
  (DIN has ḫ) and `ḡ` for غ (DIN has ġ). Long vowels take macrons (ā ī ū),
  emphatics take dots below (ḥ ṣ ḍ ṭ ẓ). We make one further substitution for
  readability: Wiktionary writes hamza and ayin with the IPA letters ʔ and ʕ,
  which no learner reads; these become the ALA-LC ʼ and ʻ.
* **Hebrew** — Wiktionary's Modern Israeli transliteration: phonemic, with an
  ACUTE ACCENT ON THE STRESSED VOWEL (kélev, khatúl, érets). Stress is
  unpredictable in Hebrew and not written in the script, so that accent is the
  single most useful thing the layer carries.
* **Persian** — the modern Iranian convention, which writes the long a as `â`
  (salâm). Wiktionary carries BOTH that and the Classical `ā` (salām), often
  on the same entry; mixing them inside one course is the same defect as
  Hausa naming one aspect four ways, so the `â` form is preferred and a
  lone `ā` form is converted.

WHAT THIS DOES NOT SOLVE: an unvocalised word with two readings still has two.
`ספר` is séfer (book) or sapár (barber); the table takes Wiktionary's first
listing and cannot know which the sentence means. A homograph rate this layer
gets wrong is the honest limit of a lookup, and it wants a native reviewer.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

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

# Wiktionary writes hamza and ayin with IPA letters. No learner reads those.
IPA_TO_ALALC = {"ʔ": "ʼ", "ʕ": "ʻ"}


def bare(text: str) -> str:
    return MARKS.sub("", text or "")


def _clean(reading: str, code: str) -> str:
    for a, b in IPA_TO_ALALC.items():
        reading = reading.replace(a, b)
    if code == "fa":
        # one long-a convention per course, the modern Iranian â
        reading = reading.replace("ā", "â").replace("ō", "ô").replace("ē", "ê")
    return reading.strip()


def harvest(code: str) -> dict[str, str]:
    path = DATA / "raw" / f"{code}_kaikki.jsonl"
    if not path.exists():
        print(f"missing {path} — the kaikki extract is gitignored", file=sys.stderr)
        raise SystemExit(1)
    out: dict[str, str] = {}
    prefer_a: set[str] = set()   # fa: entries already seen with â
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            word = entry.get("word")
            if not word:
                continue
            key = bare(word)
            for form in entry.get("forms") or []:
                if "romanization" not in (form.get("tags") or []):
                    continue
                raw = (form.get("form") or "").strip()
                if not raw:
                    continue
                # Persian lists Classical and modern side by side; the modern
                # â form wins even when the Classical one was seen first.
                if code == "fa" and "â" in raw:
                    out[key] = _clean(raw, code)
                    prefer_a.add(key)
                elif key not in out or (code == "fa" and key not in prefer_a):
                    out.setdefault(key, _clean(raw, code))
                break
    return out


def main() -> int:
    for code in ("ar", "he", "fa"):
        table = harvest(code)
        # keep only what the course can use: its vocabulary plus every token
        # its sentences contain, so the file stays small enough to ship
        need: set[str] = set()
        with (DATA / f"{code}_frequency.tsv").open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                w = (row.get("word") or "").strip()
                if w:
                    need.add(bare(w))
        # ...and every token the GRAMMAR DRILLS use. Harvesting only the
        # frequency list and the sentence bank left the drills at 89% (he) and
        # 78% (fa) once new ones were authored, under the orthography guard's
        # 95% floor — the drills draw on vocabulary the sentence bank does not.
        grammar = DATA / "grammar" / f"{code}_grammar.json"
        if grammar.exists():
            data = json.loads(grammar.read_text(encoding="utf-8"))
            points = data if isinstance(data, list) else (
                data.get("points") or data.get("grammar_points") or [])
            for point in points:
                for drill in point.get("drills") or []:
                    for tok in (drill.get("sentence") or "").split():
                        tok = re.sub(r"[^؀-ۿ֐-׿]", "", tok)
                        if tok:
                            need.add(bare(tok))
                            for pre in ("ال", "وال", "بال", "فال", "لل", "و", "ف",
                                        "ب", "ل", "ك", "س", "ה", "ו", "ב", "ל",
                                        "כ", "ש", "מ"):
                                if tok.startswith(pre) and len(tok) > len(pre) + 1:
                                    need.add(bare(tok[len(pre):]))
        with (DATA / f"{code}_sentences.tsv").open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                for tok in (row.get("sentence") or "").split():
                    tok = re.sub(r"[^؀-ۿ֐-׿]", "", tok)
                    if tok:
                        need.add(bare(tok))
                        # ...and every clitic-stripped form the reader will try
                        for pre in ("ال", "وال", "بال", "فال", "لل", "و", "ف",
                                    "ب", "ل", "ك", "س", "ה", "ו", "ב", "ל", "כ", "ש", "מ"):
                            if tok.startswith(pre) and len(tok) > len(pre) + 1:
                                need.add(bare(tok[len(pre):]))
        covered = sorted(w for w in need if w in table)
        out = DATA / f"{code}_readings.tsv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
            writer.writerow(["word", "reading"])
            for w in covered:
                writer.writerow([w, table[w]])
        print(f"{code}: {len(covered):,}/{len(need):,} needed forms covered "
              f"({100 * len(covered) / max(1, len(need)):.0f}%) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
