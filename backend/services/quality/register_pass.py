"""Read every Arabic row and ask one question: is this Modern Standard Arabic?

`docs/quality/ar-register-programme.md` is the brief; this is §5 step 2. The
prompts are pinned since PR #473, so new content is *asked* for MSA — this
script is for the content that already exists, which no instrument in the
repo can read. The tripwire (`ARABIC_DIALECT_MARKERS`) stays a tripwire: 29
whole words, measured under 5% precision on this corpus, and **zero hits** in
the current sentence bank. A judge that reads the sentence is the instrument.

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

STORES = ("sentences", "vocab", "grammar", "readings", "db-sentences", "db-locale")

# ---------------------------------------------------------------------------
# The verdict schema — programme §3.1, exactly.
# ---------------------------------------------------------------------------

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "i": {"type": "integer", "description": "The item's index in this batch."},
        "verdict": {"type": "string", "enum": ["dialect", "classical", "msa", "unsure"]},
        "variety": {
            "type": ["string", "null"],
            "enum": ["egyptian", "levantine", "gulf", "iraqi", "maghrebi", "mixed", None],
        },
        "evidence": {
            "type": "array", "items": {"type": "string"},
            "description": "The exact words that carry the verdict. Empty for msa.",
        },
        "kind": {
            "type": ["string", "null"],
            "enum": ["lexeme", "morphology", "orthography_only", "archaic", None],
        },
        "msa": {
            "type": ["string", "null"],
            "description": "The minimal MSA rewrite, keeping meaning, headword and level. Null if none is needed or none is possible.",
        },
        "meaning_kept": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "note": {"type": "string"},
    },
    "required": ["i", "verdict", "variety", "evidence", "kind", "msa",
                 "meaning_kept", "confidence", "note"],
    "additionalProperties": False,
}

BATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": VERDICT_SCHEMA}},
    "required": ["verdicts"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# The judge's rules — programme §1, rendered.
# ---------------------------------------------------------------------------

_RULES = """\
You are an Arabic register judge. For each item you answer one question: is \
this Modern Standard Arabic (الفصحى), the register of news and textbooks?

WHAT COUNTS AS NOT-MSA

1. Dialect lexemes — words MSA does not have.
   Egyptian: عايز/عاوز, مش, فين, إيه, إزاي, إزيك, دلوقتي, كده, علشان/عشان, \
ده/دي/دول (as demonstratives), بتاع, برضو, لسه, أوي, يلا, بكرة (as "tomorrow"), \
ماشي, خلاص (as "OK").
   Levantine: بدي/بدك, شو, ليش, وين, هيك, هاد/هاي/هدول, منيح, كتير, هلق, لسا, \
عم (as progressive marker), كمان (as "also"), معلش, كيفك.
   Gulf/Iraqi: شلون, وش/وشو, شنو, ماكو/أكو, مو, الحين, توه, زين (as "good"), \
عيل, هسه, دحين.
   Maghrebi: واش, بزاف, غادي, كاين, علاش, دابا.

2. Dialect morphology — MSA words in dialect grammar. The b-imperfect \
(بيكتب, بتروح) and the ha-/h- future (هيروح, حيروح); negation with مش or ما…ش \
(ما عرفتش); a demonstrative AFTER its noun (الكتاب ده); a question word at the \
end (رايح فين؟); عم/قاعد/بـ progressives; pronunciation spelled out (ث→ت, \
ذ→د/ز, ق→ء/ك/g).

3. Classical or archaic — forms MSA no longer uses productively: energic and \
jussive-with-ن forms, Qurʾanic vocabulary in an everyday sentence, حرف نداء \
archaisms. Verdict "classical", kind "archaic". The fix is plain MSA press \
register, never a more colloquial one.

WHAT IS NOT A TELL — these have all been verified in this corpus as ordinary \
MSA, and false alarms here have cost more than misses:
   هو (he), عم (paternal uncle, and "from what?"), عمال (workers), دول \
(states, and "to internationalize"), بدون, شكرًا, تمام, مين (harbours), كمان \
(violin), زي (a verbal noun), زين (to adorn), خلاص (deliverance), بكرة (a ball, \
and "early morning" — بكرة القدم is football), الحين inside بين الحين والآخر, \
الموظفين (contains فين), خلّص (form II, to rescue), أوي (verbal noun of أوى).
   A word is a tell only AS A WHOLE WORD IN ITS DIALECT SENSE. بـ followed by \
a NOUN is the preposition, never the b-imperfect: بالسيارة, بنفسك, بالنسبة, \
بيتها are all MSA. Judge the sentence, not the substring.

