"""Onboarding router — first-run language choice, placement, and setup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.onboarding import (
    CEFR_ORDER,
    MAX_ADAPTIVE_ITEMS,
    adaptive_next,
    complete_onboarding,
    estimate_level,
    get_placement_answers,
    get_status,
    sample_placement_items,
)
from backend.repositories.pool import rls_connection
from backend.services.nlp import validate_answer_async
from backend.services.nlp.base import AnswerResult

router = APIRouter()

# Below this many graded items, a placement test isn't meaningful — the client
# falls back to self-reported level.
MIN_PLACEMENT_ITEMS = 4
# Answers the NLP layer judges correct (or sloppy-but-right) count as a pass.
_PASSING = {AnswerResult.CORRECT, AnswerResult.CORRECT_SLOPPY}


class PlacementAnswer(BaseModel):
    id: str
    input: str


class ScorePlacement(BaseModel):
    answers: list[PlacementAnswer]


class AdaptiveHistory(BaseModel):
    history: list[PlacementAnswer] = Field(default_factory=list, max_length=32)


class CompleteOnboarding(BaseModel):
    language_id: str
    level: str
    batch_size: int | None = Field(default=None, ge=1, le=50)
    native_language: str | None = None
    # Signup plan: 'single' studies only this language (lower price),
    # 'all' unlocks every language. Payment wiring is WP16; the choice is
    # captured from day one.
    plan_scope: str | None = Field(default=None, pattern="^(single|all)$")


async def _language_code(conn, language_id: str) -> str | None:
    return await conn.fetchval("SELECT code FROM languages WHERE id = $1", language_id)


@router.get("/status")
async def onboarding_status(user: dict = Depends(get_current_user)):
    """Whether the user has finished onboarding (drives first-run routing)."""
    async with rls_connection(user["id"]) as conn:
        return await get_status(conn, user["id"])


@router.get("/placement/{language_id}")
async def get_placement(language_id: str, user: dict = Depends(get_current_user)):
    """Return placement prompts for a language, or signal self-report fallback.

    Each item shows an English definition; the learner types the word in the
    target language. Answers are validated server-side on submit.
    """
    async with rls_connection(user["id"]) as conn:
        items = await sample_placement_items(conn, language_id)
    if len(items) < MIN_PLACEMENT_ITEMS:
        # Not enough graded content to place — let the client self-report.
        return {"available": False, "items": []}
    return {"available": True, "items": items}


@router.post("/placement/{language_id}/next")
async def placement_next(
    language_id: str,
    body: AdaptiveHistory,
    user: dict = Depends(get_current_user),
):
    """Adaptive placement: grade the history so far, return the next item
    or the final estimate.

    Stateless — the client replays its answer history each round; the same
    history always walks the same deterministic level staircase (start A2,
    up on correct, down on a miss, stop early once the estimate is stable,
    hard cap at MAX_ADAPTIVE_ITEMS). Most learners finish in 5–8 items.
    """
    async with rls_connection(user["id"]) as conn:
        code = await _language_code(conn, language_id)
        if code is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Language not found"
            )
        pool = await sample_placement_items(conn, language_id)
        if len(pool) < MIN_PLACEMENT_ITEMS:
            return {
                "available": False, "done": True,
                "estimated_level": None, "per_level": {}, "asked": 0,
            }
        answers = await get_placement_answers(
            conn, language_id, [a.id for a in body.history]
        )

    pool_by_id = {it["id"]: it for it in pool}
    graded: list[tuple[dict, bool]] = []
    per_level: dict[str, list[int]] = {}
    for entry in body.history:
        item = pool_by_id.get(entry.id)
        key = answers.get(entry.id)
        if item is None or key is None or key["level"] is None:
            continue  # not one of ours — ignore rather than error
        try:
            result, _ = await validate_answer_async(
                code, entry.input, key["answer"], None
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail=f"Unsupported language: {code}"
            ) from exc
        correct = result in _PASSING
        graded.append((item, correct))
        tally = per_level.setdefault(key["level"], [0, 0])
        tally[1] += 1
        if correct:
            tally[0] += 1

    nxt = adaptive_next(pool, graded)
    if nxt is None:
        estimated = estimate_level(
            {lvl: (c, t) for lvl, (c, t) in per_level.items()}
        )
        return {
            "available": True, "done": True,
            "estimated_level": estimated,
            "per_level": {
                lvl: {"correct": c, "total": t}
                for lvl, (c, t) in per_level.items()
            },
            "asked": len(graded),
        }
    return {
        "available": True, "done": False,
        "item": nxt, "asked": len(graded), "max_items": MAX_ADAPTIVE_ITEMS,
    }


@router.post("/placement/{language_id}")
async def score_placement(
    language_id: str,
    body: ScorePlacement,
    user: dict = Depends(get_current_user),
):
    """Score submitted placement answers and estimate a starting level."""
    async with rls_connection(user["id"]) as conn:
        code = await _language_code(conn, language_id)
        if code is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Language not found"
            )
        answers = await get_placement_answers(
            conn, language_id, [a.id for a in body.answers]
        )

    # Tally correct/total per CEFR level using the language's NLP validator.
    per_level: dict[str, list[int]] = {}
    for answer in body.answers:
        item = answers.get(answer.id)
        if item is None or item["level"] is None:
            continue
        try:
            result, _ = await validate_answer_async(code, answer.input, item["answer"], None)
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail=f"Unsupported language: {code}"
            ) from exc
        tally = per_level.setdefault(item["level"], [0, 0])
        tally[1] += 1
        if result in _PASSING:
            tally[0] += 1

    estimated = estimate_level({lvl: (c, t) for lvl, (c, t) in per_level.items()})
    return {
        "estimated_level": estimated,
        "per_level": {lvl: {"correct": c, "total": t} for lvl, (c, t) in per_level.items()},
    }


@router.post("/complete")
async def complete(
    body: CompleteOnboarding,
    user: dict = Depends(get_current_user),
):
    """Finish onboarding: subscribe to content at/below the chosen level."""
    if body.level not in CEFR_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"level must be one of {list(CEFR_ORDER)}",
        )
    async with rls_connection(user["id"]) as conn:
        result = await complete_onboarding(
            conn, user["id"], body.language_id, body.level, batch_size=body.batch_size
        )
        if body.plan_scope:
            await conn.execute(
                """
                UPDATE user_profiles
                SET plan_scope = $2,
                    plan_language_id = CASE WHEN $2 = 'single'
                                            THEN $3::uuid ELSE NULL END
                WHERE id = $1
                """,
                user["id"], body.plan_scope, body.language_id,
            )
        if body.native_language:
            # Seed the tutor's memory with the learner's native language.
            from backend.repositories.tutor import (
                get_user_profile,
                upsert_user_profile,
            )
            profile = await get_user_profile(conn, user["id"])
            profile["native_language"] = body.native_language
            await upsert_user_profile(conn, user["id"], profile)
    return result
