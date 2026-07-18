"""Contributor router — language specialists author grammar explanations.

Authorization is enforced here (app layer): role reads run on the user's RLS
connection; content writes run on a privileged connection only after the
caller's role is verified for the target language.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.contributor import (
    add_drill,
    add_review_note,
    admin_engagement,
    approve_explanation,
    approve_suggestion,
    can_contribute,
    can_review,
    create_grammar_point,
    delete_account,
    delete_drill,
    entity_language,
    find_user_by_email,
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
    list_all_roles,
    list_drills,
    list_feedback,
    list_grammar_points,
    list_review_notes,
    list_suggestions,
    reject_suggestion,
    resolve_feedback,
    resolve_review_note,
    revoke_role,
    save_ai_check,
    save_explanation,
    set_account_plan,
    set_language_policy,
    set_language_tutor_model,
    submit_suggestion,
    update_drill,
)
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.tutor import aggregate_tutor_usage, set_tutor_access
from backend.services.drills import validate_drill
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

VALID_ROLES = ("contributor", "reviewer", "admin")


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
        "review_policy": policy,
        "tutor_model": tutor_model,
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
            body.translation, body.hint,
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
    public signup is disabled, so the admin mints email+password accounts
    for friends via the Supabase admin API."""
    await _require_admin(user["id"])
    from backend.dependencies import get_settings
    settings = get_settings()
    if not settings.supabase_service_role_key or not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Account creation isn't configured on the server "
                "(SUPABASE_SERVICE_ROLE_KEY / SUPABASE_URL missing)."
            ),
        )
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
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
        logger.warning("account creation: couldn't reach Supabase: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't reach the authentication service — please try again.",
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
