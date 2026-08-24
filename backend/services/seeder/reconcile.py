"""Bring the database in line with the committed TSVs — safely, and reversibly.

**Why this exists.** `load_vocabulary` inserts with `ON CONFLICT DO NOTHING`
on `(language_id, word)`. That is right for re-runs — it will not stomp an
admin's edit — but it means a CORRECTED gloss never reaches a learner. Every
repair this program has made to an existing row is invisible in production
until something updates it: `ana` reglossed from "his, her" to the progressive
particle, `creo` from a form of *crear* to "I believe", `soc` from "stump of a
tree" to "I am". The seeder adds new words; it cannot fix old ones.

**What it will not do.** It never DELETEs a vocabulary row. `user_cards.card_id`
is a polymorphic reference with no foreign key, so deleting vocabulary does not
cascade — it orphans the learner's card, and `get_due_cards` INNER JOINs
vocabulary, so the card silently stops appearing while keeping its SRS state.
Rows that have left the TSV are REPORTED, with the number of learner cards
that would be affected, and left for a human to decide.

**Reversibility.** Nothing is written until a rollback file exists on disk.
The rollback is plain SQL restoring every prior value, and can be replayed with
psql or `--rollback`. The whole apply runs in one transaction.

Usage:
    python -m backend.services.seeder.reconcile                    # report only
    python -m backend.services.seeder.reconcile --language mi
    python -m backend.services.seeder.reconcile --apply            # writes + rollback file
    python -m backend.services.seeder.reconcile --rollback out/reconcile-<stamp>.sql
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
from datetime import UTC
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
ROLLBACK_DIR = REPO / "out"

LANGUAGES = tuple(
    "ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko "
    "la id tl he fa".split()
)


def _sql_str(value: str) -> str:
    """Quote a Postgres string literal."""
    return "'" + value.replace("'", "''") + "'"


def read_tsv(code: str) -> dict[str, dict]:
    """word -> row, from the committed frequency file."""
    path = DATA / f"{code}_frequency.tsv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip()
            if word:
                out[word] = row
    return out


async def survey(conn, code: str) -> dict:
    """Compare one language's committed file against the database."""
    tsv = read_tsv(code)
    if not tsv:
        return {"code": code, "skipped": "no frequency file"}

    lang_id = await conn.fetchval("SELECT id FROM languages WHERE code = $1", code)
    if lang_id is None:
        return {"code": code, "skipped": "language not in the database"}

    db_rows = await conn.fetch(
        """
        SELECT v.id, v.word, v.part_of_speech, t.definition
        FROM vocabulary v
        LEFT JOIN translations t
               ON t.vocabulary_id = v.id AND t.locale = 'en'
        WHERE v.language_id = $1
        """,
        lang_id,
    )

    gloss_changes, pos_changes, missing_translation = [], [], []
    for row in db_rows:
        want = tsv.get(row["word"])
        if want is None:
            continue
        new_gloss = (want.get("en") or "").strip()
        new_pos = (want.get("pos") or "").strip()
        if new_gloss and row["definition"] is None:
            missing_translation.append({"id": row["id"], "word": row["word"],
                                        "new": new_gloss})
        elif new_gloss and row["definition"] != new_gloss:
            gloss_changes.append({"id": row["id"], "word": row["word"],
                                  "old": row["definition"], "new": new_gloss})
        if new_pos and (row["part_of_speech"] or "") != new_pos:
            pos_changes.append({"id": row["id"], "word": row["word"],
                                "old": row["part_of_speech"], "new": new_pos})

    # In the database but no longer in the file. Never deleted here.
    db_words = {r["word"] for r in db_rows}
    departed = sorted(db_words - set(tsv))
    departed_detail = []
    if departed:
        rows = await conn.fetch(
            """
            SELECT v.id, v.word,
                   (SELECT count(*) FROM user_cards uc
                     WHERE uc.card_type = 'vocabulary' AND uc.card_id = v.id) AS cards
            FROM vocabulary v
            WHERE v.language_id = $1 AND v.word = ANY($2::text[])
            """,
            lang_id, departed,
        )
        departed_detail = [{"id": r["id"], "word": r["word"], "cards": r["cards"]}
                           for r in rows]

    return {
        "code": code, "db_rows": len(db_rows), "tsv_rows": len(tsv),
        "gloss_changes": gloss_changes, "pos_changes": pos_changes,
        "missing_translation": missing_translation, "departed": departed_detail,
        "absent_from_db": sorted(set(tsv) - db_words),
    }


