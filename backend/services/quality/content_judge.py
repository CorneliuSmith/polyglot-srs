"""One judge, five questions: a model reads the row and says whether it is right.

Every defect that reached a learner this month passed every mechanical check
in the repository, because each check asks whether a row is well-formed and
none asks whether it is right. The instruments that found them — the Arabic
register judge, the English sense audit, the gloss-faithfulness audit — were
models reading the row, calibrated against a gold set, run by hand in a
session and thrown away afterwards (`docs/plans/quality-guardrails-telemetry.md`
§0, §4.3 J1). `register_pass.py` was the first of them written down as code,
and this module is its discipline made the shape every question takes:

- **Rules with tells and non-tells.** Each question's system prompt names
  what counts, names what has already been verified NOT to count, says that
  `unsure` is a legal answer, and asks for every item exactly once. The
  register judge went 53/56 to 56/56 by fixing the question it was asked, not
  the model; a question is where the calibration lives.
- **One schema, both providers.** `schema_for(question)` renders the
  programme's §3.1 verdict shape with that question's enums. Anthropic
  enforces it through `output_config`, a local OpenAI-compatible endpoint
  through guided JSON, so a model that cannot hold the shape fails loudly
  instead of returning prose the caller silently drops.
- **Gold before store.** `grade_gold` applies the same three §3.2 gates to
  every question — agreement on the binary split, full recall on the
  labelled positives, the near-miss class never filed as the finding — and
  the CLI exits 2 below them. A question whose gold set is unlabelled cannot
  grade, and says so instead of reporting agreement against nothing.
- **The spend is counted.** `run_items` returns the token usage summed across
  its batches beside the verdicts. The owner's condition for a nightly judge
  was that its cost be visible and capped from the admin panel; the judge
  loop (a later unit) writes these numbers to `tutor_usage` as `kind='judge'`
  so they appear in AI costs beside `summary`.

Nothing here writes to a database or a data file. `register_pass` keeps its
stores, its fix queue and its journal and imports the provider layer from
here; the store passes for the other four questions arrive with the loop, and
until then this CLI refuses to run anything but `--gold`.

Usage:

    python -m backend.services.quality.content_judge --question sense --gold
    python -m backend.services.quality.content_judge --question register --gold \\
        --base-url http://gpu:8000/v1 --model jais-2-8b
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
EVAL = DATA / "eval"
OUT_DIR = REPO / "out"

logger = logging.getLogger("content_judge")

BATCH_SIZE = 20

# Every gold set carries these beside the question's own item columns
# (`data/eval/README.md`). `label` is the reviewer's verdict in the gold
# vocabulary; `category` the reviewer's kind; the rest is machine-written.
GOLD_COMMON_COLUMNS = ("id", "store", "field", "label", "category", "evidence", "note", "stratum")

# What `run_items` returns beside the verdicts, and what the loop logs.
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens", "calls")


# ---------------------------------------------------------------------------
# A question
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Question:
    """One thing the judge is asked about a row, with everything that makes
    the answer gradeable.

    `positive` is the class the question exists to find and `negative` the
    clean answer(s); the §3.2 agreement gate is measured over rows a reviewer
    labelled one or the other. `guard_labels` are the reviewer's near-miss
    labels — a spelling variant for register, a real-but-second sense for
    sense — that the third gate says must never come back as the finding. A
    false alarm has cost this programme more than a miss every time, and the
    guard class is where a keen judge produces them.

    `label_map` turns a gold label into a verdict the same way
    `register_pass` did: `orthography_only` is a reviewer saying "MSA, with a
    spelling note", and is compared as `msa`.
    """

    name: str
    rules: str
    verdict_enum: tuple[str, ...]
    category_enum: tuple[str, ...]
    item_fields: tuple[str, ...]
    gold_path: Path
    label_map: dict[str, str]
    positive: frozenset[str]
    negative: frozenset[str]
    guard_labels: frozenset[str] = frozenset()
    # The course whose register pin the prompt carries when the caller gives
    # none, and whose checker tier picks the model. None: the caller says.
    default_code: str | None = None
    # §3.1 names the category `kind` and the rewrite `msa`; `content_verdicts`
    # names them `category` and `expected`. The register question keeps the
    # programme's names because its reviewers' TSV and its tests are written
    # to them; every later question uses the table's.
    category_field: str = "category"
    expected_field: str = "expected"
    expected_description: str = "The correction the card should carry, or null."
    evidence_description: str = "The exact words that carry the verdict."
    # Register only: which dialect, and whether the rewrite kept the meaning.
    variety_enum: tuple[str, ...] | None = None
    asks_meaning_kept: bool = False

    def system_prompt(self, code: str | None = None) -> str:
        return system_prompt_for(self, code)


def system_prompt_for(question: Question, code: str | None = None) -> str:
    """The rules plus the course's register pin, when the course has one.

    The pin is the same string every maker and checker in `backend/services`
    carries since PR #473, so the judge and the makers hold one standard
    rather than two that merely agree today. A course with nothing to pin
    (English) gets the rules alone, byte for byte."""
    from backend.services.quality_rules import register_line

    pin = register_line(code or question.default_code).strip()
    return question.rules + ("\n" + pin if pin else "")


# ---------------------------------------------------------------------------
# The verdict schema — programme §3.1, rendered per question
# ---------------------------------------------------------------------------


def schema_for(question: Question) -> dict[str, Any]:
    """The §3.1 verdict object with this question's enums.

    Property names come from the question (`kind`/`msa` for register,
    `category`/`expected` for the rest), enums from its tuples, and every
    property is required with `additionalProperties: false` — that is what
    lets a local endpoint's guided decoding and Anthropic's `output_config`
    hold the same shape."""
    props: dict[str, Any] = {
        "i": {"type": "integer", "description": "The item's index in this batch."},
        "verdict": {"type": "string", "enum": list(question.verdict_enum)},
    }
    if question.variety_enum:
        props["variety"] = {"type": ["string", "null"],
                            "enum": [*question.variety_enum, None]}
    props["evidence"] = {"type": "array", "items": {"type": "string"},
                         "description": question.evidence_description}
    props[question.category_field] = {"type": ["string", "null"],
                                      "enum": [*question.category_enum, None]}
    props[question.expected_field] = {"type": ["string", "null"],
                                      "description": question.expected_description}
    if question.asks_meaning_kept:
        props["meaning_kept"] = {"type": "boolean"}
    props["confidence"] = {"type": "number", "minimum": 0, "maximum": 1}
    props["note"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


_BATCH_SCHEMAS: dict[str, dict[str, Any]] = {}


def batch_schema_for(question: Question) -> dict[str, Any]:
    """The batch envelope, one object per question.

    Cached so both providers send the very same object and a caller can
    check identity (`register_pass.BATCH_SCHEMA` is this object for the
    register question)."""
    schema = _BATCH_SCHEMAS.get(question.name)
    if schema is None:
        schema = {"type": "object",
                  "properties": {"verdicts": {"type": "array", "items": schema_for(question)}},
                  "required": ["verdicts"], "additionalProperties": False}
        _BATCH_SCHEMAS[question.name] = schema
    return schema


def blank_verdict(question: Question, note: str) -> dict[str, Any]:
    """The `unsure` row for an item the judge did not answer.

    Built from the schema so every property the caller will read exists:
    a missing key and a null read the same in a report, but a missing key
    raises in `fix_rows`. For register this is byte-identical to the row
    `register_pass` used to build by hand."""
    out: dict[str, Any] = {}
    for name, spec in schema_for(question)["properties"].items():
        if name == "i":
            continue
        if name == "verdict":
            out[name] = "unsure"
        elif name == "note":
            out[name] = note
        elif spec.get("type") == "array":
            out[name] = []
        elif spec.get("type") == "boolean":
            out[name] = False
        elif spec.get("type") == "number":
            out[name] = 0.0
        else:
            out[name] = None
    return out


# ---------------------------------------------------------------------------
# The two providers. One schema; the transport is a flag.
# ---------------------------------------------------------------------------


def _empty_usage() -> dict[str, int]:
    return dict.fromkeys(USAGE_KEYS, 0)


def _usage_of(usage: Any) -> dict[str, int]:
    """An Anthropic usage block as the loop's five counters, for one call.

    Same field mapping as `tutor._add_usage`, so the judge's rows in
    `tutor_usage` are priced the way every other kind is. A response that
    reports no usage still counts as a call."""
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "calls": 1,
    }


def _openai_usage_of(usage: Any) -> dict[str, int]:
    """The OpenAI-compatible `usage` object (vLLM, Ollama) as the same five.

    No cache counters exist on that API; they stay zero rather than absent so
    the loop sums one shape."""
    usage = usage if isinstance(usage, dict) else {}
    return {
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or 0),
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
        "calls": 1,
    }


def add_usage(total: dict[str, int], usage: dict[str, int] | None) -> None:
    for key in USAGE_KEYS:
        total[key] = total.get(key, 0) + int((usage or {}).get(key) or 0)


async def _judge_anthropic(question: Question, items: list[dict], model: str | None,
                           code: str | None = None) -> tuple[list[dict], dict[str, int]]:
    """Ask Claude, with the schema enforced by output_config.

    The model is the CHECKER tier — `sentence_checker`, one up from the
    maker — because §6 of the quality rules says never self-certify. The
    reply's `usage` comes back with the verdicts: the judge is the one place
    this programme spends the key on a schedule, and the owner asked for the
    spend to be visible."""
    from anthropic import AsyncAnthropic

    from backend.config import get_settings
    from backend.services.models import resolve_model

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model or resolve_model("sentence_checker", code or question.default_code),
        max_tokens=8192,
        system=system_prompt_for(question, code),
        messages=[{"role": "user", "content": json.dumps(items, ensure_ascii=False)}],
        output_config={"format": {"type": "json_schema", "schema": batch_schema_for(question)}},
    )
    return _parse(_text_of(response)), _usage_of(getattr(response, "usage", None))


async def _judge_openai(question: Question, items: list[dict], base_url: str, model: str,
                        code: str | None = None) -> tuple[list[dict], dict[str, int]]:
    """Ask an OpenAI-compatible endpoint, with vLLM guided JSON.

    vLLM, Ollama and llama.cpp all speak this; `response_format.json_schema`
    is what makes the local judge hold the same shape as the Anthropic one
    instead of returning prose we would have to regex."""
    import httpx

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt_for(question, code)},
            {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": f"{question.name}_verdicts",
                            "schema": batch_schema_for(question), "strict": True},
        },
    }
    url = base_url.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=180) as http:
        response = await http.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
    return (_parse(body["choices"][0]["message"]["content"]),
            _openai_usage_of(body.get("usage")))


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
    "every row is clean" — the worst possible failure for a judge."""
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


