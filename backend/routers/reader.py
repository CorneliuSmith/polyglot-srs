"""Reader router (WP21) — generate, shelf, and explain.

Costs ride the tutor allowance: one generation or one explanation counts
as one tutor message, logged through the same usage/cost pipeline the
admin cost panel already reads.
"""

from __future__ import annotations

import logging
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.reader import (
    get_learner_model,
    get_reading,
    list_readings,
    log_grammar_gaps,
    save_reading,
)
from backend.repositories.tutor import (
    get_language_profile,
    get_weak_areas,
    log_tutor_usage,
)
from backend.routers.tutor import _get_allowance, _reject_if_unavailable
from backend.services.rate_limit import tutor_chat_limiter
from backend.services.reader import (
    MAX_TOPIC_CHARS,
    explain_sentence,
    generate_reading,
)
from backend.services.tutor import resolve_tutor_model

logger = logging.getLogger("reader")
router = APIRouter()


class GenerateRequest(BaseModel):
    language_id: str
    language_code: str = Field(min_length=2, max_length=8)
    topic: str = Field(min_length=1, max_length=MAX_TOPIC_CHARS)


class ExplainRequest(BaseModel):
    sentence_index: int = Field(ge=0)


async def _support_gloss_locale(conn, user_id: str, language_code: str) -> str:
    """Glosses follow the same rule as definitions: English targets render
    help in the learner's support locale; everything else glosses in English."""
    if language_code != "en":
        return "en"
    row = await conn.fetchrow(
        "SELECT support_locale FROM user_profiles WHERE id = $1", user_id
    )
    locale = row["support_locale"] if row else None
    return locale or "en"


@router.post("/generate")
async def generate(
    body: GenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Write the learner a level-locked text on their topic."""
    allowance = await _get_allowance(user["id"], body.language_id)
    _reject_if_unavailable(allowance)
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — slow down a moment.",
        )

    async with rls_connection(user["id"]) as conn:
        learner = await get_learner_model(conn, user["id"], body.language_id)
        # The tutor's Active Focus and weak items feed re-exposure.
        weak = await get_weak_areas(conn, user["id"], body.language_id, limit=6)
        lang_profile = await get_language_profile(conn, user["id"], body.language_id)
        gloss_locale = await _support_gloss_locale(
            conn, user["id"], body.language_code
        )
        override_model = await conn.fetchval(
            "SELECT tutor_model FROM languages WHERE id = $1", body.language_id
        )
    learner["weak_words"] = [w.get("word") for w in weak if w.get("word")]
    learner["focus"] = [
        f.get("structure")
        for f in (lang_profile["profile"].get("_active_focus") or [])
        if isinstance(f, dict) and f.get("structure")
    ]
    model = resolve_tutor_model(body.language_code, override_model)

    try:
        reading, usage = await generate_reading(
            body.language_code, body.topic.strip(), learner,
            gloss_locale=gloss_locale, model=model,
        )
    except ValueError as exc:
        logger.error("Reading generation invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The reading came back malformed — try again",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The writer is busy — try again in a moment",
        ) from exc
    except anthropic.APIError as exc:
        logger.error("Anthropic API error (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Reading generation is temporarily unavailable",
        ) from exc

    async with rls_connection(user["id"]) as conn:
        await log_tutor_usage(
            conn, user["id"], body.language_id, model, usage=usage
        )
        reading_id = await save_reading(
            conn, user["id"], body.language_id, body.topic.strip(),
            reading, learner["level"],
        )

    # Curriculum-gap collection (owner request): structures the path
    # doesn't cover get logged operator-side. Best-effort — a gap-log
    # hiccup must never cost the learner their reading.
    try:
        example = reading["sentences"][0]["text"] if reading["sentences"] else None
        async with privileged_connection() as conn:
            logged = await log_grammar_gaps(
                conn, body.language_id, reading.get("structures") or [], example
            )
        if logged:
            logger.info("Reader logged %d grammar gap(s)", logged)
    except Exception as exc:  # noqa: BLE001
        logger.error("Grammar gap logging failed: %s", exc)

    used_after = None if allowance["unlimited"] else allowance["used"] + 1
    return {
        "id": reading_id,
        "reading": reading,
        "level": learner["level"],
        "allowance": {
            **allowance,
            "used": used_after,
            "remaining": (
                None if allowance["unlimited"]
                else max(0, allowance["limit"] - used_after)
            ),
        },
    }


@router.get("/readings")
async def shelf(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    async with rls_connection(user["id"]) as conn:
        readings = await list_readings(conn, user["id"], language_id)
    return {"readings": readings}


@router.get("/readings/{reading_id}")
async def one_reading(
    reading_id: UUID,
    user: dict = Depends(get_current_user),
):
    async with rls_connection(user["id"]) as conn:
        reading = await get_reading(conn, user["id"], str(reading_id))
    if reading is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No such reading"
        )
    return reading


@router.post("/readings/{reading_id}/explain")
async def explain(
    reading_id: UUID,
    body: ExplainRequest,
    user: dict = Depends(get_current_user),
):
    """Stage 3: explain one sentence's grammar (allowance-gated)."""
    async with rls_connection(user["id"]) as conn:
        reading = await get_reading(conn, user["id"], str(reading_id))
    if reading is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No such reading"
        )
    sentences = reading["sentences"]
    if body.sentence_index >= len(sentences):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sentence_index out of range",
        )

    # The reading knows its language only via language_id — resolve code +
    # allowance together.
    async with rls_connection(user["id"]) as conn:
        row = await conn.fetchrow(
            """
            SELECT l.id AS language_id, l.code, l.tutor_model
            FROM readings r JOIN languages l ON r.language_id = l.id
            WHERE r.id = $1
            """,
            str(reading_id),
        )
    allowance = await _get_allowance(user["id"], str(row["language_id"]))
    _reject_if_unavailable(allowance)
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — slow down a moment.",
        )

    sentence = sentences[body.sentence_index]
    model = resolve_tutor_model(row["code"], row["tutor_model"])
    try:
        explanation, usage = await explain_sentence(
            row["code"], sentence["text"], sentence.get("translation", ""),
            reading.get("level") or "A1", model=model,
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API error (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Explanations are temporarily unavailable",
        ) from exc

    async with rls_connection(user["id"]) as conn:
        await log_tutor_usage(
            conn, user["id"], str(row["language_id"]), model, usage=usage
        )
    return {"explanation": explanation}
