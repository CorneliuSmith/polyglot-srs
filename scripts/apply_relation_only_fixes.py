#!/usr/bin/env python3
"""Apply the relation-only repair: rewritten definitions into gloss_overrides.tsv.

Reads the workflow's `rows` (each confirmed by an independent checker) and
writes them as per-course overrides, after gates that encode what this repair
is FOR. The defect is a definition that names a grammatical relation and gives
no meaning; a repair that still trips `is_relation_only` has not repaired it,
and that is the one gate nothing else in the pipeline would catch.

Usage: apply_relfix.py <rows.json> [--apply]
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

BANNED = re.compile(r'\be\.g\.|\bi\.e\.|\bsee also\b|\bcf\.', re.IGNORECASE)

# Quality rule 28: a double quote inside a TSV field is csv-escaped into
# `""..""` noise, and the remedy the rule gives is to reword rather than to
# accept it. The relation shape wants to quote the lemma's meaning — `of
# byt' "to be"` — so the quotes are earned; single ones read the same and
# survive the writer untouched. 123 rows in the file already carry the noise
# from before this was noticed; they are not this pass's to rewrite.
SMART = {"“": "'", "”": "'", "‘": "'", "’": "'", '"': "'"}


def detune_quotes(text: str) -> str:
    for bad, good in SMART.items():
        text = text.replace(bad, good)
    return text
PARENS = re.compile(r"\([^)]*\)")


def meaning_of(text: str) -> str:
    """The definition with every parenthetical removed: the part that must
    carry the meaning.

    Two of the gates below run on THIS and not on the whole line, because the
    house shape puts the relation in parentheses and the relation is ALLOWED
    to name the lemma. Measured on this pass's first run: testing the whole
    line refused 248 good repairs out of 251 refusals.

    `debe` -> "he/she/it must, ought to; owes (third-person singular present
    of deber)" is not circular: `deber` sits in the parenthesis, which is
    where the learner needs it. And `сына` -> "(of) a son, a son's" does not
    lead with the relation — it leads with a parenthesised optional English
    word, which is how a genitive is glossed. Both are the shape the
    programme asked for (quality rule 19: verify every hit).
    """
    return " ".join(PARENS.sub(" ", text or "").split())


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


def validate(word: str, pos: str, before: str, after: str) -> str | None:
    """None when the rewrite may ship, else the reason it may not."""
    text = (after or "").strip()
    if not text:
        return "empty"
    if len(text) < 3:
        return "too short to be a definition"
    if len(text) > 220:
        return "longer than a learner definition"
    if "\t" in text or "\n" in text:
        return "carries a tab or newline"
    if BANNED.search(text):
        return "carries a citation or see-also"
    meaning = meaning_of(text)
    if len(meaning) < 3:
        return "nothing outside the parentheses: the meaning has to be there"
    # THE gate. The whole point of the repair is that this stops being true.
    if is_relation_only(text):
        return "still gives only the relation: not repaired"
    if is_circular(word, pos, meaning):
        return "circular: the meaning uses the headword"
    if text.strip() == (before or "").strip():
        return "unchanged"
    return None


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    payload = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload["rows"]
    apply_it = "--apply" in argv

    freq: dict[str, dict[str, dict]] = {}
    for row in rows:
        code = row["code"]
        if code not in freq:
            freq[code] = {r["word"]: r for r in read_tsv(DATA / f"{code}_frequency.tsv")}

    existing = read_tsv(OVERRIDES)
    columns = list(existing[0].keys()) if existing else ["language", "word", "pos", "en"]
    by_key = {(r["language"], r["word"]): r for r in existing}

    report = Counter()
    refused: list[dict] = []
    written: list[dict] = []

    for fix in rows:
        code, word = fix["code"], (fix.get("word") or "").strip()
        entry = freq[code].get(word)
        if entry is None:
            report["skipped_not_in_frequency_file"] += 1
            refused.append({**fix, "refused": "word is not in the frequency file"})
            continue
        pos = (entry.get("pos") or "").strip()
        before = (entry.get("en") or "").strip()
        after = (fix.get("definition") or "").strip()
        detuned = detune_quotes(after)
        if detuned != after:
            report["quotes_normalised"] += 1
            after = detuned
        why = validate(word, pos, before, after)
        if why:
            report[f"refused: {why}"] += 1
            refused.append({**fix, "refused": why, "pos": pos, "before": before})
            continue
        key = (code, word)
        if key in by_key:
            # An override here is the previous repair pass's own work on the
            # same row; this pass only reaches rows still reading as a bare
            # relation, so replacing it IS the repair.
            by_key[key]["en"] = after
            if not (by_key[key].get("pos") or "").strip():
                by_key[key]["pos"] = pos
            report["override_updated"] += 1
        else:
            row = {"language": code, "word": word, "pos": pos, "en": after}
            existing.append(row)
            by_key[key] = row
            report["override_added"] += 1
        written.append({"code": code, "rank": fix.get("rank"), "word": word,
                        "pos": pos, "was": before, "now": after})

    print(f"confirmed rows in: {len(rows)}")
    for key, n in sorted(report.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {key}")
    print(f"  {len(written):5}  to write")
    per = Counter(r["code"] for r in written)
    print("  per course: " + ", ".join(f"{c} {n}" for c, n in per.most_common()))

    out = Path(argv[0]).resolve().parent / "relfix-out"
    out.mkdir(exist_ok=True)
    (out / "written.json").write_text(json.dumps(written, ensure_ascii=False, indent=1),
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