def judge_for(question: Question, base_url: str | None, model: str | None,
              code: str | None = None) -> Callable:
    """The judge callable for this run: `await judge(payload)` returns
    `(verdicts, usage)`."""
    if base_url:
        if not model:
            raise SystemExit("--base-url needs --model (the endpoint's model id).")

        async def local(items: list[dict]) -> tuple[list[dict], dict[str, int]]:
            return await _judge_openai(question, items, base_url, model, code)
        return local

    async def anthropic(items: list[dict]) -> tuple[list[dict], dict[str, int]]:
        return await _judge_anthropic(question, items, model, code)
    return anthropic


def judge_name(base_url: str | None, model: str | None, code: str | None = None) -> str:
    """The name a run is journaled under — never the URL, which may carry
    credentials."""
    if base_url:
        host = urlsplit(base_url).hostname or "local"
        return f"local:{model}@{host}"
    if model:
        return model
    from backend.services.models import resolve_model
    return resolve_model("sentence_checker", code)


# ---------------------------------------------------------------------------
# Running a set of items through the judge
# ---------------------------------------------------------------------------


async def run_items(question: Question, items: list[dict], judge: Callable, *,
                    batch_size: int = BATCH_SIZE,
                    concurrency: int = 4) -> tuple[list[dict], dict[str, int]]:
    """Every item judged exactly once, batches in flight up to *concurrency*,
    and the tokens the batches cost, summed.

    A batch that fails is reported as `unsure` for each of its items rather
    than dropped: a missing row and a clean row look identical in a count,
    and this programme has shipped that mistake before (quality rule 14).

    A judge may return `(verdicts, usage)` or a bare verdict list. The bare
    list is counted as no tokens and no call: `register_pass`'s tests and a
    hand-written fake have nothing to report, and refusing them would make
    every caller wrap its fake for a number nobody reads."""
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    sem = asyncio.Semaphore(concurrency)
    props = [k for k in schema_for(question)["properties"] if k != "i"]

    async def one(batch: list[dict]) -> tuple[list[dict], dict[str, int]]:
        payload = [{"i": n, **{k: v for k, v in item.items() if k != "id"}}
                   for n, item in enumerate(batch)]
        async with sem:
            try:
                result = await judge(payload)
            except Exception as exc:                       # noqa: BLE001
                logger.warning("%s: batch failed (%s) — %d items to unsure",
                               question.name, exc.__class__.__name__, len(batch))
                return ([{**item, **blank_verdict(question, f"judge error: {exc}")}
                         for item in batch], _empty_usage())
        if isinstance(result, tuple):
            verdicts, usage = result
        else:
            verdicts, usage = result, _empty_usage()
        by_i = {v.get("i"): v for v in verdicts if isinstance(v, dict)}
        out = []
        for n, item in enumerate(batch):
            v = by_i.get(n)
            if v is None:
                out.append({**item, **blank_verdict(
                    question, "judge returned no verdict for this item")})
            else:
                out.append({**item, **{k: v.get(k) for k in props}})
        return out, usage

    results: list[dict] = []
    totals = _empty_usage()
    for chunk, usage in await asyncio.gather(*(one(b) for b in batches)):
        results.extend(chunk)
        add_usage(totals, usage)
    return results, totals


