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

## The English appears in TWO places, and both are pivots

  * `example_sentences.translation` (locale 'en') — the "in context" line
    under a vocabulary card. Every other locale's row for that sentence is
    generated from it.
  * `drill_sentences.translation` — the English under a grammar drill.
    Every `drill_hint_translations` row is generated from it.

The first pass shipped covering only example sentences, which left half
the cards in the product unexamined. `--source` selects; the default is
both.

Deliberately NOT in scope: `drill_sentences.hint`. A hint is judged on
whether it narrows without leaking, not on fidelity to a source, and that
is `backend.services.quality.audit_content`'s job. Vocabulary definitions
have their own clarity pass in `review_hints.py`.

## Two consequences per source, because neither is obvious

  * Fixing the English makes every locale rendering DERIVED from it stale.
    Those rows are deleted, not left to rot — the demand-driven loop
    refills them from the corrected English on next use.
  * The repo file and the database drift apart, and they drift in OPPOSITE
    directions:
      - `data/<code>_sentences.tsv` seeds ON CONFLICT DO NOTHING, so
        editing the file changes nothing on an existing row. The mirror is
        for FRESH environments only, and is opt-in (--write-tsv).
      - `data/grammar/<code>_grammar.json` seeds by UPDATE in place on
        (sentence, answer), so the NEXT re-seed would overwrite a database
        fix with the file's stale English. Mirroring drills is therefore
        not optional and happens whenever a fix is applied.

## Two ways to run it

Against the API (bills per row; nothing is written on --dry-run):

    python -m backend.services.seeder.review_translations --language hi --limit 20 --dry-run
    python -m backend.services.seeder.review_translations --language hi --limit 20
    python -m backend.services.seeder.review_translations --all --source drill

Or offline, with **no API key at all** — the judging is done by a Claude
Code session, which is already paid for, and this module just moves rows in
and out of a file:

    python -m backend.services.seeder.review_translations --language hi --limit 50 --export hi.jsonl
    # ... the session fills verdict/fixed/note on each line, in place ...
    python -m backend.services.seeder.review_translations --apply hi.jsonl --dry-run
    python -m backend.services.seeder.review_translations --apply hi.jsonl

Both write through the same code, so the journal, the stale-locale deletes
and the grammar-JSON mirror behave identically. Undo is the same either way:

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

SOURCES = ("example", "drill")


# ---------------------------------------------------------------- candidates

