"""Tutor router — AI tutoring grounded in the user's study data and memory."""

from __future__ import annotations

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection
from backend.repositories.tutor import (
    get_language_profile,
    get_study_stats,
    get_user_profile,
    get_weak_areas,
    has_tutor_entitlement,
    upsert_language_profile,
    upsert_user_profile,
)
from backend.services.rate_limit import tutor_chat_limiter
from backend.services.tutor import (
    _LANGUAGE_BRIEFS,
    merge_remembered,
    summarize_session,
    tutor_chat,
)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class TutorChatRequest(BaseModel):
    language_id: str
    language_code: str
    messages: list[ChatMessage] = Field(min_length=1)


class SessionEndRequest(BaseModel):
    language_id: str
    language_code: str
    messages: list[ChatMessage] = Field(min_length=1)


async def _check_entitlement(user_id: str, language_id: str) -> bool:
    settings = get_settings()
    if settings.tutor_free_access:
        return True
    async with rls_connection(user_id) as conn:
        return await has_tutor_entitlement(conn, user_id, language_id)


def _tutor_configured() -> bool:
    """True when the tutor can run — a real API key, or dev mock mode."""
    settings = get_settings()
    return bool(settings.anthropic_api_key) or getattr(
        settings, "tutor_dev_mock", False
    )


def _require_configured(language_code: str) -> None:
    if not _tutor_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI tutor is not configured on this server",
        )
    if language_code not in _LANGUAGE_BRIEFS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No tutor available for language: {language_code}",
        )


@router.get("/status")
async def tutor_status(
    language_id: str,
    language_code: str,
    user: dict = Depends(get_current_user),
):
    """Report whether the tutor is available and the user is entitled to it."""
    available = _tutor_configured() and language_code in _LANGUAGE_BRIEFS
    entitled = await _check_entitlement(user["id"], language_id) if available else False
    return {"available": available, "entitled": entitled}


@router.post("/chat")
async def chat(
    body: TutorChatRequest,
    user: dict = Depends(get_current_user),
):
    """Run one tutor conversation turn.

    Grounds the tutor in the user's study stats, weak cards, and durable
    learner memory, then persists any facts the tutor's `remember` tool
    surfaced this turn.
    """
    _require_configured(body.language_code)
    if not await _check_entitlement(user["id"], body.language_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Tutor access requires a subscription for this language",
        )
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You're sending messages too fast — slow down a moment.",
        )

    async with rls_connection(user["id"]) as conn:
        weak_areas = await get_weak_areas(conn, user["id"], body.language_id)
        study_stats = await get_study_stats(conn, user["id"], body.language_id)
        user_profile = await get_user_profile(conn, user["id"])
        lang = await get_language_profile(conn, user["id"], body.language_id)

    try:
        reply, remembered = await tutor_chat(
            body.language_code,
            [m.model_dump() for m in body.messages],
            weak_areas,
            user_profile=user_profile,
            language_profile=lang["profile"],
            session_summary=lang["session_summary"],
            study_stats=study_stats,
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

    if remembered:
        new_user, new_lang = merge_remembered(
            user_profile, lang["profile"], remembered
        )
        async with rls_connection(user["id"]) as conn:
            if new_user != user_profile:
                await upsert_user_profile(conn, user["id"], new_user)
            if new_lang != lang["profile"]:
                await upsert_language_profile(
                    conn, user["id"], body.language_id, new_lang
                )

    return {"reply": reply, "remembered": len(remembered)}


@router.post("/session/end")
async def end_session(
    body: SessionEndRequest,
    user: dict = Depends(get_current_user),
):
    """Summarize a finished session into durable memory.

    Called by the client on an explicit "End session" action or after the
    conversation goes idle. Runs the cheaper summarizer model off the chat
    hot path and folds the result into the learner's profiles + summary.
    """
    _require_configured(body.language_code)
    if not await _check_entitlement(user["id"], body.language_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Tutor access requires a subscription for this language",
        )

    async with rls_connection(user["id"]) as conn:
        user_profile = await get_user_profile(conn, user["id"])
        lang = await get_language_profile(conn, user["id"], body.language_id)

    try:
        result = await summarize_session(
            body.language_code,
            [m.model_dump() for m in body.messages],
            user_profile=user_profile,
            language_profile=lang["profile"],
            prior_summary=lang["session_summary"],
        )
    except anthropic.APIError:
        # Summarization is best-effort — never fail the user's session-end.
        return {"summarized": False}

    new_user = {**user_profile, **(result.get("user_profile_updates") or {})}
    new_lang = {**lang["profile"], **(result.get("language_profile_updates") or {})}
    summary = result.get("session_summary") or lang["session_summary"]

    async with rls_connection(user["id"]) as conn:
        await upsert_user_profile(conn, user["id"], new_user)
        await upsert_language_profile(
            conn,
            user["id"],
            body.language_id,
            new_lang,
            session_summary=summary,
            touch_session=True,
        )

    return {"summarized": True}