# ---------------------------------------------------------------------------
# The gold set: reading it, and the three §3.2 gates
# ---------------------------------------------------------------------------


def _read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_gold(question: Question) -> list[dict]:
    if not question.gold_path.exists():
        raise SystemExit(
            f"no gold set for '{question.name}' at {question.gold_path.relative_to(REPO)} — "
            "reviewers build one to the columns in data/eval/README.md before this "
            "question can be graded.")
    return _read_tsv(question.gold_path)


def gold_items(question: Question, rows: Sequence[dict]) -> list[dict]:
    """Gold rows as judge items: `id` plus the question's item fields, read
    from the columns of the same name.

    A vocabulary row's rank is the question, not decoration (see the sense
    and register rules), so when a set has no `rank` column the rank is read
    from the builder's id convention, `<code>-vocab-<rank>`."""
    items = []
    for row in rows:
        item: dict[str, Any] = {"id": row["id"]}
        for name in question.item_fields:
            value = row.get(name) or ""
            if name == "rank":
                value = value.strip()
                if not value and "-vocab-" in row["id"]:
                    value = row["id"].rsplit("-", 1)[-1]
                if not value.isdigit():
                    continue
                item[name] = int(value)
            else:
                item[name] = value
        items.append(item)
    return items


def grade_gold(question: Question, labelled: Sequence[dict], results: Sequence[dict]) -> dict:
    """Agreement per §3.2, per stratum and store, plus the three gates.

    Gate 1: agreement on the binary split — the finding versus the clean
    answer — over the rows a reviewer labelled one or the other, at 95%.
    Gate 2: recall on the labelled positives, all of them: they are few and
    known, and a judge that finds nine of ten is not calibrated.
    Gate 3: a row carrying a guard label (the near-miss class) is never filed
    as the finding. This is the gate a keen judge fails, and the one that
    would send another pass's work into this question's queue."""
    by_id = {r["id"]: r for r in results}
    rows = []
    for item in labelled:
        label = (item.get("label") or "").strip().lower()
        if not label:
            continue
        got = by_id.get(item["id"])
        if got is None:
            continue
        rows.append({
            "id": item["id"], "store": item.get("store", ""),
            "stratum": (item.get("stratum") or "").split(":")[0],
            "expected": question.label_map.get(label, label), "got": got.get("verdict"),
            "label": label, "got_category": got.get(question.category_field),
        })
    if not rows:
        return {"labelled": 0, "note": "no labelled rows — reviewers have not filled the set"}

    positive = question.positive

    def is_finding(verdict: str | None) -> bool:
        return verdict in positive

    binary = [r for r in rows if r["expected"] in positive | question.negative]
    agree = sum(1 for r in binary if is_finding(r["got"]) == is_finding(r["expected"]))
    positives = [r for r in rows if r["expected"] in positive]
    caught = [r for r in positives if is_finding(r["got"])]
    guarded = [r for r in rows if r["label"] in question.guard_labels]
    misfiled = [r for r in guarded if is_finding(r["got"])]

    per_stratum: dict[str, dict] = {}
    per_store: dict[str, dict] = {}
    for r in binary:
        hit = int(is_finding(r["got"]) == is_finding(r["expected"]))
        for table, key in ((per_stratum, r["stratum"]), (per_store, r["store"])):
            bucket = table.setdefault(key, {"n": 0, "agree": 0})
            bucket["n"] += 1
            bucket["agree"] += hit

    return {
        "question": question.name,
        "labelled": len(rows),
        "binary_n": len(binary), "binary_agree": agree,
        "agreement": (agree / len(binary)) if binary else None,
        "positives": len(positives), "caught": len(caught),
        "recall": (len(caught) / len(positives)) if positives else None,
        "guard_n": len(guarded), "guard_misfiled": len(misfiled),
        "per_stratum": per_stratum, "per_store": per_store,
        "misses": [r for r in positives if not is_finding(r["got"])],
        "false_alarms": [r for r in binary
                         if not is_finding(r["expected"]) and is_finding(r["got"])],
        "gate_agreement": bool(binary) and agree / len(binary) >= 0.95,
        "gate_recall": bool(positives) and len(caught) == len(positives),
        "gate_guard": not misfiled,
    }


