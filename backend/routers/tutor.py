"""Tutor router — AI tutoring grounded in the user's study data and memory.

Access model (flat tiers, never billed per message):
  free accounts  — a monthly message allowance to genuinely try the tutor
  plus accounts  — flat subscription with a generous DAILY fair-use cap
  operator mode  — TUTOR_FREE_ACCESS=true bypasses limits entirely (demos)
Allowances are shown openly in the UI (/status returns the meter).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection
from backend.repositories.tutor import (
    count_tutor_messages,
    get_language_profile,
    get_study_stats,
    get_user_profile,
    get_weak_areas,
    has_tutor_entitlement,
    log_tutor_usage,
    upsert_language_profile,
    upsert_user_profile,
)
from backend.services.rate_limit import tutor_chat_limiter
from backend.services.tutor import (
    _LANGUAGE_BRIEFS,
    merge_remembered,
    summarize_session,
    tutor_chat,
    tutor_chat_stream,
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


async def _get_allowance(user_id: str, language_id: str) -> dict:
    """The caller's tutor allowance: tier, window usage, and reset time.

    Message counts are the only unit exposed — the flat tier price never
    depends on usage, and the UI shows exactly this payload.
    """
    settings = get_settings()
    if settings.tutor_free_access:
        return {
            "tier": "unlimited", "unlimited": True, "entitled": True,
            "limit": None, "used": 0, "remaining": None, "resets_at": None,
        }
    now = datetime.now(UTC)
    async with rls_connection(user_id) as conn:
        entitled = await has_tutor_entitlement(conn, user_id, language_id)
        if entitled:
            window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            resets_at = window_start + timedelta(days=1)
            limit = settings.tutor_plus_daily_messages
            tier = "plus"
        else:
            window_start = now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            resets_at = (window_start + timedelta(days=32)).replace(day=1)
            limit = settings.tutor_free_monthly_messages
            tier = "free"
        used = await count_tutor_messages(conn, user_id, window_start)
    return {
        "tier": tier, "unlimited": False, "entitled": entitled,
        "limit": limit, "used": used, "remaining": max(0, limit - used),
        "resets_at": resets_at.isoformat(),
    }


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
    """Report tutor availability plus the caller's allowance meter."""
    available = _tutor_configured() and language_code in _LANGUAGE_BRIEFS
    if not available:
        return {"available": False, "entitled": False, "allowance": None}
    allowance = await _get_allowance(user["id"], language_id)
    return {
        "available": True,
        "entitled": allowance["entitled"],
        "allowance": allowance,
    }


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
    allowance = await _get_allowance(user["id"], body.language_id)
    if not allowance["unlimited"] and allowance["remaining"] <= 0:
        # Flat pricing: hitting the cap never costs money — free users are
        # offered the upgrade, plus users just wait for the daily reset.
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "allowance_exhausted",
                "tier": allowance["tier"],
                "limit": allowance["limit"],
                "resets_at": allowance["resets_at"],
            },
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
        # WP15a: per-language model override (NULL = global default).
        model = await conn.fetchval(
            "SELECT tutor_model FROM languages WHERE id = $1", body.language_id
        )

    try:
        reply, remembered = await tutor_chat(
            body.language_code,
            [m.model_dump() for m in body.messages],
            weak_areas,
            user_profile=user_profile,
            language_profile=lang["profile"],
            session_summary=lang["session_summary"],
            study_stats=study_stats,
            model=model,
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

    settings = get_settings()
    async with rls_connection(user["id"]) as conn:
        await log_tutor_usage(
            conn, user["id"], body.language_id, model or settings.tutor_model
        )
        if remembered:
            new_user, new_lang = merge_remembered(
                user_profile, lang["profile"], remembered
            )
            if new_user != user_profile:
                await upsert_user_profile(conn, user["id"], new_user)
            if new_lang != lang["profile"]:
                await upsert_language_profile(
                    conn, user["id"], body.language_id, new_lang
                )

    used_after = None if allowance["unlimited"] else allowance["used"] + 1
    return {
        "reply": reply,
        "remembered": len(remembered),
        "allowance": {
            **allowance,
            "used": used_after,
            "remaining": (
                None if allowance["unlimited"]
                else max(0, allowance["limit"] - used_after)
            ),
        },
    }


@router.post("/chat/stream")
async def chat_stream(
    body: TutorChatRequest,
    user: dict = Depends(get_current_user),
):
    """Streaming tutor turn (WP9d): Server-Sent Events.

    Emits `data: {json}` lines — {"type":"delta","text"} chunks as the
    model writes, a rare {"type":"reset"} when streamed text belonged to a
    tool-use turn, and a final {"type":"done","reply","remembered",
    "allowance"} after persistence. Gating (allowance, rate limit) is
    identical to /chat.
    """
    _require_configured(body.language_code)
    allowance = await _get_allowance(user["id"], body.language_id)
    if not allowance["unlimited"] and allowance["remaining"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "allowance_exhausted",
                "tier": allowance["tier"],
                "limit": allowance["limit"],
                "resets_at": allowance["resets_at"],
            },
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
        model = await conn.fetchval(
            "SELECT tutor_model FROM languages WHERE id = $1", body.language_id
        )

    async def event_source():
        import json as _json

        settings = get_settings()
        try:
            async for event in tutor_chat_stream(
                body.language_code,
                [m.model_dump() for m in body.messages],
                weak_areas,
                user_profile=user_profile,
                language_profile=lang["profile"],
                session_summary=lang["session_summary"],
                study_stats=study_stats,
                model=model,
            ):
                if event["type"] == "done":
                    # Persist BEFORE the client sees "done" so a reload
                    # right after can't observe a half-recorded turn.
                    remembered = event.get("remembered") or []
                    async with rls_connection(user["id"]) as conn:
                        await log_tutor_usage(
                            conn, user["id"], body.language_id,
                            model or settings.tutor_model,
                        )
                        if remembered:
                            new_user, new_lang = merge_remembered(
                                user_profile, lang["profile"], remembered
                            )
                            if new_user != user_profile:
                                await upsert_user_profile(
                                    conn, user["id"], new_user
                                )
                            if new_lang != lang["profile"]:
                                await upsert_language_profile(
                                    conn, user["id"], body.language_id, new_lang
                                )
                    used_after = (
                        None if allowance["unlimited"] else allowance["used"] + 1
                    )
                    event = {
                        **event,
                        "remembered": len(remembered),
                        "allowance": {
                            **allowance,
                            "used": used_after,
                            "remaining": (
                                None if allowance["unlimited"]
                                else max(0, allowance["limit"] - used_after)
                            ),
                        },
                    }
                yield f"data: {_json.dumps(event)}\n\n"
        except ValueError as exc:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except anthropic.RateLimitError:
            yield (
                "data: "
                + _json.dumps({
                    "type": "error",
                    "message": "Tutor is busy — try again in a moment",
                })
                + "\n\n"
            )
        except anthropic.APIError:
            yield (
                "data: "
                + _json.dumps({
                    "type": "error",
                    "message": "Tutor is temporarily unavailable",
                })
                + "\n\n"
            )

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    # Anyone who actually chatted in the current window may summarize —
    # summarization is part of the message they already spent, not a new
    # spend. Blocks only callers who never talked to the tutor.
    allowance = await _get_allowance(user["id"], body.language_id)
    if not allowance["unlimited"] and allowance["used"] == 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No tutor session to summarize",
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