async def _example_candidates(conn, lang_id: str, limit: int) -> list[dict]:
    """English rows for this language, commonest words first.

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
    return [{**dict(r), "display": r["sentence"], "answer": None} for r in rows]


async def _drill_candidates(conn, lang_id: str, limit: int) -> list[dict]:
    """Grammar drills for this language, earliest in the path first.

    The stored `sentence` carries a {{answer}} blank; the translation
    renders the COMPLETED sentence, so the blank is filled before the
    judge sees it. Handing over the gapped form would have the judge
    compare "I drink tea" against "मैं चाय ___ हूँ" and call it broken.
    """
    rows = await conn.fetch(
        """
        SELECT ds.id, ds.sentence, ds.answer, ds.translation
        FROM drill_sentences ds
        JOIN grammar_points gp ON gp.id = ds.grammar_point_id
        WHERE gp.language_id = $1
          AND ds.translation IS NOT NULL
          AND length(trim(ds.translation)) > 0
          AND coalesce(ds.flagged, false) = false
        ORDER BY gp.display_order, ds.display_order, ds.id
        LIMIT $2
        """,
        lang_id, limit,
    )
    out = []
    for r in rows:
        item = dict(r)
        item["display"] = (item["sentence"] or "").replace(
            "{{answer}}", item["answer"] or "")
        out.append(item)
    return out


# ------------------------------------------------------------------- writing

async def _apply_example(conn, item: dict, new: str) -> None:
    await conn.execute(
        "UPDATE example_sentences SET translation = $2 WHERE id = $1",
        item["id"], new,
    )


async def _apply_drill(conn, item: dict, new: str) -> None:
    await conn.execute(
        "UPDATE drill_sentences SET translation = $2 WHERE id = $1",
        item["id"], new,
    )


async def _stale_example(conn, item: dict, lang_id: str) -> int:
    """Drop locale renderings generated from an English that just changed.

    They were faithful to the OLD English and are now quietly wrong. The
    auto-translate loop refills them on demand from the corrected text.
    Keyed by sentence, not id: one sentence is an example for several
    words, and each carries its own locale rows.
    """
    result = await conn.execute(
        """
        DELETE FROM example_sentences
        WHERE language_id = $1 AND sentence = $2 AND translation_locale <> 'en'
        """,
        lang_id, item["sentence"],
    )
    return int(result.split()[-1]) if result.startswith("DELETE") else 0


async def _stale_drill(conn, item: dict, _lang_id: str) -> int:
    """Same, for the drill overlay — and the whole row goes, not a column.

    `drill_hint_translations` holds the locale hint AND translation in one
    row, and `auto_translate.pending_drills` gates on the row being
    ABSENT. Blanking the translation column would leave a row that never
    refills, so the hint rendering is spent again alongside it. This is
    exactly what `seed_grammar` does when a re-seed changes the English.
    """
    result = await conn.execute(
        "DELETE FROM drill_hint_translations WHERE drill_id = $1", item["id"],
    )
    return int(result.split()[-1]) if result.startswith("DELETE") else 0


async def _queue_example(conn, item: dict, note: str) -> None:
    await _flag(conn, "example_sentences", item, note)


async def _queue_drill(conn, item: dict, note: str) -> None:
    await _flag(conn, "drill_sentences", item, note)


async def _flag(conn, table: str, item: dict, note: str) -> None:
    """Park an uncertain pair in the review queue rather than guessing.

    Uses the flag columns the Review workspace already reads, so it
    surfaces where a reviewer is already looking instead of in a log
    nobody opens. Both tables carry the same pair of columns.
    """
    try:
        await conn.execute(
            f"UPDATE {table} SET flagged = true, flag_reason = $2 WHERE id = $1",
            item["id"], f"English translation needs review: {note}"[:500],
        )
    except (asyncpg.UndefinedColumnError, asyncpg.UndefinedTableError):
        # Pre-migration deploy: the queue columns aren't there yet. Losing
        # the flag is survivable; failing the whole run is not.
        logger.warning("%s has no flag columns yet — %s not queued", table, item["id"])


# The one asymmetry worth knowing: an example-sentence fix survives a
# re-seed whatever the file says, while a drill fix does NOT — seeding
# UPDATEs drills in place from the JSON. So drills always mirror.
_SOURCE = {
    "example": {
        "label": "example sentences",
        "candidates": _example_candidates,
        "apply": _apply_example,
        "stale": _stale_example,
        "queue": _queue_example,
        "mirror_always": False,
    },
    "drill": {
        "label": "grammar drills",
        "candidates": _drill_candidates,
        "apply": _apply_drill,
        "stale": _stale_drill,
        "queue": _queue_drill,
        "mirror_always": True,
    },
}


def _zero() -> dict:
    return {"checked": 0, "fixed": 0, "queued": 0, "stale_dropped": 0}


async def review_source(
    conn, source: str, code: str, lang, *, limit: int, batch_size: int,
    dry_run: bool, write_tsv: bool,
) -> dict:
    """One (language, content type) pass. Returns its counts."""
    spec = _SOURCE[source]
    counts = _zero()
    items = await spec["candidates"](conn, lang["id"], limit)
    if not items:
        logger.info("%s/%s: nothing to review", code, source)
        return counts

    fixes: list[dict] = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        payload = [
            {"i": i, "sentence": it["display"], "translation": it["translation"]}
            for i, it in enumerate(batch)
        ]
        verdicts = await review_source_translations(lang["name"], payload)
        counts["checked"] += len(batch)
        for v in verdicts:
            it = batch[v["i"]]
            if v["verdict"] == "fixed" and v["translation"]:
                fixes.append({"item": it, "old": it["translation"],
                              "new": v["translation"]})
                logger.info("  FIX [%s] %s\n    %s\n    -> %s  (%s)",
                            source, it["display"], it["translation"],
                            v["translation"], v["note"])
            elif v["verdict"] == "reject":
                counts["queued"] += 1
                logger.info("  ASK [%s] %s — %s", source, it["display"], v["note"])
                if not dry_run:
                    await spec["queue"](conn, it, v["note"])

    if dry_run:
        logger.info("%s/%s: DRY RUN — %d would be fixed, %d queued for a human",
                    code, source, len(fixes), counts["queued"])
        return counts

    if fixes:
        _journal(code, source, fixes)

    for fix in fixes:
        await spec["apply"](conn, fix["item"], fix["new"])
        counts["fixed"] += 1
        counts["stale_dropped"] += await spec["stale"](conn, fix["item"], lang["id"])

    if fixes:
        if source == "drill":
            # Not optional: without this the next `seed_grammar` run puts
            # the old English straight back.
            _rewrite_grammar_json(
                code, {(f["item"]["sentence"], f["item"]["answer"]): f["new"]
                       for f in fixes})
        elif write_tsv:
            _rewrite_tsv(code, {f["item"]["sentence"]: f["new"] for f in fixes})
    return counts


def _journal(code: str, source: str, fixes: list[dict]) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = BACKUP_DIR / f"translations_{code}_{source}_{stamp}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for fix in fixes:
            it = fix["item"]
            f.write(json.dumps(
                {"id": str(it["id"]), "source": source, "language": code,
                 "sentence": it["sentence"], "answer": it["answer"],
                 "old": fix["old"], "new": fix["new"]},
                ensure_ascii=False) + "\n")
    logger.info("%s/%s: originals journaled to %s (undo: --restore %s)",
                code, source, path, path.name)
    return path


async def review_language(
    db_url: str, code: str, *, limit: int, batch_size: int, dry_run: bool,
    write_tsv: bool, sources: tuple[str, ...] = SOURCES,
) -> dict:
    """Every English-bearing content type for one language."""
    conn = await asyncpg.connect(db_url)
    total = _zero()
    total["by_source"] = {}
    try:
        lang = await conn.fetchrow(
            "SELECT id, name FROM languages WHERE code = $1", code
        )
        if not lang:
            logger.warning("no such language: %s", code)
            return total
        for source in sources:
            counts = await review_source(
                conn, source, code, lang, limit=limit, batch_size=batch_size,
                dry_run=dry_run, write_tsv=write_tsv,
            )
            total["by_source"][source] = counts
            for k in _zero():
                total[k] += counts[k]
        return total
    finally:
        await conn.close()


# ------------------------------------------- offline mode (no API key needed)
#
# The pass above calls the Anthropic API, which bills. When the judging is
# done by a Claude Code session instead, the model is already in the room and
# paying twice is silly — so the work splits in two:
#
#   --export FILE   read candidates, write them out, call nothing
#   (the session fills in verdict/fixed/note, editing the file in place)
#   --apply FILE    write the verdicts back, with every safety the API path has
#
# One file round-trips deliberately. A separate verdicts file would lose the
# original English, and without the original there is no way to notice that a
# row changed between export and apply — so a stale export would silently
# overwrite somebody's newer edit.

_LOOKUP = {
    "drill": """
        SELECT ds.id, ds.sentence, ds.answer, ds.translation,
               l.code AS code, gp.language_id AS language_id
        FROM drill_sentences ds
        JOIN grammar_points gp ON gp.id = ds.grammar_point_id
        JOIN languages l ON l.id = gp.language_id
        WHERE ds.id = $1
    """,
    "example": """
        SELECT es.id, es.sentence, NULL::text AS answer, es.translation,
               l.code AS code, es.language_id AS language_id
        FROM example_sentences es
        JOIN languages l ON l.id = es.language_id
        WHERE es.id = $1
    """,
}


async def _resolve_row(conn, row_id: str, hint: str | None):
    """Find a row by id, trusting but not requiring the file's `source`."""
    order = [hint] if hint in _SOURCE else []
    order += [s for s in SOURCES if s != hint]
    for source in order:
        try:
            row = await conn.fetchrow(_LOOKUP[source], row_id)
        except (ValueError, TypeError, asyncpg.DataError):
            return None  # not a uuid at all
        if row:
            return source, dict(row)
    return None