def print_gold_report(question: Question, report: dict) -> bool:
    """Print the §3.2 report. Returns True when all three gates pass."""
    if not report.get("labelled"):
        print(f"\nGOLD SET NOT LABELLED — nothing to grade '{question.name}' against.")
        print(report.get("note", ""))
        print(f"Reviewers fill the `label` column of {question.gold_path.relative_to(REPO)} "
              "to data/eval/README.md.")
        return False
    finding = "|".join(sorted(question.positive))
    clean = "|".join(sorted(question.negative))
    guard = "|".join(sorted(question.guard_labels)) or "(no guard class)"
    pct = f"{report['agreement']:.1%}" if report["agreement"] is not None else "n/a"
    rec = f"{report['recall']:.1%}" if report["recall"] is not None else "n/a"
    print(f"\nCALIBRATION — {question.name}: {report['labelled']} labelled items")
    print(f"  {finding} vs {clean} agreement : {pct} "
          f"({report['binary_agree']}/{report['binary_n']})   "
          f"gate >= 95%  {'PASS' if report['gate_agreement'] else 'FAIL'}")
    print(f"  recall on labelled {finding}: {rec} "
          f"({report['caught']}/{report['positives']})   "
          f"gate = 100%  {'PASS' if report['gate_recall'] else 'FAIL'}")
    print(f"  {guard} filed as {finding}: {report['guard_misfiled']}"
          f"/{report['guard_n']}   gate = 0  "
          f"{'PASS' if report['gate_guard'] else 'FAIL'}")
    if report["per_stratum"]:
        print("  by stratum:")
        for name, b in sorted(report["per_stratum"].items(), key=lambda t: -t[1]["n"]):
            print(f"     {name:18s} {b['agree']}/{b['n']}")
    for miss in report["misses"][:10]:
        print(f"  MISS  {miss['id']} expected {miss['expected']}, got {miss['got']}")
    for fa in report["false_alarms"][:10]:
        print(f"  FALSE ALARM  {fa['id']} expected {fa['expected']}, got {fa['got']}")
    return all((report["gate_agreement"], report["gate_recall"], report["gate_guard"]))


def summarise(question: Question, results: Sequence[dict]) -> dict:
    counts: dict[str, int] = {}
    categories: dict[str, int] = {}
    for r in results:
        verdict = r.get("verdict") or "?"
        counts[verdict] = counts.get(verdict, 0) + 1
        category = r.get(question.category_field)
        if category:
            categories[category] = categories.get(category, 0) + 1
    confident = sum(1 for r in results
                    if r.get("verdict") in question.positive
                    and (r.get("confidence") or 0) >= 0.7)
    return {"question": question.name, "items": len(results), "verdicts": counts,
            "categories": categories, "confident_findings": confident}


# ---------------------------------------------------------------------------
# The questions
# ---------------------------------------------------------------------------

# Register — programme §1, rendered. Verbatim the rules `register_pass`
# calibrated to 56/56 on the documented set; `register_pass._RULES` is this
# string, so its tests read the same text.
REGISTER_RULES = """\
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

# Sense — `docs/quality/en-sense-ar-gloss-2026-09-18.md` §2, and CHECKS §36
# for the relation-only class. 8.1% of English definitions measured rare or
# wrong, 15–17% in ranks 2,001–6,000, and nothing in the repo looks for it.
SENSE_RULES = """\
You are an English lexicographer judging vocabulary cards for a language-learning \
app. For each item you answer one question: does this English definition give \
the sense of the word that a learner at this frequency rank actually meets?

