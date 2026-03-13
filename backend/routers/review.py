"""Review router — due cards and SM-2 submission."""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_current_user
from backend.repositories.cards import get_due_cards, update_card_srs
from backend.repositories.pool import rls_connection
from backend.repositories.review import insert_review_log
from backend.services.srs import (
    AnswerResult,
    CardState,
    map_answer_to_quality,
    sm2_update,
)

router = APIRouter()

ANSWER_RESULT_MAP = {
    "correct": AnswerResult.CORRECT,
    "correct_sloppy": AnswerResult.CORRECT_SLOPPY,
    "wrong_form": AnswerResult.WRONG_FORM,
    "wrong": AnswerResult.WRONG,
}


class SubmitReview(BaseModel):
    card_id: str
    answer_result: str
    time_taken_ms: int | None = None


@router.get("/due")
async def get_due(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Return due cards for the user's active language, sorted by next_review ASC."""
    async with rls_connection(user["id"]) as conn:
        cards = await get_due_cards(conn, language_id)
    return cards


@router.post("/submit")
async def submit_review(
    body: SubmitReview,
    user: dict = Depends(get_current_user),
):
    """Apply SM-2 update to a card and record the review log entry."""
    ar_enum = ANSWER_RESULT_MAP.get(body.answer_result)
    if ar_enum is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid answer_result: {body.answer_result}. "
            f"Must be one of: {list(ANSWER_RESULT_MAP.keys())}",
        )

    quality = map_answer_to_quality(ar_enum)

    async with rls_connection(user["id"]) as conn:
        # Fetch current card state
        row = await conn.fetchrow(
            "SELECT ease_factor, interval, repetitions, streak, lapses "
            "FROM user_cards WHERE id = $1",
            body.card_id,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found",
            )

        state = CardState(
            ease_factor=float(row["ease_factor"]),
            interval=row["interval"],
            repetitions=row["repetitions"],
            streak=row["streak"],
            lapses=row["lapses"],
        )

        ease_before = state.ease_factor
        interval_before = state.interval

        result = sm2_update(state, quality)

        await update_card_srs(conn, body.card_id, {
            "ease_factor": result.ease_factor,
            "interval": result.interval,
            "repetitions": result.repetitions,
            "streak": result.streak,
            "lapses": result.lapses,
            "next_review": result.next_review,
        })

        await insert_review_log(
            conn,
            user_id=user["id"],
            card_id=body.card_id,
            quality=quality,
            ease_before=ease_before,
            ease_after=result.ease_factor,
            interval_before=interval_before,
            interval_after=result.interval,
            time_taken_ms=body.time_taken_ms,
            answer_result=body.answer_result,
        )

    return {
        "next_review": result.next_review.isoformat(),
        "ease_factor": result.ease_factor,
        "interval": result.interval,
        "quality": quality,
    }