async def export_file(db_url: str, codes: list[str], *, limit: int,
                      sources: tuple[str, ...], path: Path) -> int:
    """Write the rows a judge should look at. Calls no model, spends nothing."""
    conn = await asyncpg.connect(db_url)
    n = 0
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for code in codes:
                lang = await conn.fetchrow(
                    "SELECT id, name FROM languages WHERE code = $1", code)
                if not lang:
                    logger.warning("no such language: %s", code)
                    continue
                for source in sources:
                    items = await _SOURCE[source]["candidates"](
                        conn, lang["id"], limit)
                    for it in items:
                        f.write(json.dumps({
                            "id": str(it["id"]),
                            "source": source,
                            "language": code,
                            # The sentence in the language being taught, blank
                            # already filled for a drill. This is the thing the
                            # English is judged AGAINST.
                            "sentence": it["display"],
                            "english": it["translation"],
                            # For the judge to fill in:
                            "verdict": "",   # ok | fixed | reject
                            "fixed": "",     # the better English, if verdict=fixed
                            "note": "",      # a few words on what was wrong
                        }, ensure_ascii=False) + "\n")
                        n += 1
                    logger.info("%s/%s: %d exported", code, source, len(items))
    finally:
        await conn.close()
    return n


async def apply_file(db_url: str, path: Path, *, dry_run: bool,
                     write_tsv: bool) -> dict:
    """Apply a judged export. Same journal, deletes and mirrors as the API path."""
    records = [json.loads(line) for line in
               path.read_text(encoding="utf-8").splitlines() if line.strip()]
    conn = await asyncpg.connect(db_url)
    totals = _zero()
    # unjudged: nobody filled a verdict in. unchanged: judged, and the verdict
    # was "leave it". Lumping them together makes a complete, careful run read
    # exactly like a file that never got looked at.
    totals.update(unjudged=0, unchanged=0, stale=0, unknown=0)
    groups: dict[tuple[str, str], list[dict]] = {}
    try:
        for rec in records:
            verdict = str(rec.get("verdict") or "").strip().lower()
            if verdict not in ("ok", "fixed", "reject"):
                # A line nobody judged is left alone rather than guessed at —
                # including a half-finished file.
                totals["unjudged"] += 1
                continue
            totals["checked"] += 1
            if verdict == "ok":
                totals["unchanged"] += 1
                continue

            found = await _resolve_row(conn, str(rec.get("id") or ""),
                                       rec.get("source"))
            if not found:
                totals["unknown"] += 1
                logger.warning("  no such row, skipping: %s", rec.get("id"))
                continue
            source, row = found

            if row["translation"] != rec.get("english"):
                # Edited since the export was taken. Applying now would undo
                # whoever did that, so it goes back in the queue instead.
                totals["stale"] += 1
                logger.warning("  changed since export, skipping: %s", row["id"])
                continue

            if verdict == "reject":
                totals["queued"] += 1
                if not dry_run:
                    await _SOURCE[source]["queue"](
                        conn, row, str(rec.get("note") or "unclear"))
                continue

            new = str(rec.get("fixed") or "").strip()
            if not new or new == row["translation"]:
                # "fixed" with nothing different in it is really an "ok".
                totals["unchanged"] += 1
                continue
            groups.setdefault((row["code"], source), []).append(
                {"item": row, "old": row["translation"], "new": new})

        planned = sum(len(v) for v in groups.values())
        if dry_run:
            logger.info(
                "DRY RUN — %d would be fixed, %d queued for a human, "
                "%d left as-is, %d not judged, %d changed since export, "
                "%d not found",
                planned, totals["queued"], totals["unchanged"],
                totals["unjudged"], totals["stale"], totals["unknown"])
            return totals

        for (code, source), fixes in groups.items():
            _journal(code, source, fixes)
            for fix in fixes:
                await _SOURCE[source]["apply"](conn, fix["item"], fix["new"])
                totals["fixed"] += 1
                totals["stale_dropped"] += await _SOURCE[source]["stale"](
                    conn, fix["item"], fix["item"]["language_id"])
            if source == "drill":
                _rewrite_grammar_json(
                    code, {(f["item"]["sentence"], f["item"]["answer"]): f["new"]
                           for f in fixes})
            elif write_tsv:
                _rewrite_tsv(code, {f["item"]["sentence"]: f["new"]
                                    for f in fixes})
        return totals
    finally:
        await conn.close()


