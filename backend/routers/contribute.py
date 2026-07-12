"""Contributor router — language specialists author grammar explanations.

Authorization is enforced here (app layer): role reads run on the user's RLS
connection; content writes run on a privileged connection only after the
caller's role is verified for the target language.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.contributor import (
    add_drill,
    add_review_note,
    approve_explanation,
    can_contribute,
    can_review,
    create_grammar_point,
    delete_drill,
    find_user_by_email,
    get_feedback_language,
    get_language_policy,
    get_language_tutor_model,
    get_note_language,
    get_point_for_check,
    get_point_language,
    get_point_language_and_code,
    get_roles,
    grant_role,
    is_admin,
    list_all_roles,
    list_drills,
    list_feedback,
    list_grammar_points,
    list_review_notes,
    resolve_feedback,
    resolve_review_note,
    revoke_role,
    save_ai_check,
    save_explanation,
    set_language_policy,
    set_language_tutor_model,
    update_drill,
)
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.tutor import aggregate_tutor_usage
from backend.services.drills import validate_drill
from backend.services.rate_limit import ai_review_limiter
from backend.services.semantic_check import ai_available, semantic_check_point
from backend.services.tutor_costs import estimate_cost_usd

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
