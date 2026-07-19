"""Maker–checker clarity pass over card definitions ("hints").

Targets the confusing, Wiktionary-derived definitions — the ones with a
grammatical parenthetical that reads like an instruction ("to speak, to talk
(perfective поговорить)") or raw dictionary jargon ("inflection of…",
"plural of…"). The checker rewords the clearly-confusing ones and leaves the
rest; a fix removes the pattern, so re-running naturally converges. Uncertain
ones go to translation_reviews for a human.

Pilot first (needs a real key; run on the server):
    python -m backend.services.seeder.review_hints --language ru --limit 30 --dry-run
    python -m backend.services.seeder.review_hints --language ru --limit 30
    python -m backend.services.seeder.review_hints --all
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from backend.services.translate import review_definitions, translations_available

logger = logging.getLogger("review_hints")

# Every applied rewrite is journaled here first, so a whole run can be
# reverted with --restore <file> — the checker can never make things
# permanently worse.
BACKUP_DIR = Path(__file__).resolve().parents[3] / "data" / "backups"

# Definitions likely to read as an instruction or as raw dictionary plumbing.
SUSPICIOUS = r"\((perfective|imperfective|plural|feminine|masculine|neuter|" \
             r"declined|inflection|alternative|genitive|dative|accusative|" \
             r"vocative|archaic|obsolete|dated) |inflection of|alternative form of|" \
             r"alternative spelling of|plural of|feminine of|masculine of"


async def _pending(conn, lang_id, limit):
    return await conn.fetch(
        """
        SELECT v.id, v.word, t.definition
        FROM vocabulary v
        JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en'
        WHERE v.language_id = $1
          AND t.definition ~* $2
          AND NOT EXISTS (SELECT 1 FROM translation_reviews r
                          WHERE r.vocabulary_id = v.id AND r.locale = 'en-hint')
        ORDER BY v.frequency_rank NULLS LAST
        LIMIT $3
        """,
        lang_id, SUSPICIOUS, limit,
    )


async def review_language(db_url, code, *, limit, batch_size, concurrency,
                          model, dry_run):
    conn = await asyncpg.connect(db_url)
    try:
        lang = await conn.fetchrow("SELECT id, name FROM languages WHERE code = $1", code)
        if not lang:
            raise ValueError(f"unknown language '{code}'")
        rows = await _pending(conn, lang["id"], limit)
        if not rows:
            logger.info("%s: no confusing definitions matched", code)
            return {"code": code, "fixed": 0, "queued": 0, "kept": 0}

        batches = [rows[i:i + batch_size] for i in range(0, len(rows), batch_size)]
        sem = asyncio.Semaphore(concurrency)

        async def run(batch):
            items = [{"i": n, "word": r["word"], "definition": r["definition"]}
                     for n, r in enumerate(batch)]
            async with sem:
                res = await review_definitions(lang["name"], items, model)
            by_i = {x["i"]: x for x in res}
            return [{**by_i[n], "id": batch[n]["id"],
                     "old": batch[n]["definition"]}
                    for n in range(len(batch)) if n in by_i]

        backup_file = None
        fixed = queued = kept = 0
        for chunk in await asyncio.gather(*(run(b) for b in batches)):
            for r in chunk:
                if r["verdict"] == "fixed" and r["definition"]:
                    if not dry_run:
                        if backup_file is None:
                            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
                            backup_file = BACKUP_DIR / f"hints_{code}_{stamp}.jsonl"
                        with open(backup_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(
                                {"vocabulary_id": str(r["id"]), "word": r["word"],
                                 "old": r["old"], "new": r["definition"]},
                                ensure_ascii=False) + "\n")
                        await conn.execute(
                            "UPDATE translations SET definition = $1 "
                            "WHERE vocabulary_id = $2 AND locale = 'en'",
                            r["definition"], r["id"])
                    fixed += 1
                elif r["verdict"] == "reject":
                    if not dry_run:
                        await conn.execute(
                            """INSERT INTO translation_reviews
                                 (vocabulary_id, locale, proposed, reason)
                               VALUES ($1, 'en-hint', $2, $3)
                               ON CONFLICT (vocabulary_id, locale) DO NOTHING""",
                            r["id"], r.get("definition") or "", r["note"])
                    queued += 1
                else:
                    kept += 1
        verb = "would fix" if dry_run else "fixed"
        logger.info("%s: %s %d, queued %d, kept %d", code, verb, fixed, queued, kept)
        if backup_file is not None:
            logger.info("%s: originals journaled to %s (undo: --restore %s)",
                        code, backup_file, backup_file.name)
        return {"code": code, "fixed": fixed, "queued": queued, "kept": kept}
    finally:
        await conn.close()


async def restore(db_url: str, backup_path: Path) -> int:
    """Revert every rewrite journaled in a backup file. Returns rows restored."""
    conn = await asyncpg.connect(db_url)
    try:
        n = 0
        with open(backup_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                result = await conn.execute(
                    "UPDATE translations SET definition = $1 "
                    "WHERE vocabulary_id = $2 AND locale = 'en'",
                    rec["old"], rec["vocabulary_id"])
                n += int(result.endswith("1"))
        return n
    finally:
        await conn.close()


async def main() -> None:
    p = argparse.ArgumentParser(description="Maker–checker clarity pass over definitions")
    p.add_argument("--language")
    p.add_argument("--all", action="store_true")
    p.add_argument("--limit", type=int, default=5_000)
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--model", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--restore", metavar="FILE",
                   help="undo a previous run from its backup file "
                        "(name or path under data/backups/)")
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return
    if args.restore:
        path = Path(args.restore)
        if not path.exists():
            path = BACKUP_DIR / args.restore
        if not path.exists():
            print(f"ERROR: backup file not found: {args.restore}")
            return
        n = await restore(args.db_url, path)
        print(f"RESTORED {n} definitions from {path.name}")
        return
    if not translations_available():
        print("ERROR: no ANTHROPIC_API_KEY (and TUTOR_DEV_MOCK off).")
        return

    codes = [args.language]
    if args.all:
        conn = await asyncpg.connect(args.db_url)
        codes = [r["code"] for r in await conn.fetch("SELECT code FROM languages ORDER BY code")]
        await conn.close()
    elif not args.language:
        print("ERROR: pass --language CODE or --all.")
        return

    tot = {"fixed": 0, "queued": 0, "kept": 0}
    for c in codes:
        s = await review_language(args.db_url, c, limit=args.limit,
                                  batch_size=args.batch_size, concurrency=args.concurrency,
                                  model=args.model, dry_run=args.dry_run)
        for k in tot:
            tot[k] += s[k]
    print(f"\nDONE — fixed {tot['fixed']}, queued {tot['queued']}, kept {tot['kept']}"
          + (" [dry run]" if args.dry_run else ""))


if __name__ == "__main__":
    asyncio.run(main())
