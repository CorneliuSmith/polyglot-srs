"""Reader router (WP21) — generate, shelf, and explain.

Costs ride the tutor allowance: one generation or one explanation counts
as one tutor message, logged through the same usage/cost pipeline the
admin cost panel already reads.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.assessment import get_assessment_summary
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.profile import effective_support_locale
from backend.repositories.reader import (
    delete_reading,
    get_reading,
    list_readings,
    log_grammar_gaps,
    save_reading,
)
from backend.repositories.tutor import log_tutor_usage
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
    # Per-text options (bounded): how long, whose voice, how hard.
    length: str = Field(default="medium", pattern="^(short|medium|long)$")
    voice: str = Field(default="any", pattern="^(any|first|third|dialogue)$")
    # Relative (easier/level/stretch) or an explicit CEFR pin — the owner:
    # "add a1 - c2 levels as an option".
    complexity: str = Field(
        default="level",
        pattern="^(easier|level|stretch|A1|A2|B1|B2|C1|C2)$",
    )


class ExplainRequest(BaseModel):
    sentence_index: int = Field(ge=0)


async def _support_gloss_locale(conn, user_id: str, language_code: str) -> str:
    """Glosses follow the same rule as card content since #186: every course
    renders help in the learner's support locale — including the self-pair
    (Spanish-from-Spanish gets monolingual Spanish glosses, the way a
    learner's dictionary would)."""
    del language_code
    return await effective_support_locale(conn, user_id) or "en"


# Readings being written right now, one per user, OUTLIVING the request
# that started them. The synchronous shape died in production exactly the
# way recommendations did (see routers/recommendations.py _DRAFTS):
# DigitalOcean's gateway caps a request at about a minute, and a reading is
# no longer one model call — #285 grades every text and rewrites one that
# misses, so a C2 text is two full generations plus a grading pass. The
# owner's screenshot: "Couldn't write that one" on Theoretical Physics at
# C2, which is precisely the longest, slowest text the app can produce.
#
# The request now only STARTS the write; the page polls GET /generate/status
# until it lands. Nothing about the work changed — only who holds the
# connection while it happens.
_WRITES: dict[str, asyncio.Task] = {}
# The finished reading, waiting to be collected by the next poll.
_RESULTS: dict[str, dict] = {}
# Why the last write failed — served by the poll so the page can say what
# went wrong instead of spinning, and admins get the exception text.
_WRITE_ERRORS: dict[str, str] = {}


def _writing(user_id: str) -> bool:
    task = _WRITES.get(str(user_id))
    return task is not None and not task.done()


async def _write_reading(
    user_id: str,
    body: GenerateRequest,
    *,
    learner: dict,
    gloss_locale: str,
    model: str | None,
    allowance: dict,
    admin: bool,
) -> None:
    """The whole write, run as a background task: one model call (plus the
    contract grader, plus at most one rewrite), then save, log usage, and
    collect curriculum gaps. Every outcome lands somewhere the poll can see
    it — a task nobody awaits otherwise fails silently."""
    key = str(user_id)
    try:
        reading, usage = await generate_reading(
            body.language_code, body.topic.strip(), learner,
            gloss_locale=gloss_locale, model=model,
            options={
                "length": body.length,
                "voice": body.voice,
                "complexity": body.complexity,
            },
        )
        async with rls_connection(user_id) as conn:
            await log_tutor_usage(
                conn, user_id, body.language_id, model, usage=usage
            )
            reading_id = await save_reading(
                conn, user_id, body.language_id, body.topic.strip(),
                reading, learner["level"],
            )

        # Curriculum-gap collection (owner request): structures the path
        # doesn't cover get logged operator-side. Best-effort — a gap-log
        # hiccup must never cost the learner their reading.
        try:
            example = (
                reading["sentences"][0]["text"] if reading["sentences"] else None
            )
            async with privileged_connection() as conn:
                logged = await log_grammar_gaps(
                    conn, body.language_id,
                    reading.get("structures") or [], example,
                )
            if logged:
                logger.info("Reader logged %d grammar gap(s)", logged)
        except Exception as exc:  # noqa: BLE001
            logger.error("Grammar gap logging failed: %s", exc)

        used_after = None if allowance["unlimited"] else allowance["used"] + 1
        _RESULTS[key] = {
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
        _WRITE_ERRORS.pop(key, None)
    except anthropic.RateLimitError:
        _WRITE_ERRORS[key] = "The writer is busy — try again in a moment."
    except Exception as exc:  # noqa: BLE001 — surfaced by the poll, never lost
        logger.exception(
            "Reading generation failed for %s (%s, %s)",
            user_id, body.language_code, body.complexity,
        )
        msg = "Couldn't write that one — try again, or a different topic."
        if admin:
            msg += f" [{type(exc).__name__}: {exc}]"
        _WRITE_ERRORS[key] = msg
    finally:
        _WRITES.pop(key, None)


@router.post("/generate")
async def generate(
    body: GenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Start writing the learner a level-locked text on their topic.

    Runs the gates, then hands the model call to a background task and
    answers immediately: holding the connection through a graded,
    possibly-rewritten C2 text is what the gateway killed. The page polls
    /generate/status for the result.
    """
    allowance = await _get_allowance(user["id"], body.language_id)
    _reject_if_unavailable(allowance)
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — slow down a moment.",
        )
    # A write already running is joined, not doubled — an impatient second
    # tap must never spend a second generation.
    if _writing(user["id"]):
        return {"generating": True}

    async with rls_connection(user["id"]) as conn:
        # The 'reading' assessment tier: level, known words/structures, weak
        # words, and Active Focus — what level-locking a text needs, no more.
        learner = await get_assessment_summary(
            conn, user["id"], body.language_id, depth="reading"
        )
        gloss_locale = await _support_gloss_locale(
            conn, user["id"], body.language_code
        )
        override_model = await conn.fetchval(
            "SELECT tutor_model FROM languages WHERE id = $1", body.language_id
        )
    model = resolve_tutor_model(body.language_code, override_model)

    key = str(user["id"])
    _RESULTS.pop(key, None)
    _WRITE_ERRORS.pop(key, None)
    _WRITES[key] = asyncio.create_task(
        _write_reading(
            user["id"], body,
            learner=learner, gloss_locale=gloss_locale, model=model,
            allowance=allowance, admin=bool(user.get("is_admin")),
        )
    )
    return {"generating": True}


@router.get("/generate/status")
async def generate_status(user: dict = Depends(get_current_user)):
    """Has the text landed yet?

    Returns the finished reading exactly once — collecting it clears the
    slot, so a second poll after the page has it doesn't re-open a text the
    learner already closed.
    """
    key = str(user["id"])
    if key in _RESULTS:
        return {"generating": False, **_RESULTS.pop(key)}
    error = _WRITE_ERRORS.pop(key, None)
    if error:
        return {"generating": False, "error": error}
    return {"generating": _writing(user["id"])}


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


@router.delete("/readings/{reading_id}")
async def remove_reading(
    reading_id: UUID,
    user: dict = Depends(get_current_user),
):
    """Drop one reading from the shelf — housekeeping, owner request.

    Only the text goes. Words the learner saved out of it are their own
    cards now and stay: nothing links a card to the reading it came from,
    so deleting is genuinely just tidying. Idempotent from the client's
    point of view via the 404 (already gone reads the same as never
    yours), and RLS backs the ownership check independently.
    """
    async with rls_connection(user["id"]) as conn:
        deleted = await delete_reading(conn, user["id"], str(reading_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No such reading"
        )
    return {"deleted": True}


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
