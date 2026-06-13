"""Tutor router — AI tutoring chat grounded in the user's SRS failure data."""

from __future__ import annotations

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection
from backend.repositories.tutor import get_weak_areas, has_tutor_entitlement
from backend.services.tutor import _LANGUAGE_BRIEFS, tutor_chat

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class TutorChatRequest(BaseModel):
    language_id: str
    language_code: str
    messages: list[ChatMessage] = Field(min_length=1)


async def _check_entitlement(user_id: str, language_id: str) -> bool:
    settings = get_settings()
    if settings.tutor_free_access:
        return True
    async with rls_connection(user_id) as conn:
        return await has_tutor_entitlement(conn, user_id, language_id)


@router.get("/status")
async def tutor_status(
    language_id: str,
    language_code: str,
    user: dict = Depends(get_current_user),
):
    """Report whether the tutor is available and the user is entitled to it."""
    settings = get_settings()
    available = bool(settings.anthropic_api_key) and language_code in _LANGUAGE_BRIEFS
    entitled = await _check_entitlement(user["id"], language_id) if available else False
    return {"available": available, "entitled": entitled}


@router.post("/chat")
async def chat(
    body: TutorChatRequest,
    user: dict = Depends(get_current_user),
):
    """Run one tutor conversation turn.

    The tutor's system prompt is grounded in the user's weakest cards for the
    language, queried fresh each turn so coaching tracks today's failures.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI tutor is not configured on this server",
        )
    if body.language_code not in _LANGUAGE_BRIEFS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No tutor available for language: {body.language_code}",
        )
    if not await _check_entitlement(user["id"], body.language_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Tutor access requires a subscription for this language",
        )

    async with rls_connection(user["id"]) as conn:
        weak_areas = await get_weak_areas(conn, user["id"], body.language_id)

    try:
        reply = await tutor_chat(
            body.language_code,
            [m.model_dump() for m in body.messages],
            weak_areas,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Tutor is busy — try again in a moment",
        ) from exc
    except anthropic.APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Tutor is temporarily unavailable",
        ) from exc

    return {"reply": reply}
