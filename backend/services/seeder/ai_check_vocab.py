"""Bulk AI semantic check over a language's vocabulary.

The vocabulary twin of `generate_grammar --ai-check` — but NOT for the same
reason, and the difference matters enough to state up front.

**This does not make vocabulary visible.** The two-part publish gate
(`reviewed OR ai_check_status = 'pass'`) is applied to GRAMMAR POINTS only;
every such clause in repositories/cards.py is `gp.`, never `v.`. The single
gate on vocabulary is `level_source <> 'ai' OR policy IN ('ai_ok','all')` —
a word whose CEFR level was AI-estimated waits for a reviewer or a permissive
policy. Its `ai_check_status` is advisory metadata a reviewer reads, and
nothing keys visibility off it.

So what this is for: a quality signal at scale. It reads each word's gloss
and examples and records whether they hold up, which is what routes bad
cards into the review queue instead of waiting for a learner to hit one and
report it. Worth running on a freshly seeded language; just don't run it
expecting words to appear afterwards, because they are already there.

Resumable by default: a run only picks up words with no verdict yet, so an
interrupted run (an API hiccup, a laptop lid) can simply be re-run and costs
nothing already paid for. Ordered by level then frequency, so the words a
beginner meets first become visible first rather than the whole language
staying dark until the C2 tail finishes.

    python -m backend.services.seeder.ai_check_vocab --language he
    python -m backend.services.seeder.ai_check_vocab --language id --level A1
    python -m backend.services.seeder.ai_check_vocab --language fa --recheck-all

Cost is real — one model call per word. --limit exists so a first run can be
sized deliberately rather than discovered.
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from backend.services.semantic_check import ai_available, semantic_check_vocab

logger = logging.getLogger(__name__)

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


async def ai_check_vocabulary(
    db_url: str,
    language_code: str,
    *,
    only_missing: bool = True,
    level: str | None = None,
    limit: int | None = None,
) -> dict:
    """Check vocabulary and store each verdict. Returns run counts."""
    import asyncpg

    if not ai_available():
        raise RuntimeError(
            "AI review needs ANTHROPIC_API_KEY (or TUTOR_DEV_MOCK=1 for a "
            "canned pass/pass run while wiring this up)."
        )
    conn = await asyncpg.connect(db_url)
    try:
        language_id = await conn.fetchval(
            "SELECT id FROM languages WHERE code = $1", language_code
        )
        if not language_id:
            raise ValueError(f"Language '{language_code}' not found in DB")

        clauses = ["v.language_id = $1"]
        params: list = [language_id]
        if only_missing:
            clauses.append("v.ai_check_status IS NULL")
        if level:
            params.append(level)
            clauses.append(f"v.level = ${len(params)}")
        sql = f"""
            SELECT v.id, v.word,
                   (SELECT t.definition FROM translations t
                     WHERE t.vocabulary_id = v.id AND t.locale = 'en'
                     LIMIT 1) AS definition
            FROM vocabulary v
            WHERE {' AND '.join(clauses)}
            ORDER BY v.level ASC NULLS LAST, v.frequency_rank ASC NULLS LAST
        """
        if limit:
            params.append(limit)
            sql += f" LIMIT ${len(params)}"
        words = await conn.fetch(sql, *params)

        passed = concerns = skipped = 0
        for w in words:
            if not w["definition"]:
                # Nothing to judge against. Left unchecked rather than
                # failed: a missing gloss is a content gap for the
                # definitions feed, not a verdict about the word.
                skipped += 1
                continue
            examples = await conn.fetch(
                """
                SELECT sentence, translation
                FROM example_sentences
                WHERE vocabulary_id = $1
                ORDER BY difficulty_rank ASC NULLS LAST
                LIMIT 5
                """,
                w["id"],
            )
            result = await semantic_check_vocab(
                language_code, w["word"], w["definition"],
                [dict(e) for e in examples],
            )
            await conn.execute(
                """
                UPDATE vocabulary
                SET ai_check_status = $2,
                    ai_check_notes = NULLIF($3, ''),
                    ai_checked_at = now()
                WHERE id = $1
                """,
                w["id"], result["status"], result["notes"],
            )
            if result["status"] == "pass":
                passed += 1
            else:
                concerns += 1
            logger.info("%s: %s — %s", language_code, w["word"], result["status"])
        return {
            "checked": passed + concerns,
            "passed": passed,
            "concerns": concerns,
            "skipped_no_definition": skipped,
        }
    finally:
        await conn.close()


async def _main() -> None:
    import os

    parser = argparse.ArgumentParser(
        description="Bulk AI semantic check over a language's vocabulary"
    )
    parser.add_argument("--language", "-l", required=True)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument(
        "--level", choices=CEFR_LEVELS,
        help="Only this CEFR band (a ten-thousand-word run is long; this "
             "lets you do it in sittings)",
    )
    parser.add_argument(
        "--limit", type=int,
        help="Stop after this many words — size a first run deliberately",
    )
    parser.add_argument(
        "--recheck-all", action="store_true",
        help="Re-check words that already have a verdict, not just missing ones",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        raise SystemExit(1)

    stats = await ai_check_vocabulary(
        args.db_url, args.language,
        only_missing=not args.recheck_all,
        level=args.level,
        limit=args.limit,
    )
    print(
        f"{args.language}: checked {stats['checked']} "
        f"({stats['passed']} pass, {stats['concerns']} concerns"
        + (f", {stats['skipped_no_definition']} skipped with no gloss"
           if stats["skipped_no_definition"] else "")
        + ")"
    )


if __name__ == "__main__":
    asyncio.run(_main())
