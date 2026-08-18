"""Words that are several words, and the cards that teach only one of them.

The failure this reports was found on a Portuguese card. It taught `a`, gave
one meaning, and drilled "O que ele está a fazer?" three times — where `a` is
neither the article nor the pronoun it defined but the preposition of the
European progressive. Definition and exercise were about different words that
happen to share a spelling.

That is not a wrong sense being picked over a right one; every sense is real.
It is a card with room for one gloss standing in front of a word that has six.
Portuguese `a` carries entries under six parts of speech, Turkish `bir` six,
Yoruba `o` five — and all of them sit in the first handful of ranks, so they
are the first words a learner ever meets.

Two things are measured, because the fix differs:

  UNDER-GLOSSED — the word has several word-class senses and the gloss names
                  fewer. The learner is told one thing and shown another.
  POS MISMATCH  — the part of speech recorded in the frequency list is not
                  among the ones the dictionary carries at all, which means
                  the row was built from a sense that no longer wins.

This reads the committed files only: no database, no API key, no network.

Usage:
    python -m backend.services.seeder.audit_polysemy
    python -m backend.services.seeder.audit_polysemy --language pt --detail
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
RAW = DATA / "raw"

# Parts of speech that denote a word rather than a glyph or a place. A `name`
# or `character` entry is not a competing sense — that confusion is a separate
# defect, and source_data ranks those out.
WORD_POS = frozenset(
    "pron pronoun det article particle conj prep postp adv verb noun adj num "
    "intj classifier counter".split()
)

# Below this many distinct word classes a headword is ordinary polysemy that a
# single gloss can carry ("bank" the noun). At three the senses are usually
# different words sharing a spelling, and one gloss cannot serve them.
POLYSEMY_AT = 3
DEFAULT_BAND = 1000


def load_band(code: str, band: int) -> dict[str, tuple[int, str, str]]:
    """word -> (rank, pos, gloss) for the top *band* of the frequency list."""
    path = DATA / f"{code}_frequency.tsv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                rank = int(row.get("rank") or 0)
            except ValueError:
                continue
            if 0 < rank <= band:
                out[(row.get("word") or "").strip().lower()] = (
                    rank,
                    (row.get("pos") or "").strip(),
                    (row.get("en") or "").strip(),
                )
    return out


def pos_by_word(code: str, wanted: set[str]) -> dict[str, set[str]]:
    """word -> the word-class parts of speech the extract actually carries."""
    path = RAW / f"{code}_kaikki.jsonl"
    if not path.exists():
        return {}
    found: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = (obj.get("word") or "").strip().lower()
            if word not in wanted:
                continue
            pos = (obj.get("pos") or "").strip().lower()
            # A part of speech with no gloss anywhere is not a sense a card
            # could have taught, so it should not count against the gloss.
            if pos in WORD_POS and any(s.get("glosses") for s in obj.get("senses") or []):
                found[word].add(pos)
    return found


def _senses_named(gloss: str) -> int:
    """How many senses the gloss appears to state, counted on its separators."""
    return len([part for part in gloss.split(";") if part.strip()]) or 1


def audit_language(code: str, band: int = DEFAULT_BAND) -> dict:
    words = load_band(code, band)
    if not words:
        return {"code": code, "state": "no frequency list", "polysemous": [], "mismatched": []}
    if not (RAW / f"{code}_kaikki.jsonl").exists():
        # The extract is the only evidence of the other senses, and it is a
        # 7GB cache that is deliberately not committed. Absent is "unknown",
        # never "clean".
        return {"code": code, "state": "no extract cached", "polysemous": [], "mismatched": []}

    carried = pos_by_word(code, set(words))
    polysemous, mismatched = [], []
    for word, (rank, pos, gloss) in words.items():
        senses = carried.get(word, set())
        if len(senses) >= POLYSEMY_AT and _senses_named(gloss) < len(senses):
            polysemous.append(
                {
                    "rank": rank,
                    "word": word,
                    "pos": pos,
                    "senses": sorted(senses),
                    "named": _senses_named(gloss),
                    "gloss": gloss,
                }
            )
        if senses and pos and pos.lower() not in senses:
            mismatched.append(
                {"rank": rank, "word": word, "pos": pos, "senses": sorted(senses)}
            )
    polysemous.sort(key=lambda r: r["rank"])
    mismatched.sort(key=lambda r: r["rank"])
    return {
        "code": code,
        "state": "ok",
        "band": band,
        "words": len(words),
        "polysemous": polysemous,
        "mismatched": mismatched,
    }


def audit_all(codes=None, band: int = DEFAULT_BAND) -> list[dict]:
    if codes is None:
        codes = sorted(p.stem.replace("_kaikki", "") for p in RAW.glob("*_kaikki.jsonl"))
    return [audit_language(code, band) for code in codes]


def print_report(reports: list[dict]) -> None:
    print(
        "Words carrying three or more word-class senses whose gloss names fewer.\n"
        "These are the first words a learner meets, and the card teaches one of them.\n"
    )
    print(f"{'lang':<6}{'state':<20}{'band':>7}{'under-glossed':>15}{'pos mismatch':>14}")
    print("-" * 62)
    for report in sorted(reports, key=lambda r: -len(r["polysemous"])):
        print(
            f"{report['code']:<6}{report['state']:<20}{report.get('words', 0):>7}"
            f"{len(report['polysemous']):>15}{len(report['mismatched']):>14}"
        )
    print("-" * 62)
    print(
        f"{'all':<6}{'':<20}{sum(r.get('words', 0) for r in reports):>7}"
        f"{sum(len(r['polysemous']) for r in reports):>15}"
        f"{sum(len(r['mismatched']) for r in reports):>14}"
    )
    unknown = [r["code"] for r in reports if r["state"] == "no extract cached"]
    if unknown:
        print(
            f"\nNo cached extract for: {', '.join(unknown)} — reported as unknown"
            "\nrather than clean, since the extract is the only evidence of the"
            "\nother senses and data/raw is deliberately not committed."
        )


def print_detail(report: dict, limit: int = 30) -> None:
    print(f"\n=== {report['code']} — under-glossed ({len(report['polysemous'])}) ===")
    for row in report["polysemous"][:limit]:
        print(
            f"  rank {row['rank']:>4} {row['word']!r:<14} "
            f"{len(row['senses'])} senses ({', '.join(row['senses'])}), "
            f"gloss names {row['named']}"
        )
        print(f"       {row['gloss'][:96]}")
    if len(report["polysemous"]) > limit:
        print(f"  … {len(report['polysemous']) - limit} more")
    if report["mismatched"]:
        print(f"\n=== {report['code']} — recorded POS not among the senses ===")
        for row in report["mismatched"][:limit]:
            print(
                f"  rank {row['rank']:>4} {row['word']!r:<14} "
                f"recorded {row['pos']!r}, extract has {', '.join(row['senses'])}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m backend.services.seeder.audit_polysemy",
        description="Report high-frequency words whose gloss teaches one of several senses.",
    )
    parser.add_argument("--language", "-l", help="audit one language")
    parser.add_argument("--band", type=int, default=DEFAULT_BAND)
    parser.add_argument("--detail", action="store_true", help="list the words for --language")
    parser.add_argument("--json", dest="json_out", help="write the full work list here")
    args = parser.parse_args(argv)

    reports = audit_all([args.language] if args.language else None, args.band)
    print_report(reports)
    if args.detail and args.language:
        print_detail(reports[0])
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(reports, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {args.json_out}")
    # Reporting only: this is an authoring work-list, and a language whose
    # senses are genuinely simple should not be able to fail anyone's build.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
