"""Admin-driven bulk content generation (WP42).

The deployed app holds the ANTHROPIC_API_KEY, so an admin can fill a language's
content gaps from the panel: draft + verify example sentences for words that
have none, and drills for grammar points that have none. Two guarantees make it
safe to hand a paid key to a button:

  * IDEMPOTENT — a run only ever touches items still UNDER target (words with
    too few examples, points with too few drills), and every insert dedupes on
    the sentence text. Re-running after a completed pass finds nothing and
    spends nothing.
  * PREVIEWABLE — dry_run resolves the exact work-list and a cost ESTIMATE
    without calling the model, so the admin sees the bill before paying it.

Model choice per (task, language) comes from the WP39 registry; the estimate is
priced at list rates. Everything the model produces is tagged source='ai' with
the model in origin_detail and is left for human review — never self-certified.
"""

from __future__ import annotations

import asyncpg

from backend.repositories.contributor import (
    add_drill,
    add_example_sentence,
    backfill_example_translation,
    flag_example_sentence,
    points_with_thin_cells,
    vocab_needing_examples,
    vocab_with_examples,
)
from backend.services.generate import (
    audit_examples,
    generate_drills,
    generate_examples,
)
from backend.services.models import resolve_model
from backend.services.tutor_costs import estimate_cost_usd

# Rough per-generated-item token accounting for the dry-run estimate. A maker
# call sends the point/word context + instructions and gets back N short
# sentences; the checker is offline (no model). These are deliberately generous
# so the preview never UNDER-states the bill.
_EST_INPUT_TOKENS_PER_ITEM = 700
_EST_OUTPUT_TOKENS_PER_SENTENCE = 60

# A single run is bounded so one click can't run away with the key; the admin
# re-runs to continue (idempotent, so it picks up where it left off).
MAX_ITEMS_PER_RUN = 100
MAX_PER_ITEM = 10


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


async def plan_run(
    conn: asyncpg.Connection,
    *,
    kind: str,
    language_id: str,
    language_code: str,
    target_per_item: int,
    max_items: int,
) -> dict:
    """Resolve the idempotent work-list and a cost estimate WITHOUT generating.
    *kind* is 'vocab' or 'grammar'."""
    target_per_item = _clamp(target_per_item, 1, MAX_PER_ITEM)
    max_items = _clamp(max_items, 1, MAX_ITEMS_PER_RUN)
    if kind == "vocab":
        items = await vocab_needing_examples(
            conn, language_id, target_per_item, max_items
        )
        model = resolve_model("sentence_maker", language_code)
        # each item needs (target - it_has) more; that's what the maker drafts
        to_make = sum(max(0, target_per_item - i["example_count"]) for i in items)
    elif kind == "grammar":
        # Cell-aware: target_per_item is the target drills PER paradigm cell, so
        # thickening a conjugation form stays balanced across persons.
        items = await points_with_thin_cells(
            conn, language_id, target_per_item, max_items
        )
        model = resolve_model("grammar_maker", language_code)
        to_make = sum(
            max(0, target_per_item - n)
            for it in items for n in it["cell_counts"].values()
        )
    else:
        raise ValueError(f"unknown generation kind: {kind!r}")

    est_cost = estimate_cost_usd(
        model,
        input_tokens=_EST_INPUT_TOKENS_PER_ITEM * len(items),
        output_tokens=_EST_OUTPUT_TOKENS_PER_SENTENCE * to_make,
    )
    return {
        "kind": kind,
        "model": model,
        "target_per_item": target_per_item,
        "items_to_process": len(items),
        "sentences_to_attempt": to_make,
        "est_cost_usd": est_cost,
        "_items": items,  # internal — stripped before returning to the client
    }


