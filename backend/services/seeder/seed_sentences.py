"""Load example sentences for vocabulary.

Reads TWO sources, both tab-separated with a ``word/sentence/translation``
header (an optional ``difficulty_rank`` column grades the sentence):

  - data/sentences/{code}_sentences.tsv — hand-curated (source='curated')
  - data/{code}_sentences.tsv — the sourcing pipeline's Tatoeba output
    (source='tatoeba', CC-BY)

Each sentence is matched to its vocabulary row by (language, lowercased word)
and inserted into example_sentences. A sentence containing the word lets the
review screen blank it out (cloze) — vocabulary taught *in context* rather
than as a flashcard.

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


async def _seed_file(
    conn, lang_id, path, source: str, license_: str, code: str = "",
) -> int:
    # Hindi rides the transliteration hint layer (like ru/ar/el): when the
    # TSV carries no romanization, compute one from the Devanagari.
    romanize = None
    if code == "hi":
        from backend.services.nlp.hindi import devanagari_to_roman
        romanize = devanagari_to_roman

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
            rank_raw = (row.get("difficulty_rank") or "").strip()
            rank = int(rank_raw) if rank_raw.isdigit() else 1
            result = await conn.execute(
                """
                INSERT INTO example_sentences
                    (language_id, vocabulary_id, sentence, translation,
                     difficulty_rank, source, license, gloss, transliteration)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (vocabulary_id, sentence, translation_locale)
                    DO NOTHING
                """,
                lang_id, vocab_id, sentence,
                (row.get("translation") or "").strip() or None,
                rank, source, license_,
                (row.get("gloss") or "").strip() or None,
                (row.get("transliteration") or "").strip()
                or (romanize(sentence) if romanize else None),
            )
            if result.endswith(" 1"):
                count += 1
    return count


async def seed(db_url: str, code: str) -> int:
    curated = SENTENCES_DIR / f"{code}_sentences.tsv"
    pipeline = DATA_DIR / f"{code}_sentences.tsv"
    if not curated.exists() and not pipeline.exists():
        logger.warning("no sentence file for %s in %s or %s",
                       code, SENTENCES_DIR, DATA_DIR)
        return 0
    conn = await asyncpg.connect(db_url)
    try:
        lang_id = await conn.fetchval("SELECT id FROM languages WHERE code = $1", code)
        if not lang_id:
            raise ValueError(f"language '{code}' not found")
        count = 0
        if curated.exists():
            count += await _seed_file(
                conn, lang_id, curated, "curated", "curated", code
            )
        if pipeline.exists():
            count += await _seed_file(
                conn, lang_id, pipeline, "tatoeba", "CC-BY 2.0 FR", code
            )
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
