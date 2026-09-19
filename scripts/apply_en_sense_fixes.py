#!/usr/bin/env python3
"""Apply the English sense pass: maker-checker findings into gloss_overrides.tsv.

Reads the workflow's `confirmed` list (rows where BOTH the maker and the
checker said the existing definition is not the sense a learner meets, and the
checker supplied a replacement it stands behind), validates every replacement
mechanically, and writes the survivors as `en` overrides.

Two things it deliberately does NOT do:

- It never writes a row the checker did not confirm, and never one whose
  confidence is below 0.7 on either side. `unsure` routes to a human.
- It never RETIRES anything. A large share of the findings are personal
  names, and the 25 Aug rule for those is the owner's; this script counts
  them and writes them to a separate report for the write-up, so the decision
  is taken with a number rather than in passing.

It takes the output of either English definition pass, which differ in one
way that matters: the SENSE pass repairs a definition that exists and the row
already has a part of speech, while the BLANK pass writes the first definition
a row has ever had and must supply the part of speech too (those rows carry
none — the extractor gave up on them entirely). A row carrying `definition`
is read as the second shape, `checker_replacement` as the first.

Usage: apply_en_sense_fixes.py <confirmed.json> [--apply]
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.services.quality.audit_content import (  # noqa: E402
    is_circular,
    is_relation_only,
)

DATA = REPO / "data"
OVERRIDES = DATA / "gloss_overrides.tsv"
FREQUENCY = DATA / "en_frequency.tsv"
CODE = "en"

# A replacement that is itself only a name description teaches nothing a
# learner can produce the headword from — the 25 Aug rule's own criterion.
# These are counted and reported, never written, because retiring is a
# decision the owner already took once with a table in front of them.
# The head form must be the WHOLE gist: "a male given name", "a surname".
# It ends there, or continues with a qualifier about the name itself. Without
# the tail this matched "the name given to a book, film, song or other work" —
# the correct definition of `title` — and routed a real repair into the
# retirement bucket. One false positive in 120, found by re-reading the bucket
# rather than the code (quality rule 19: verify every hit).
NAME_ONLY = re.compile(
    r"^(a |an |the )?(male |female |masculine |feminine |english |common )*"
    r"(given |first |fore|sur|family |place |proper )?name"
    r"\s*(\(|,|;|$|\bfor\b|\bshort for\b|\bused\b|\bof (welsh|irish|greek|latin|hebrew)\b)",
    re.IGNORECASE,
)
NAME_ANYWHERE = re.compile(
    r"\b(given name|first name|surname|family name|forename|"
    r"a male name|a female name|diminutive of the name)\b",
    re.IGNORECASE,
)

# A learner definition is one line. An example sentence, a citation or a
# "see also" is the shape the maker charter forbids.
BANNED = re.compile(r'["“”]|\be\.g\.|\bi\.e\.|\bsee also\b|\bcf\.', re.IGNORECASE)

# The English half of `audit_locale_rows.nominal_gloss_on_a_verb`: a verb row
# whose definition opens with an article is describing a thing, not an action
# — "whistle (verb): a small instrument you blow" is the defect that pass
# measured in Arabic at 23% of divergences, and the maker charter forbids it
# in every locale. Cheap and one-directional; the checker was asked the same
# question in words, so this is the mechanical half of two-signal confirmation
# (quality rule 71).
NOUN_SHAPED = re.compile(r"^(a|an|the)\s", re.IGNORECASE)
VERB_POS = {"verb", "v", "vb"}

# Asked for a definition and given a verdict about the row. Two judges in a
# row wrote "not an English word - a corpus artefact with no sense to define;
# the card should be retired" into the field a learner reads, which is a
# perfectly correct observation and a catastrophic definition. Those rows are
# real findings and belong in the retire bucket, not the gloss file. The rule
# generalises past this pass: any field a model fills needs a predicate for
# "the model answered a different question".
META = re.compile(
    r"\bnot an? (english |real |actual )?word\b"
    r"|\bcorpus artefact\b|\bcorpus artifact\b"
    r"|\bshould be retired\b|\bthe card should\b|\bno sense to define\b"
    r"|\bretire the (row|card|entry)\b|\bno definition is possible\b"
    r"|\bextraction artefact\b|\bextraction artifact\b|\bcorrupted spelling\b"
    r"|\bno (everyday|real|usable) (sense|noun sense|meaning)\b"
    r"|\bthis (row|card|entry|token)\b|\bfor a learner card\b"
    r"|\bnot a (word|sense|definition)\b|\bdefines the\b",
    re.IGNORECASE,
)


def read_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(r) for r in csv.DictReader(handle, delimiter="\t")]


def write_tsv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t",
                                lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def validate(word: str, pos: str, replacement: str) -> str | None:
    """None when the replacement may ship, else the reason it may not."""
    text = (replacement or "").strip()
    if not text:
        return "empty"
    if len(text) < 3:
        return "too short to be a definition"
    if len(text) > 200:
        return "longer than a learner definition"
    if "\t" in text or "\n" in text:
        return "carries a tab or newline"
    if BANNED.search(text):
        return "carries a quote, citation or see-also"
    if is_circular(word, pos, text):
        return "circular: uses the headword"
    if is_relation_only(text):
        return "gives a relation and no meaning"
    if NAME_ONLY.match(text) or NAME_ANYWHERE.search(text):
        return "names a name: the 25 Aug retirement rule, not a gloss fix"
    if pos.strip().lower() in VERB_POS and NOUN_SHAPED.match(text):
        return "noun-shaped definition on a verb row"
    if META.search(text):
        return "a verdict about the row, not a definition: a retirement candidate"
    return None


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    payload = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    confirmed = payload if isinstance(payload, list) else payload["confirmed"]
    apply_it = "--apply" in argv

    freq = {r["word"]: r for r in read_tsv(FREQUENCY)}
    existing = read_tsv(OVERRIDES)
    columns = list(existing[0].keys()) if existing else ["language", "word", "pos", "en"]
    by_key = {(r["language"], r["word"]): r for r in existing}

    report = Counter()
    refused: list[dict] = []
    names: list[dict] = []
    retire: list[dict] = []
    written: list[dict] = []

    for fix in confirmed:
        word = (fix.get("word") or "").strip()
        entry = freq.get(word)
        if entry is None:
            report["skipped_not_in_frequency_file"] += 1
            refused.append({**fix, "refused": "word is not in en_frequency.tsv"})
            continue
        # The blank pass supplies the part of speech, because the rows it
        # writes have none; the sense pass repairs a row that already has one,
        # and must never overwrite it from a judge's opinion.
        supplied_pos = (fix.get("pos") or "").strip()
        pos = (entry.get("pos") or "").strip() or supplied_pos
        replacement = (fix.get("checker_replacement")
                       or fix.get("definition") or "").strip()
        why = validate(word, pos, replacement)
        if why:
            report[f"refused: {why}"] += 1
            row = {**fix, "refused": why, "pos": pos}
            bucket = (names if "names a name" in why
                      else retire if "retirement candidate" in why
                      else refused)
            bucket.append(row)
            continue
        key = (CODE, word)
        if key in by_key:
            # An override is a decision an earlier pass took, sometimes with a
            # reviewer behind it. This pass reports the disagreement rather
            # than quietly winning it.
            report["skipped_already_overridden"] += 1
            refused.append({**fix, "pos": pos,
                            "refused": "an override already exists",
                            "existing": by_key[key].get("en", "")})
            continue
        row = {"language": CODE, "word": word, "pos": pos, "en": replacement}
        existing.append(row)
        by_key[key] = row
        report["override_added"] += 1
        written.append({"rank": fix.get("rank"), "word": word, "pos": pos,
                        "was": fix.get("evidence"), "now": replacement})

    print(f"confirmed findings in: {len(confirmed)}")
    for key, n in sorted(report.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {key}")
    print(f"  {len(written):5}  overrides to write (new rows only)")
    print(f"  {len(names):5}  personal names (owner's 25 Aug rule, not written)")
    print(f"  {len(retire):5}  retirement candidates: not words (not written)")

    out = Path(argv[0]).resolve().parent / "en-sense-out"
    out.mkdir(exist_ok=True)
    (out / "written.json").write_text(json.dumps(written, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    (out / "names.json").write_text(json.dumps(names, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    (out / "retire.json").write_text(json.dumps(retire, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    (out / "refused.json").write_text(json.dumps(refused, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"reports in {out}")

    if apply_it and written:
        existing.sort(key=lambda r: (r.get("language", ""), r.get("word", "")))
        write_tsv(OVERRIDES, existing, columns)
        print(f"WROTE {OVERRIDES} ({len(existing)} rows)")
    elif not apply_it:
        print("dry run; pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
