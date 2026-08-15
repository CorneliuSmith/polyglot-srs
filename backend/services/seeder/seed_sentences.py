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

    # One round trip for the whole word→id map, then pipelined batch
    # inserts — the old per-row lookup+insert (2 round trips × 29k rows for
    # Russian) blew straight through command timeouts on the remote DB.
    vocab_rows = await conn.fetch(
        "SELECT lower(word) AS w, id FROM vocabulary WHERE language_id = $1",
        lang_id,
    )
    id_by_word = {r["w"]: r["id"] for r in vocab_rows}

    args = []
    for row in _read_rows(path):
        vocab_id = id_by_word.get(row["word"].lower())
        if not vocab_id:
            continue
        # A row may carry its own provenance (e.g. an extractor-authored 'ai'
        # example); otherwise it inherits the file's default source. An 'ai' row
        # lands reviewed=false — hidden from learners until a reviewer approves
        # it, matching add_example_sentence(source='ai').
        row_source = row["source"] or source
        reviewed = row_source != "ai"
        args.append((
            lang_id, vocab_id, row["sentence"], row["translation"],
            row["rank"], row_source, license_, row["gloss"],
            row["transliteration"]
            or (romanize(row["sentence"]) if romanize else None),
            reviewed, row["translation_locale"],
        ))

    before = await conn.fetchval(
        "SELECT count(*) FROM example_sentences WHERE language_id = $1", lang_id
    )
    for i in range(0, len(args), 1000):
        await conn.executemany(
            """
            INSERT INTO example_sentences
                (language_id, vocabulary_id, sentence, translation,
                 difficulty_rank, source, license, gloss, transliteration,
                 reviewed, translation_locale)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (vocabulary_id, sentence, translation_locale)
                DO NOTHING
            """,
            args[i:i + 1000],
        )
    after = await conn.fetchval(
        "SELECT count(*) FROM example_sentences WHERE language_id = $1", lang_id
    )
    return after - before


def _read_rows(path):
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            word = (row.get("word") or "").strip()
            sentence = (row.get("sentence") or "").strip()
            if not word or not sentence:
                continue
            rank_raw = (row.get("difficulty_rank") or "").strip()
            yield {
                "word": word,
                "sentence": sentence,
                "translation": (row.get("translation") or "").strip() or None,
                "rank": int(rank_raw) if rank_raw.isdigit() else 1,
                "gloss": (row.get("gloss") or "").strip() or None,
                "transliteration": (row.get("transliteration") or "").strip(),
                "source": (row.get("source") or "").strip().lower() or None,
                # The language the TRANSLATION is written in — not the course.
                # data/en_sentences.tsv carries this column and every one of
                # its 202,772 rows is a NON-English locale (tr, de, fr, ru, es,
                # it, pt, ro, ar, el, sw, hi, ca; zero 'en'). Dropping it filed
                # all of them as English, so a Russian learner of English was
                # served Spanish, French and Romanian under "in context" — and
                # because the conflict key is (vocabulary_id, sentence,
                # translation_locale), collapsing 13 locales onto 'en' also
                # meant 12 of every 13 translations were silently discarded.
                # Every other course's file omits the column; those really are
                # English translations, so 'en' stays the default.
                "translation_locale":
                    (row.get("translation_locale") or "").strip().lower() or "en",
            }