WHERE THE DEFINITIONS COME FROM. They were taken from a lexical database whose \
sense order is NOT frequency order — senses are listed by lexicographic \
convention, and the maker took the first one it was offered. So a common word \
can carry a definition that is technically a sense of it and is not the sense \
anyone meets: "runner" defined as a smuggler, "cub" as an awkward and \
inexperienced youth, "sadly" as "in an unfortunate way", "tab" as the bill in \
a restaurant, "board" as the committee. Each of those is in the dictionary. \
None is what a learner at rank 5,000 needs. The rank is the question: a word \
this frequent earned its rank with its everyday sense, and the card must teach \
that one.

VERDICTS
  "primary"   — the definition gives the sense most learners meet first and \
most often. The everyday sense of a word that has one; for a technical word \
whose only common sense is technical, the technical sense.
  "secondary" — a real, common sense, but not the one this rank was earned by \
("bank" as the river bank at rank 500). Acceptable on a card: this is not a \
finding. Still put the primary sense in "expected".
  "rare"      — a genuine sense that is rare, technical, dated, regional or \
slang, and cannot have earned this rank ("runner" the smuggler). Category: \
"technical", "dated", "slang" or "regional".
  "wrong"     — not a usable sense at all: a sense of a different word or a \
different spelling ("not_a_sense"); a definition of the wrong part of speech \
for the card's "pos" ("wrong_pos"); or a definition that gives only a \
grammatical relation and no meaning — "first-person singular present of \
necesitar" — which is true and teaches nothing ("relation_only"; the card \
should say "I need", meaning first, relation in parentheses).
  "unsure"    — you cannot tell which sense the rank belongs to.

WHAT IS NOT A FINDING — judge the sense, never the wording:
   - A definition shorter, plainer or differently phrased than yours.
   - A definition that gives the everyday sense in a slightly formal register.
   - Deep-tail vocabulary (past rank ~6,000) is largely technical, and there \
the rare-looking sense genuinely is the word; that is "primary".
   - British and American senses are both everyday senses.
   - A definition consistent with "pos" is judged on that reading even if \
another part of speech is commoner ("duck" tagged verb, defined as lowering \
the head: primary).

EXPECTED. For every verdict except "primary" and "unsure", set "expected" to \
the short everyday definition the card should carry: one line, the kind a \
learner's dictionary gives, matching "pos". For "primary" set it to null.

EVIDENCE. The words of the definition that carry the verdict; empty for \
"primary".

"unsure" IS A LEGAL ANSWER and routes to a human. Use it rather than guessing. \
Set "confidence" honestly: below 0.7 means you want a reviewer.

Answer with one verdict object per item, in the schema given, using the item's \
own "i". Return every item exactly once."""

# Gloss — the same report, §3: 24.6% of Arabic glosses on English cards
# diverge from the sense the English definition names, flat across every
# band, and the maker's charter forbids exactly that.
GLOSS_RULES = """\
You are a bilingual lexicographer judging the gloss on an English vocabulary \
card. Each item carries the English headword, its part of speech, the English \
definition, the gloss, and the locale (language code) the gloss is written in. \
For each item you answer one question: does the gloss render THAT sense — the \
sense the English definition names — with a matching part of speech?

THE CONTRACT THE GLOSS WAS WRITTEN UNDER. The maker was told to give "the \
single word or short phrase a native speaker would use for THAT specific sense \
(use the definition and example to disambiguate). Match the part of speech." \
You are checking that contract and nothing else. Judge the gloss against the \
DEFINITION, never against the headword alone: when the English definition is \
itself a rare sense, a gloss that renders it faithfully is "faithful" — the \
fault is upstream and a different question owns it. In 16 of 358 measured rows \
the English was rare and the gloss carried it faithfully into the learner's \
language; those are not gloss defects.

VERDICTS
  "faithful" — the gloss is a word or short phrase a native speaker would use \
for the definition's sense, in the same part of speech.
  "diverges" — it is not, with a category:
     "sense_mismatch"    — a different sense of the headword, or a different \
word: "board" defined as the committee and glossed as a plank; "mate" (verb) \
glossed "friend". 61% of measured divergences.
     "wrong_pos"         — the right sense in the wrong word class: "whistle" \
(verb) glossed with the object you blow, صَفَّارَة, where the verb is صفَر. 23%.
     "transliteration"   — the English sounds spelled in the locale's script \
instead of a translation: "ufo" as يُو أَف أَو. 10%.
     "register"          — the right sense in a register the card cannot carry: \
a nursery word for the 183rd commonest English word ("father" as بابا where \
أب or والد is the word), a literary or a colloquial form where the locale has \
a standard one. 3%.
     "instance_not_class" — names one instance where the definition names the \
class.
  "absent"   — the gloss is empty, or is not in the locale's language at all \
(English left untranslated, a third language).
  "unsure"   — you cannot tell without more context.

WHAT IS NOT A DIVERGENCE — false alarms here have cost more than misses:
   - A synonym you would not have chosen. The contract asks for A word a \
native speaker would use, not THE word you would use. A word a native speaker \
would use for this sense, in this part of speech, is "faithful"; put your \
preference in the note if you must, and do not file it.
   - A short phrase where a single word exists. The contract allows "single \
word or short phrase". A verb phrase is a verb: يُلقي نظرة for "glance" is \
faithful, and its object نظرة is not a noun gloss.
   - The same part of speech in the locale's own grammar: an English gerund \
glossed by a verbal noun ("learning" → التعلم) matches.
   - Spelling: diacritics, hamza seats, ة vs ه, word-final ى vs ي, transliterated \
loanwords the locale's press uses. The spelling pass owns those.

EXPECTED. For "diverges" and "absent", set "expected" to the gloss a native \
speaker would use for the definition's sense, matching "pos", in the locale. \
For "faithful" set it to null.

EVIDENCE. The words of the gloss — and of the definition, when the mismatch \
is between them — that carry the verdict; empty for "faithful".

"unsure" IS A LEGAL ANSWER and routes to a human. Use it rather than guessing. \
Set "confidence" honestly: below 0.7 means you want a reviewer.

Answer with one verdict object per item, in the schema given, using the item's \
own "i". Return every item exactly once."""

