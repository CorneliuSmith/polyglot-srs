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

from backend.repositories.cards import (
    _chart_form_index,
    _form_key,
    _reset_chart_form_index,
    _word_tokens,
)
from backend.repositories.contributor import (
    add_drill,
    add_example_sentence,
    backfill_example_translation,
    drill_answers_for_charts,
    flag_drill,
    flag_example_sentence,
    get_language_tutor_model,
    points_for_overlap_audit,
    points_with_drills,
    points_with_thin_cells,
    record_overlap,
    suggest_example_translation,
    upsert_vocabulary_charts,
    vocab_needing_examples,
    vocab_with_examples,
)
from backend.services.generate import (
    audit_drills,
    audit_examples,
    audit_overlap,
    generate_chart,
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


async def _model_override(conn: asyncpg.Connection, language_id: str) -> str | None:
    """The admin's per-language model override (languages.tutor_model), for
    every resolve_model() call in this module — previously only tutor chat
    and the Reader threaded this through, so an admin's override silently
    had no effect on generation/recheck/overlap runs. Safe to pass into
    checker-task calls too: resolve_model() only honors an override for the
    'tutor_model' field, never a checker's 'tutor_model_low_resource'."""
    return await get_language_tutor_model(conn, language_id)


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
    override = await _model_override(conn, language_id)
    if kind == "vocab":
        items = await vocab_needing_examples(
            conn, language_id, target_per_item, max_items
        )
        model = resolve_model("sentence_maker", language_code, override=override)
        # each item needs (target - it_has) more; that's what the maker drafts
        to_make = sum(max(0, target_per_item - i["example_count"]) for i in items)
    elif kind == "grammar":
        # Cell-aware: target_per_item is the target drills PER paradigm cell, so
        # thickening a conjugation form stays balanced across persons.
        items = await points_with_thin_cells(
            conn, language_id, target_per_item, max_items
        )
        model = resolve_model("grammar_maker", language_code, override=override)
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
                        cell=cell, lemma=cand.get("lemma"),
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
    model = resolve_model(
        "sentence_checker", language_code,
        override=await _model_override(conn, language_id),
    )
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
    maker_model = resolve_model(
        "sentence_maker", language_code,
        override=await _model_override(conn, language_id),
    )

    words_audited = flagged = backfilled = suggested = alternatives = 0
    for word in items:
        sentences = word["examples"]
        if not sentences:
            continue
        words_audited += 1
        verdicts = await audit_examples(
            word, sentences, language_name, language_code,
            model=audit_model, level=word.get("level"),
        )
        good = 0
        for sent, verdict in zip(sentences, verdicts):
            if not verdict["ok"]:
                if await flag_example_sentence(conn, sent["id"], verdict["reason"]):
                    flagged += 1
                continue
            good += 1
            existing = (sent["translation"] or "").strip()
            if not existing:
                # Missing translation → fill in place (nothing to overwrite).
                if verdict["translation"] and await backfill_example_translation(
                    conn, sent["id"], verdict["translation"]
                ):
                    backfilled += 1
            elif (
                not verdict["translation_ok"]
                and verdict["translation"]
                and verdict["translation"] != existing
            ):
                # Present but weak → propose a replacement for reviewer sign-off,
                # never overwrite a possibly human-authored translation.
                if await suggest_example_translation(
                    conn, sent["id"], verdict["translation"],
                    verdict["reason"] or "translation could be clearer or more useful",
                ):
                    suggested += 1

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
        "translations_suggested": suggested,
        "alternatives_generated": alternatives,
        "est_cost_usd": plan["est_cost_usd"],
    }


async def plan_recheck_drills(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    max_items: int,
) -> dict:
    """Resolve the drill-recheck work-list + cost estimate WITHOUT calling the
    model. One judge call per point (all its drills at once)."""
    max_items = _clamp(max_items, 1, MAX_ITEMS_PER_RUN)
    items = await points_with_drills(conn, language_id, max_items)
    model = resolve_model(
        "sentence_checker", language_code,
        override=await _model_override(conn, language_id),
    )
    drills = sum(len(p["drills"]) for p in items)
    est_cost = estimate_cost_usd(
        model,
        input_tokens=_EST_INPUT_TOKENS_PER_ITEM * len(items),
        output_tokens=_EST_OUTPUT_TOKENS_PER_SENTENCE * drills,
    )
    return {
        "kind": "recheck_drills",
        "model": model,
        "points_to_audit": len(items),
        "drills_to_audit": drills,
        "est_cost_usd": est_cost,
        "_items": items,
    }