ORTHOGRAPHY IS NOT REGISTER. Word-final ى vs ي, ة vs ه, hamza seats (أ/إ/ا), \
the presence or absence of tashkeel, and Arabic-Indic digits are spelling, and \
the grader already folds them. Never return "dialect" for one of these. If the \
only oddity is spelling, return verdict "msa" with kind "orthography_only" and \
name the spelling in the note, so the spelling pass can have it.

ALLOWED MSA VARIATION. Pan-Arab MSA has regional lexical preferences that are \
all MSA and must not be "fixed": سيارة everywhere; هاتف/جوال/موبايل (prefer \
هاتف as the most widely understood, accept the others); مدرِّس/معلِّم; \
الآن/حاليًا. Loanwords MSA press uses (إنترنت, كمبيوتر, تلفزيون) are fine.

VOCABULARY ENTRIES ARE A DIFFERENT QUESTION. An item with a "rank" is a \
headword from a frequency list, and the question is not only "is this string \
MSA?" but "does this ENTRY exist because of an MSA word?". The rank is a count \
over a real corpus, and a corpus of written Arabic contains dialect. So when \
the headword is also a dialect word, ask whether the GLOSS's sense could \
plausibly be that frequent:
  - If the gloss names a common MSA word, the rank is earned and the entry is \
MSA. كمان at rank ~4200 glossed "violin" is a real word at a believable rank. \
So are دول "states / to internationalize", زين "to adorn", عم "from what?", \
خلاص "deliverance", بكرة "ball, early morning".
  - If the gloss names something vanishingly rare — an obscure plant, a \
technical botanical or anatomical sense, a verb no newspaper has printed in a \
century — then that sense cannot have earned a rank in the low thousands, and \
the count belongs to the dialect homograph. The entry is a dialect word wearing \
an MSA gloss. Return "dialect", name the dialect word in the evidence, and say \
in the note which sense the rank actually belongs to. Set "msa" to null: there \
is nothing to rewrite, the entry should be retired.
This is the same shape as a misspelling that outranks the word it is a \
misspelling of — the frequency is real, and it belongs to something other than \
the entry it is filed under. Judge the rank, not only the string.

THE REWRITE. Rewrite the minimum: keep every MSA word, replace only the \
evidence, keep the meaning, keep the headword's surface form where one is \
given, and keep the level. If the meaning exists only in dialect (a greeting \
formula, a proverb), set "msa" to null and say so in the note — inventing an \
MSA sentence nobody says is worse than retiring the row.

"unsure" IS A LEGAL ANSWER and routes to a human. Use it rather than guessing. \
Set "confidence" honestly: below 0.7 means you want a reviewer.

Answer with one verdict object per item, in the schema given, using the item's \
own "i". Return every item exactly once."""


def system_prompt() -> str:
    """The judge's system prompt: §1 as rules, plus the course's register pin.

    The pin is the same string every maker and checker in `backend/services`
    carries since PR #473, so the judge and the makers hold one standard
    rather than two that merely agree today."""
    from backend.services.quality_rules import register_line

    return _RULES + "\n" + register_line(CODE).strip()


# ---------------------------------------------------------------------------
# The two providers
# ---------------------------------------------------------------------------


async def _judge_anthropic(items: list[dict], model: str | None) -> list[dict]:
    """Ask Claude, with the schema enforced by output_config."""
    from anthropic import AsyncAnthropic

    from backend.config import get_settings
    from backend.services.models import resolve_model

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model or resolve_model("sentence_checker", CODE),
        max_tokens=8192,
        system=system_prompt(),
        messages=[{"role": "user", "content": json.dumps(items, ensure_ascii=False)}],
        output_config={"format": {"type": "json_schema", "schema": BATCH_SCHEMA}},
    )
    return _parse(_text_of(response))


async def _judge_openai(items: list[dict], base_url: str, model: str) -> list[dict]:
    """Ask an OpenAI-compatible endpoint, with vLLM guided JSON.

    vLLM, Ollama and llama.cpp all speak this; `response_format.json_schema`
    is what makes the local judge hold the same shape as the Anthropic one
    instead of returning prose we would have to regex."""
    import httpx

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "register_verdicts", "schema": BATCH_SCHEMA,
                            "strict": True},
        },
    }
    url = base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=180) as http:
        response = await http.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
    return _parse(body["choices"][0]["message"]["content"])


