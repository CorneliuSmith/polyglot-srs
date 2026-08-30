"""Delete example sentences the committed bank no longer endorses.

**Why this exists.** `seed_sentences` inserts with `ON CONFLICT DO NOTHING`,
so it can only ever ADD. When a bank is curated down — the owner's 26 Aug
decision to thin English "to the best few per word, selected for variety" —
the rows that were cut stay in the database forever, and the review card
picks from everything present. English shipped 196,004 sentences against a
curated 70,975, so a learner opening the card for "I" was shown "I am.",
"I am you." and "I am!" while "I think he did it." sat unused in the file.

**What it will not do.**

* It never touches a row whose source is not `tatoeba`. `curated` and `ai`
  rows are human-authored or human-reviewed and are not reproducible from a
  file; the bulk corpus is.
* It never leaves a word with no example sentence. A word whose every row
  would be deleted keeps its rows and is reported instead.
* It matches on (word, SENTENCE) — never on the translation locale. The file
  keeps one row per sentence, the database holds that sentence once per
  locale, and a German learner needs the `de` translation of a sentence the
  file happens to store with its `es` one. Keying on locale would delete
  every other language's translation of a sentence the bank endorses.

**Reversibility.** Nothing is deleted until a rollback file exists on disk.
The rollback is plain SQL re-inserting every deleted row with its original
id, so learner-facing ids survive a round trip. The whole prune runs in one
transaction.

    python -m backend.services.seeder.prune_sentences -l en          # report
    python -m backend.services.seeder.prune_sentences -l en --apply  # writes
    python -m backend.services.seeder.prune_sentences --rollback out/prune-<stamp>.sql
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

REPO = Path(__file__).resolve().parents[3]
DATA_DIR = REPO / "data"
ROLLBACK_DIR = REPO / "out"

# Only the bulk corpus is reproducible from a committed file. Everything else
# represents work a human did that no rebuild would bring back.
PRUNABLE_SOURCES = ("tatoeba",)


def file_pairs(code: str) -> set[tuple[str, str]]:
    """(word, sentence) the committed bank endorses, lowercased on the word."""
    path = DATA_DIR / f"{code}_sentences.tsv"
    if not path.exists():
        return set()
    out: set[tuple[str, str]] = set()
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip().lower()
            sentence = (row.get("sentence") or "").strip()
            if word and sentence:
                out.add((word, sentence))
    return out


async def survey(conn: asyncpg.Connection, code: str) -> dict:
    """What a prune of *code* would delete, and what it would refuse to."""
    keep = file_pairs(code)
    if not keep:
        return {"code": code, "skipped": "no committed bank", "delete": [],
                "protected": 0, "kept_empty": []}
    rows = await conn.fetch(
        """
        SELECT es.id, es.vocabulary_id, lower(v.word) AS word, es.sentence,
               es.translation, es.translation_locale, es.difficulty_rank,
               es.source, es.license, es.gloss, es.transliteration,
               es.reviewed, es.language_id
        FROM example_sentences es
        JOIN vocabulary v ON v.id = es.vocabulary_id
        JOIN languages l  ON l.id = v.language_id
        WHERE l.code = $1
        """,
        code,
    )
    protected = sum(1 for r in rows if r["source"] not in PRUNABLE_SOURCES)
    # Group by word so the "never strand a word" rule can be applied per word.
    by_word: dict[str, list] = {}
    for r in rows:
        by_word.setdefault(r["word"], []).append(r)

    delete, kept_empty = [], []
    for word, group in by_word.items():
        survivors = [
            r for r in group
            if r["source"] not in PRUNABLE_SOURCES or (word, r["sentence"]) in keep
        ]
        candidates = [
            r for r in group
            if r["source"] in PRUNABLE_SOURCES and (word, r["sentence"]) not in keep
        ]
        if not candidates:
            continue
        if not survivors:
            # Deleting these would leave the word with nothing at all.
            kept_empty.append(word)
            continue
        delete.extend(candidates)
    return {"code": code, "skipped": None, "delete": delete,
            "protected": protected, "kept_empty": kept_empty,
            "total": len(rows)}


def write_rollback(reports: list[dict], stamp: str) -> Path:
    """Every statement needed to put the rows back, ids included."""
    ROLLBACK_DIR.mkdir(exist_ok=True)
    path = ROLLBACK_DIR / f"prune-sentences-{stamp}.sql"
    lines = [
        "-- Rollback for backend.services.seeder.prune_sentences",
        f"-- generated {stamp}",
        '-- Replay with: psql "$DATABASE_URL" -f this-file',
        "BEGIN;",
    ]

    def lit(v) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int | float):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    for rep in reports:
        for r in rep["delete"]:
            cols = ("id", "language_id", "vocabulary_id", "sentence",
                    "translation", "difficulty_rank", "source", "license",
                    "gloss", "transliteration", "reviewed", "translation_locale")
            vals = ", ".join(lit(r[c]) for c in cols)
            lines.append(
                f"INSERT INTO example_sentences ({', '.join(cols)}) "
                f"VALUES ({vals}) ON CONFLICT (id) DO NOTHING;"
            )
    lines.append("COMMIT;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


async def apply(conn: asyncpg.Connection, reports: list[dict]) -> int:
    ids = [r["id"] for rep in reports for r in rep["delete"]]
    if not ids:
        return 0
    async with conn.transaction():
        for i in range(0, len(ids), 5000):
            await conn.execute(
                "DELETE FROM example_sentences WHERE id = ANY($1::uuid[])",
                ids[i:i + 5000],
            )
    return len(ids)


def print_report(reports: list[dict]) -> None:
    print(f"{'lang':<6}{'db':>9}{'delete':>9}{'keeps':>8}{'protected':>11}{'stranded':>10}")
    print("-" * 53)
    tot_d = tot_p = 0
    for rep in reports:
        if rep.get("skipped"):
            continue
        d = len(rep["delete"])
        tot_d += d
        tot_p += rep["protected"]
        print(f"{rep['code']:<6}{rep['total']:>9,}{d:>9,}"
              f"{rep['total'] - d:>8,}{rep['protected']:>11,}"
              f"{len(rep['kept_empty']):>10,}")
    print("-" * 53)
    print(f"{'all':<6}{'':>9}{tot_d:>9,}{'':>8}{tot_p:>11,}")
    print("\ndelete    tatoeba rows the committed bank no longer endorses")
    print("keeps     rows that remain (curated/ai are never candidates)")
    print("protected rows exempt by source — curated or ai")
    print("stranded  words whose every row would go; left untouched instead")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--language", "-l", default="all")
    ap.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--apply", action="store_true",
                    help="delete (a rollback file is written first)")
    ap.add_argument("--rollback", metavar="FILE", help="replay a rollback file and exit")
    args = ap.parse_args()
    if not args.db_url:
        print("ERROR: DATABASE_URL not set. Pass --db-url or set DATABASE_URL.")
        return
    conn = await asyncpg.connect(args.db_url)
    try:
        if args.rollback:
            await conn.execute(Path(args.rollback).read_text(encoding="utf-8"))
            print(f"rolled back from {args.rollback}")
            return
        if args.language == "all":
            codes = [p.name.split("_")[0]
                     for p in sorted(DATA_DIR.glob("*_sentences.tsv"))]
        else:
            codes = [args.language]
        reports = [await survey(conn, c) for c in codes]
        print_report(reports)
        if not args.apply:
            print("\nDRY RUN — nothing deleted. Re-run with --apply to write.")
            return
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = write_rollback(reports, stamp)
        print(f"\nrollback written first: {path}")
        n = await apply(conn, reports)
        print(f"deleted {n:,} example sentences")
        print(f"undo with: python -m backend.services.seeder.prune_sentences "
              f"--rollback {path}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
