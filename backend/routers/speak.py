"""Speak router — conversation practice (docs/plans/speak.md, stage 1).

Costs ride the tutor allowance, the way Reader and Gym do: one turn counts
as one message. The end-of-session summary is logged kind='summary', which
tracks its cost without charging the learner for finishing — being shown
what you got wrong should never be the thing you run out of.
"""

from __future__ import annotations

import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.assessment import get_assessment_summary
from backend.repositories.pool import rls_connection
from backend.repositories.speak import (
    SpeakUnavailableError,
    append_turn,
    end_session,
    get_session,
    list_recent_sessions,
    list_turns,
    start_session,
    tables_ready,
)
from backend.repositories.tutor import log_tutor_usage
from backend.routers.tutor import _get_allowance, _reject_if_unavailable
from backend.services.generate import generation_available
from backend.services.rate_limit import tutor_chat_limiter
from backend.services.speak import (
    MAX_TOPIC_CHARS,
    MAX_TURN_CHARS,
    speak_turn,
    summarize_speak_session,
)
from backend.services.tutor import resolve_tutor_model

logger = logging.getLogger("speak")
router = APIRouter()

# Stage 1 ships flow only. The column and this pattern already allow
# 'coach' so an old session's mode still reads back once stage 3 lands.
_MODES = "^(flow)$"


class StartRequest(BaseModel):
    language_id: str
    language_code: str = Field(min_length=2, max_length=8)
    mode: str = Field(default="flow", pattern=_MODES)
    topic: str | None = Field(default=None, max_length=MAX_TOPIC_CHARS)


class TurnRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=MAX_TURN_CHARS)


class EndRequest(BaseModel):
    session_id: str


_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Speak isn't available on this server yet",
)


