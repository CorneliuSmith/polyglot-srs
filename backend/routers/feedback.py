"""General app feedback.

The channel for everything the content-scoped ones cannot carry: "the
keyboard is cut off on my phone", "I couldn't find the Gym", "the placement
test wouldn't start". Anyone can send; staff triage.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.contributor import get_roles, is_admin
from backend.repositories.feedback import (
    CATEGORIES,
    count_open_feedback,
    feedback_summary,
    list_feedback,
    list_my_feedback,
    set_feedback_status,
    submit_feedback,
)
from backend.repositories.pool import privileged_connection, rls_connection

router = APIRouter()

STATUSES = ("open", "triaged", "closed")


class FeedbackCreate(BaseModel):
    category: str
    # Long enough for a real description, short enough that nothing pathological
    # lands in the table. The floor is deliberately low: "gym 500s" is a
    # perfectly good bug report.
    message: str = Field(min_length=3, max_length=4000)
    language_id: str | None = None
    page: str | None = Field(default=None, max_length=200)


class FeedbackTriage(BaseModel):
    status: str
    admin_note: str | None = Field(default=None, max_length=4000)


async def _require_staff(user_id: str) -> None:
    """Any staff role can read the queue — feedback is not admin-secret, and
    the people who can fix a content complaint are contributors."""
    async with rls_connection(user_id) as conn:
        roles = await get_roles(conn, user_id)
    if not (is_admin(roles) or roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need a staff role to read feedback",
        )


async def _require_admin(user_id: str) -> None:
    async with rls_connection(user_id) as conn:
        roles = await get_roles(conn, user_id)
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can triage feedback",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    body: FeedbackCreate,
    user: dict = Depends(get_current_user),
):
    """Send feedback about the app."""
    if body.category not in CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"category must be one of {', '.join(CATEGORIES)}",
        )
    async with rls_connection(user["id"]) as conn:
        feedback_id = await submit_feedback(
            conn,
            user["id"],
            category=body.category,
            message=body.message,
            language_id=body.language_id,
            page=body.page,
        )
    if feedback_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Feedback needs migration 20260906 applied — "
                "check /api/health/schema"
            ),
        )
    return {"id": feedback_id}


@router.get("/mine")
async def my_feedback(user: dict = Depends(get_current_user)):
    """What I've already sent, and what came of it."""
    async with rls_connection(user["id"]) as conn:
        return {"feedback": await list_my_feedback(conn, user["id"])}


@router.get("/summary")
async def feedback_badge(user: dict = Depends(get_current_user)):
    """Is there anything waiting? Two numbers, for the dashboard prompt.

    Declared BEFORE the "" route on purpose — FastAPI matches in definition
    order, and a later /summary would be shadowed by the queue handler.
    """
    await _require_staff(user["id"])
    async with privileged_connection() as conn:
        return await feedback_summary(conn)


@router.get("")
async def all_feedback(
    status_filter: str | None = None,
    language_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """The triage queue (staff)."""
    await _require_staff(user["id"])
    if status_filter is not None and status_filter not in STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {', '.join(STATUSES)}",
        )
    async with privileged_connection() as conn:
        items = await list_feedback(
            conn, status=status_filter, language_id=language_id
        )
        open_count = await count_open_feedback(conn)
    return {"feedback": items, "open_count": open_count}


@router.put("/{feedback_id}")
async def triage_feedback(
    feedback_id: str,
    body: FeedbackTriage,
    user: dict = Depends(get_current_user),
):
    """Move one item along, optionally recording what was decided."""
    await _require_admin(user["id"])
    if body.status not in STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {', '.join(STATUSES)}",
        )
    async with privileged_connection() as conn:
        ok = await set_feedback_status(
            conn, feedback_id, status=body.status, admin_note=body.admin_note
        )
    if not ok:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"updated": True}
