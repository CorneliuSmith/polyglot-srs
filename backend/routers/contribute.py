"""Contributor router — language specialists author grammar explanations.

Authorization is enforced here (app layer): role reads run on the user's RLS
connection; content writes run on a privileged connection only after the
caller's role is verified for the target language.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.change_requests import (
    cast_vote,
    create_request,
    get_request_language,
    list_requests,
    resolve_request,
)
from backend.repositories.contributor import (
    accept_example_translation,
    add_drill,
    add_recommendation,
    add_review_note,
    admin_cohorts,
    admin_engagement,
    admin_engagement_user_detail,
    admin_engagement_users,
    admin_timeseries,
    approve_explanation,
    approve_suggestion,
    can_contribute,
    can_review,
    can_trial_review,
    confirm_vocab_level,
    create_auth_user,
    create_grammar_point,
    delete_account,
    delete_drill,
    delete_example_sentence,
    dismiss_example_translation,
    edit_example_sentence,
    entity_language,
    find_user_by_email,
    generation_coverage,
    get_feedback_language,
    get_language_policy,
    get_language_tutor_model,
    get_note_language,
    get_point_for_check,
    get_point_language,
    get_point_language_and_code,
    get_roles,
    get_suggestion,
    grant_role,
    is_admin,
    list_accounts,
    list_ai_leveled_vocab,
    list_all_roles,
    list_drills,
    list_feedback,
    list_grammar_points,
    list_pending_drills,
    list_pending_examples,
    list_review_notes,
    list_suggestions,
    list_translation_reviews,
    list_vocab_examples,
    list_vocab_items,
    recommendations_for_targets,
    reject_suggestion,
    resolve_feedback,
    resolve_review_note,
    resolve_translation_review,
    review_drill,
    review_example,
    revoke_role,
    save_ai_check,
    save_explanation,
    set_account_plan,
    set_language_policy,
    set_language_tutor_model,
    submit_suggestion,
    trial_reviewer_activity,
    update_drill,
)
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.tutor import aggregate_tutor_usage, set_tutor_access
from backend.services.drills import validate_drill
from backend.services.generate import generation_available
from backend.services.generation_admin import (
    MAX_ITEMS_PER_RUN,
    MAX_PER_ITEM,
    plan_run,
    run_generation,
)
from backend.services.models import LOW_RESOURCE_LANGUAGES, resolve_model
from backend.services.rate_limit import ai_review_limiter
from backend.services.semantic_check import ai_available, semantic_check_point
from backend.services.tutor_costs import estimate_cost_usd

logger = logging.getLogger(__name__)
router = APIRouter()


class ReferenceLink(BaseModel):
    title: str
    url: str


class ExplanationUpdate(BaseModel):
    explanation: str = Field(min_length=1)
    culture_note: str = ""
    references: list[ReferenceLink] = Field(default_factory=list)


class NewGrammarPoint(BaseModel):
    language_id: str
    title: str = Field(min_length=1, max_length=200)
    level: str | None = None
    explanation: str = ""
    culture_note: str = ""
    references: list[ReferenceLink] = Field(default_factory=list)


class NewDrill(BaseModel):
    sentence: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=200)
    translation: str = ""
    hint: str = ""


class EditDrill(BaseModel):
    sentence: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=200)
    translation: str = ""
    hint: str = ""
    # Friction: no silent edits. Every change to a live card carries a
    # rationale that lands in the point's review notes for a second
    # reviewer to verify.
    change_note: str = Field(min_length=10, max_length=2000)


class NewReviewNote(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


class RoleGrant(BaseModel):
    # identify the account either way; email is what an admin actually knows
    user_id: str | None = None
    email: str | None = None
    language_id: str | None = None
    role: str

VALID_ROLES = ("contributor", "trial_reviewer", "reviewer", "admin")


@router.get("/roles")
async def my_roles(user: dict = Depends(get_current_user)):
    """Return the caller's contributor roles (drives the contributor UI)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    return {"roles": roles, "is_admin": is_admin(roles)}


@router.get("/grammar")
async def grammar_for_language(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """List a language's grammar points for editing (role-gated)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        if not can_contribute(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        points = await list_grammar_points(conn, language_id)
        policy = await get_language_policy(conn, language_id)
        tutor_model = await get_language_tutor_model(conn, language_id)
    return {
        "points": points,
        "is_admin": is_admin(roles),
        "can_review": can_review(roles, language_id),
        # Trial reviewers can open the queue and recommend, but not publish.
        "can_trial_review": can_trial_review(roles, language_id),
        # Contributors have all reviewer permissions on the change-request
        # board (raise + vote); only admins accept/reject.
        "can_contribute": can_contribute(roles, language_id),
        "review_policy": policy,
        "tutor_model": tutor_model,
    }


@router.get("/vocab")
async def vocab_for_language(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """List a language's vocabulary for review (role-gated).

    Read-only: the change-request board (target_type='vocabulary') is how
    reviewers propose and vote on fixes — this just surfaces what's there so
    they can spot thin or missing entries while browsing.
    """
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        if not can_contribute(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        items = await list_vocab_items(conn, language_id)
    return {
        "items": items,
        "is_admin": is_admin(roles),
        "can_review": can_review(roles, language_id),
        "can_contribute": can_contribute(roles, language_id),
    }


class PolicyUpdate(BaseModel):
    language_id: str
    policy: str


@router.post("/language-policy")
async def update_language_policy(
    body: PolicyUpdate,
    user: dict = Depends(get_current_user),
):
    """Set a language's grammar review policy (admin-only)."""
    if body.policy not in ("strict", "ai_ok"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="policy must be 'strict' or 'ai_ok'",
        )
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can change the review policy",
        )
    async with privileged_connection() as conn:
        await set_language_policy(conn, body.language_id, body.policy)
    return {"policy": body.policy}