async def _language(conn, language_id: str) -> tuple[str, str, str | None]:
    """(display name, code, admin model override) for the course."""
    row = await conn.fetchrow(
        "SELECT name, code, tutor_model FROM languages WHERE id = $1",
        language_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Unknown language")
    return row["name"], row["code"], row["tutor_model"]


async def _support_language(conn, user_id: str) -> str | None:
    """The language to write corrections IN. None → English."""
    code = await conn.fetchval(
        "SELECT support_locale FROM user_profiles WHERE id = $1", user_id
    )
    if not code or code == "en":
        return None
    return await conn.fetchval(
        "SELECT name FROM languages WHERE code = $1", code
    ) or code


@router.get("/status")
async def speak_status(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Whether Speak can run here, plus the caller's allowance meter.

    Reports unavailable — rather than failing later — when the migration
    hasn't been applied, so the UI hides the entry instead of offering a
    conversation that cannot be saved.
    """
    if not generation_available():
        return {"available": False, "allowance": None, "sessions": []}
    async with rls_connection(user["id"]) as conn:
        if not await tables_ready(conn):
            return {"available": False, "allowance": None, "sessions": []}
        try:
            sessions = await list_recent_sessions(conn, user["id"], language_id)
        except SpeakUnavailableError:
            return {"available": False, "allowance": None, "sessions": []}
    allowance = await _get_allowance(user["id"], language_id)
    return {"available": True, "allowance": allowance, "sessions": sessions}


@router.post("/start")
async def start(
    body: StartRequest,
    user: dict = Depends(get_current_user),
):
    """Open a session. No model call — and so no allowance draw — until the
    learner actually says something."""
    if not generation_available():
        raise _UNAVAILABLE
    allowance = await _get_allowance(user["id"], body.language_id)
    _reject_if_unavailable(allowance)
    topic = (body.topic or "").strip() or None
    try:
        async with rls_connection(user["id"]) as conn:
            session_id = await start_session(
                conn, user["id"], body.language_id, body.mode, topic
            )
    except SpeakUnavailableError as exc:
        raise _UNAVAILABLE from exc
    return {"session_id": session_id, "mode": body.mode, "topic": topic}


@router.post("/turn")
async def turn(
    body: TurnRequest,
    user: dict = Depends(get_current_user),
):
    """One exchange: they say something, the partner answers.

    Errors noticed this turn are stored but never returned — flow mode shows
    them only in the end-of-session summary. The client cannot leak what the
    learner is not meant to see yet if it is never sent.

    The session, not the request, decides which course this is: a client
    that passed its own language_id could point a session at another
    course's model and level.
    """
    if not generation_available():
        raise _UNAVAILABLE
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Say something first")

    try:
        async with rls_connection(user["id"]) as conn:
            session = await get_session(conn, user["id"], body.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Unknown session")
            if session["ended_at"]:
                raise HTTPException(
                    status_code=409, detail="That session is already finished"
                )
            language_id = session["language_id"]
            history = await list_turns(conn, body.session_id)
            language_name, code, override_model = await _language(
                conn, language_id
            )
            support_language = await _support_language(conn, user["id"])
            learner = await get_assessment_summary(
                conn, user["id"], language_id, depth="reading"
            )
    except SpeakUnavailableError as exc:
        raise _UNAVAILABLE from exc

    allowance = await _get_allowance(user["id"], language_id)
    _reject_if_unavailable(allowance)
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You're sending messages too fast — slow down a moment.",
        )

    model = resolve_tutor_model(code, override_model)
    try:
        result, usage = await speak_turn(
            language_name,
            learner["level"],
            [
                {"learner_text": t["learner_text"],
                 "partner_text": t["partner_text"]}
                for t in history
            ],
            text,
            topic=session["topic"],
            support_language=support_language,
            model=model,
        )
    except ValueError as exc:
        logger.error("Speak turn came back malformed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="That didn't come through — say it again",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Your partner is busy — try again in a moment",
        ) from exc
    except anthropic.APIError as exc:
        logger.error("Anthropic API error (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speak is temporarily unavailable",
        ) from exc

    async with rls_connection(user["id"]) as conn:
        await log_tutor_usage(
            conn, user["id"], language_id, model, usage=usage
        )
        await append_turn(
            conn, body.session_id, len(history), text,
            result["reply"], result["errors"],
        )

    used_after = None if allowance["unlimited"] else (allowance["used"] or 0) + 1
    return {
        "reply": result["reply"],
        "turn_index": len(history),
        "allowance": {
            **allowance,
            "used": used_after,
            "remaining": (
                None if allowance["unlimited"] or allowance["limit"] is None
                else max(0, allowance["limit"] - used_after)
            ),
        },
    }


@router.post("/end")
async def end(
    body: EndRequest,
    user: dict = Depends(get_current_user),
):
    """Finish the session and return the breakdown.

    Deliberately NOT gated on the allowance. Someone who has just spent
    their last message on a conversation must still be told what they got
    wrong — the summary is the payoff for the turns they already paid for,
    and a session with no errors costs nothing at all.
    """
    try:
        async with rls_connection(user["id"]) as conn:
            session = await get_session(conn, user["id"], body.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Unknown session")
            # Re-ending returns the stored breakdown rather than paying for
            # a second pass over the same transcript.
            if session["ended_at"] and session["summary"]:
                return {"summary": session["summary"], "already_ended": True}
            turns = await list_turns(conn, body.session_id)
            language_name, code, override_model = await _language(
                conn, session["language_id"]
            )
            support_language = await _support_language(conn, user["id"])
    except SpeakUnavailableError as exc:
        raise _UNAVAILABLE from exc

    errors = [e for t in turns for e in (t["errors"] or [])]
    model = resolve_tutor_model(code, override_model)
    summary, usage = await summarize_speak_session(
        language_name,
        [{"learner_text": t["learner_text"], "partner_text": t["partner_text"]}
         for t in turns],
        errors,
        support_language=support_language,
        model=model,
    )

    async with rls_connection(user["id"]) as conn:
        if usage:
            await log_tutor_usage(
                conn, user["id"], session["language_id"], model,
                usage=usage, kind="summary",
            )
        await end_session(conn, body.session_id, summary)
    return {"summary": summary, "already_ended": False}
