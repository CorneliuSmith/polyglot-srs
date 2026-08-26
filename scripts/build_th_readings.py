"""Regenerate data/th_readings.tsv from the Thai Wiktionary extract.

The Thai reading layer is a LOOKUP, not a computation — see
`backend/services/nlp/thai_reading.py` for why (both computed engines failed
adversarial verification on ordinary words, and the failures were lexical).

Needs the gitignored kaikki extract and the optional Thai extra:
    pip install -e '.[thai]'
    python scripts/build_th_readings.py

Emits every distinct Thai token the course actually uses — vocabulary plus
segmented sentence tokens — with its Royal Institute (RTGS) romanisation and,
in a third column against a future tone layer, the Paiboon tone-marked form.

Two things it does NOT copy verbatim from Wiktionary:

* **Single-consonant entries are dropped.** They are letter NAMES (นอ หนู →
  "no"), not words, and the runtime segmenter is a longest-match walk — so a
  bare letter becomes filler for a word the table lacks, and `รู้จักคุณ` comes
  apart into `รู้` plus a meaningless `cho`. Without them the segmentation
  simply fails and the reading is withheld, which is the honest outcome.
* **Impossible codas are folded.** Wiktionary's loanword rows are spelled from
  the source language rather than transcribed: บราซิล as *bra-sil*, กรีซ as
  *kris*. Thai closes a syllable only on k ng t n p m or a vowel, and the same
  table gets the native words right (บอล bon, บิล bin), so those rows
  contradict it. 59 of 4,079.
"""
from __future__ import annotations

import csv
import json
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
KAIKKI = DATA / "raw" / "th_kaikki.jsonl"
OUT = DATA / "th_readings.tsv"


# RTGS final-consonant table, for the codas Thai cannot actually close on.
# ส ศ ษ ช ซ -> t, ฟ -> p, ล ฬ -> n.
FINAL_MAP = {"ch": "t", "s": "t", "f": "p", "l": "n"}


# Loanwords whose Wiktionary reading is missing the epenthetic syllable a
# medial ส forces: ออสเตรเลีย is ออด-สะ-เตฺร-เลีย, four syllables, but the
# column gives a three-syllable "os-tre-lia". The table's own NATIVE rows show
# the convention (ทศวรรษ thot-sa-wat, โฆษณา khot-sa-na), so these contradict
# their own file.
#
# They are EXCLUDED rather than corrected, and listed by hand rather than by
# rule. A rule keyed on "the word contains ส" fired on 71 rows and turned
# สวัสดี into *sa-wat-sa-di* — the most common word in the language. Placing
# the epenthesis correctly needs a syllable-aligned parse of the Thai, which
# is exactly the work this lookup table exists to avoid. Excluding them costs
# 0.5% of sentence coverage; guessing costs a learner the word.
EPENTHESIS_UNRESOLVED = {
    "ออสเตรเลีย", "ออสเตรีย", "คริสต์มาส", "สุขสันต์วันคริสต์มาส", "ดิสนีย์",
    "บาสเกตบอล", "ปาเลสไตน์", "พลาสติก", "ลิสบอน", "วิสกี้", "วิสคอนซิน",
    "อัฟกานิสถาน", "อิสตันบูล", "อิสราเอล", "อีสเตอร์", "เบสบอล", "เลสเบี้ยน",
    "เวสต์เวอร์จิเนีย", "แอสไพริน",
}


def _legal_codas(reading: str) -> str:
    """Fold a syllable-final consonant onto the one Thai really pronounces."""
    out = []
    for syllable in reading.split("-"):
        for suffix, replacement in FINAL_MAP.items():
            if syllable.endswith(suffix) and len(syllable) > len(suffix):
                syllable = syllable[:-len(suffix)] + replacement
                break
        out.append(syllable)
    return "-".join(out)


TONE_MARKS = "\u0300\u0301\u0302\u030C"   # low, high, falling, rising


def _tone_of(syllable: str) -> str:
    for ch in unicodedata.normalize("NFD", syllable):
        if ch in TONE_MARKS:
            return ch
    return ""


def _with_tone(syllable: str, mark: str) -> str:
    """Put *mark* on the syllable's first vowel."""
    if not mark:
        return syllable
    d = unicodedata.normalize("NFD", syllable)
    for i, ch in enumerate(d):
        if ch in "aeiou":
            return unicodedata.normalize("NFC", d[:i + 1] + mark + d[i + 1:])
    return syllable


def phonetics(rtgs: str, paiboon: str) -> str:
    """RTGS spelling carrying Paiboon's tone marks.

    RTGS is readable and toneless; Paiboon has the tone and 32% of it uses IPA
    letters (gɔɔ-rá-nii) a learner cannot read. Neither is usable alone. Both
    are hyphenated by syllable and every one of the 4,045 rows aligns
    one-to-one, so the tone transfers by position: kot-mai + gòt-mǎai gives
    kòt-mǎi — the letters the learner already reads, with the tone Thai needs.
    """
    left, right = rtgs.split("-"), paiboon.split("-")
    if len(left) != len(right):
        return ""
    return "-".join(_with_tone(a, _tone_of(b)) for a, b in zip(left, right))


def main() -> int:
    if not KAIKKI.exists():
        print(f"missing {KAIKKI} — the kaikki extract is gitignored", file=sys.stderr)
        return 1
    from pythainlp.tokenize import word_tokenize

    rtgs: dict[str, str] = {}
    tone: dict[str, str] = {}
    with KAIKKI.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("lang_code") != "th":
                continue
            word = entry.get("word")
            if not word:
                continue
            for sound in entry.get("sounds") or []:
                tags = sound.get("raw_tags") or []
                roman = (sound.get("roman") or "").strip()
                if not roman:
                    continue
                if "Royal Institute" in tags:
                    rtgs.setdefault(word, roman)
                elif "Paiboon" in tags:
                    tone.setdefault(word, roman)

    need: set[str] = set()
    with (DATA / "th_frequency.tsv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip()
            if word:
                need.add(word)
    with (DATA / "th_sentences.tsv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            for token in word_tokenize(
                    (row.get("sentence") or "").strip(), keep_whitespace=False):
                if any("฀" <= c <= "๿" for c in token):
                    need.add(token)

    covered = sorted(w for w in need if w in rtgs)
    # Two corrections to Wiktionary's own column, both the same class: its
    # LOANWORD rows are spelled from the source language rather than
    # transcribed, and contradict the native rows in the same table
    # (บอล bon, บิล bin). Thai closes a syllable on only k ng t n p m and the
    # vowels; RTGS maps everything else onto those. 59 rows, ~1%.
    covered = [w for w in covered
               if not (len(w) == 1 and "ก" <= w <= "ฮ")
               and w not in EPENTHESIS_UNRESOLVED]
    for word in covered:
        rtgs[word] = _legal_codas(rtgs[word])
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["word", "rtgs", "tone", "phonetics"])
        for word in covered:
            t = tone.get(word, "")
            writer.writerow([word, rtgs[word], t, phonetics(rtgs[word], t) if t else ""])
    print(f"{len(covered)}/{len(need)} tokens covered ({100 * len(covered) / len(need):.1f}%)")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