# Scripture — `docs/quality/ar-surfaces-2026-09-17.md` §3: Qurʾān 18:24 and a
# hadith served as beginner example sentences; programme §1.4 names the class
# and no rule looked for it. The class exists in every language.
SCRIPTURE_RULES = """\
You are judging example sentences for a language-learning app. Each item \
carries the sentence, its English translation, and the language code of the \
course. For each item you answer one question: is this everyday example \
sentence a verbatim or near-verbatim scriptural or liturgical text?

WHY THE QUESTION EXISTS. Sentence banks are harvested from corpora and \
generated by models, and both reach for what is memorable. The Arabic bank \
was found serving Qurʾān 18:24 verbatim — عَسَى أَن يَهْدِيَنِ رَبِّي لِأَقْرَبَ \
مِنْ هَذَا رَشَدًا — and a hadith (Waraqa ibn Nawfal's words) twice, as beginner \
example sentences. A learner drilling "maybe" or "guide" should not be \
reciting scripture, and a card that quotes scripture as an everyday sentence \
is an editorial decision nobody made. The same class exists in every course: \
Bible verses in any translation, the Lord's Prayer, the Shema, the Gita, sutra \
lines, creeds, set prayers and hymn lines.

VERDICTS
  "scripture" — the sentence is, or is within a few words of, a passage of a \
scripture or a fixed liturgical text: the Qurʾān, hadith, the Bible, the \
Tanakh, the Vedas or the Gita, the Pali canon, a creed, a set prayer, a hymn. \
The tells: the exact wording; archaic, pausal or fully vocalised forms that \
only the source uses (يَهْدِيَنِ for يهديني); the frame of a well-known verse. \
Category: "quran", "hadith", "bible", "tanakh", "hindu", "buddhist", \
"liturgy" (a creed, a set prayer, a hymn), or "other". Name the source in the \
note (book and chapter:verse, or the collection) when you can.
  "literary"  — not scripture, but a quotation or a fixed text: a proverb, a \
line of poetry, a famous speech, a saying attributed to a named person, an \
anthem. This is NOT a finding for this question — proverbs and poetry may be \
fine on a card, and whether they suit the level is another question's. Name \
the source in the note.
  "plain"     — an ordinary sentence.
  "unsure"    — you suspect a source and cannot name it.

WHAT IS NOT A TELL — a sentence ABOUT religion is not scripture:
   - Religious vocabulary or subject matter: "She prays every morning", "The \
mosque is closed on Monday", a sentence that mentions God, a church, a fast.
   - Everyday formulae with a religious origin: إن شاء الله, "God willing", \
"bless you", السلام عليكم, "goodbye".
   - An elevated or literary register on its own; MSA press register is not \
scripture.
   - A quotation of a secular text: that is "literary".

EXPECTED. Set "expected" to null, or — when one small change makes the \
sentence everyday while keeping the meaning and the headword — to that rewrite.

EVIDENCE. The words that identify the source; empty for "plain".

"unsure" IS A LEGAL ANSWER and routes to a human. Use it rather than guessing. \
Set "confidence" honestly: below 0.7 means you want a reviewer.

Answer with one verdict object per item, in the schema given, using the item's \
own "i". Return every item exactly once."""