class TutorModelUpdate(BaseModel):
    language_id: str
    model: str | None = None  # None resets to the global default


# The models an admin may assign per language (WP15a). Order = strongest
# first; None (the global default) is always allowed.
ALLOWED_TUTOR_MODELS = (
    "claude-fable-5",
    "claude-opus-4-8",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
)


@router.post("/language-tutor-model")
async def update_language_tutor_model(
    body: TutorModelUpdate,
    user: dict = Depends(get_current_user),
):
    """Set a language's tutor model override (admin-only; None = default)."""
    if body.model is not None and body.model not in ALLOWED_TUTOR_MODELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"model must be one of {list(ALLOWED_TUTOR_MODELS)} or null",
        )
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can change the tutor model",
        )
    async with privileged_connection() as conn:
        await set_language_tutor_model(conn, body.language_id, body.model)
    return {"tutor_model": body.model}


@router.get("/tutor-usage")
async def tutor_usage_overview(
    days: int = 30,
    user: dict = Depends(get_current_user),
):
    """Aggregated tutor token usage + estimated cost (admin-only, WP9b).

    Rolls up tutor_usage by (language, model, kind) over the window and
    prices each row at list pricing — the data behind per-language model
    choices (WP15a). Estimates only; learners are billed flat tiers.
    """
    await _require_admin(user["id"])
    days = max(1, min(days, 365))
    since = datetime.now(UTC) - timedelta(days=days)
    async with privileged_connection() as conn:
        rows = await aggregate_tutor_usage(conn, since)
    priced = [
        {
            **row,
            "est_cost_usd": estimate_cost_usd(
                row["model"], row["input_tokens"], row["output_tokens"],
                row["cache_write_tokens"], row["cache_read_tokens"],
            ),
        }
        for row in rows
    ]
    return {
        "days": days,
        "rows": priced,
        "total_messages": sum(
            r["messages"] for r in priced if r["kind"] == "chat"
        ),
        "total_est_cost_usd": round(
            sum(r["est_cost_usd"] for r in priced), 4
        ),
    }


# ---------------------------------------------------------------------------
# Content generation panel (WP42, admin-only): fill example/drill gaps with the
# deployed key. Coverage + model recs + "what next", then idempotent runs with
# a dry-run cost preview.
# ---------------------------------------------------------------------------


def _next_language_score(row: dict) -> int:
    """Rank for "which languages to do next": total unfilled items, so the
    biggest gaps float up. Low-resource languages get a boost (they're the
    reason the paid pipeline exists) — see the endpoint for the tie-break."""
    return row["vocab_no_examples"] + row["grammar_no_drills"]


@router.get("/admin/generation/coverage")
async def generation_coverage_overview(user: dict = Depends(get_current_user)):
    """Per-language content coverage, the model each generation task would use,
    and a ranked "do next" list (admin-only, WP42).

    The recommendation sorts by unfilled items, with low-resource languages
    (which the registry pins to a stronger model) prioritized on ties — those
    are the ones the paid pipeline is really for.
    """
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        rows = await generation_coverage(conn)
    for r in rows:
        code = r["language_code"]
        r["low_resource"] = code in LOW_RESOURCE_LANGUAGES
        r["sentence_model"] = resolve_model("sentence_maker", code)
        r["grammar_model"] = resolve_model("grammar_maker", code)
        r["unfilled"] = _next_language_score(r)
    # Biggest gap first; on a tie, low-resource wins (it should be done sooner).
    ranked = sorted(
        rows, key=lambda r: (r["unfilled"], r["low_resource"]), reverse=True
    )
    next_up = [
        {
            "language_id": r["language_id"],
            "language_code": r["language_code"],
            "language_name": r["language_name"],
            "unfilled": r["unfilled"],
            "low_resource": r["low_resource"],
        }
        for r in ranked
        if r["unfilled"] > 0
    ][:5]
    return {
        "available": generation_available(),
        "coverage": rows,
        "recommended_next": next_up,
        "limits": {"max_items": MAX_ITEMS_PER_RUN, "max_per_item": MAX_PER_ITEM},
    }


class GenerationRunRequest(BaseModel):
    language_id: str
    language_code: str
    kind: str = Field(pattern="^(vocab|grammar)$")
    target_per_item: int = Field(default=3, ge=1, le=MAX_PER_ITEM)
    max_items: int = Field(default=25, ge=1, le=MAX_ITEMS_PER_RUN)
    dry_run: bool = True


@router.post("/admin/generation/run")
async def generation_run(
    body: GenerationRunRequest,
    user: dict = Depends(get_current_user),
):
    """Fill a language's example/drill gaps (admin-only, WP42).

    dry_run (the default) resolves the work-list and a cost ESTIMATE without
    calling the model, so the bill is visible before it's paid. With
    dry_run=false it runs maker→checker→persist for each gap item; the run is
    idempotent (only under-target items are touched, inserts dedupe), so a
    re-run continues rather than duplicating — no wasted spend.
    """
    await _require_admin(user["id"])
    if not body.dry_run and not generation_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation needs ANTHROPIC_API_KEY (or dev-mock) on the server.",
        )
    # Confirm the language exists and get its display name for the maker prompt.
    async with privileged_connection() as conn:
        lang = await conn.fetchrow(
            "SELECT code, name FROM languages WHERE id = $1", body.language_id
        )
        if lang is None or lang["code"] != body.language_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown language."
            )
        if body.dry_run:
            plan = await plan_run(
                conn,
                kind=body.kind,
                language_id=body.language_id,
                language_code=body.language_code,
                target_per_item=body.target_per_item,
                max_items=body.max_items,
            )
            plan.pop("_items", None)
            return {"dry_run": True, **plan}
        result = await run_generation(
            conn,
            kind=body.kind,
            language_id=body.language_id,
            language_code=body.language_code,
            language_name=lang["name"],
            target_per_item=body.target_per_item,
            max_items=body.max_items,
        )
    return {"dry_run": False, **result}


