"""Check the ENGLISH translation against the sentence it claims to translate.

Every other pass in this codebase runs English → L. `generate_sentence_
translations` takes the English and produces Spanish; the checker then
grades that Spanish against that English. The English is ground truth
everywhere and is itself never examined — so a loose English caps every
language derived from it, and the damage is invisible because each
downstream locale looks *correct relative to its source*.

The owner found it from the outside: a Spanish rendering that was good,
sitting under an English one that was not.

This pass reverses the direction. It reads the sentence in the language
being taught and judges the English. Confident corrections are applied;
anything uncertain goes to the review queue for a human instead.

Two consequences it handles, because neither is obvious:

  * Fixing the English makes every locale rendering DERIVED from it stale.
    Those rows are deleted, not left to rot — the demand-driven loop
    refills them from the corrected English on next use.
  * data/<code>_sentences.tsv seeds with ON CONFLICT DO NOTHING, so
    editing the file and re-seeding changes nothing on an existing row.
    --write-tsv keeps the repo copy in step for FRESH environments, but
    the database is what a running deployment reads.

Pilot first (needs a real key; nothing is written on --dry-run):
    python -m backend.services.seeder.review_translations --language hi --limit 20 --dry-run
    python -m backend.services.seeder.review_translations --language hi --limit 20
    python -m backend.services.seeder.review_translations --all
    python -m backend.services.seeder.review_translations --restore <file>
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

from backend.services.translate import review_source_translations, translations_available

logger = logging.getLogger("review_translations")

REPO = Path(__file__).resolve().parents[3]
# Every applied change is journaled BEFORE it lands, so a whole run can be
# undone with --restore. A checker that can only make things worse
# permanently is not one anybody will dare run over real content.
BACKUP_DIR = REPO / "data" / "backups"


async def _candidates(conn, lang_id: str, limit: int) -> list[dict]:
    """English rows for this language, longest-untouched first.

    Only rows whose English is the one on the card: the 'en' locale row.
    A row a human has already edited or flagged is left alone — this pass
    exists to catch what nobody has looked at.
    """
    rows = await conn.fetch(
        """
        SELECT es.id, es.sentence, es.translation
        FROM example_sentences es
        WHERE es.language_id = $1
          AND es.translation_locale = 'en'
          AND es.translation IS NOT NULL
          AND length(trim(es.translation)) > 0
          AND coalesce(es.flagged, false) = false
          AND es.suggested_translation IS NULL
        ORDER BY es.difficulty_rank NULLS LAST, es.id
        LIMIT $2
        """,
        lang_id, limit,
    )
    return [dict(r) for r in rows]


async def _stale_locales(conn, sentence: str, lang_id: str) -> int:
    """Drop locale renderings generated from an English that just changed.

    They were faithful to the OLD English and are now quietly wrong. The
    auto-translate loop refills them on demand from the corrected text.
    """
    result = await conn.execute(
        """
        DELETE FROM example_sentences
        WHERE language_id = $1 AND sentence = $2 AND translation_locale <> 'en'
        """,
        lang_id, sentence,
    )
    return int(result.split()[-1]) if result.startswith("DELETE") else 0


async def review_language(
    db_url: str, code: str, *, limit: int, batch_size: int, dry_run: bool,
    write_tsv: bool,
) -> dict:
    conn = await asyncpg.connect(db_url)
    counts = {"checked": 0, "fixed": 0, "queued": 0, "stale_dropped": 0}
    backup_file = None
    try:
        lang = await conn.fetchrow(
            "SELECT id, name FROM languages WHERE code = $1", code
        )
        if not lang:
            logger.warning("no such language: %s", code)
            return counts
        items = await _candidates(conn, lang["id"], limit)
        if not items:
            logger.info("%s: nothing to review", code)
            return counts

        fixes: list[tuple[str, str, str, str]] = []  # id, sentence, old, new
        for start in range(0, len(items), batch_size):
            batch = items[start:start + batch_size]
            payload = [
                {"i": i, "sentence": it["sentence"], "translation": it["translation"]}
                for i, it in enumerate(batch)
            ]
            verdicts = await review_source_translations(lang["name"], payload)
            counts["checked"] += len(batch)
            for v in verdicts:
                it = batch[v["i"]]
                if v["verdict"] == "fixed" and v["translation"]:
                    fixes.append((it["id"], it["sentence"], it["translation"],
                                  v["translation"]))
                    logger.info("  FIX %s\n    %s\n    -> %s  (%s)",
                                it["sentence"], it["translation"],
                                v["translation"], v["note"])
                elif v["verdict"] == "reject":
                    counts["queued"] += 1
                    logger.info("  ASK %s — %s", it["sentence"], v["note"])
                    if not dry_run:
                        await _queue_for_human(conn, it, v["note"])

        if dry_run:
            logger.info("%s: DRY RUN — %d would be fixed, %d queued for a human",
                        code, len(fixes), counts["queued"])
            return counts

        if fixes:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            backup_file = BACKUP_DIR / f"translations_{code}_{stamp}.jsonl"
            with open(backup_file, "w", encoding="utf-8") as f:
                for sid, sentence, old, new in fixes:
                    f.write(json.dumps(
                        {"id": str(sid), "sentence": sentence,
                         "old": old, "new": new},
                        ensure_ascii=False) + "\n")

        for sid, sentence, _old, new in fixes:
            await conn.execute(
                "UPDATE example_sentences SET translation = $2 WHERE id = $1",
                sid, new,
            )
            counts["fixed"] += 1
            counts["stale_dropped"] += await _stale_locales(conn, sentence, lang["id"])

        if write_tsv and fixes:
            _rewrite_tsv(code, {s: n for _i, s, _o, n in fixes})

        if backup_file:
            logger.info("%s: originals journaled to %s (undo: --restore %s)",
                        code, backup_file, backup_file.name)
        return counts
    finally:
        await conn.close()


async def _queue_for_human(conn, item: dict, note: str) -> None:
    """Park an uncertain pair in the review queue rather than guessing.

    Uses the same suggestion columns the Review workspace already reads,
    so it surfaces where a reviewer is already looking instead of in a log
    nobody opens.
    """
    try:
        await conn.execute(
            """
            UPDATE example_sentences
            SET flagged = true,
                flag_reason = $2
            WHERE id = $1
            """,
            item["id"], f"English translation needs review: {note}"[:500],
        )
    except asyncpg.UndefinedColumnError:
        # Pre-migration deploy: the queue columns aren't there yet. Losing
        # the flag is survivable; failing the whole run is not.
        logger.warning("flagged/flag_reason not migrated — %s not queued", item["id"])


def _rewrite_tsv(code: str, replacements: dict[str, str]) -> int:
    """Mirror the fixes into data/<code>_sentences.tsv.

    Only for FRESH environments: seeding uses ON CONFLICT DO NOTHING, so
    this never changes an existing row in a running deployment. Keeping it
    in step still matters — otherwise the repo and the database disagree
    and the next seed of a new environment reintroduces the old English.
    """
    path = REPO / "data" / f"{code}_sentences.tsv"
    if not path.exists():
        logger.info("no %s — skipping TSV mirror", path.name)
        return 0
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = 0
    out = []
    for line in lines:
        parts = line.rstrip("\n").split("\t")
        # word, sentence, translation, rank[, ...] — leave anything that
        # doesn't match the shape exactly as it was.
        if len(parts) >= 3 and parts[1] in replacements:
            parts[2] = replacements[parts[1]]
            out.append("\t".join(parts) + "\n")
            changed += 1
        else:
            out.append(line)
    if changed:
        path.write_text("".join(out), encoding="utf-8")
        logger.info("%s: %d rows mirrored into %s", code, changed, path.name)
    return changed


async def restore(db_url: str, backup_path: Path) -> int:
    """Undo one run, exactly."""
    conn = await asyncpg.connect(db_url)
    n = 0
    try:
        with open(backup_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                await conn.execute(
                    "UPDATE example_sentences SET translation = $2 WHERE id = $1",
                    rec["id"], rec["old"],
                )
                n += 1
    finally:
        await conn.close()
    return n


async def main() -> None:
    p = argparse.ArgumentParser(
        description="Check English translations against their source sentences")
    p.add_argument("--language", "-l")
    p.add_argument("--all", action="store_true")
    p.add_argument("--limit", type=int, default=100,
                   help="rows per language (default 100)")
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--dry-run", action="store_true",
                   help="report only; write nothing")
    p.add_argument("--write-tsv", action="store_true",
                   help="also mirror fixes into data/<code>_sentences.tsv")
    p.add_argument("--restore", metavar="FILE",
                   help="undo a run, by its journal file")
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return
    if args.restore:
        path = Path(args.restore)
        if not path.is_absolute():
            path = BACKUP_DIR / args.restore
        print(f"restored {await restore(args.db_url, path)} translations")
        return
    if not translations_available():
        print("ERROR: no translation provider configured (ANTHROPIC_API_KEY).")
        return

    codes: list[str] = []
    if args.all:
        conn = await asyncpg.connect(args.db_url)
        try:
            codes = [r["code"] for r in await conn.fetch(
                "SELECT code FROM languages WHERE code <> 'en' ORDER BY code")]
        finally:
            await conn.close()
    elif args.language:
        codes = [args.language]
    else:
        print("ERROR: pass --language CODE or --all.")
        return

    total = {"checked": 0, "fixed": 0, "queued": 0, "stale_dropped": 0}
    for code in codes:
        counts = await review_language(
            args.db_url, code, limit=args.limit, batch_size=args.batch_size,
            dry_run=args.dry_run, write_tsv=args.write_tsv,
        )
        for k in total:
            total[k] += counts[k]
        print(f"{code}: checked {counts['checked']}, fixed {counts['fixed']}, "
              f"queued {counts['queued']}, stale locale rows dropped "
              f"{counts['stale_dropped']}")
    if len(codes) > 1:
        print(f"TOTAL: {total}")


if __name__ == "__main__":
    asyncio.run(main())
