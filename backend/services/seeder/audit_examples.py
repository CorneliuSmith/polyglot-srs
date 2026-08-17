"""Which words a learner meets the same example sentence for, every time.

The complaint this answers is "I'm not seeing the diversity". That turned out
not to be a prompt problem: the examples a learner meets are harvested Tatoeba
rows sitting verbatim in the seed TSVs, so strengthening the *generation*
prompts improved sentences nobody reads. It is a supply problem, and it has two
shapes — a word with one example ever, and a word with several examples that
share one structural frame ("Он идёт." "Он ест." "Он спит."). Neither is
visible to any existing test, which is why this module exists.

Two limits, stated here and printed in the report, because a silent cap reads
as coverage:

  * This reads the seed TSVs, not the database. The database also carries
    AI-generated and reviewer-edited examples, so every count here is an UPPER
    BOUND on the real gap. Use it to scope work, not to declare a language done.
  * The shape heuristic is orthographic and monolingual. A Korean or Thai token
    count does not mean what a Spanish one means, so those two languages need a
    native reader to check fifty rows before their numbers are trusted.

Usage:
    python -m backend.services.seeder.audit_examples
    python -m backend.services.seeder.audit_examples --language ko
    python -m backend.services.seeder.audit_examples --band 1000 --json out.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

# backend/services/seeder/audit_examples.py -> repo root.
REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"

LANGUAGES = tuple(
    "ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko "
    "la id tl he fa".split()
)

# The band a learner actually reaches in a first year. The whole scoping
# argument for this work is that the top of the frequency list is where a thin
# example set is felt; fixing rank 9,000 costs the same and is never seen.
DEFAULT_BAND = 1000

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Below this many examples a word has nothing to rotate through.
THIN_BELOW = 2
# At or below this many distinct shapes the set is one frame with the slot
# swapped, however many sentences it nominally holds.
MONOTONE_AT_OR_BELOW = 2


def shape(sentence: str, word: str) -> tuple[int, tuple[str, ...]]:
    """A crude structural fingerprint: length, plus the opening tokens with the
    target word removed.

    Deliberately crude. It catches the reported failure — same length, same
    frame, one slot swapped — and does not pretend to measure semantic variety,
    which needs a model and would make the detector cost as much as the fix.
    The word itself is dropped so that "Он идёт" and "Он ест" collide rather
    than reading as two different openings.
    """
    tokens = _TOKEN_RE.findall(sentence.casefold())
    target = word.casefold()
    without = [t for t in tokens if t != target]
    return (len(tokens), tuple(without[:3]))


def _read_sentences(path: Path, into: dict[str, set[str]]) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip()
            sentence = (row.get("sentence") or "").strip()
            if word and sentence:
                into.setdefault(word.casefold(), set()).add(sentence)


def load_examples(code: str) -> dict[str, set[str]]:
    """word -> its distinct example sentences, from BOTH seed locations.

    Both are read because neither alone answers "what does this word have":
    jam carries 15 rows in the pipeline file and 356 in the curated one. The
    values are sets keyed on the sentence text, which also fixes a trap in the
    English bank — it stores one row per translation locale, so en's 202,772
    rows are only 125,387 distinct (word, sentence) pairs and counting rows
    would report 1.6x the examples that actually exist.
    """
    examples: dict[str, set[str]] = {}
    _read_sentences(DATA / f"{code}_sentences.tsv", examples)
    _read_sentences(DATA / "sentences" / f"{code}_sentences.tsv", examples)
    return examples


def load_frequency(code: str) -> list[str]:
    """Headwords in frequency order. Empty when the language has no list."""
    path = DATA / f"{code}_frequency.tsv"
    if not path.exists():
        return []
    ranked: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip()
            if not word:
                continue
            try:
                rank = int(row.get("rank") or 0)
            except ValueError:
                continue
            if rank > 0:
                ranked.append((rank, word))
    ranked.sort()
    return [word for _, word in ranked]


def audit_language(code: str, band: int = DEFAULT_BAND) -> dict:
    examples = load_examples(code)
    frequency = load_frequency(code)
    if not frequency:
        # No frequency list means no way to say which words matter most, so the
        # band is meaningless and reporting 0% would be a lie about coverage.
        return {
            "code": code,
            "band": band,
            "state": "no frequency list",
            "words_in_band": 0,
            "covered": 0,
            "thin": [],
            "monotone": [],
        }

    in_band = frequency[:band]
    uncovered, thin, monotone, covered = [], [], [], 0
    for word in in_band:
        sentences = examples.get(word.casefold(), set())
        # A word with no example at all is a SOURCING gap, not a diversity one.
        # They are counted apart because the fixes differ and the costs differ
        # by an order of magnitude: a missing example needs a corpus or an
        # author, a monotone set needs one more sentence in a different frame.
        # Folding them together is why a corpus-wide "thin" figure reads as a
        # generation problem when most of it is a language with no bank.
        if not sentences:
            uncovered.append({"word": word, "examples": 0, "shapes": 0})
            continue
        covered += 1
        shapes = {shape(s, word) for s in sentences}
        record = {"word": word, "examples": len(sentences), "shapes": len(shapes)}
        if len(sentences) < THIN_BELOW:
            thin.append(record)
        elif len(shapes) <= MONOTONE_AT_OR_BELOW:
            monotone.append(record)

    return {
        "code": code,
        "band": band,
        "state": "ok" if examples else "no sentence bank",
        "words_in_band": len(in_band),
        "covered": covered,
        "coverage_pct": round(100 * covered / len(in_band), 1) if in_band else 0.0,
        "total_words_with_examples": len(examples),
        "uncovered": uncovered,
        "thin": thin,
        "monotone": monotone,
    }


def audit_all(codes=LANGUAGES, band: int = DEFAULT_BAND) -> list[dict]:
    return [audit_language(code, band) for code in codes]


def print_report(reports: list[dict]) -> None:
    band = reports[0]["band"] if reports else DEFAULT_BAND
    print(f"Example supply in the top {band} words of each language.")
    print(
        "uncovered = no example at all (needs a corpus or an author); "
        "thin = exactly one;\nmonotone = several that share one frame.\n"
    )
    print(
        f"{'lang':<6}{'state':<20}{'covered':>9}{'uncovered':>11}"
        f"{'thin':>7}{'monotone':>10}{'diversity':>11}"
    )
    print("-" * 74)
    for report in sorted(
        reports, key=lambda r: -(len(r["uncovered"]) + len(r["thin"]) + len(r["monotone"]))
    ):
        diversity = len(report["thin"]) + len(report["monotone"])
        covered = (
            f"{report.get('coverage_pct', 0)}%" if report["state"] != "no frequency list" else "—"
        )
        print(
            f"{report['code']:<6}{report['state']:<20}{covered:>9}"
            f"{len(report['uncovered']):>11}{len(report['thin']):>7}"
            f"{len(report['monotone']):>10}{diversity:>11}"
        )
    total_unc = sum(len(r["uncovered"]) for r in reports)
    total_div = sum(len(r["thin"]) + len(r["monotone"]) for r in reports)
    print("-" * 74)
    print(
        f"{'all':<6}{'':<20}{'':>9}{total_unc:>11}"
        f"{sum(len(r['thin']) for r in reports):>7}"
        f"{sum(len(r['monotone']) for r in reports):>10}{total_div:>11}"
    )

    print(
        "\nTwo limits on every number above, so they are not read as more than they are:"
        "\n  * These are the seed TSVs, not the database. The database also holds"
        "\n    AI-generated and reviewer-edited examples, so this is an upper bound."
        "\n  * The shape heuristic is orthographic. Korean and Thai token counts are"
        "\n    not comparable to the European languages' — have someone who reads them"
        "\n    check fifty rows before trusting their figures."
    )


def print_language_detail(report: dict, limit: int = 25) -> None:
    code = report["code"]
    print(
        f"\n=== {code}: {len(report['uncovered'])} uncovered, "
        f"{len(report['thin'])} thin, {len(report['monotone'])} monotone ==="
    )
    for label, rows in (
        ("uncovered", report["uncovered"]),
        ("thin", report["thin"]),
        ("monotone", report["monotone"]),
    ):
        if not rows:
            continue
        print(f"\n  {label} ({len(rows)}):")
        for row in rows[:limit]:
            print(
                f"    {row['word']:<24} examples={row['examples']:<4} shapes={row['shapes']}"
            )
        if len(rows) > limit:
            print(f"    … {len(rows) - limit} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m backend.services.seeder.audit_examples",
        description="Report vocabulary whose example sentences are thin or all one shape.",
    )
    parser.add_argument("--language", "-l", help="audit one language instead of all 27")
    parser.add_argument(
        "--band",
        type=int,
        default=DEFAULT_BAND,
        help=f"how many of the most frequent words to consider (default {DEFAULT_BAND})",
    )
    parser.add_argument("--json", dest="json_out", help="write the full work list to this path")
    parser.add_argument(
        "--detail", action="store_true", help="list the affected words for --language"
    )
    args = parser.parse_args(argv)

    if args.language and args.language not in LANGUAGES:
        parser.error(f"unknown language {args.language!r}; known: {' '.join(LANGUAGES)}")

    codes = (args.language,) if args.language else LANGUAGES
    reports = audit_all(codes, args.band)
    print_report(reports)
    if args.detail and args.language:
        print_language_detail(reports[0])

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(reports, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {args.json_out}")

    # Reporting only. This is a work-list, not a gate: a thin low-resource
    # language is a known state, and failing CI on it would just get the module
    # switched off.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
