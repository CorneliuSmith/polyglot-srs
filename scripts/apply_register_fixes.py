#!/usr/bin/env python3
"""Apply the register fixes a reviewer has accepted, and nothing else.

`docs/quality/ar-register-programme.md` §5 step 6. The input is
`data/ar_register_fixes.tsv` after reviewers have filled the `decision`
column; the output is committed files, and then the owner's refeed
(`docs/quality/refeed.md`). This script never touches the database — the
programme says so in §7 and CLAUDE.md says so for every pass.

**Only `accept` and `retire` do anything.** A blank decision is an unreviewed
row and is skipped, loudly. That is the whole contract of the queue: the
judge proposes, a human disposes, and a row nobody looked at is not a
decision. `reject` and `review` are counted and left alone.

Where each accepted fix lands, and why there rather than somewhere easier:

- **A sentence rewrite** goes into `data/ar_sentences.tsv`, in place, through
  **the same blank-ability gate as `apply_authored_sentences.py`**. A
  register-correct sentence the card cannot blank is a dead row: the card
  draws it, `find_cloze` returns nothing, and the learner gets the
  definition-only fallback instead (CHECKS §29). An MSA rewrite is very
  likely to change the headword's surface form — that is what rewriting
  Arabic does — so this gate rejects more here than it does for authored
  sentences, and every rejection is printed rather than counted.
- **A retirement** goes into `data/vocab_exclusions.tsv` with the reason
  `dialect`, never a deletion. A retired word keeps every learner's card and
  history and stops being drawn (`refeed.md` step 3). Deleting the row would
  regenerate on the next build (quality rule 27).
- **A gloss fix** goes into `data/gloss_overrides.tsv`, which outranks the
  seed (`docs/quality/ar.md`, 7 Sep).
- **A drill or explanation edit** goes into `data/grammar/ar_grammar.json` at
  the id's index, verified against the text it claims to replace, so an
  off-by-one in the round trip cannot file one point's rewrite under another
  (quality rule 28).
- **A culture note** is written only in the fixed shape the owner settled on:
  "In MSA this is X. In Egyptian you will hear Y, in Levantine Z." One per
  point. Anything else is refused, because the culture note is the ONE place
  dialect is allowed to live and an unlabelled comparison there is the defect
  this programme exists to remove.

    python -m scripts.apply_register_fixes --dry-run
    python -m scripts.apply_register_fixes
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
sys.path.insert(0, str(REPO))

from backend.services.extract import find_cloze  # noqa: E402
from backend.services.linked_forms import forms_of  # noqa: E402
from backend.services.span_finders import span_finder  # noqa: E402

FIXES = DATA / "ar_register_fixes.tsv"
SENTENCES = DATA / "ar_sentences.tsv"
FREQUENCY = DATA / "ar_frequency.tsv"
EXCLUSIONS = DATA / "vocab_exclusions.tsv"
OVERRIDES = DATA / "gloss_overrides.tsv"
GRAMMAR = DATA / "grammar" / "ar_grammar.json"

CODE = "ar"
ACTIONABLE = {"accept", "retire"}

# The owner's fixed shape for a culture note (decision 5, settled). Dialect
# lives here and nowhere else, and only when it is labelled as dialect.
CULTURE_NOTE = re.compile(
    r"^In MSA this is .+?\. In \w+ you will hear .+?(?:, in \w+ .+?)?\.$", re.S)

RETIRE_REASON = ("a dialect entry the frequency count treated as a word; the "
                 "course teaches Modern Standard Arabic "
                 "(docs/quality/ar-register-programme.md, 2026)")


def read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clozable(word: str, sentence: str) -> bool:
    """The only presence test that matters: the one the card runs at draw."""
    return find_cloze(sentence, forms_of(word, CODE), span_finder(CODE)) is not None


def _sid(word: str, sentence: str) -> str:
    import hashlib
    return "ar-sent-" + hashlib.sha1(
        f"{word}\t{sentence}".encode()).hexdigest()[:12]


def apply_sentences(rows: list[dict], report: Counter, rejects: list[str],
                    dry_run: bool) -> None:
    if not rows:
        return
    bank = read_tsv(SENTENCES)
    by_id = {}
    for n, row in enumerate(bank):
        by_id.setdefault(_sid(row["word"], row["sentence"]), []).append(n)
    changed = 0
    for fix in rows:
        targets = by_id.get(fix["id"])
        if not targets:
            rejects.append(f"{fix['id']}: no row in the bank with that id "
                           "(the sentence changed since the pass ran)")
            report["sentence_missing"] += 1
            continue
        after = (fix.get("after") or "").strip()
        if not after:
            rejects.append(f"{fix['id']}: accepted but no replacement text")
            report["sentence_empty"] += 1
            continue
        word = bank[targets[0]]["word"]
        if not clozable(word, after):
            rejects.append(
                f"{fix['id']}: the card cannot blank {word!r} in the rewrite "
                f"— {after[:48]!r}. Needs an authored replacement, not this one.")
            report["sentence_not_clozable"] += 1
            continue
        for n in targets:
            bank[n]["sentence"] = after
        changed += len(targets)
        report["sentence_rewritten"] += 1
    if changed and not dry_run:
        write_tsv(SENTENCES, bank, list(bank[0].keys()))


def apply_retirements(rows: list[dict], report: Counter,
                      dry_run: bool) -> set[str]:
    """Dialect headwords into `vocab_exclusions.tsv`. Returns what was retired.

    A retirement, never a deletion: the exclusion path keeps every learner's
    card and history and stops the word being drawn (`refeed.md` step 3),
    while deleting the row would simply regenerate on the next build
    (quality rule 27)."""
    if not rows:
        return set()
    freq = {r["rank"]: r for r in read_tsv(FREQUENCY)}
    existing = read_tsv(EXCLUSIONS)
    have = {(r["language"], r["word"]) for r in existing}
    added = []
    retired: set[str] = set()
    for fix in rows:
        rank = fix["id"].rsplit("-", 1)[-1]
        entry = freq.get(rank)
        if not entry:
            report["retire_unknown_rank"] += 1
            continue
        retired.add(entry["word"])
        if (CODE, entry["word"]) in have:
            report["retire_already"] += 1
            continue
        added.append({"language": CODE, "word": entry["word"],
                      "reason": RETIRE_REASON})
        have.add((CODE, entry["word"]))
        report["retired"] += 1
    if added and not dry_run:
        write_tsv(EXCLUSIONS, existing + added, ["language", "word", "reason"])
    return retired


def apply_glosses(rows: list[dict], retired_words: set[str], report: Counter,
                  dry_run: bool) -> None:
    """Gloss fixes into `gloss_overrides.tsv`, which outranks the seed.

    The file has FOUR columns — language, word, pos, en — and the gloss is
    `en`. Writing positionally into the third would have put English into the
    part-of-speech column of every row it touched.

    A word being retired in the same run never gets an override. Every
    override's word must still be in the frequency file (`TestNoDormantOverrides`,
    quality rule 51) and an exclusion orphans it — that guard has fired twice
    on this programme for exactly this, both times from a pass that excluded
    and glossed in one go."""
    if not rows:
        return
    freq = {r["rank"]: r for r in read_tsv(FREQUENCY)}
    existing = read_tsv(OVERRIDES)
    columns = list(existing[0].keys()) if existing else \
        ["language", "word", "pos", "en"]
    by_key = {(r["language"], r["word"]): r for r in existing}
    for fix in rows:
        rank = fix["id"].rsplit("-", 1)[-1]
        entry = freq.get(rank)
        after = (fix.get("after") or "").strip()
        if not entry or not after:
            report["gloss_skipped"] += 1
            continue
        if entry["word"] in retired_words:
            report["gloss_skipped_word_retired"] += 1
            continue
        key = (CODE, entry["word"])
        if key in by_key:
            by_key[key]["en"] = after
        else:
            row = {"language": CODE, "word": entry["word"],
                   "pos": entry.get("pos") or "", "en": after}
            existing.append(row)
            by_key[key] = row
        report["gloss_fixed"] += 1
    # An exclusion added by this same run orphans any override already on
    # that word, so those come out here rather than being left for the guard.
    if retired_words:
        before = len(existing)
        existing = [r for r in existing
                    if not (r["language"] == CODE and r["word"] in retired_words)]
        dropped = before - len(existing)
        if dropped:
            report["gloss_override_dropped_as_retired"] += dropped
    if (report["gloss_fixed"] or report["gloss_override_dropped_as_retired"]) \
            and not dry_run:
        write_tsv(OVERRIDES, existing, columns)


def apply_grammar(rows: list[dict], report: Counter, rejects: list[str],
                  dry_run: bool) -> None:
    if not rows:
        return
    raw = GRAMMAR.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    points = parsed["points"] if isinstance(parsed, dict) else parsed
    for fix in rows:
        after = (fix.get("after") or "").strip()
        parts = fix["id"].split("-")
        try:
            if fix["id"].startswith("ar-drill-"):
                p_i, d_i = int(parts[2]), int(parts[3])
                target = points[p_i]["drills"][d_i]
                field = "sentence"
            elif fix["id"].startswith("ar-expl-"):
                p_i, d_i = int(parts[2]), None
                target = points[p_i]
                field = "explanation"
            elif fix["id"].startswith("ar-note-"):
                p_i, d_i = int(parts[2]), None
                target = points[p_i]
                field = "culture_note"
            else:
                report["grammar_unknown_id"] += 1
                continue
        except (IndexError, ValueError):
            rejects.append(f"{fix['id']}: no such point or drill")
            report["grammar_missing"] += 1
            continue
        if field == "culture_note":
            if not CULTURE_NOTE.match(after):
                rejects.append(
                    f"{fix['id']}: a culture note must read 'In MSA this is X. "
                    f"In Egyptian you will hear Y, in Levantine Z.' — got "
                    f"{after[:60]!r}")
                report["note_wrong_shape"] += 1
                continue
            if (target.get("culture_note") or "").strip():
                report["note_already"] += 1
                continue
            if not dry_run:
                target["culture_note"] = after
            report["note_added"] += 1
            continue
        before = (fix.get("before") or "").strip()
        current = (target.get(field) or "").strip()
        if before and current and before != current:
            rejects.append(
                f"{fix['id']}: the text at that index is not the text the fix "
                "claims to replace — the file moved under the queue")
            report["grammar_drifted"] += 1
            continue
        if not after:
            report["grammar_empty"] += 1
            continue
        if not dry_run:
            target[field] = after
        report[f"grammar_{field}"] += 1
    if not dry_run and any(k.startswith("grammar_") and k not in
                           ("grammar_missing", "grammar_drifted", "grammar_empty",
                            "grammar_unknown_id") for k in report):
        indent = len(re.search(r"\n( +)\"", raw).group(1)) if re.search(r"\n( +)\"", raw) else 2
        out = json.dumps(parsed, ensure_ascii=False, indent=indent)
        GRAMMAR.write_text(out + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixes", type=Path, default=FIXES)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.fixes.exists():
        print(f"no fix queue at {args.fixes} — run the register pass with "
              "--apply first, then have reviewers fill the decision column.")
        return 1
    rows = read_tsv(args.fixes)
    decisions = Counter((r.get("decision") or "").strip().lower() or "(blank)"
                        for r in rows)
    actionable = [r for r in rows
                  if (r.get("decision") or "").strip().lower() in ACTIONABLE]
    print(f"{len(rows)} queued · decisions {dict(decisions)}")
    if decisions["(blank)"]:
        print(f"  {decisions['(blank)']} rows have NO decision and are skipped. "
              "Nothing is applied unreviewed (programme §5 step 5).")
    if not actionable:
        print("nothing to apply.")
        return 0

    report: Counter = Counter()
    rejects: list[str] = []
    retire = [r for r in actionable
              if (r.get("decision") or "").strip().lower() == "retire"]
    accept = [r for r in actionable
              if (r.get("decision") or "").strip().lower() == "accept"]

    # Retirements first: a word retired in this run must not also receive a
    # gloss override, and any override it already has has to come out.
    retired_words = apply_retirements(
        [r for r in retire if r["store"] == "vocab"], report, args.dry_run)
    apply_sentences([r for r in accept if r["store"] == "sentences"],
                    report, rejects, args.dry_run)
    apply_glosses([r for r in accept if r["store"] == "vocab"],
                  retired_words, report, args.dry_run)
    apply_grammar([r for r in accept if r["store"] == "grammar"],
                  report, rejects, args.dry_run)
    for row in retire:
        if row["store"] != "vocab":
            rejects.append(f"{row['id']}: only a vocabulary entry can be retired; "
                           "a dialect-only SENTENCE is deleted by the prune, not here")

    print("\napplied:" if not args.dry_run else "\nwould apply:")
    for key, count in sorted(report.items()):
        print(f"   {key:26s} {count}")
    if rejects:
        print(f"\nrefused {len(rejects)}:")
        for line in rejects[:25]:
            print(f"   {line}")
        if len(rejects) > 25:
            print(f"   ... and {len(rejects) - 25} more")
    if args.dry_run:
        print("\nDRY RUN — nothing written.")
    else:
        print("\nWritten to the committed files. The owner's refeed is next:")
        print("   docs/quality/refeed.md — snapshot, seeder.run, reconcile --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