def write_rollback(reports: list[dict], stamp: str) -> Path:
    """Every statement needed to put the database back as it was."""
    ROLLBACK_DIR.mkdir(exist_ok=True)
    path = ROLLBACK_DIR / f"reconcile-{stamp}.sql"
    lines = [
        "-- Rollback for backend.services.seeder.reconcile",
        f"-- generated {stamp}",
        "-- Replay with: psql \"$DATABASE_URL\" -f this-file",
        "BEGIN;",
    ]
    for rep in reports:
        for c in rep.get("gloss_changes", []):
            if c["old"] is None:
                lines.append(
                    f"DELETE FROM translations WHERE vocabulary_id = '{c['id']}' "
                    f"AND locale = 'en';  -- {rep['code']} {c['word']}")
            else:
                lines.append(
                    f"UPDATE translations SET definition = {_sql_str(c['old'])} "
                    f"WHERE vocabulary_id = '{c['id']}' AND locale = 'en';"
                    f"  -- {rep['code']} {c['word']}")
        for c in rep.get("missing_translation", []):
            lines.append(
                f"DELETE FROM translations WHERE vocabulary_id = '{c['id']}' "
                f"AND locale = 'en';  -- {rep['code']} {c['word']} (was absent)")
        for c in rep.get("pos_changes", []):
            old = "NULL" if c["old"] is None else _sql_str(c["old"])
            lines.append(
                f"UPDATE vocabulary SET part_of_speech = {old} "
                f"WHERE id = '{c['id']}';  -- {rep['code']} {c['word']}")
    lines.append("COMMIT;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


async def apply(conn, reports: list[dict]) -> dict:
    counts = {"gloss": 0, "pos": 0, "added_translation": 0}
    async with conn.transaction():
        for rep in reports:
            for c in rep.get("gloss_changes", []):
                await conn.execute(
                    "UPDATE translations SET definition = $1 "
                    "WHERE vocabulary_id = $2 AND locale = 'en'",
                    c["new"], c["id"])
                counts["gloss"] += 1
            for c in rep.get("missing_translation", []):
                await conn.execute(
                    "INSERT INTO translations (vocabulary_id, locale, definition) "
                    "VALUES ($1, 'en', $2) "
                    "ON CONFLICT (vocabulary_id, locale) DO UPDATE SET definition = $2",
                    c["id"], c["new"])
                counts["added_translation"] += 1
            for c in rep.get("pos_changes", []):
                await conn.execute(
                    "UPDATE vocabulary SET part_of_speech = $1 WHERE id = $2",
                    c["new"], c["id"])
                counts["pos"] += 1
    return counts


def print_report(reports: list[dict], detail: bool) -> None:
    print(f"{'lang':<6}{'db':>7}{'tsv':>7}{'gloss':>7}{'pos':>6}{'no-tr':>7}"
          f"{'gone':>6}{'new':>6}")
    print("-" * 52)
    tot = {"gloss": 0, "pos": 0, "tr": 0, "gone": 0, "new": 0}
    for rep in reports:
        if rep.get("skipped"):
            continue
        g, p = len(rep["gloss_changes"]), len(rep["pos_changes"])
        t, d = len(rep["missing_translation"]), len(rep["departed"])
        n = len(rep["absent_from_db"])
        tot["gloss"] += g
        tot["pos"] += p
        tot["tr"] += t
        tot["gone"] += d
        tot["new"] += n
        print(f"{rep['code']:<6}{rep['db_rows']:>7}{rep['tsv_rows']:>7}"
              f"{g:>7}{p:>6}{t:>7}{d:>6}{n:>6}")
    print("-" * 52)
    print(f"{'all':<6}{'':>14}{tot['gloss']:>7}{tot['pos']:>6}{tot['tr']:>7}"
          f"{tot['gone']:>6}{tot['new']:>6}")
    print("\ngloss  definitions this would CORRECT (ON CONFLICT DO NOTHING never did)")
    print("pos    parts of speech this would correct")
    print("no-tr  rows with no English translation row at all — would be inserted")
    print("gone   in the database, no longer in the file — REPORTED ONLY, never deleted")
    print("new    in the file, not yet in the database — run the seeder, not this")

    if detail:
        for rep in reports:
            if rep.get("skipped") or not rep["gloss_changes"]:
                continue
            print(f"\n{rep['code']} — gloss corrections")
            for c in rep["gloss_changes"][:20]:
                print(f"  {c['word']:<16}{str(c['old'])[:34]!r}")
                print(f"  {'':<16}-> {c['new'][:60]!r}")
            if len(rep["gloss_changes"]) > 20:
                print(f"  … {len(rep['gloss_changes']) - 20} more")
    for rep in reports:
        if rep.get("skipped") or not rep["departed"]:
            continue
        risky = [d for d in rep["departed"] if d["cards"]]
        print(f"\n{rep['code']} — {len(rep['departed'])} rows left the file; "
              f"{len(risky)} have learner cards")
        for d in rep["departed"][:10]:
            flag = f"  ** {d['cards']} learner card(s)" if d["cards"] else ""
            print(f"  {d['word']}{flag}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--language", "-l", choices=(*LANGUAGES, "all"), default="all")
    ap.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--apply", action="store_true",
                    help="write the corrections (a rollback file is written first)")
    ap.add_argument("--detail", action="store_true", help="list every gloss change")
    ap.add_argument("--rollback", metavar="FILE", help="replay a rollback file and exit")
    args = ap.parse_args()

    if not args.db_url:
        print("Set DATABASE_URL or pass --db-url")
        return 2

    import asyncpg
    conn = await asyncpg.connect(args.db_url)
    try:
        if args.rollback:
            sql = Path(args.rollback).read_text(encoding="utf-8")
            await conn.execute(sql)
            print(f"rolled back from {args.rollback}")
            return 0

        codes = LANGUAGES if args.language == "all" else (args.language,)
        reports = [await survey(conn, c) for c in codes]
        print_report(reports, args.detail)

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to write.")
            return 0

        from datetime import datetime
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = write_rollback(reports, stamp)
        print(f"\nrollback written first: {path}")
        counts = await apply(conn, reports)
        print(f"applied — {counts['gloss']} glosses corrected, "
              f"{counts['added_translation']} translations inserted, "
              f"{counts['pos']} parts of speech corrected")
        print(f"undo with: python -m backend.services.seeder.reconcile "
              f"--rollback {path}")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