@router.get("/admin/generation/pending")
async def generation_pending(
    language_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Generated example sentences awaiting review for a language (admin-only,
    WP42 gate). These are hidden from learners until approved here."""
    await _require_admin(user["id"])
    limit = max(1, min(limit, 200))
    async with privileged_connection() as conn:
        return {"pending": await list_pending_examples(conn, language_id, limit)}


class ExampleReviewRequest(BaseModel):
    approve: bool


@router.post("/admin/generation/examples/{example_id}/review")
async def generation_review_example(
    example_id: str,
    body: ExampleReviewRequest,
    user: dict = Depends(get_current_user),
):
    """Approve (→ served to learners) or reject (→ deleted) a pending generated
    example (admin-only, WP42 gate). 404 if it isn't a pending 'ai' row."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        changed = await review_example(conn, example_id, body.approve)
    if not changed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending generated example with that id.",
        )
    return {"approved": body.approve}


# ---------------------------------------------------------------------------
# Generated-drill review gate (Contributor › Review tab, reviewer-accessible).
# Generated grammar drills land pending; a reviewer approves them into the
# corpus or rejects them. Parallel to the vocab example gate above, but exposed
# to reviewers (not admin-only) since it lives in the Review workspace.
# ---------------------------------------------------------------------------


@router.get("/review/generated-drills")
async def review_generated_drills(
    language_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Generated grammar drills awaiting review for a language — hidden from
    learners until approved. Reviewers/admins publish; trial reviewers view and
    recommend. Each item carries its advisory-recommendation tally."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_trial_review(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or trial reviewer for this language can review drills",
        )
    limit = max(1, min(limit, 200))
    async with privileged_connection() as conn:
        pending = await list_pending_drills(conn, language_id, limit)
        recos = await recommendations_for_targets(
            conn, "drill", [d["id"] for d in pending]
        )
    for d in pending:
        d["recommendations"] = recos.get(d["id"])
    return {"pending": pending, "can_publish": can_review(roles, language_id)}


class DrillReviewRequest(BaseModel):
    approve: bool


@router.post("/review/generated-drills/{drill_id}/review")
async def review_generated_drill(
    drill_id: str,
    body: DrillReviewRequest,
    user: dict = Depends(get_current_user),
):
    """Approve (→ permanent corpus, served to learners) or reject (→ deleted) a
    pending generated drill (reviewer or admin for its language). 404 if it
    isn't a pending 'ai' row."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        lang = await conn.fetchval(
            "SELECT gp.language_id FROM drill_sentences ds "
            "JOIN grammar_points gp ON ds.grammar_point_id = gp.id "
            "WHERE ds.id = $1", drill_id,
        )
    if lang is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such drill.")
    if not can_review(roles, str(lang)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or admin for this language can review drills",
        )
    async with privileged_connection() as conn:
        changed = await review_drill(conn, drill_id, body.approve)
    if not changed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending generated drill with that id.",
        )
    return {"approved": body.approve}


async def _example_language(conn, example_id: str):
    return await conn.fetchval(
        "SELECT language_id FROM example_sentences WHERE id = $1", example_id
    )


@router.get("/review/vocab/{vocabulary_id}/examples")
async def review_vocab_examples(
    vocabulary_id: str, user: dict = Depends(get_current_user)
):
    """Every example sentence for a word — viewable and curatable by reviewers
    and trial reviewers for the word's language. Each carries its advisory tally.
    """
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        lang = await conn.fetchval(
            "SELECT language_id FROM vocabulary WHERE id = $1", vocabulary_id
        )
    if lang is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such word.")
    if not can_trial_review(roles, str(lang)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or trial reviewer for this language can view examples",
        )
    async with privileged_connection() as conn:
        examples = await list_vocab_examples(conn, vocabulary_id)
        recos = await recommendations_for_targets(
            conn, "example", [e["id"] for e in examples]
        )
    for e in examples:
        e["recommendations"] = recos.get(e["id"])
    return {"examples": examples, "can_publish": can_review(roles, str(lang))}


class ExampleEditRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=500)
    translation: str | None = Field(default=None, max_length=500)


async def _require_example_role(user_id: str, example_id: str, *, publish: bool):
    """Gate an example action. publish=True needs a full reviewer (delete);
    publish=False allows trial reviewers too (view/curate)."""
    async with rls_connection(user_id) as conn:
        roles = await get_roles(conn, user_id)
        lang = await _example_language(conn, example_id)
    if lang is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such example.")
    allowed = can_review(roles, str(lang)) if publish else can_trial_review(roles, str(lang))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have review access for this language",
        )


@router.put("/review/examples/{example_id}")
async def edit_review_example(
    example_id: str,
    body: ExampleEditRequest,
    user: dict = Depends(get_current_user),
):
    """Curate an example sentence's text/translation (reviewer or trial reviewer)."""
    await _require_example_role(user["id"], example_id, publish=False)
    async with privileged_connection() as conn:
        changed = await edit_example_sentence(
            conn, example_id, body.sentence.strip(),
            (body.translation or "").strip() or None, user["id"],
        )
    if not changed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such example.")
    return {"ok": True}