# -------------------------------------------------------------- file mirrors

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


def _detect_indent(raw: str) -> int:
    """The file's own indent unit, so a mirror is a small diff.

    Most grammar files are indent=2; ha, ko, mi, pt and yo are indent=1.
    Re-dumping at the wrong width rewrites every line of a 3000-line file
    and buries the one that changed.
    """
    for line in raw.splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)
    return 2


def _rewrite_grammar_json(code: str, replacements: dict[tuple[str, str], str]) -> int:
    """Mirror drill fixes into data/grammar/<code>_grammar.json.

    Unlike the TSV this is REQUIRED, not a courtesy to fresh environments:
    `seed_grammar` matches a drill on (sentence, answer) and UPDATEs its
    translation in place, so the next seed of a running deployment would
    overwrite the database fix with the file's stale English. Same match
    key here, for that reason.
    """
    path = REPO / "data" / "grammar" / f"{code}_grammar.json"
    if not path.exists():
        logger.warning("no %s — drill fixes will be REVERTED by the next seed",
                       path.name)
        return 0
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    changed = 0
    for point in data.get("points", []):
        for drill in point.get("drills", []):
            new = replacements.get((drill.get("sentence"), drill.get("answer")))
            if new is not None and drill.get("translation") != new:
                drill["translation"] = new
                changed += 1
    if changed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=_detect_indent(raw)) + "\n",
            encoding="utf-8")
        logger.info("%s: %d drills mirrored into %s", code, changed, path.name)
    if changed < len(replacements):
        # The database has a drill the file does not (curated additions are
        # inserted with source 'ai'). Nothing to do, but say so rather than
        # let the numbers quietly disagree.
        logger.info("%s: %d of %d fixed drills had no row in %s",
                    code, len(replacements) - changed, len(replacements), path.name)
    return changed