async def run_generation(
    conn: asyncpg.Connection,
    *,
    kind: str,
    language_id: str,
    language_code: str,
    language_name: str,
    target_per_item: int,
    max_items: int,
) -> dict:
    """Execute the planned run: maker→checker→persist for each gap item. Returns
    an analysis (accepted, rejected-by-reason, persisted, model, cost estimate)."""
    plan = await plan_run(
        conn,
        kind=kind,
        language_id=language_id,
        language_code=language_code,
        target_per_item=target_per_item,
        max_items=max_items,
    )
    items = plan.pop("_items")
    model = plan["model"]
    target = plan["target_per_item"]

    accepted = persisted = 0
    items_touched = 0

    for item in items:
        if kind == "vocab":
            need = max(0, target - item["example_count"])
            if need == 0:
                continue
            passed = await generate_examples(
                item, need, language_name, language_code, maker_model=model
            )
            accepted += len(passed)
            for cand in passed:
                row_id = await add_example_sentence(
                    conn, item["vocabulary_id"], language_id,
                    cand["sentence"], cand.get("translation"),
                    source="ai", origin_detail=model,
                )
                if row_id:
                    persisted += 1
            items_touched += 1
        else:
            # Grammar: fill each thin cell up to target, balanced.
            point = {
                "title": item["title"],
                "explanation": item["explanation"],
                "examples": [],
            }
            touched = False
            for cell, have in item["cell_counts"].items():
                need = max(0, target - have)
                if need == 0:
                    continue
                touched = True
                passed = await generate_drills(
                    point, need, language_name, language_code,
                    maker_model=model, cell=cell,
                )
                accepted += len(passed)
                for cand in passed:
                    row_id = await add_drill(
                        conn, item["point_id"], cand["sentence"], cand["answer"],
                        cand.get("translation"), cand.get("hint"),
                        source="ai", origin_detail=model, decertify=False,
                        cell=cell,
                    )
                    if row_id:
                        persisted += 1
            if touched:
                items_touched += 1

    # accepted = candidates that cleared the checker; persisted = those actually
    # written (accepted minus any that collided with an existing sentence, the
    # idempotency dedupe). attempted comes from the plan for the accept rate.
    return {
        "kind": kind,
        "language_code": language_code,
        "language_name": language_name,
        "model": model,
        "target_per_item": target,
        "items_processed": items_touched,
        "sentences_attempted": plan["sentences_to_attempt"],
        "sentences_accepted": accepted,
        "sentences_persisted": persisted,
        "duplicates_skipped": accepted - persisted,
        "est_cost_usd": plan["est_cost_usd"],
    }


async def plan_recheck(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    max_items: int,
) -> dict:
    """Resolve the recheck work-list + a cost estimate WITHOUT calling the model.
    The audit is one judge call per word (all its sentences at once)."""
    max_items = _clamp(max_items, 1, MAX_ITEMS_PER_RUN)
    items = await vocab_with_examples(conn, language_id, max_items)
    model = resolve_model("sentence_checker", language_code)
    sentences = sum(len(w["examples"]) for w in items)
    est_cost = estimate_cost_usd(
        model,
        input_tokens=_EST_INPUT_TOKENS_PER_ITEM * len(items),
        output_tokens=_EST_OUTPUT_TOKENS_PER_SENTENCE * sentences,
    )
    return {
        "kind": "recheck",
        "model": model,
        "words_to_audit": len(items),
        "sentences_to_audit": sentences,
        "est_cost_usd": est_cost,
        "_items": items,
    }


async def recheck_examples(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    language_name: str,
    target_per_item: int,
    max_items: int,
) -> dict:
    """Audit EXISTING example sentences and heal each word back to target.

    For every word with examples: run the LLM judge over its current sentences;
    FLAG the ones it rejects (left for a human), BACKFILL a missing translation
    on the ones it keeps, then draft fresh alternatives (maker→checker) so the
    word still has *target* good sentences. New alternatives land reviewed=false.
    Idempotent: flagged rows are excluded from the audited set on a re-run, and
    alternative inserts dedupe on the sentence text.
    """
    target = _clamp(target_per_item, 1, MAX_PER_ITEM)
    plan = await plan_recheck(
        conn, language_id=language_id, language_code=language_code,
        max_items=max_items,
    )
    items = plan.pop("_items")
    audit_model = plan["model"]
    maker_model = resolve_model("sentence_maker", language_code)

    words_audited = flagged = backfilled = alternatives = 0
    for word in items:
        sentences = word["examples"]
        if not sentences:
            continue
        words_audited += 1
        verdicts = await audit_examples(
            word, sentences, language_name, language_code, model=audit_model
        )
        good = 0
        for sent, verdict in zip(sentences, verdicts):
            if not verdict["ok"]:
                if await flag_example_sentence(conn, sent["id"], verdict["reason"]):
                    flagged += 1
                continue
            good += 1
            if verdict["translation"] and not (sent["translation"] or "").strip():
                if await backfill_example_translation(
                    conn, sent["id"], verdict["translation"]
                ):
                    backfilled += 1

        # Heal back to target with fresh, verified alternatives.
        need = max(0, target - good)
        if need:
            passed = await generate_examples(
                word, need, language_name, language_code, maker_model=maker_model
            )
            for cand in passed:
                row_id = await add_example_sentence(
                    conn, word["vocabulary_id"], language_id,
                    cand["sentence"], cand.get("translation"),
                    source="ai", origin_detail=maker_model,
                )
                if row_id:
                    alternatives += 1

    return {
        "kind": "recheck",
        "language_code": language_code,
        "language_name": language_name,
        "model": audit_model,
        "target_per_item": target,
        "words_audited": words_audited,
        "sentences_audited": plan["sentences_to_audit"],
        "sentences_flagged": flagged,
        "translations_backfilled": backfilled,
        "alternatives_generated": alternatives,
        "est_cost_usd": plan["est_cost_usd"],
    }