@router.delete("/review/examples/{example_id}")
async def delete_review_example(
    example_id: str, user: dict = Depends(get_current_user)
):
    """Delete an example sentence (full reviewer / admin only)."""
    await _require_example_role(user["id"], example_id, publish=True)
    async with privileged_connection() as conn:
        changed = await delete_example_sentence(conn, example_id)
    return {"ok": changed}


@router.post("/review/examples/{example_id}/translation/accept")
async def accept_example_translation_suggestion(
    example_id: str, user: dict = Depends(get_current_user)
):
    """Apply the audit's suggested translation to the live one (full reviewer)."""
    await _require_example_role(user["id"], example_id, publish=True)
    async with privileged_connection() as conn:
        changed = await accept_example_translation(conn, example_id, user["id"])
    if not changed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending translation suggestion.",
        )
    return {"ok": True}


@router.post("/review/examples/{example_id}/translation/dismiss")
async def dismiss_example_translation_suggestion(
    example_id: str, user: dict = Depends(get_current_user)
):
    """Discard the audit's suggested translation, keeping the current one
    (full reviewer)."""
    await _require_example_role(user["id"], example_id, publish=True)
    async with privileged_connection() as conn:
        changed = await dismiss_example_translation(conn, example_id)
    return {"ok": changed}


# ---------------------------------------------------------------------------
# Advisory recommendations (trial reviewers) + trial-reviewer activity.
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    target_type: str  # 'drill' | 'example'
    target_id: str
    recommendation: str  # 'approve' | 'reject'
    note: str = Field(default="", max_length=2000)


async def _recommend_target_language(conn, target_type: str, target_id: str):
    if target_type == "drill":
        return await conn.fetchval(
            "SELECT gp.language_id FROM drill_sentences ds "
            "JOIN grammar_points gp ON ds.grammar_point_id = gp.id "
            "WHERE ds.id = $1", target_id,
        )
    if target_type == "example":
        return await conn.fetchval(
            "SELECT language_id FROM example_sentences WHERE id = $1", target_id
        )
    return None