# ------------------------------------------------------------------- restore

_RESTORE_SQL = {
    "example": "UPDATE example_sentences SET translation = $2 WHERE id = $1",
    "drill": "UPDATE drill_sentences SET translation = $2 WHERE id = $1",
}


async def restore(db_url: str, backup_path: Path) -> int:
    """Undo one run, exactly — file mirrors included.

    Journal lines written before drills were covered carry no `source`;
    they are all example sentences.
    """
    conn = await asyncpg.connect(db_url)
    n = 0
    drills: dict[str, dict[tuple[str, str], str]] = {}
    try:
        with open(backup_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                source = rec.get("source", "example")
                await conn.execute(_RESTORE_SQL[source], rec["id"], rec["old"])
                n += 1
                if source == "drill" and rec.get("language"):
                    drills.setdefault(rec["language"], {})[
                        (rec["sentence"], rec.get("answer"))] = rec["old"]
    finally:
        await conn.close()
    for code, replacements in drills.items():
        _rewrite_grammar_json(code, replacements)
    return n


async def main() -> None:
    p = argparse.ArgumentParser(
        description="Check English translations against their source sentences")
    p.add_argument("--language", "-l")
    p.add_argument("--all", action="store_true")
    p.add_argument("--source", "-s", choices=[*SOURCES, "all"], default="all",
                   help="which English to check (default: both)")
    p.add_argument("--limit", type=int, default=100,
                   help="rows per language PER SOURCE (default 100)")
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--dry-run", action="store_true",
                   help="report only; write nothing")
    p.add_argument("--write-tsv", action="store_true",
                   help="also mirror example fixes into data/<code>_sentences.tsv "
                        "(drill fixes always mirror — a re-seed would undo them)")
    p.add_argument("--restore", metavar="FILE",
                   help="undo a run, by its journal file")
    p.add_argument("--export", metavar="FILE",
                   help="write candidates to FILE and call no model — for "
                        "judging in a Claude Code session instead of the API")
    p.add_argument("--apply", metavar="FILE",
                   help="apply a judged export (the same file, verdicts filled in)")
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

    sources = SOURCES if args.source == "all" else (args.source,)

    # --apply needs no language list and no provider: the file says what to do.
    if args.apply:
        counts = await apply_file(args.db_url, Path(args.apply),
                                  dry_run=args.dry_run, write_tsv=args.write_tsv)
        print(f"applied: {counts}")
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

    # Exporting reads and writes a file. No provider needed, nothing spent.
    if args.export:
        path = Path(args.export)
        n = await export_file(args.db_url, codes, limit=args.limit,
                              sources=sources, path=path)
        print(f"exported {n} rows to {path} — fill in verdict/fixed/note, "
              f"then: --apply {path} --dry-run")
        return

    if not translations_available():
        print("ERROR: no translation provider configured (ANTHROPIC_API_KEY).\n"
              "       To judge in a Claude Code session instead, use --export.")
        return

    total = _zero()
    for code in codes:
        counts = await review_language(
            args.db_url, code, limit=args.limit, batch_size=args.batch_size,
            dry_run=args.dry_run, write_tsv=args.write_tsv, sources=sources,
        )
        for k in total:
            total[k] += counts[k]
        for source in sources:
            c = counts["by_source"].get(source, _zero())
            print(f"{code}/{source}: checked {c['checked']}, fixed {c['fixed']}, "
                  f"queued {c['queued']}, stale locale rows dropped "
                  f"{c['stale_dropped']}")
    if len(codes) > 1 or len(sources) > 1:
        print(f"TOTAL: {total}")


if __name__ == "__main__":
    asyncio.run(main())
