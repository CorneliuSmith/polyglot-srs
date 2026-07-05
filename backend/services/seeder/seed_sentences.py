"""Load curated example sentences for vocabulary.

Reads data/sentences/{code}_sentences.tsv (tab-separated, header:
``word<TAB>sentence<TAB>translation``), matches each sentence to its vocabulary
row by (language, lowercased word), and inserts into example_sentences. Each
sentence must contain the word so the review screen can blank it out (cloze) —
this is what makes vocabulary taught *in context* rather than as a flashcard.

CLI:
    python -m backend.services.seeder.seed_sentences --language es
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os

import asyncpg

from .base import DATA_DIR

SENTENCES_DIR = DATA_DIR / "sentences"
logger = logging.getLogger("seed_sentences")


async def seed(db_url: str, code: str) -> int:
    path = SENTENCES_DIR / f"{code}_sentences.tsv"
    if not path.exists():
        logger.warning("no sentence file at %s", path)
        return 0
    conn = await asyncpg.connect(db_url)
    try:
        lang_id = await conn.fetchval("SELECT id FROM languages WHERE code = $1", code)
        if not lang_id:
            raise ValueError(f"language '{code}' not found")
        count = 0
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                word = (row.get("word") or "").strip()
                sentence = (row.get("sentence") or "").strip()
                if not word or not sentence:
                    continue
                vocab_id = await conn.fetchval(
                    "SELECT id FROM vocabulary "
                    "WHERE language_id = $1 AND lower(word) = lower($2)",
                    lang_id, word,
                )
                if not vocab_id:
                    continue
                result = await conn.execute(
                    """
                    INSERT INTO example_sentences
                        (language_id, vocabulary_id, sentence, translation,
                         difficulty_rank, source, license)
                    VALUES ($1, $2, $3, $4, 1, 'curated', 'curated')
                    ON CONFLICT (vocabulary_id, sentence) DO NOTHING
                    """,
                    lang_id, vocab_id, sentence,
                    (row.get("translation") or "").strip() or None,
                )
                if result.endswith(" 1"):
                    count += 1
        logger.info("OK %s: %d example sentences loaded", code, count)
        return count
    finally:
        await conn.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed example sentences for vocabulary")
    parser.add_argument("--language", "-l", required=True)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    if not args.db_url:
        print("ERROR: DATABASE_URL not set. Pass --db-url or set DATABASE_URL.")
        return
    n = await seed(args.db_url, args.language)
    print(f"OK {args.language}: {n} example sentences loaded")


if __name__ == "__main__":
    asyncio.run(main())
