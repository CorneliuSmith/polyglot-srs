"""Languages router — the public language list, and the learner's ask for
their support language to be filled on a course."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.dependencies import get_current_user
from backend.repositories.languages import get_all_languages
from backend.repositories.pool import get_pool, rls_connection
from backend.repositories.profile import effective_support_locale
from backend.repositories.translation_requests import add_request, my_request
from backend.services.rate_limit import translation_request_limiter
from backend.services.tts import voice_for

router = APIRouter()


@router.get("/")
async def list_languages():
    """Return all available languages. No auth required.

    has_tts says whether a neural voice exists for the language — the UI
    uses it to show the "we're collecting real recordings" note on
    languages (Jamaican Patois) where no synthetic voice can exist.
    """
    languages = await get_all_languages(get_pool())
    for lang in languages:
        lang["has_tts"] = voice_for(lang["code"]) is not None
    return languages


async def _ask_state(conn, user_id: str, language_id: str) -> dict:
    """What the settings page needs to render the ask, for ONE course.

    The locale is resolved server-side from the profile, never taken from
    the client: a learner asks for the language they are actually reading
    help in, and there is nothing to spoof.

    `can_ask` is deliberately narrow. English is the source, so there is
    nothing to fill; a course already draining its backlog has nothing to
    ask for; and a database without migration 20261024 answers
    available=false rather than offering a button that cannot save.
    """
    locale = await effective_support_locale(conn, user_id)
    lang = await conn.fetchrow(
        "SELECT name, auto_translate_enabled FROM languages WHERE id = $1",
        language_id,
    )
    state = {
        "available": False,
        "locale": locale,
        "locale_name": None,
        "auto_translate_enabled": None,
        "can_ask": False,
        "request": None,
    }
    if lang is None or locale is None:
        return state
    state["auto_translate_enabled"] = bool(lang["auto_translate_enabled"])
    state["locale_name"] = await conn.fetchval(
        "SELECT name FROM languages WHERE code = $1", locale
    ) or locale
    state["request"] = await my_request(conn, user_id, language_id, locale)
    # available answers "can this server store an ask at all", which is a
    # different question from "should this learner see one".
    state["available"] = state["request"] is not None or await _requests_ready(conn)
    state["can_ask"] = (
        state["available"]
        and not state["auto_translate_enabled"]
        and state["request"] is None
    )
    return state


async def _requests_ready(conn) -> bool:
    from backend.repositories.translation_requests import requests_table_present

    return await requests_table_present(conn)


@router.get("/translation-request")
async def translation_request_state(
    language_id: str, user: dict = Depends(get_current_user)
):
    """Whether this learner can ask for their support language on this
    course, and whether they already have."""
    async with rls_connection(user["id"]) as conn:
        return await _ask_state(conn, user["id"], language_id)


class TranslationRequest(BaseModel):
    language_id: str
    note: str | None = None


@router.post("/translation-request")
async def create_translation_request(
    body: TranslationRequest, user: dict = Depends(get_current_user)
):
    """Ask for the course's backlog to be filled into this learner's
    support language.

    The ask is evidence for a budget decision, not a promise: enabling a
    course costs the operator real money per word, which is why the toggle
    exists at all. What the learner is already getting — the demand lane
    and the baseline corpus — happens either way, and the settings copy
    says so rather than implying the course is untranslated.
    """
    if not await translation_request_limiter.allow(str(user["id"])):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — try again later",
        )
    async with rls_connection(user["id"]) as conn:
        state = await _ask_state(conn, user["id"], body.language_id)
        if state["locale"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="English help needs no translation",
            )
        if state["auto_translate_enabled"]:
            # Nothing to ask for: answer with the state so the client can
            # simply re-render rather than show an error for good news.
            return {**state, "result": "already_on"}
        result = await add_request(
            conn, user["id"], body.language_id, state["locale"], body.note
        )
        if result == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Translation requests need migration 20261024 applied — "
                    "run `supabase db push` (check /api/health/schema)"
                ),
            )
        return {**await _ask_state(conn, user["id"], body.language_id),
                "result": result}
