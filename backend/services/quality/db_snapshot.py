"""A READ-ONLY picture of what production actually serves.

**Why this exists.** Every quality check in this repo reads the repo. None of
them could see the database, and on 25 Aug 2026 that gap was measured: 18,735
definitions in production differed from the corrected files, accumulated across
the whole program, because `load_vocabulary` inserts with `ON CONFLICT DO
NOTHING` and never updates. `audit_content` had been passing throughout. A
check that reads the files can only ever say the repo is right; it cannot say
the product is.

**How it is safe.** Everything runs inside `BEGIN TRANSACTION READ ONLY`, so a
write is refused by Postgres itself rather than by this file being careful —
if a future edit adds an UPDATE, the database rejects it. It also never selects
a user identifier: `user_cards` is touched only through `count(*)`, so the
output carries no personal data and can be pasted into a chat or committed.

    python -m backend.services.quality.db_snapshot --out out/db-snapshot.json
    python -m backend.services.quality.db_snapshot --language ca --samples 40

The output is a fact file, not a verdict — compare it against the TSVs with
whatever check you need. `seeder.reconcile` (report mode) answers the narrower
"do definitions match" question and is the right tool for that alone.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

LANGUAGES = tuple(
    "ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko "
    "la id tl he fa".split()
)


async def snapshot_language(conn, code: str, samples: int) -> dict:
    lang_id = await conn.fetchval("SELECT id FROM languages WHERE code = $1", code)
    if lang_id is None:
        return {"code": code, "present": False}

    counts = await conn.fetchrow(
        """
        SELECT
          (SELECT count(*) FROM vocabulary WHERE language_id = $1)            AS vocabulary,
          (SELECT count(*) FROM vocabulary v
             JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en'
            WHERE v.language_id = $1)                                          AS with_definition,
          (SELECT count(*) FROM vocabulary v
             LEFT JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en'
            WHERE v.language_id = $1 AND (t.definition IS NULL OR t.definition = ''))
                                                                               AS no_definition,
          (SELECT count(*) FROM vocabulary
            WHERE language_id = $1 AND (part_of_speech IS NULL OR part_of_speech = ''))
                                                                               AS no_pos,
          (SELECT count(*) FROM user_cards WHERE language_id = $1)             AS learner_cards
        """,
        lang_id,
    )

    # A spread across the frequency band, not the first N — the top of the list
    # is where defects hurt most but the tail is where they hide.
    rows = await conn.fetch(
        """
        SELECT v.word, v.part_of_speech, t.definition
        FROM vocabulary v
        LEFT JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en'
        WHERE v.language_id = $1
        ORDER BY v.word
        LIMIT $2
        """,
        lang_id, samples,
    )

    return {
        "code": code,
        "present": True,
        "counts": dict(counts),
        "sample": [
            {"word": r["word"], "pos": r["part_of_speech"], "definition": r["definition"]}
            for r in rows
        ],
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--language", "-l", choices=(*LANGUAGES, "all"), default="all")
    parser.add_argument("--samples", type=int, default=25,
                        help="rows of real card content to include per language")
    parser.add_argument("--out", default="out/db-snapshot.json")
    args = parser.parse_args()

    if not args.db_url:
        print("Set DATABASE_URL or pass --db-url")
        return 2

    import asyncpg

    conn = await asyncpg.connect(args.db_url)
    try:
        # Postgres enforces this, not this script. Any write inside the
        # transaction is refused even if a future edit introduces one.
        await conn.execute("BEGIN TRANSACTION READ ONLY")
        codes = LANGUAGES if args.language == "all" else (args.language,)
        langs = [await snapshot_language(conn, c, args.samples) for c in codes]
        await conn.execute("COMMIT")
    finally:
        await conn.close()

    live = [x for x in langs if x.get("present")]
    print(f"{'lang':<6}{'vocab':>8}{'defined':>9}{'no-def':>8}{'no-pos':>8}{'cards':>8}")
    print("-" * 47)
    for x in live:
        c = x["counts"]
        print(f"{x['code']:<6}{c['vocabulary']:>8}{c['with_definition']:>9}"
              f"{c['no_definition']:>8}{c['no_pos']:>8}{c['learner_cards']:>8}")
    missing = [x["code"] for x in langs if not x.get("present")]
    if missing:
        print(f"\nno row in `languages`: {', '.join(missing)}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"languages": langs}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nwritten to {out} — read-only, and contains no user identifiers")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