async def repair_locales(db_url: str, code: str) -> int:
    """Relabel rows this seeder previously filed under the wrong locale.

    Re-seeding cannot fix them: the insert is ON CONFLICT DO NOTHING, so a
    row already sitting there — with the wrong translation_locale — is left
    exactly as it is. The damage has to be corrected in place first.

    Matching is on the translation TEXT, not on position: a row is relabelled
    only when its stored translation is character-for-character the one the
    file lists for that locale. So a Spanish string is only ever relabelled
    'es'. Rows a human has since edited no longer match and are left alone.

    Run this BEFORE re-seeding. Repair fixes the labels of the rows that
    survived; the re-seed then inserts the 12-in-13 that the conflict key
    silently swallowed while every locale was masquerading as 'en'.
    """
    conn = await asyncpg.connect(db_url)
    try:
        lang_id = await conn.fetchval(
            "SELECT id FROM languages WHERE code = $1", code)
        if not lang_id:
            raise ValueError(f"language '{code}' not found")
        vocab_rows = await conn.fetch(
            "SELECT lower(word) AS w, id FROM vocabulary WHERE language_id = $1",
            lang_id,
        )
        id_by_word = {r["w"]: r["id"] for r in vocab_rows}

        fixed = 0
        for path in (SENTENCES_DIR / f"{code}_sentences.tsv",
                     DATA_DIR / f"{code}_sentences.tsv"):
            if not path.exists():
                continue
            args = [
                (row["translation_locale"], vocab_id, row["sentence"],
                 row["translation"])
                for row in _read_rows(path)
                if row["translation_locale"] != "en" and row["translation"]
                and (vocab_id := id_by_word.get(row["word"].lower()))
            ]
            for i in range(0, len(args), 1000):
                batch = args[i:i + 1000]
                # Drop the stale row FIRST where the correctly-labelled one
                # already exists, or the relabel below collides with it:
                #   uq_example_sentences_vocab_sentence_locale
                #   (vocabulary_id, sentence, translation_locale)
                #
                # That collision is not hypothetical. A seed run with the
                # FIXED seeder inserts the 'es' row alongside the stale 'en'
                # one (different locale, so no conflict), which is exactly
                # the duplicate the seeder tests describe. Repairing after
                # such a run then tries to make a second 'es' row.
                #
                # Only ever deletes a row whose translation text is
                # character-for-character the file's, and only when the
                # correct row is already present — a proven duplicate, never
                # the last copy of anything.
                await conn.executemany(
                    """
                    DELETE FROM example_sentences
                     WHERE vocabulary_id = $2
                       AND sentence = $3
                       AND translation = $4
                       AND translation_locale = 'en'
                       -- Never delete a row a human has touched. The text
                       -- match above catches an EDIT (edited text no longer
                       -- matches the file), but flagging or suggesting
                       -- leaves the text alone — so those need saying
                       -- outright. A flagged duplicate stays mislabelled
                       -- and visible to a reviewer, which beats silently
                       -- dropping their flag.
                       AND coalesce(is_modified, false) = false
                       AND coalesce(flagged, false) = false
                       AND suggested_translation IS NULL
                       AND EXISTS (
                           SELECT 1 FROM example_sentences e2
                            WHERE e2.vocabulary_id = $2
                              AND e2.sentence = $3
                              AND e2.translation_locale = $1)
                    """,
                    batch,
                )
                await conn.executemany(
                    """
                    UPDATE example_sentences
                       SET translation_locale = $1
                     WHERE vocabulary_id = $2
                       AND sentence = $3
                       AND translation = $4
                       AND translation_locale = 'en'
                       AND NOT EXISTS (
                           SELECT 1 FROM example_sentences e2
                            WHERE e2.vocabulary_id = $2
                              AND e2.sentence = $3
                              AND e2.translation_locale = $1)
                    """,
                    batch,
                )
            fixed += len(args)
        logger.info("%s: repair pass covered %d file rows", code, fixed)
        return fixed
    finally:
        await conn.close()


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
    parser.add_argument("--repair-locales", action="store_true",
                        help="relabel rows filed under the wrong locale; run "
                             "this BEFORE re-seeding (the insert is ON "
                             "CONFLICT DO NOTHING and cannot fix them)")
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    if not args.db_url:
        print("ERROR: DATABASE_URL not set. Pass --db-url or set DATABASE_URL.")
        return
    if args.repair_locales:
        n = await repair_locales(args.db_url, args.language)
        print(f"OK {args.language}: repair pass covered {n} file rows — "
              f"now re-run without --repair-locales to insert the "
              f"translations the old conflict key dropped")
        return
    n = await seed(args.db_url, args.language)
    print(f"OK {args.language}: {n} example sentences loaded")


if __name__ == "__main__":
    asyncio.run(main())
