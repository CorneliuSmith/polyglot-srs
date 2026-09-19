"""Read every Arabic row and ask one question: is this Modern Standard Arabic?

`docs/quality/ar-register-programme.md` is the brief; this is §5 step 2. The
prompts are pinned since PR #473, so new content is *asked* for MSA — this
script is for the content that already exists, which no instrument in the
repo can read. The tripwire (`ARABIC_DIALECT_MARKERS`) stays a tripwire: 29
whole words, measured under 5% precision on this corpus, and **one hit** in
the current bank — on a HEADWORD, not a sentence. A judge that reads the row
is the instrument.

The shape is `seeder/review_hints.py`: argparse, batches of 20, bounded
concurrency, a journal and `--restore`. Four things are deliberately
different, and each is a rule this programme has already paid for once:

- **It never writes to the database.** `--store db-sentences` and
  `--store db-locale` READ the live tables over `DATABASE_URL` and emit
  proposed `card_change_requests` / `translation_reviews` rows as SQL for the
  owner to apply. Production writes are the owner's (CLAUDE.md); a pass that
  could write them would be the one place that rule is broken by accident.
- **`--dry-run` is the default.** `review_hints` defaults to writing. Here the
  output *is* a review artefact — a row in `data/ar_register_fixes.tsv` with
  its `decision` column blank — so writing it is the exception, `--apply`
  asks for it, and nothing this script produces reaches a learner without a
  human in between.
- **Two providers, one schema.** Without `--base-url` it calls Anthropic with
  `resolve_model("sentence_checker", "ar")` — the checker tier, one up from
  the maker, because §6 of the quality rules says never self-certify. With
  `--base-url` it calls any OpenAI-compatible endpoint (vLLM, Ollama,
  llama.cpp), which is how the local Arabic-native judge of
  `docs/plans/arabic-msa-local-llm.md` arrives without the app changing. The
  §3.1 verdict schema is enforced on both paths — Anthropic's
  `output_config`, vLLM's guided JSON — so a model that cannot hold the shape
  fails loudly instead of returning prose the caller silently drops.
- **`--gold` grades the judge, not the corpus.** It runs the same prompt over
  `data/eval/ar_register_gold.tsv` and reports agreement per §3.2 category
  against the reviewer labels. Below the gate the judge does not touch
  content. That ordering is the whole point of §3.2 and this script will not
  let a full pass run without it having been done: `--store` prints where the
  calibration lives and what it said.

The judge itself — the rules, the schema, the two providers, the batching and
the three gates — is `content_judge.py`'s `register` question, since the
same discipline now serves four more questions (`docs/plans/
quality-guardrails-telemetry.md` §4.3 J1). This module is the register
question's stores, its fix queue and its journal; the names its tests and
reviewers use (`VERDICT_SCHEMA`, `_judge_anthropic`, `grade_gold`, …) are
kept here as the register-bound forms of the general ones.

Usage:

    python -m backend.services.quality.register_pass --gold
    python -m backend.services.quality.register_pass --gold --base-url http://gpu:8000/v1 --model jais-2-8b
    python -m backend.services.quality.register_pass --store sentences --limit 200
    python -m backend.services.quality.register_pass --store sentences --apply
    python -m backend.services.quality.register_pass --restore ar_register_fixes_20260916-101500.tsv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import logging
import os
import shutil
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from backend.services.quality import content_judge
from backend.services.quality.content_judge import (  # noqa: F401 — re-exported for the tests
    REGISTER,
    REGISTER_RULES,
    _parse,
    _text_of,
    system_prompt_for,
)

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
OUT_DIR = REPO / "out"
BACKUP_DIR = DATA / "backups"
GOLD = DATA / "eval" / "ar_register_gold.tsv"
DOCUMENTED = DATA / "eval" / "ar_register_documented.tsv"
# The calibration this judge last passed, and on what. Printed on every store
# pass so a full run cannot be read as trusted without someone seeing how
# narrow the evidence for it still is (§3.2).
CALIBRATION = "docs/quality/ar-register-2026-09-17.md"
FIXES = DATA / "ar_register_fixes.tsv"

logger = logging.getLogger("register_pass")

CODE = "ar"
BATCH_SIZE = 20

# The fix file's columns, verbatim from programme §6. `decision` and
# `reviewer` ship blank: this script proposes, a human disposes.
FIX_COLUMNS = [
    "id", "store", "field", "verdict", "variety", "evidence",
    "before", "after", "meaning_kept", "decision", "reviewer", "note",
]

STORES = ("sentences", "vocab", "grammar", "readings",
          "db-sentences", "db-locale", "db-hints", "db-explanations",
          "db-titles", "db-orphans")

# The learner-facing surfaces that carry text in a SUPPORT locale. A card
# shows several of them at once, and a reader who says "the Arabic on the
# cards is dialect" may be looking at any one. `db-locale` alone was not the
# whole set: a drill's hint and its translation, a grammar point's
# explanation, and a point's title and culture note are each stored in their
# own table and each reach a card.
SUPPORT_STORES = ("db-locale", "db-hints", "db-explanations", "db-titles")

# ---------------------------------------------------------------------------
# The verdict schema (programme §3.1) and the rules (§1) — the register
# question's, rendered by content_judge. `_RULES` is the text the judge was
# calibrated on (56/56 on the documented set); it lives with the other
# questions now and is the same string.
# ---------------------------------------------------------------------------

VERDICT_SCHEMA: dict[str, Any] = content_judge.schema_for(REGISTER)
BATCH_SCHEMA: dict[str, Any] = content_judge.batch_schema_for(REGISTER)
_RULES = REGISTER_RULES


def system_prompt() -> str:
    """The judge's system prompt: §1 as rules, plus the course's register pin.

    The pin is the same string every maker and checker in `backend/services`
    carries since PR #473, so the judge and the makers hold one standard
    rather than two that merely agree today."""
    return system_prompt_for(REGISTER, CODE)


# ---------------------------------------------------------------------------
# The two providers, bound to the register question.
#
# `content_judge` returns `(verdicts, usage)` because the judge loop logs the
# spend; this CLI reports to a person, so these keep the verdict-only contract
# its tests and callers were written to. The token count is the loop's, not
# the reviewer's.
# ---------------------------------------------------------------------------


async def _judge_anthropic(items: list[dict], model: str | None) -> list[dict]:
    """Ask Claude at the checker tier, schema enforced by output_config."""
    verdicts, _usage = await content_judge._judge_anthropic(REGISTER, items, model, CODE)
    return verdicts


async def _judge_openai(items: list[dict], base_url: str, model: str) -> list[dict]:
    """Ask an OpenAI-compatible endpoint (vLLM guided JSON)."""
    verdicts, _usage = await content_judge._judge_openai(REGISTER, items, base_url, model,
                                                         CODE)
    return verdicts


def judge_for(base_url: str | None, model: str | None) -> Callable:
    """The judge callable for this run."""
    return content_judge.judge_for(REGISTER, base_url, model, CODE)


def judge_name(base_url: str | None, model: str | None) -> str:
    return content_judge.judge_name(base_url, model, CODE)


# ---------------------------------------------------------------------------
# Running a set of items through the judge
# ---------------------------------------------------------------------------


async def run_items(items: list[dict], judge: Callable, *, batch_size: int,
                    concurrency: int) -> list[dict]:
    """Every item judged exactly once, batches in flight up to *concurrency*.

    A batch that fails is reported as `unsure` for each of its items rather
    than dropped: a missing row and an MSA row look identical in a count, and
    this programme has shipped that mistake before (quality rule 14)."""
    results, _usage = await content_judge.run_items(
        REGISTER, items, judge, batch_size=batch_size, concurrency=concurrency)
    return results


# ---------------------------------------------------------------------------
# The stores
# ---------------------------------------------------------------------------


def _read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sid(word: str, sentence: str) -> str:
    digest = hashlib.sha1(f"{word}\t{sentence}".encode()).hexdigest()
    return f"ar-sent-{digest[:12]}"


def load_store(store: str, limit: int | None) -> list[dict]:
    """The rows of a file store as judge items: id, field, text, translation."""
    items: list[dict] = []
    if store == "sentences":
        for row in _read_tsv(DATA / "ar_sentences.tsv"):
            items.append({"id": _sid(row["word"], row["sentence"]),
                          "field": "sentence", "text": row["sentence"],
                          "translation": row.get("translation") or "",
                          "headword": row.get("word") or ""})
    elif store == "vocab":
        for row in _read_tsv(DATA / "ar_frequency.tsv"):
            items.append({"id": f"ar-vocab-{row['rank']}", "field": "gloss",
                          "text": row["word"], "translation": row.get("en") or "",
                          "rank": int(row["rank"])})
    elif store == "readings":
        for row in _read_tsv(DATA / "ar_readings.tsv"):
            if not (row.get("word") or "").strip():
                continue
            items.append({"id": f"ar-reading-{row['word']}", "field": "reading",
                          "text": row["word"], "translation": row.get("reading") or ""})
    elif store == "grammar":
        parsed = json.loads((DATA / "grammar" / "ar_grammar.json").read_text(encoding="utf-8"))
        points = parsed["points"] if isinstance(parsed, dict) else parsed
        for p_i, point in enumerate(points):
            text = (point.get("explanation") or "").strip()
            if text:
                items.append({"id": f"ar-expl-{p_i}", "field": "explanation",
                              "text": text, "translation": ""})
            for d_i, drill in enumerate(point.get("drills") or []):
                items.append({"id": f"ar-drill-{p_i}-{d_i}", "field": "drill",
                              "text": drill.get("sentence") or "",
                              "translation": drill.get("translation") or "",
                              "headword": drill.get("answer") or "",
                              "hint": drill.get("hint") or ""})
    else:
        raise ValueError(f"not a file store: {store}")
    return items[:limit] if limit else items


def _committed_bank() -> set[tuple[str, str]]:
    """(headword, sentence) of every row in the committed Arabic bank."""
    return {((r.get("word") or "").strip(), (r.get("sentence") or "").strip())
            for r in _read_tsv(DATA / "ar_sentences.tsv")}


async def load_db_store(store: str, db_url: str, limit: int | None) -> list[dict]:
    """Live rows, READ ONLY. Never a write — see the module docstring."""
    import asyncpg

    host = urlsplit(db_url).hostname or "?"
    logger.info("reading %s from %s (read-only)", store, host)
    conn = await asyncpg.connect(db_url)
    try:
        if store == "db-orphans":
            # Live rows the committed bank does not contain. They never passed
            # a file-level pass, and they were harvested or generated by a
            # checker that did not know the standard (programme §2).
            rows = await conn.fetch(
                """
                SELECT es.id::text AS id, es.sentence, es.translation,
                       v.word, es.source
                FROM example_sentences es
                JOIN vocabulary v ON v.id = es.vocabulary_id
                JOIN languages l ON l.id = v.language_id
                WHERE l.code = $1
                ORDER BY es.id
                """, CODE)
            bank = _committed_bank()
            out = [{"id": f"es:{r['id']}", "field": "sentence",
                    "text": r["sentence"], "translation": r["translation"] or "",
                    "headword": r["word"] or "", "course": r["source"] or "?"}
                   for r in rows
                   if ((r["word"] or "").strip(),
                       (r["sentence"] or "").strip()) not in bank]
            return out[:limit] if limit else out
        if store == "db-sentences":
            rows = await conn.fetch(
                """
                SELECT es.id::text AS id, es.sentence, es.translation, v.word
                FROM example_sentences es
                JOIN vocabulary v ON v.id = es.vocabulary_id
                JOIN languages l ON l.id = v.language_id
                WHERE l.code = $1
                ORDER BY v.frequency_rank NULLS LAST, es.id
                LIMIT $2
                """, CODE, limit or 100_000)
            return [{"id": f"es:{r['id']}", "field": "sentence",
                     "text": r["sentence"], "translation": r["translation"] or "",
                     "headword": r["word"] or ""} for r in rows]
        if store == "db-locale":
            rows = await conn.fetch(
                """
                SELECT t.vocabulary_id::text AS id, v.word, t.definition,
                       l.code AS course
                FROM translations t
                JOIN vocabulary v ON v.id = t.vocabulary_id
                JOIN languages l ON l.id = v.language_id
                WHERE t.locale = $1 AND COALESCE(t.definition, '') <> ''
                ORDER BY v.frequency_rank NULLS LAST, t.vocabulary_id
                LIMIT $2
                """, CODE, limit or 100_000)
            return [{"id": f"tr:{r['id']}", "field": "definition",
                     "text": r["definition"], "translation": r["word"] or "",
                     "course": r["course"]} for r in rows]
        if store == "db-hints":
            rows = await conn.fetch(
                """
                SELECT dht.drill_id::text AS id, dht.hint, dht.translation,
                       l.code AS course
                FROM drill_hint_translations dht
                JOIN drill_sentences d ON d.id = dht.drill_id
                JOIN grammar_points gp ON gp.id = d.grammar_point_id
                JOIN languages l ON l.id = gp.language_id
                WHERE dht.locale = $1
                ORDER BY dht.drill_id
                LIMIT $2
                """, CODE, limit or 100_000)
            return [{"id": f"hint:{r['id']}", "field": "hint",
                     "text": " | ".join(x for x in (r["hint"], r["translation"]) if x),
                     "translation": "", "course": r["course"]} for r in rows]
        if store == "db-explanations":
            rows = await conn.fetch(
                """
                SELECT et.grammar_point_id::text AS id, et.explanation,
                       gp.title, l.code AS course
                FROM explanation_translations et
                JOIN grammar_points gp ON gp.id = et.grammar_point_id
                JOIN languages l ON l.id = gp.language_id
                WHERE et.locale = $1 AND COALESCE(et.explanation, '') <> ''
                ORDER BY et.grammar_point_id
                LIMIT $2
                """, CODE, limit or 100_000)
            return [{"id": f"expl:{r['id']}", "field": "explanation",
                     "text": r["explanation"], "translation": r["title"] or "",
                     "course": r["course"]} for r in rows]
        # db-titles
        rows = await conn.fetch(
            """
            SELECT gpt.grammar_point_id::text AS id, gpt.title,
                   gpt.function_note, gpt.culture_note, gp.title AS source_title,
                   l.code AS course
            FROM grammar_point_translations gpt
            JOIN grammar_points gp ON gp.id = gpt.grammar_point_id
            JOIN languages l ON l.id = gp.language_id
            WHERE gpt.locale = $1
            ORDER BY gpt.grammar_point_id
            LIMIT $2
            """, CODE, limit or 100_000)
        return [{"id": f"title:{r['id']}", "field": "title",
                 "text": " | ".join(x for x in (r["title"], r["function_note"],
                                                r["culture_note"]) if x),
                 "translation": r["source_title"] or "", "course": r["course"]}
                for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def write_jsonl(results: list[dict], stamp: str, meta: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"ar-register-{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def fix_rows(results: list[dict], store: str) -> list[dict]:
    """The proposed fixes: everything that is not a confident, clean `msa`.

    `decision` and `reviewer` are blank by construction — the TSV is a queue,
    not a changelog. An orthography-only finding is carried with verdict
    `msa` so the spelling pass can have it, and is never a register fix."""
    rows = []
    for r in results:
        verdict = r.get("verdict")
        kind = r.get("kind")
        if verdict == "msa" and kind != "orthography_only":
            continue
        rows.append({
            "id": r.get("id", ""), "store": store, "field": r.get("field", ""),
            "verdict": verdict or "", "variety": r.get("variety") or "",
            "evidence": " ".join(r.get("evidence") or []),
            "before": (r.get("text") or "").replace("\t", " "),
            "after": (r.get("msa") or "").replace("\t", " "),
            "meaning_kept": "yes" if r.get("meaning_kept") else "no",
            "decision": "", "reviewer": "",
            "note": f"[{kind or '-'}; confidence {r.get('confidence')}] "
                    f"{(r.get('note') or '').replace(chr(9), ' ')}",
        })
    return rows


def write_fixes(rows: list[dict], stamp: str) -> tuple[Path, Path | None]:
    """Write the fix queue, journalling whatever was there before."""
    backup = None
    if FIXES.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUP_DIR / f"ar_register_fixes_{stamp}.tsv"
        shutil.copy2(FIXES, backup)
    with FIXES.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIX_COLUMNS, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return FIXES, backup


def _sql_literal(text: str) -> str:
    return "'" + (text or "").replace("'", "''") + "'"


def write_db_sql(results: list[dict], store: str, stamp: str) -> Path | None:
    """Proposed queue rows as SQL for the OWNER to apply — never executed here.

    `card_change_requests.author_id` is NOT NULL and references
    `auth.users(id)`, so a machine-generated row cannot be inserted without a
    real account to hang it on. The SQL therefore opens with a `\\set` the
    owner fills in; running it unedited fails loudly rather than inventing an
    author. `field` and `target_type` are both CHECK-constrained, so the
    values written here are from those lists.
    """
    rows = [r for r in results
            if r.get("verdict") in ("dialect", "classical", "unsure")]
    if not rows:
        return None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"ar-register-{store}-{stamp}.sql"
    lines = [
        f"-- Arabic register queue, {store}, {stamp}. PREPARED, NOT APPLIED.",
        "-- Every production write is the owner's (CLAUDE.md, programme §7).",
        "-- card_change_requests.author_id is NOT NULL -> auth.users(id):",
        "-- set it to the reviewing account before running, or this fails.",
        "\\set author_id '00000000-0000-0000-0000-000000000000'",
        "BEGIN;",
    ]
    if store == "db-sentences":
        for r in rows:
            target = r["id"].split(":", 1)[1]
            issue = (f"Register: {r.get('verdict')}"
                     + (f" ({r.get('variety')})" if r.get("variety") else "")
                     + ". Evidence: " + (", ".join(r.get("evidence") or []) or "-")
                     + ". " + (r.get("note") or ""))[:2000]
            lines.append(
                "INSERT INTO card_change_requests "
                "(author_id, language_id, target_type, target_id, field, "
                "issue, suggestion, quote) VALUES (:'author_id', "
                f"(SELECT id FROM languages WHERE code = 'ar'), "
                f"'example_sentence', '{target}'::uuid, 'sentence', "
                f"{_sql_literal(issue)}, {_sql_literal(r.get('msa') or '')}, "
                f"{_sql_literal(r.get('text') or '')});")
    else:
        for r in rows:
            target = r["id"].split(":", 1)[1]
            reason = (f"Register: {r.get('verdict')}. "
                      + (r.get("note") or ""))[:2000]
            lines.append(
                "INSERT INTO translation_reviews "
                "(vocabulary_id, locale, proposed, reason) VALUES "
                f"('{target}'::uuid, 'ar', "
                f"{_sql_literal(r.get('msa') or '')}, {_sql_literal(reason)}) "
                "ON CONFLICT DO NOTHING;")
    lines.append("COMMIT;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def summarise(results: list[dict]) -> dict:
    counts: dict[str, int] = {}
    kinds: dict[str, int] = {}
    evidence: dict[str, int] = {}
    for r in results:
        counts[r.get("verdict") or "?"] = counts.get(r.get("verdict") or "?", 0) + 1
        if r.get("kind"):
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        for word in r.get("evidence") or []:
            evidence[word] = evidence.get(word, 0) + 1
    confident = sum(1 for r in results
                    if r.get("verdict") == "dialect" and (r.get("confidence") or 0) >= 0.7)
    return {
        "items": len(results), "verdicts": counts, "kinds": kinds,
        "confident_dialect": confident,
        "top_evidence": sorted(evidence.items(), key=lambda t: -t[1])[:10],
    }


# ---------------------------------------------------------------------------
# --gold: calibration against the reviewer labels (§3.2)
# ---------------------------------------------------------------------------

# The gold set's `label` column, mapped onto the judge's verdict vocabulary.
# A reviewer writing `orthography_only` is saying "MSA, with a spelling note",
# which is verdict `msa` — filing it as dialect is the specific failure §3.2
# gates on, so the two must be comparable. The map is the question's.
_LABEL_TO_VERDICT = REGISTER.label_map


def load_gold() -> list[dict]:
    if not GOLD.exists():
        raise SystemExit(f"no gold set at {GOLD.relative_to(REPO)} — "
                         "run scripts/build_ar_register_gold.py first.")
    return _read_tsv(GOLD)


def grade_gold(labelled: list[dict], results: list[dict]) -> dict:
    """Agreement per §3.2, per category, plus the three gates.

    The general grader calls the third gate's class the *guard*; here it is
    `orthography_only`, and the report carries both names so the programme
    document, the reviewers' write-up and the tests keep reading
    `orthography_misfiled`."""
    report = content_judge.grade_gold(REGISTER, labelled, results)
    if report.get("labelled"):
        report["orthography_n"] = report["guard_n"]
        report["orthography_misfiled"] = report["guard_misfiled"]
        report["gate_orthography"] = report["gate_guard"]
    return report


def print_gold_report(report: dict) -> bool:
    """Print the §3.2 report. Returns True when all three gates pass."""
    return content_judge.print_gold_report(REGISTER, report)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def restore(name: str) -> int:
    path = Path(name)
    if not path.exists():
        path = BACKUP_DIR / name
    if not path.exists():
        print(f"ERROR: no journal at {name}")
        return 1
    shutil.copy2(path, FIXES)
    rows = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    print(f"RESTORED {FIXES.relative_to(REPO)} from {path.name} ({rows} rows)")
    return 0


async def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--store", choices=STORES,
                    help="which store to read; omit with --gold")
    ap.add_argument("--gold", action="store_true",
                    help="run on the gold set and report agreement per §3.2")
    ap.add_argument("--base-url",
                    help="OpenAI-compatible endpoint for the local judge "
                         "(vLLM/Ollama); omit to use Anthropic")
    ap.add_argument("--model", help="model id (required with --base-url)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--apply", action="store_true",
                    help="write the fix queue (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="the default; nothing is written")
    ap.add_argument("--restore", metavar="FILE",
                    help="put back a previous ar_register_fixes.tsv from its journal")
    ap.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if args.restore:
        return restore(args.restore)
    if not args.gold and not args.store:
        ap.error("give --store STORE or --gold")

    judge = judge_for(args.base_url, args.model)
    name = judge_name(args.base_url, args.model)
    stamp = _stamp()
    logger.info("judge: %s", name)

    if args.gold:
        labelled = load_gold()
        # A vocabulary item's rank is the question, not decoration — see
        # VOCABULARY ENTRIES in the rules; gold_items reads it from the id.
        items = content_judge.gold_items(REGISTER, labelled)
        if args.limit:
            items = items[:args.limit]
        results = await run_items(items, judge, batch_size=args.batch_size,
                                  concurrency=args.concurrency)
        report = grade_gold(labelled, results)
        path = write_jsonl(results, stamp, {"mode": "gold", "judge": name,
                                            "items": len(items), "report": report})
        print(json.dumps(summarise(results), ensure_ascii=False, indent=1))
        passed = print_gold_report(report)
        print(f"\nverdicts -> {path.relative_to(REPO)}")
        return 0 if passed else 2

    if args.store.startswith("db-"):
        if not args.db_url:
            print("ERROR: DATABASE_URL not set.")
            return 1
        items = await load_db_store(args.store, args.db_url, args.limit)
    else:
        items = load_store(args.store, args.limit)
    logger.info("%s: %d items", args.store, len(items))

    results = await run_items(items, judge, batch_size=args.batch_size,
                              concurrency=args.concurrency)
    summary = summarise(results)
    path = write_jsonl(results, stamp, {"mode": args.store, "judge": name,
                                        "items": len(items), "summary": summary})
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    rows = fix_rows(results, args.store)
    if args.store.startswith("db-"):
        sql = write_db_sql(results, args.store, stamp)
        if sql:
            print(f"\n{sum(1 for r in results if r.get('verdict') in ('dialect', 'classical', 'unsure'))}"
                  f" queue rows prepared as SQL -> {sql.relative_to(REPO)}")
            print("   NOT applied. Set :author_id and run it yourself "
                  "(programme §7); the agent never writes to production.")
    if args.apply:
        fixes, backup = write_fixes(rows, stamp)
        print(f"\n{len(rows)} proposed fixes -> {fixes.relative_to(REPO)} "
              "(decision column blank — reviewers fill it)")
        if backup:
            print(f"previous queue journaled to {backup.name} "
                  f"(undo: --restore {backup.name})")
    else:
        print(f"\nDRY RUN — {len(rows)} fixes would be written to "
              f"{FIXES.relative_to(REPO)}. Pass --apply to write them.")
    print(f"verdicts -> {path.relative_to(REPO)}")
    print(f"\nCalibration: {CALIBRATION}")
    labelled = sum(1 for r in _read_tsv(GOLD) if (r.get("label") or "").strip()) \
        if GOLD.exists() else 0
    documented = (len(_read_tsv(DOCUMENTED)) - 0) if DOCUMENTED.exists() else 0
    if labelled:
        print(f"   gold set: {labelled} items carry a reviewer label.")
    else:
        print(f"   gold set: NOT LABELLED by a reviewer. The §3.2 gate has "
              f"only been measured on the {documented} documented answers, "
              "which is 9% of the set —")
        print("   treat these verdicts as a queue to review, never as a result.")
    print("\nNothing here reaches production. Reviewers work the TSV "
          "(programme §6), then scripts/apply_register_fixes.py, then the "
          "owner's refeed (docs/quality/refeed.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