def _text_of(response: Any) -> str:
    parts = []
    for block in getattr(response, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def _parse(text: str) -> list[dict]:
    """The verdict list out of a model's reply, or an explicit failure.

    A schema-constrained call should never need the brace scan; it is here
    because a local server whose guided decoding is misconfigured returns
    prose that parses as nothing, and silently returning [] would read as
    "every row is MSA" — the worst possible failure for this script."""
    if not (text or "").strip():
        raise ValueError("judge returned an empty response")
    try:
        blob = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError(f"judge returned no JSON object: {text[:200]!r}") from None
        blob = json.loads(text[start:end + 1])
    verdicts = blob.get("verdicts") if isinstance(blob, dict) else blob
    if not isinstance(verdicts, list):
        raise ValueError(f"judge returned no verdict list: {str(blob)[:200]!r}")
    return verdicts


def judge_for(base_url: str | None, model: str | None) -> Callable:
    """The judge callable for this run, and the name to record it under."""
    if base_url:
        if not model:
            raise SystemExit("--base-url needs --model (the endpoint's model id).")

        async def local(items: list[dict]) -> list[dict]:
            return await _judge_openai(items, base_url, model)
        return local

    async def anthropic(items: list[dict]) -> list[dict]:
        return await _judge_anthropic(items, model)
    return anthropic


def judge_name(base_url: str | None, model: str | None) -> str:
    if base_url:
        host = urlsplit(base_url).hostname or "local"
        return f"local:{model}@{host}"
    if model:
        return model
    from backend.services.models import resolve_model
    return resolve_model("sentence_checker", CODE)


# ---------------------------------------------------------------------------
# Running a set of items through the judge
# ---------------------------------------------------------------------------


async def run_items(items: list[dict], judge: Callable, *, batch_size: int,
                    concurrency: int) -> list[dict]:
    """Every item judged exactly once, batches in flight up to *concurrency*.

    A batch that fails is reported as `unsure` for each of its items rather
    than dropped: a missing row and an MSA row look identical in a count, and
    this programme has shipped that mistake before (quality rule 14)."""
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    sem = asyncio.Semaphore(concurrency)

    async def one(batch: list[dict]) -> list[dict]:
        payload = [{"i": n, **{k: v for k, v in item.items() if k != "id"}}
                   for n, item in enumerate(batch)]
        async with sem:
            try:
                verdicts = await judge(payload)
            except Exception as exc:                       # noqa: BLE001
                logger.warning("batch failed (%s) — %d items to unsure",
                               exc.__class__.__name__, len(batch))
                return [{**item, "verdict": "unsure", "variety": None,
                         "evidence": [], "kind": None, "msa": None,
                         "meaning_kept": False, "confidence": 0.0,
                         "note": f"judge error: {exc}"} for item in batch]
        by_i = {v.get("i"): v for v in verdicts if isinstance(v, dict)}
        out = []
        for n, item in enumerate(batch):
            v = by_i.get(n)
            if v is None:
                out.append({**item, "verdict": "unsure", "variety": None,
                            "evidence": [], "kind": None, "msa": None,
                            "meaning_kept": False, "confidence": 0.0,
                            "note": "judge returned no verdict for this item"})
            else:
                out.append({**item, **{k: v.get(k) for k in VERDICT_SCHEMA["properties"]
                                       if k != "i"}})
        return out

    results: list[dict] = []
    for chunk in await asyncio.gather(*(one(b) for b in batches)):
        results.extend(chunk)
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


async def load_db_store(store: str, db_url: str, limit: int | None) -> list[dict]:
    """Live rows, READ ONLY. Never a write — see the module docstring."""
    import asyncpg

    host = urlsplit(db_url).hostname or "?"
    logger.info("reading %s from %s (read-only)", store, host)
    conn = await asyncpg.connect(db_url)
    try:
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
        rows = await conn.fetch(
            """
            SELECT t.vocabulary_id::text AS id, v.word, t.definition
            FROM translations t
            JOIN vocabulary v ON v.id = t.vocabulary_id
            WHERE t.locale = $1 AND COALESCE(t.definition, '') <> ''
            ORDER BY v.frequency_rank NULLS LAST, t.vocabulary_id
            LIMIT $2
            """, CODE, limit or 100_000)
        return [{"id": f"tr:{r['id']}", "field": "definition",
                 "text": r["definition"], "translation": r["word"] or ""}
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
# gates on, so the two must be comparable.
_LABEL_TO_VERDICT = {
    "dialect": "dialect", "classical": "classical", "msa": "msa",
    "orthography_only": "msa", "unsure": "unsure", "broken": "broken",
}


def load_gold() -> list[dict]:
    if not GOLD.exists():
        raise SystemExit(f"no gold set at {GOLD.relative_to(REPO)} — "
                         "run scripts/build_ar_register_gold.py first.")
    return _read_tsv(GOLD)


def grade_gold(labelled: list[dict], results: list[dict]) -> dict:
    """Agreement per §3.2, per category, plus the two hard gates."""
    by_id = {r["id"]: r for r in results}
    rows = []
    for item in labelled:
        label = (item.get("label") or "").strip().lower()
        if not label:
            continue
        expected = _LABEL_TO_VERDICT.get(label, label)
        got = by_id.get(item["id"])
        if got is None:
            continue
        rows.append({
            "id": item["id"], "store": item.get("store", ""),
            "stratum": (item.get("stratum") or "").split(":")[0],
            "expected": expected, "got": got.get("verdict"),
            "label_kind": label, "got_kind": got.get("kind"),
        })
    if not rows:
        return {"labelled": 0, "note": "no labelled rows — reviewers have not filled the set"}

    # Gate 1: agreement on dialect vs msa, over the rows where the reviewer
    # said one or the other.
    binary = [r for r in rows if r["expected"] in ("dialect", "msa")]
    agree = sum(1 for r in binary
                if (r["got"] == "dialect") == (r["expected"] == "dialect"))
    # Gate 2: recall on the labelled dialect rows — all of them, §3.2.
    positives = [r for r in rows if r["expected"] == "dialect"]
    caught = [r for r in positives if r["got"] == "dialect"]
    # Gate 3: an orthography-only row must never be filed as dialect.
    orth = [r for r in rows if r["label_kind"] == "orthography_only"]
    misfiled = [r for r in orth if r["got"] == "dialect"]

    per_stratum: dict[str, dict] = {}
    for r in binary:
        bucket = per_stratum.setdefault(r["stratum"], {"n": 0, "agree": 0})
        bucket["n"] += 1
        bucket["agree"] += int((r["got"] == "dialect") == (r["expected"] == "dialect"))
    per_store: dict[str, dict] = {}
    for r in binary:
        bucket = per_store.setdefault(r["store"], {"n": 0, "agree": 0})
        bucket["n"] += 1
        bucket["agree"] += int((r["got"] == "dialect") == (r["expected"] == "dialect"))

    return {
        "labelled": len(rows),
        "binary_n": len(binary), "binary_agree": agree,
        "agreement": (agree / len(binary)) if binary else None,
        "positives": len(positives), "caught": len(caught),
        "recall": (len(caught) / len(positives)) if positives else None,
        "orthography_n": len(orth), "orthography_misfiled": len(misfiled),
        "per_stratum": per_stratum, "per_store": per_store,
        "misses": [r for r in positives if r["got"] != "dialect"],
        "false_alarms": [r for r in binary
                         if r["expected"] == "msa" and r["got"] == "dialect"],
        "gate_agreement": bool(binary) and agree / len(binary) >= 0.95,
        "gate_recall": bool(positives) and len(caught) == len(positives),
        "gate_orthography": not misfiled,
    }


def print_gold_report(report: dict) -> bool:
    """Print the §3.2 report. Returns True when all three gates pass."""
    if not report.get("labelled"):
        print("\nGOLD SET NOT LABELLED — nothing to grade against.")
        print(report.get("note", ""))
        print("Reviewers fill the `label` column of "
              f"{GOLD.relative_to(REPO)} using programme §1 and §6.")
        return False
    pct = f"{report['agreement']:.1%}" if report["agreement"] is not None else "n/a"
    rec = f"{report['recall']:.1%}" if report["recall"] is not None else "n/a"
    print(f"\nCALIBRATION — {report['labelled']} labelled items")
    print(f"  dialect vs msa agreement : {pct} "
          f"({report['binary_agree']}/{report['binary_n']})   "
          f"gate >= 95%  {'PASS' if report['gate_agreement'] else 'FAIL'}")
    print(f"  recall on labelled dialect: {rec} "
          f"({report['caught']}/{report['positives']})   "
          f"gate = 100%  {'PASS' if report['gate_recall'] else 'FAIL'}")
    print(f"  orthography-only misfiled : {report['orthography_misfiled']}"
          f"/{report['orthography_n']}   gate = 0  "
          f"{'PASS' if report['gate_orthography'] else 'FAIL'}")
    if report["per_stratum"]:
        print("  by stratum:")
        for name, b in sorted(report["per_stratum"].items(), key=lambda t: -t[1]["n"]):
            print(f"     {name:18s} {b['agree']}/{b['n']}")
    for miss in report["misses"][:10]:
        print(f"  MISS  {miss['id']} expected dialect, got {miss['got']}")
    for fa in report["false_alarms"][:10]:
        print(f"  FALSE ALARM  {fa['id']} expected msa, got dialect")
    return all((report["gate_agreement"], report["gate_recall"],
                report["gate_orthography"]))


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
        items = []
        for r in labelled:
            item = {"id": r["id"], "field": r["field"], "text": r["text"],
                    "translation": r.get("translation") or ""}
            # A vocabulary item's rank is the question, not decoration —
            # see VOCABULARY ENTRIES in the rules.
            if r["id"].startswith("ar-vocab-"):
                item["rank"] = int(r["id"].rsplit("-", 1)[-1])
            items.append(item)
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