# Card shape — CHECKS §37 (the alphabet card that served "Oh sod."), DEBT.md's
# twelve held abbreviations and bare stems. Every sentence rule asks "is this
# sentence good for this word"; none asked whether the card should have one.
CARD_SHAPE_RULES = """\
You are judging vocabulary cards for a language-learning app. Each item \
carries the headword as the card shows it, its part of speech, its English \
definition, and the language code of the course. For each item you answer one \
question: should this card carry an example sentence at all?

WHY THE QUESTION EXISTS. Every rule that reads a sentence asks "is this \
sentence good for this word"; none asked "should this card have a sentence". \
A Russian alphabet card for й was serving "У меня есть несколько билетов в \
15-й ряд" because the builder matched the letter inside an ordinal suffix; н \
was serving н.э. and Г-н, matched inside abbreviations; ё was serving a crude \
interjection to a beginner. Every one of those sentences passes every \
mechanical check. The card was the defect.

VERDICTS
  "needs_sentence" — an ordinary word. A sentence that uses it as a word \
helps the learner, and the card should carry one.
  "no_sentence"    — the entry is real and stays, but a sentence can only \
match it INSIDE other words, so the card should show its definition prompt \
alone. Category:
     "letter"       — an alphabet letter or a letter name. A row whose part of \
speech is "letter" NEVER carries a sentence; that rule is already in the code, \
so return "no_sentence"/"letter" for every such row whatever its definition \
says.
     "bound_stem"   — a stem, affix, clitic or particle that never stands \
alone: a bare Korean verb stem (잡-, 갖-, 걷-), an Arabic clitic (ي, ت), a prefix \
like "un-" or a suffix like "-ness". A bound stem cannot be a whole \
orthographic word, so no sentence can contain it as a word; whatever sentence \
matched did so inside another word.
     "abbreviation" — a written abbreviation or unit symbol: Portuguese "s" for \
segundo, Spanish "x" for "por", Arabic هـ for the Hijri year, "km", "n.º". It is \
a whole token only inside the notation it belongs to (10 s, 5 km), and a \
builder matching a one- or two-letter string will match inside words far more \
often than in that notation. Whether an abbreviation should be a card at all \
is an open owner decision; do not retire it for being one.
  "retire"         — the entry should not be a card at all. Category:
     "proper_name"  — a personal given name or surname that is in the list \
because the corpus is full of it (Tom, Sami, María). "A male given name" gives \
the learner nothing to produce. A place, language, nationality, festival or \
institution that a learner uses as a word (Paris, Ramadan, the UN) is an \
ordinary entry: "needs_sentence".
     "artefact"     — not a word of this language: a bare diacritic, \
punctuation, a fragment left by extraction, a misspelling of a word that has \
its own entry.
  "unsure"         — you cannot tell.

A SINGLE-CHARACTER STRING IS NOT ALWAYS A LETTER — false alarms here have cost \
more than misses. Italian "e" (and), Russian "а" (and, but), Portuguese "a" \
(the), Hebrew ב (in, at), Arabic ب (with, by), Māori "i" and "a" are real words \
that need a sentence; 758 one-character rows in this bank are words. Judge by \
the part of speech and the definition, never by length. Nor is a short word a \
stem: a Korean particle written as a syllable (은, 는, 을) attaches to a word \
and is a word of the language; "un" in English is not.

EXPECTED. Set "expected" to null; nothing is rewritten for this question.

EVIDENCE. The words of the form or the definition that carry the verdict; \
empty for "needs_sentence".

"unsure" IS A LEGAL ANSWER and routes to a human. Use it rather than guessing. \
Set "confidence" honestly: below 0.7 means you want a reviewer.

Answer with one verdict object per item, in the schema given, using the item's \
own "i". Return every item exactly once."""


_COMMON_LABELS = {"unsure": "unsure", "broken": "broken"}

REGISTER = Question(
    name="register",
    rules=REGISTER_RULES,
    verdict_enum=("dialect", "classical", "msa", "unsure"),
    category_enum=("lexeme", "morphology", "orthography_only", "archaic"),
    item_fields=("field", "text", "translation", "rank"),
    # The set `scripts/build_ar_register_gold.py` builds, 614 rows, not the
    # `<name>_gold.tsv` pattern: renaming it would orphan the reviewers' work.
    gold_path=EVAL / "ar_register_gold.tsv",
    label_map={"dialect": "dialect", "classical": "classical", "msa": "msa",
               "orthography_only": "msa", **_COMMON_LABELS},
    positive=frozenset({"dialect"}),
    negative=frozenset({"msa"}),
    guard_labels=frozenset({"orthography_only"}),
    default_code="ar",
    category_field="kind",
    expected_field="msa",
    expected_description="The minimal MSA rewrite, keeping meaning, headword and level. "
                         "Null if none is needed or none is possible.",
    evidence_description="The exact words that carry the verdict. Empty for msa.",
    variety_enum=("egyptian", "levantine", "gulf", "iraqi", "maghrebi", "mixed"),
    asks_meaning_kept=True,
)

SENSE = Question(
    name="sense",
    rules=SENSE_RULES,
    verdict_enum=("primary", "secondary", "rare", "wrong", "unsure"),
    category_enum=("technical", "dated", "slang", "regional",
                   "relation_only", "wrong_pos", "not_a_sense"),
    item_fields=("word", "rank", "pos", "definition"),
    gold_path=EVAL / "sense_gold.tsv",
    label_map={"primary": "primary", "secondary": "secondary", "rare": "rare",
               "wrong": "wrong", **_COMMON_LABELS},
    positive=frozenset({"rare", "wrong"}),
    negative=frozenset({"primary", "secondary"}),
    guard_labels=frozenset({"secondary"}),
    default_code="en",
    expected_description="The short everyday definition the card should carry, matching pos. "
                         "Null for primary.",
    evidence_description="The words of the definition that carry the verdict. "
                         "Empty for primary.",
)