async def recheck_drills(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    language_name: str,
    target_per_item: int,
    max_items: int,
) -> dict:
    """Audit EXISTING drills and heal each point back to target — the drill twin
    of recheck_examples.

    For every point with drills: run the LLM judge over its current drills, FLAG
    the ones it rejects (left for a human), then draft fresh alternatives
    (maker→checker) so the point still has *target* good drills. New alternatives
    land reviewed=false. Idempotent: flagged drills are excluded from the audited
    set on a re-run, and inserts dedupe on the sentence text.
    """
    target = _clamp(target_per_item, 1, MAX_PER_ITEM)
    plan = await plan_recheck_drills(
        conn, language_id=language_id, language_code=language_code,
        max_items=max_items,
    )
    items = plan.pop("_items")
    audit_model = plan["model"]
    maker_model = resolve_model(
        "grammar_maker", language_code,
        override=await _model_override(conn, language_id),
    )

    points_audited = flagged = alternatives = 0
    for point in items:
        drills = point["drills"]
        if not drills:
            continue
        points_audited += 1
        verdicts = await audit_drills(
            point, drills, language_name, language_code,
            model=audit_model, level=point.get("level"),
        )
        good = 0
        for drill, verdict in zip(drills, verdicts):
            if not verdict["ok"]:
                if await flag_drill(conn, drill["id"], verdict["reason"]):
                    flagged += 1
                continue
            good += 1

        # Heal back to target with fresh, verified alternatives.
        need = max(0, target - good)
        if need:
            passed = await generate_drills(
                point, need, language_name, language_code, maker_model=maker_model
            )
            for cand in passed:
                row_id = await add_drill(
                    conn, point["point_id"], cand["sentence"], cand["answer"],
                    cand.get("translation"), cand.get("hint"),
                    source="ai", origin_detail=maker_model, decertify=False,
                    lemma=cand.get("lemma"),
                )
                if row_id:
                    alternatives += 1

    return {
        "kind": "recheck_drills",
        "language_code": language_code,
        "language_name": language_name,
        "model": audit_model,
        "target_per_item": target,
        "points_audited": points_audited,
        "drills_audited": plan["drills_to_audit"],
        "drills_flagged": flagged,
        "alternatives_generated": alternatives,
        "est_cost_usd": plan["est_cost_usd"],
    }


# ---------------------------------------------------------------------------
# Morphology CHART backfill (-k forms, WP45 track 3). The Gym's chart lookup
# resolves a drill's answer through the reverse form index built from the
# charts themselves; every answer that DOESN'T resolve is a hole — either the
# word is missing from vocabulary entirely, or its row has no chart tables.
# This run has the LLM produce the paradigm chart for each such word, verified
# by containment: the drill's answer is a known-true form, so a chart that
# doesn't contain it is rejected (services/generate.check_chart). Verified
# charts are upserted onto the vocabulary row (created if absent); existing
# charts are never overwritten, which is also what makes re-runs idempotent.
# ---------------------------------------------------------------------------

# A chart call carries the drill context; the response is a full paradigm
# table, much bigger than a sentence. Generous, so the preview never
# under-states the bill.
_EST_INPUT_TOKENS_PER_CHART = 500
_EST_OUTPUT_TOKENS_PER_CHART = 700


def _forms_dedupe_key(item: dict) -> str:
    """One chart covers all of a word's forms — collapse work items that name
    the same word (stored lemma when the drill has one, else the answer's
    folded key)."""
    lemma = (item.get("lemma") or "").strip().lower()
    if lemma:
        return f"l:{lemma}"
    tokens = _word_tokens(item.get("answer") or "")
    return f"a:{_form_key(max(tokens, key=len))}" if tokens else "a:"


async def plan_forms(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    max_items: int,
) -> dict:
    """Resolve the chart work-list + cost estimate WITHOUT calling the model:
    distinct drill answers whose forms the Gym's chart lookup cannot resolve."""
    max_items = _clamp(max_items, 1, MAX_ITEMS_PER_RUN)
    answers = await drill_answers_for_charts(conn, language_id)
    # The index may be cached from before this run's own writes — rebuild it so
    # the work-list reflects the database as it is now.
    _reset_chart_form_index()
    index = await _chart_form_index(conn, language_code)

    items: list[dict] = []
    seen: set[str] = set()
    for a in answers:
        tokens = [t for t in _word_tokens(a["answer"]) if len(t) > 2]
        if not tokens:
            continue
        if any(_form_key(t) in index for t in tokens):
            continue  # the Gym already finds a chart for this answer
        lemma_key = _form_key((a.get("lemma") or "").strip())
        if lemma_key and lemma_key in index:
            # The word already carries charts (they just lack this form). The
            # upsert never overwrites existing charts, so generating here
            # could never store anything — attempting it is pure waste, and
            # excluding it is what makes repeated runs converge to zero.
            continue
        key = _forms_dedupe_key(a)
        if key in seen:
            continue
        seen.add(key)
        items.append(a)
        if len(items) >= max_items:
            break

    model = resolve_model(
        "grammar_maker", language_code,
        override=await _model_override(conn, language_id),
    )
    est_cost = estimate_cost_usd(
        model,
        input_tokens=_EST_INPUT_TOKENS_PER_CHART * len(items),
        output_tokens=_EST_OUTPUT_TOKENS_PER_CHART * len(items),
    )
    return {
        "kind": "forms",
        "model": model,
        "answers_scanned": len(answers),
        "charts_to_attempt": len(items),
        "est_cost_usd": est_cost,
        "_items": items,
    }