@router.post("/review/recommend")
async def recommend(body: RecommendRequest, user: dict = Depends(get_current_user)):
    """A trial reviewer's advisory approve/reject on a pending item. Never
    publishes — a full reviewer still decides."""
    if body.target_type not in ("drill", "example"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bad target_type")
    if body.recommendation not in ("approve", "reject"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bad recommendation")
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        lang = await _recommend_target_language(conn, body.target_type, body.target_id)
    if lang is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such item.")
    if not can_trial_review(roles, str(lang)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or trial reviewer for this language can recommend",
        )
    async with privileged_connection() as conn:
        await add_recommendation(
            conn, user["id"], str(lang), body.target_type, body.target_id,
            body.recommendation, body.note.strip(),
        )
    return {"ok": True}


@router.get("/review/trial-reviewers")
async def list_trial_reviewers(
    language_id: str, user: dict = Depends(get_current_user)
):
    """Trial reviewers for a language and their activity, so an admin can decide
    who to promote to a full reviewer (admin-only)."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        return {"reviewers": await trial_reviewer_activity(conn, language_id)}


@router.get("/review/ai-levels")
async def review_ai_levels(
    language_id: str, user: dict = Depends(get_current_user)
):
    """Words carrying a provisional AI-estimated CEFR level, for a reviewer to
    confirm or adjust. Confirming also finalises the word's deck placement."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_trial_review(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or trial reviewer for this language can view this",
        )
    async with privileged_connection() as conn:
        words = await list_ai_leveled_vocab(conn, language_id)
    return {"words": words, "can_publish": can_review(roles, language_id)}


class VocabLevelRequest(BaseModel):
    level: str


@router.post("/review/vocab/{vocabulary_id}/level")
async def set_vocab_level(
    vocabulary_id: str,
    body: VocabLevelRequest,
    user: dict = Depends(get_current_user),
):
    """Confirm or adjust a word's CEFR level — marks it curated (trusted) and
    finalises its deck. Full reviewers/admins only."""
    if body.level not in ("A1", "A2", "B1", "B2", "C1", "C2"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bad level"
        )
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        lang = await conn.fetchval(
            "SELECT language_id FROM vocabulary WHERE id = $1", vocabulary_id
        )
    if lang is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such word.")
    if not can_review(roles, str(lang)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer or admin for this language can confirm levels",
        )
    async with privileged_connection() as conn:
        changed = await confirm_vocab_level(conn, vocabulary_id, body.level)
    if not changed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such word.")
    return {"ok": True}


@router.get("/engagement")
async def engagement_overview(
    days: int = 30,
    user: dict = Depends(get_current_user),
):
    """App-wide engagement snapshot (admin-only): active users, feature
    usage, study time, and the languages people actually study — read from
    the activity tables normal use already writes."""
    await _require_admin(user["id"])
    days = max(1, min(days, 365))
    async with privileged_connection() as conn:
        return await admin_engagement(conn, days)


@router.get("/engagement/users")
async def engagement_users(
    days: int = 30,
    user: dict = Depends(get_current_user),
):
    """Per-user drill-down behind the engagement tiles (admin-only): who
    each user is, when they were last active, and what they did in the
    window."""
    await _require_admin(user["id"])
    days = max(1, min(days, 365))
    async with privileged_connection() as conn:
        return {"users": await admin_engagement_users(conn, days)}


@router.get("/analytics/timeseries")
async def analytics_timeseries(
    days: int = 30,
    user: dict = Depends(get_current_user),
):
    """Daily active-users / reviews / minutes / signups series (admin;
    WP26a) for the 7/30/90-day charts."""
    await _require_admin(user["id"])
    days = max(7, min(days, 90))
    async with privileged_connection() as conn:
        return {"days": days, "series": await admin_timeseries(conn, days)}


@router.get("/analytics/cohorts")
async def analytics_cohorts(
    user: dict = Depends(get_current_user),
):
    """Weekly signup-cohort retention grid (admin; WP26b)."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        return {"cohorts": await admin_cohorts(conn, 8)}


@router.get("/engagement/users/{user_id}")
async def engagement_user_detail(
    user_id: str,
    days: int = 30,
    user: dict = Depends(get_current_user),
):
    """Per-language breakdown for one account (admin-only) — the expanded
    view under a row in the engagement users table."""
    await _require_admin(user["id"])
    try:
        uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid user id") from exc
    days = max(1, min(days, 365))
    async with privileged_connection() as conn:
        return {
            "languages": await admin_engagement_user_detail(conn, user_id, days)
        }


@router.put("/grammar/{point_id}")
async def update_grammar(
    point_id: str,
    body: ExplanationUpdate,
    user: dict = Depends(get_current_user),
):
    """Save a contributor explanation for a grammar point (pending review)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        language_id = await get_point_language(conn, point_id)
    if language_id is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        await save_explanation(
            conn, point_id, body.explanation, body.culture_note, user["id"],
            references=[r.model_dump() for r in body.references],
        )
    return {"saved": True, "reviewed": False}


@router.post("/grammar")
async def create_point(
    body: NewGrammarPoint,
    user: dict = Depends(get_current_user),
):
    """Create a new grammar point (contributor for the language; pending review)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_contribute(roles, body.language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        point_id = await create_grammar_point(
            conn, body.language_id, body.title, body.level,
            body.explanation or None, body.culture_note or None,
            [r.model_dump() for r in body.references], user["id"],
        )
    if point_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A grammar point with that title already exists",
        )
    return {"id": point_id}


@router.get("/grammar/{point_id}/drills")
async def get_drills(
    point_id: str,
    user: dict = Depends(get_current_user),
):
    """List a grammar point's drill sentences (role-gated)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
        if info is None:
            raise HTTPException(status_code=404, detail="Grammar point not found")
        if not can_contribute(roles, info[0]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        drills = await list_drills(conn, point_id)
    return {"drills": drills}


@router.post("/grammar/{point_id}/drills")
async def create_drill(
    point_id: str,
    body: NewDrill,
    user: dict = Depends(get_current_user),
):
    """Add a drill sentence — NLP-validated so it's guaranteed answerable."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    language_id, language_code = info
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    if not await validate_drill(language_code, body.sentence, body.answer):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The sentence must contain the {{answer}} blank and the answer "
                "must validate in this language."
            ),
        )
    async with privileged_connection() as conn:
        drill_id = await add_drill(
            conn, point_id, body.sentence, body.answer,
            body.translation, body.hint,
        )
    return {"id": drill_id}


@router.put("/grammar/{point_id}/drills/{drill_id}")
async def edit_drill(
    point_id: str,
    drill_id: str,
    body: EditDrill,
    user: dict = Depends(get_current_user),
):
    """Edit a live drill — reviewer/admin only, with guard rails.

    Friction by design: the sentence must still pass the NLP answerability
    gate, the answer must be a single token that doesn't leak into the
    visible frame, the hint must not reveal the answer, and a change_note
    (≥10 chars) is required. The edit de-certifies the point (reviewed →
    false) and files the note in the point's review queue so a DIFFERENT
    reviewer re-approves before learners see it.
    """
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    language_id, language_code = info
    if not can_review(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin or a reviewer for this language can edit live cards",
        )
    answer = body.answer.strip()
    if " " in answer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The answer must be a single token (one blank, one word)",
        )
    visible = body.sentence.replace("{{answer}}", " ")
    if re.search(rf"(?<![^\W\d_]){re.escape(answer)}(?![^\W\d_])", visible, re.IGNORECASE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The answer appears in the visible sentence — it would give itself away",
        )
    if body.hint and answer.lower() in body.hint.lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The hint contains the answer — it would give itself away",
        )
    if not await validate_drill(language_code, body.sentence, answer):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The sentence must contain the {{answer}} blank and the answer "
                "must validate in this language."
            ),
        )
    async with privileged_connection() as conn:
        ok = await update_drill(
            conn, drill_id, point_id, body.sentence, answer,
            body.translation, body.hint, modified_by=user["id"],
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Drill not found")
        await add_review_note(
            conn, point_id, user["id"],
            f"[card edit] {body.change_note}",
        )
    return {"saved": True, "reviewed": False}


@router.delete("/grammar/{point_id}/drills/{drill_id}")
async def remove_drill(
    point_id: str,
    drill_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a drill sentence (role-gated by the point's language)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    if not can_contribute(roles, info[0]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        await delete_drill(conn, drill_id)
    return {"deleted": True}


@router.post("/grammar/{point_id}/ai-check")
async def ai_check(
    point_id: str,
    user: dict = Depends(get_current_user),
):
    """Run the advisory AI semantic review and store its verdict on the point."""
    if not ai_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI review is not configured on this server",
        )
    if not await ai_review_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI checks — try again in a minute.",
        )
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
        if info is None:
            raise HTTPException(status_code=404, detail="Grammar point not found")
        if not can_contribute(roles, info[0]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        point = await get_point_for_check(conn, point_id)

    result = await semantic_check_point(
        point["language_code"], point["title"], point["explanation"], point["drills"]
    )
    async with privileged_connection() as conn:
        await save_ai_check(conn, point_id, result["status"], result["notes"])
    return result


TARGET_TYPES = ("grammar_point", "drill", "vocabulary", "example_sentence", "other")
FIELDS = ("sentence", "hint", "translation", "answer", "explanation", "other")


class NewChangeRequest(BaseModel):
    language_id: str
    target_type: str = "other"
    target_id: str | None = None
    target_label: str | None = Field(default=None, max_length=500)
    field: str = "other"
    issue: str = Field(min_length=1, max_length=2000)
    suggestion: str | None = Field(default=None, max_length=2000)


class VoteBody(BaseModel):
    vote: int = Field(ge=-1, le=1)


class ResolveBody(BaseModel):
    status: str  # 'accepted' | 'rejected'


@router.post("/change-requests", status_code=status.HTTP_201_CREATED)
async def create_change_request(
    body: NewChangeRequest, user: dict = Depends(get_current_user)
):
    """Raise a votable change request on a card (reviewer / contributor /
    admin for the card's language). Low-friction: name the field, say what's
    wrong, optionally suggest a fix. Learners use 'Report an issue' instead."""
    if body.target_type not in TARGET_TYPES or body.field not in FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid target_type or field",
        )
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_contribute(roles, body.language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need a reviewer or contributor role for this language",
        )
    async with privileged_connection() as conn:
        req_id = await create_request(
            conn, user["id"], body.language_id, body.target_type,
            body.target_id, (body.target_label or "").strip() or None,
            body.field, body.issue.strip(),
            (body.suggestion or "").strip() or None,
        )
    return {"id": req_id}


@router.get("/change-requests")
async def get_change_requests(
    language_id: str,
    status: str = "open",
    user: dict = Depends(get_current_user),
):
    """The review board for a language (reviewer / contributor / admin)."""
    if status not in ("open", "accepted", "rejected"):
        raise HTTPException(status_code=422, detail="Invalid status")
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need a reviewer or contributor role for this language",
        )
    async with privileged_connection() as conn:
        requests = await list_requests(conn, language_id, user["id"], status)
    return {"requests": requests, "can_resolve": is_admin(roles)}


@router.post("/change-requests/{request_id}/vote")
async def vote_change_request(
    request_id: str, body: VoteBody, user: dict = Depends(get_current_user)
):
    """Up/down/clear a vote (reviewer / contributor / admin for the language)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    async with privileged_connection() as conn:
        language_id = await get_request_language(conn, request_id)
        if language_id is None:
            raise HTTPException(status_code=404, detail="Change request not found")
        if not can_contribute(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You need a reviewer or contributor role for this language",
            )
        await cast_vote(conn, request_id, user["id"], body.vote)
    return {"ok": True}


@router.post("/change-requests/{request_id}/resolve")
async def resolve_change_request(
    request_id: str, body: ResolveBody, user: dict = Depends(get_current_user)
):
    """Accept or reject a change request — admins only."""
    if body.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=422, detail="status must be accepted or rejected")
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can accept or reject a change request",
        )
    async with privileged_connection() as conn:
        ok = await resolve_request(conn, request_id, user["id"], body.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Change request not found or already resolved")
    return {"status": body.status}


@router.post("/grammar/{point_id}/notes")
async def flag_point_issue(
    point_id: str,
    body: NewReviewNote,
    user: dict = Depends(get_current_user),
):
    """File a reviewer note against a point — the middle ground between
    fixing it yourself and silently not approving."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        language_id = await get_point_language(conn, point_id)
    if language_id is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        note_id = await add_review_note(conn, point_id, user["id"], body.note.strip())
    return {"id": note_id}


@router.get("/notes")
async def review_notes(
    language_id: str,
    include_resolved: bool = False,
    user: dict = Depends(get_current_user),
):
    """List reviewer notes for a language (role-gated)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        notes = await list_review_notes(
            conn, language_id, include_resolved=include_resolved
        )
    return {"notes": notes}


@router.post("/notes/{note_id}/resolve")
async def resolve_note(
    note_id: str,
    user: dict = Depends(get_current_user),
):
    """Mark a reviewer note resolved (reviewer for the language, or admin)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    async with privileged_connection() as conn:
        language_id = await get_note_language(conn, note_id)
        if language_id is None:
            raise HTTPException(status_code=404, detail="Note not found")
        if not can_review(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a reviewer for this language or an admin can resolve notes",
            )
        ok = await resolve_review_note(conn, note_id, user["id"])
    return {"resolved": ok}


@router.post("/grammar/{point_id}/approve")
async def approve_grammar(
    point_id: str,
    user: dict = Depends(get_current_user),
):
    """Record the human sign-off that makes content visible to learners.

    Admins approve anywhere; reviewers approve for their language.
    """
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        language_id = await get_point_language(conn, point_id)
    if language_id is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    if not can_review(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin or a reviewer for this language can approve content",
        )
    async with privileged_connection() as conn:
        # Nobody certifies their own change (§3b: content is never
        # self-certified) — the last editor can't be the approver.
        submitted_by = await conn.fetchval(
            "SELECT explanation_submitted_by FROM grammar_points WHERE id = $1",
            point_id,
        )
        if submitted_by is not None and str(submitted_by) == user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You edited this point — a different reviewer must approve it",
            )
        ok = await approve_explanation(conn, point_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    return {"approved": True}


@router.get("/feedback")
async def feedback_queue(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """List learner feedback for a language (role-gated)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        items = await list_feedback(conn, language_id)
    return {"feedback": items}


@router.post("/feedback/{feedback_id}/resolve")
async def resolve_card_feedback(
    feedback_id: str,
    user: dict = Depends(get_current_user),
):
    """Mark a learner feedback item resolved (role-gated by its language)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    async with privileged_connection() as conn:
        language_id = await get_feedback_language(conn, feedback_id)
        if language_id is None:
            raise HTTPException(status_code=404, detail="Feedback not found")
        if not can_contribute(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        await resolve_feedback(conn, feedback_id)
    return {"resolved": True}


class NewSuggestion(BaseModel):
    entity_type: str = Field(pattern="^(vocabulary|grammar)$")
    entity_id: str
    proposed: dict
    note: str | None = Field(default=None, max_length=1000)


class RejectSuggestion(BaseModel):
    review_note: str | None = Field(default=None, max_length=1000)


@router.post("/suggestions")
async def create_suggestion(
    body: NewSuggestion,
    user: dict = Depends(get_current_user),
):
    """Propose an edit to a live card. Contributor-gated; nothing goes live
    until a reviewer approves it."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    async with privileged_connection() as conn:
        language_id = await entity_language(conn, body.entity_type, body.entity_id)
        if language_id is None:
            raise HTTPException(status_code=404, detail="Card not found")
        if not can_contribute(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        try:
            sid = await submit_suggestion(
                conn, language_id, body.entity_type, body.entity_id,
                user["id"], body.proposed, body.note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": sid}


@router.get("/suggestions")
async def suggestions_queue(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Pending suggestions for a language (reviewer/admin only)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_review(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a reviewer role for this language",
        )
    async with privileged_connection() as conn:
        items = await list_suggestions(conn, language_id)
    return {"suggestions": items}


@router.post("/suggestions/{suggestion_id}/approve")
async def approve_content_suggestion(
    suggestion_id: str,
    user: dict = Depends(get_current_user),
):
    """Apply a suggestion to the live card (reviewer/admin for its language)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    async with privileged_connection() as conn:
        s = await get_suggestion(conn, suggestion_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        if not can_review(roles, s["language_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a reviewer role for this language",
            )
        applied = await approve_suggestion(conn, suggestion_id, user["id"])
        if not applied:
            raise HTTPException(status_code=409, detail="Already resolved")
    return {"approved": True}


@router.post("/suggestions/{suggestion_id}/reject")
async def reject_content_suggestion(
    suggestion_id: str,
    body: RejectSuggestion,
    user: dict = Depends(get_current_user),
):
    """Reject a suggestion (reviewer/admin for its language); nothing applied."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    async with privileged_connection() as conn:
        s = await get_suggestion(conn, suggestion_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        if not can_review(roles, s["language_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a reviewer role for this language",
            )
        ok = await reject_suggestion(conn, suggestion_id, user["id"], body.review_note)
        if not ok:
            raise HTTPException(status_code=409, detail="Already resolved")
    return {"rejected": True}


@router.get("/translation-reviews")
async def translation_reviews_queue(user: dict = Depends(get_current_user)):
    """Glosses/hints the AI maker-checker refused to auto-apply (admin-only)."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        return {"reviews": await list_translation_reviews(conn)}


async def _resolve_review(review_id: str, user: dict, approve: bool) -> dict:
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        outcome = await resolve_translation_review(conn, review_id, approve)
    if outcome == "not_found":
        raise HTTPException(status_code=404, detail="Review item not found")
    if outcome == "not_pending":
        raise HTTPException(status_code=409, detail="Already resolved")
    if outcome == "empty":
        raise HTTPException(
            status_code=422,
            detail="Nothing to apply — this item has no proposed text; reject it "
                   "or fix the card directly.",
        )
    return {"approved" if approve else "rejected": True}


@router.post("/translation-reviews/{review_id}/approve")
async def approve_translation_review(
    review_id: str, user: dict = Depends(get_current_user),
):
    return await _resolve_review(review_id, user, approve=True)


@router.post("/translation-reviews/{review_id}/reject")
async def reject_translation_review(
    review_id: str, user: dict = Depends(get_current_user),
):
    return await _resolve_review(review_id, user, approve=False)


class NewAccount(BaseModel):
    email: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=10, max_length=100)


class PlanOverride(BaseModel):
    plan_scope: str = Field(pattern="^(single|all)$")
    plan_language_id: str | None = None


@router.get("/users")
async def accounts(user: dict = Depends(get_current_user)):
    """Every account at a glance (admin-only): email, joined, plan, roles,
    study volume. The demo/deploy admin console."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        return {"users": await list_accounts(conn)}


@router.post("/users")
async def create_account(
    body: NewAccount,
    user: dict = Depends(get_current_user),
):
    """Create an account directly (admin-only) — the invite-only beta path:
    public signup is disabled, so the admin mints email+password accounts.

    DATABASE FIRST: this deploy's HTTP egress to *.supabase.co hangs (the
    old API-first order spent its whole gateway window waiting before the
    fallback could run → 504). The SQL path writes the same rows the admin
    API writes — confirmed auth.users with the bf-crypt hash GoTrue checks
    at sign-in, plus the email identity — and completes in ~1s over the
    (working) database connection. The admin API is kept as the backup for
    environments where the SQL path can't run.
    """
    await _require_admin(user["id"])
    try:
        async with privileged_connection() as conn:
            uid = await create_auth_user(conn, body.email, body.password)
        return {"id": uid, "email": body.email.lower()}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        ) from None
    except Exception as db_exc:  # noqa: BLE001
        logger.warning(
            "account creation: SQL path failed (%s) — trying the admin API",
            db_exc,
        )

    from backend.dependencies import get_settings
    settings = get_settings()
    if not settings.supabase_service_role_key or not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Account creation failed: the database path errored and the "
                "admin API isn't configured (SUPABASE_SERVICE_ROLE_KEY / "
                "SUPABASE_URL missing)."
            ),
        )
    import httpx
    # Short timeouts: stay well under the platform's ~10s gateway window so
    # a hung call returns our own clear 502, never an opaque 504.
    try:
        timeout = httpx.Timeout(3.0, connect=2.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
                json={"email": body.email, "password": body.password,
                      "email_confirm": True},
            )
    except httpx.HTTPError as exc:
        kind = type(exc).__name__
        logger.warning("account creation: admin API also failed (%s): %s", kind, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Account creation failed on both paths — the database write "
                f"errored and the authentication service was unreachable ({kind})."
            ),
        ) from exc
    # Duplicate email — Supabase tags it error_code=email_exists (422).
    if resp.status_code == 422 and (
        "already" in resp.text.lower() or "email_exists" in resp.text
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
    if resp.status_code >= 400:
        logger.warning(
            "account creation: Supabase %s — %s", resp.status_code, resp.text[:300]
        )
        detail = "The authentication service rejected the account."
        try:
            msg = resp.json().get("msg") or resp.json().get("error_description")
            if msg:
                detail = f"{detail} {msg}"
        except ValueError:
            pass
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    created = resp.json()
    return {"id": created.get("id"), "email": created.get("email")}


@router.delete("/users/{user_id}")
async def remove_account(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    """Permanently delete an account and everything it owns (admin-only).

    Cascades through auth AND app tables. Admins cannot delete themselves
    — a second admin (or the Supabase dashboard) must do it, so a slip
    can't lock the project out of its only admin.
    """
    await _require_admin(user["id"])
    if user_id == user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't delete your own account from the admin panel",
        )
    async with privileged_connection() as conn:
        ok = await delete_account(conn, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"deleted": True}


@router.put("/users/{user_id}/plan")
async def override_plan(
    user_id: str,
    body: PlanOverride,
    user: dict = Depends(get_current_user),
):
    """Switch an account between Single-language and All-languages (admin)."""
    await _require_admin(user["id"])
    if body.plan_scope == "single" and not body.plan_language_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A single-language plan needs plan_language_id",
        )
    async with privileged_connection() as conn:
        ok = await set_account_plan(
            conn, user_id, body.plan_scope, body.plan_language_id
        )
    if not ok:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"plan_scope": body.plan_scope}


class TutorAccessOverride(BaseModel):
    access: str = Field(pattern="^(default|blocked|enabled)$")
    daily_cap: int | None = Field(default=None, ge=0, le=1000)


@router.put("/users/{user_id}/tutor")
async def override_tutor_access(
    user_id: str,
    body: TutorAccessOverride,
    user: dict = Depends(get_current_user),
):
    """Per-account tutor override (admin, WP15b): block the tutor entirely,
    or enable it with a daily message cap so a trial has bounded API cost.
    The cap is stored regardless of mode, so toggling access back and forth
    keeps the number."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM auth.users WHERE id = $1", user_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Account not found")
        await set_tutor_access(conn, user_id, body.access, body.daily_cap)
    return {"access": body.access, "daily_cap": body.daily_cap}


async def _require_admin(user_id: str) -> None:
    async with rls_connection(user_id) as conn:
        roles = await get_roles(conn, user_id)
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can manage roles",
        )


async def _resolve_role_target(body: RoleGrant) -> str:
    """The target user id from either an explicit id or an account email."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role must be 'contributor', 'reviewer', or 'admin'",
        )
    if body.user_id:
        return body.user_id
    if not body.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide user_id or email",
        )
    async with privileged_connection() as conn:
        target = await find_user_by_email(conn, body.email)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account with email {body.email}",
        )
    return target


@router.get("/roles/all")
async def all_roles(user: dict = Depends(get_current_user)):
    """Every role grant with the holder's email (admin-only)."""
    await _require_admin(user["id"])
    async with privileged_connection() as conn:
        grants = await list_all_roles(conn)
    return {"grants": grants}


@router.post("/roles")
async def grant_contributor_role(
    body: RoleGrant,
    user: dict = Depends(get_current_user),
):
    """Grant a contributor/reviewer/admin role (admin-only; by id or email)."""
    await _require_admin(user["id"])
    target = await _resolve_role_target(body)
    async with privileged_connection() as conn:
        await grant_role(conn, target, body.language_id, body.role)
    return {"granted": True, "user_id": target}


@router.post("/roles/revoke")
async def revoke_contributor_role(
    body: RoleGrant,
    user: dict = Depends(get_current_user),
):
    """Remove one role grant (admin-only; by id or email)."""
    await _require_admin(user["id"])
    target = await _resolve_role_target(body)
    async with privileged_connection() as conn:
        removed = await revoke_role(conn, target, body.language_id, body.role)
    return {"revoked": removed, "user_id": target}