GLOSS = Question(
    name="gloss",
    rules=GLOSS_RULES,
    verdict_enum=("faithful", "diverges", "absent", "unsure"),
    category_enum=("sense_mismatch", "wrong_pos", "transliteration", "register",
                   "instance_not_class"),
    item_fields=("word", "pos", "definition", "gloss", "locale"),
    gold_path=EVAL / "gloss_gold.tsv",
    # `synonym` is the reviewer's near miss: "faithful, and not the word I
    # would have used". A judge preferring its own word is this question's
    # false-alarm mode, so the class is labelled and gated.
    label_map={"faithful": "faithful", "diverges": "diverges", "absent": "absent",
               "synonym": "faithful", **_COMMON_LABELS},
    positive=frozenset({"diverges"}),
    negative=frozenset({"faithful"}),
    guard_labels=frozenset({"synonym"}),
    expected_description="The gloss a native speaker would use for the definition's sense, "
                         "matching pos, in the locale. Null for faithful.",
    evidence_description="The words of the gloss (and the definition) that carry the "
                         "verdict. Empty for faithful.",
)

SCRIPTURE = Question(
    name="scripture",
    rules=SCRIPTURE_RULES,
    verdict_enum=("scripture", "literary", "plain", "unsure"),
    category_enum=("quran", "hadith", "bible", "tanakh", "hindu", "buddhist",
                   "liturgy", "other"),
    item_fields=("sentence", "translation", "language"),
    gold_path=EVAL / "scripture_gold.tsv",
    label_map={"scripture": "scripture", "literary": "literary", "plain": "plain",
               **_COMMON_LABELS},
    positive=frozenset({"scripture"}),
    negative=frozenset({"plain", "literary"}),
    guard_labels=frozenset({"literary"}),
    expected_description="Null, or the everyday rewrite that keeps the meaning and the "
                         "headword when one small change makes the sentence plain.",
    evidence_description="The words that identify the source. Empty for plain.",
)

CARD_SHAPE = Question(
    name="card_shape",
    rules=CARD_SHAPE_RULES,
    verdict_enum=("needs_sentence", "no_sentence", "retire", "unsure"),
    category_enum=("letter", "bound_stem", "abbreviation", "proper_name", "artefact"),
    item_fields=("word", "pos", "definition", "language"),
    gold_path=EVAL / "card_shape_gold.tsv",
    # `one_letter_word` is the reviewer's near miss: Italian e, Russian а —
    # a real word one character long. CHECKS §37: 758 such rows are words.
    label_map={"needs_sentence": "needs_sentence", "no_sentence": "no_sentence",
               "retire": "retire", "one_letter_word": "needs_sentence", **_COMMON_LABELS},
    positive=frozenset({"no_sentence", "retire"}),
    negative=frozenset({"needs_sentence"}),
    guard_labels=frozenset({"one_letter_word"}),
    expected_description="Null; nothing is rewritten for this question.",
    evidence_description="The words of the form or the definition that carry the verdict. "
                         "Empty for needs_sentence.",
)

QUESTIONS: dict[str, Question] = {q.name: q for q in (REGISTER, SENSE, GLOSS, SCRIPTURE,
                                                      CARD_SHAPE)}


# ---------------------------------------------------------------------------
# CLI — gold only, until the loop brings the stores
# ---------------------------------------------------------------------------


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _shown(path: Path) -> str:
    """A path as the report prints it: relative to the repo when it is
    inside it, absolute when a caller pointed OUT_DIR elsewhere."""
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def write_jsonl(question: Question, results: Sequence[dict], stamp: str, meta: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"judge-{question.name}-{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def spend_notice(base_url: str | None) -> str:
    """The first line printed, always. The owner's standing rule is that this
    agent never spends the key; a person running this does, and should read
    that before the run starts rather than in the invoice."""
    if base_url:
        host = urlsplit(base_url).hostname or "local"
        return f"LOCAL JUDGE — {host}. The Anthropic API key is not used for this run."
    return ("THIS RUN SPENDS THE ANTHROPIC API KEY (checker tier, one call per batch). "
            "Pass --base-url to use a local OpenAI-compatible endpoint instead.")


async def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--question", required=True, choices=sorted(QUESTIONS))
    ap.add_argument("--gold", action="store_true",
                    help="run on the question's gold set and report the three gates")
    ap.add_argument("--base-url",
                    help="OpenAI-compatible endpoint for a local judge; omit for Anthropic")
    ap.add_argument("--model", help="model id (required with --base-url)")
    ap.add_argument("--code", help="course code for the register pin and checker tier "
                                   "(default: the question's own)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args(argv)
    print(spend_notice(args.base_url))
    if not args.gold:
        ap.error("only --gold runs here; the store passes arrive with the judge loop "
                 "(register's are in register_pass).")
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    question = QUESTIONS[args.question]
    code = args.code or question.default_code
    judge = judge_for(question, args.base_url, args.model, code)
    name = judge_name(args.base_url, args.model, code)
    stamp = _stamp()
    logger.info("question: %s   judge: %s", question.name, name)

    labelled = load_gold(question)
    items = gold_items(question, labelled)
    if args.limit:
        items = items[:args.limit]
    results, usage = await run_items(question, items, judge, batch_size=args.batch_size,
                                     concurrency=args.concurrency)
    report = grade_gold(question, labelled, results)
    path = write_jsonl(question, results, stamp,
                       {"mode": "gold", "judge": name, "items": len(items),
                        "usage": usage, "report": report})
    print(json.dumps(summarise(question, results), ensure_ascii=False, indent=1))
    passed = print_gold_report(question, report)
    print(f"\ntokens: {usage['input_tokens']} in, {usage['output_tokens']} out, "
          f"{usage['cache_read_tokens']} cached, over {usage['calls']} calls")
    print(f"verdicts -> {_shown(path)}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