async def run_forms(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    language_name: str,
    max_items: int,
) -> dict:
    """Generate + verify + persist a paradigm chart per unresolved drill
    answer. Safe to re-run: the work-list only ever contains answers still
    without a chart, and the upsert never overwrites existing chart tables."""
    plan = await plan_forms(
        conn, language_id=language_id, language_code=language_code,
        max_items=max_items,
    )
    items = plan.pop("_items")
    model = plan["model"]

    rejected = created = updated = skipped = 0
    for item in items:
        cand = await generate_chart(
            item, language_name, language_code, maker_model=model
        )
        if cand is None:
            rejected += 1
            continue
        _vid, status = await upsert_vocabulary_charts(
            conn, language_id, cand["lemma"], cand["part_of_speech"],
            cand["charts"], cand["usage_note"], origin_detail=model,
        )
        if status == "created":
            created += 1
        elif status == "updated":
            updated += 1
        else:
            # The word already carries charts that simply lack this form (the
            # kaikki tables stay authoritative), or an identical insert raced.
            skipped += 1
    # New charts must be visible to the Gym's cached reverse index immediately.
    _reset_chart_form_index()

    return {
        "kind": "forms",
        "language_code": language_code,
        "language_name": language_name,
        "model": model,
        "answers_scanned": plan["answers_scanned"],
        "charts_attempted": len(items),
        "charts_rejected": rejected,
        "words_created": created,
        "words_updated": updated,
        "already_charted_skipped": skipped,
        "est_cost_usd": plan["est_cost_usd"],
    }


# ---------------------------------------------------------------------------
# Grammar-point OVERLAP audit (owner, 2026-07-26) — runs alongside the
# recheck. The judge sees the syllabus per level band and reports pairs that
# teach substantially the same thing; each pair becomes an open review row
# (grammar_point_overlaps), never an automatic merge.
# ---------------------------------------------------------------------------

# Overlap hides within and next to a level, not across the whole ladder —
# judging A1 against C2 wastes tokens on pairs that can't overlap. Points are
# batched per level TOGETHER WITH the next level up, so boundary drift
# (an A2 point re-teaching an A1 one) is still caught.
_OVERLAP_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _overlap_groups(points: list[dict]) -> list[list[dict]]:
    by_level: dict[str, list[dict]] = {}
    for p in points:
        by_level.setdefault(p.get("level") or "?", []).append(p)
    groups = []
    ladder = _OVERLAP_LEVELS + ["?"]
    for i, level in enumerate(ladder):
        cohort = list(by_level.get(level, []))
        if not cohort:
            continue
        if i + 1 < len(ladder):
            cohort += by_level.get(ladder[i + 1], [])
        if len(cohort) >= 2:
            groups.append(cohort)
    return groups


async def plan_overlap(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
) -> dict:
    """Resolve the overlap work-list + cost estimate WITHOUT calling the
    model: one judge call per level band."""
    points = await points_for_overlap_audit(conn, language_id)
    groups = _overlap_groups(points)
    model = resolve_model(
        "grammar_checker", language_code,
        override=await _model_override(conn, language_id),
    )
    est_cost = estimate_cost_usd(
        model,
        # Each group call carries its titles (~30 tokens each) + instructions;
        # output is a short pair list.
        input_tokens=sum(300 + 30 * len(g) for g in groups),
        output_tokens=120 * len(groups),
    )
    return {
        "kind": "overlap",
        "model": model,
        "points_to_audit": len(points),
        "judge_calls": len(groups),
        "est_cost_usd": est_cost,
        "_groups": groups,
    }


async def run_overlap_audit(
    conn: asyncpg.Connection,
    *,
    language_id: str,
    language_code: str,
    language_name: str,
) -> dict:
    """Judge every level band and record the overlapping pairs for review.

    Idempotent: record_overlap dedupes against the open-pair unique index, so
    a re-run only adds pairs that are new (or were previously resolved and
    have drifted back). Nothing is merged or deleted here — reviewers decide.
    """
    plan = await plan_overlap(
        conn, language_id=language_id, language_code=language_code
    )
    groups = plan.pop("_groups")
    model = plan["model"]

    pairs_reported = flagged = 0
    for group in groups:
        pairs = await audit_overlap(
            group, language_name, language_code, model=model
        )
        pairs_reported += len(pairs)
        for pair in pairs:
            created = await record_overlap(
                conn, language_id,
                group[pair["a"]]["id"], group[pair["b"]]["id"],
                pair["verdict"], pair["reason"], detected_by=model,
            )
            if created:
                flagged += 1

    return {
        "kind": "overlap",
        "language_code": language_code,
        "language_name": language_name,
        "model": model,
        "points_audited": plan["points_to_audit"],
        "judge_calls": plan["judge_calls"],
        "pairs_reported": pairs_reported,
        "pairs_flagged": flagged,
        "est_cost_usd": plan["est_cost_usd"],
    }
