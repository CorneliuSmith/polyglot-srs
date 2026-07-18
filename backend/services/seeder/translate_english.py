"""Fill English course glosses for a support locale via the maker–checker.

Idempotent and resumable: only English words that still LACK a gloss in the
target locale are processed, so re-running picks up where it stopped. Approved
glosses are written to `translations`; rejected ones go to `translation_reviews`
for a human. Words are processed in batches (many per AI call) and batches run
concurrently.

Pilot first — quality and cost are unknown until you see real output:
    python -m backend.services.seeder.translate_english --locale nl --limit 40 --dry-run
    python -m backend.services.seeder.translate_english --locale nl --limit 40
Then, once happy:
    python -m backend.services.seeder.translate_english --all
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os

import asyncpg

from backend.services.translate import maker_check_batch, translations_available

logger = logging.getLogger("translate_english")


async def _pending_words(conn, en_lang_id, locale, limit):
    """English vocab with no gloss yet in *locale*, most frequent first."""
    return await conn.fetch(
        """
        SELECT v.id, v.word, v.part_of_speech AS pos,
               (SELECT definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1) AS definition,
               (SELECT sentence FROM example_sentences es
                 WHERE es.vocabulary_id = v.id ORDER BY es.difficulty_rank NULLS LAST LIMIT 1) AS example
        FROM vocabulary v
        WHERE v.language_id = $1
          AND NOT EXISTS (
            SELECT 1 FROM translations t
             WHERE t.vocabulary_id = v.id AND t.locale = $2)
          AND NOT EXISTS (
            SELECT 1 FROM translation_reviews r
             WHERE r.vocabulary_id = v.id AND r.locale = $2)
        ORDER BY v.frequency_rank NULLS LAST
        LIMIT $3
        """,
        en_lang_id, locale, limit,
    )


async def _apply_batch(conn, locale, results, dry_run):
    applied = queued = 0
    for r in results:
        if r["verdict"] in ("ok", "fixed") and r["gloss"]:
            if not dry_run:
                await conn.execute(
                    """INSERT INTO translations (vocabulary_id, locale, definition)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (vocabulary_id, locale)
                         DO UPDATE SET definition = EXCLUDED.definition""",
                    r["id"], locale, r["gloss"])
            applied += 1
        else:
            if not dry_run:
                await conn.execute(
                    """INSERT INTO translation_reviews (vocabulary_id, locale, proposed, reason)
                       VALUES ($1, $2, $3, $4)
                       ON CONFLICT (vocabulary_id, locale) DO NOTHING""",
                    r["id"], locale, r.get("proposed") or "", r["note"])
            queued += 1
    return applied, queued


async def translate_locale(db_url, locale, *, limit, batch_size, concurrency,
                           maker_model, checker_model, dry_run):
    conn = await asyncpg.connect(db_url)
    try:
        en = await conn.fetchval("SELECT id FROM languages WHERE code = 'en'")
        lang = await conn.fetchrow("SELECT name FROM languages WHERE code = $1", locale)
        if not lang:
            raise ValueError(f"unknown locale '{locale}'")
        rows = await _pending_words(conn, en, locale, limit)
        if not rows:
            logger.info("%s: nothing to do (already covered)", locale)
            return {"locale": locale, "applied": 0, "queued": 0, "processed": 0}

        batches = [rows[i:i + batch_size] for i in range(0, len(rows), batch_size)]
        sem = asyncio.Semaphore(concurrency)

        async def run(batch):
            items = [{"i": idx, "word": r["word"], "pos": r["pos"],
                      "definition": r["definition"], "example": r["example"]}
                     for idx, r in enumerate(batch)]
            async with sem:
                res = await maker_check_batch(lang["name"], items,
                                              maker_model, checker_model)
            by_i = {b["i"]: b for b in res}
            return [{**by_i[idx], "id": batch[idx]["id"], "proposed": by_i[idx]["gloss"]}
                    for idx in range(len(batch)) if idx in by_i]

        applied = queued = processed = 0
        for chunk in await asyncio.gather(*(run(b) for b in batches)):
            a, q = await _apply_batch(conn, locale, chunk, dry_run)
            applied += a
            queued += q
            processed += len(chunk)
        verb = "would apply" if dry_run else "applied"
        logger.info("%s: %s %d, queued %d (of %d processed)",
                    locale, verb, applied, queued, processed)
        return {"locale": locale, "applied": applied, "queued": queued,
                "processed": processed}
    finally:
        await conn.close()


async def main() -> None:
    p = argparse.ArgumentParser(description="Maker–checker English gloss fill")
    p.add_argument("--locale", help="target support locale, e.g. nl")
    p.add_argument("--all", action="store_true", help="every non-English language")
    p.add_argument("--limit", type=int, default=10_000, help="max words per locale (pilot with a small number)")
    p.add_argument("--batch-size", type=int, default=25)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--maker-model", default=None)
    p.add_argument("--checker-model", default=None)
    p.add_argument("--dry-run", action="store_true", help="don't write; just report counts")
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not translations_available():
        print("ERROR: no ANTHROPIC_API_KEY (and TUTOR_DEV_MOCK off). Nothing to run.")
        return
    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return

    locales = [args.locale]
    if args.all:
        conn = await asyncpg.connect(args.db_url)
        locales = [r["code"] for r in await conn.fetch(
            "SELECT code FROM languages WHERE code <> 'en' ORDER BY code")]
        await conn.close()
    elif not args.locale:
        print("ERROR: pass --locale CODE or --all.")
        return

    totals = {"applied": 0, "queued": 0, "processed": 0}
    for loc in locales:
        s = await translate_locale(
            args.db_url, loc, limit=args.limit, batch_size=args.batch_size,
            concurrency=args.concurrency, maker_model=args.maker_model,
            checker_model=args.checker_model, dry_run=args.dry_run)
        for k in totals:
            totals[k] += s[k]
    print(f"\nDONE — applied {totals['applied']}, queued {totals['queued']} "
          f"(processed {totals['processed']}) across {len(locales)} locale(s)"
          + (" [dry run]" if args.dry_run else ""))


if __name__ == "__main__":
    asyncio.run(main())
