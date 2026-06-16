"""Review router — due cards, FSRS submission, NLP validation, and learn."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.cards import (
    add_grammar_learn_batch,
    add_learn_batch,
    get_card_detail,
    get_due_cards,
    update_card_srs,
)
from backend.repositories.pool import rls_connection
from backend.repositories.review import add_card_feedback, insert_review_log
from backend.services.fsrs import (
    AnswerResult,
    CardState,
    fsrs_review,
    map_answer_to_quality,
    map_answer_to_rating,
)
from backend.services.nlp import validate_answer_async

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


class ValidateAnswerRequest(BaseModel):
    language_code: str
    user_input: str
    correct_answer: str
    card_context: dict | None = None


class LearnRequest(BaseModel):
    language_id: str
    card_type: str = "vocabulary"


class CardFeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


@router.get("/due")
async def get_due(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Return due cards for the user's active language, sorted by next_review ASC."""
    async with rls_connection(user["id"]) as conn:
        cards = await get_due_cards(conn, language_id)
    return cards


@router.get("/card/{card_id}/detail")
async def card_detail(
    card_id: str,
    user: dict = Depends(get_current_user),
):
    """Return the optional 'review this card' content (grammar/usage + examples).

    Powers the expandable panel shown after answering — lazy-loaded so it only
    costs a query when the learner chooses to dig in rather than just continue.
    """
    async with rls_connection(user["id"]) as conn:
        detail = await get_card_detail(conn, card_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )
    return detail


@router.post("/card/{card_id}/feedback")
async def submit_card_feedback(
    card_id: str,
    body: CardFeedbackRequest,
    user: dict = Depends(get_current_user),
):
    """Let a learner flag a problem with a card they're reviewing."""
    async with rls_connection(user["id"]) as conn:
        ok = await add_card_feedback(conn, user["id"], card_id, body.message.strip())
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return {"submitted": True}


@router.post("/submit")
async def submit_review(
    body: SubmitReview,
    user: dict = Depends(get_current_user),
):
    """Apply the FSRS update to a card and record the review log entry."""
    ar_enum = ANSWER_RESULT_MAP.get(body.answer_result)
    if ar_enum is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid answer_result: {body.answer_result}. "
            f"Must be one of: {list(ANSWER_RESULT_MAP.keys())}",
        )

    quality = map_answer_to_quality(ar_enum)
    rating = map_answer_to_rating(ar_enum)
    now = datetime.now(UTC)

    async with rls_connection(user["id"]) as conn:
        # Fetch current FSRS state
        row = await conn.fetchrow(
            "SELECT stability, difficulty, state, interval, "
            "repetitions, streak, lapses, last_review "
            "FROM user_cards WHERE id = $1",
            body.card_id,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found",
            )

        card = CardState(
            stability=float(row["stability"]) if row["stability"] is not None else None,
            difficulty=float(row["difficulty"]) if row["difficulty"] is not None else None,
            state=row["state"],
            repetitions=row["repetitions"],
            streak=row["streak"],
            lapses=row["lapses"],
        )
        # Days since the previous review drive the forgetting curve.
        elapsed_days = (
            (now - row["last_review"]).total_seconds() / 86400.0
            if row["last_review"] else 0.0
        )
        interval_before = row["interval"]

        result = fsrs_review(card, rating, elapsed_days, now=now)

        await update_card_srs(conn, body.card_id, {
            "stability": result.stability,
            "difficulty": result.difficulty,
            "state": result.state,
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
            answer_result=body.answer_result,
            interval_before=interval_before,
            interval_after=result.interval,
            stability_before=card.stability,
            stability_after=result.stability,
            difficulty_before=card.difficulty,
            difficulty_after=result.difficulty,
            time_taken_ms=body.time_taken_ms,
        )

    return {
        "next_review": result.next_review.isoformat(),
        "interval": result.interval,
        "stability": result.stability,
        "difficulty": result.difficulty,
        "state": result.state,
        "quality": quality,
    }


@router.post("/validate-answer")
async def validate_answer(
    body: ValidateAnswerRequest,
    user: dict = Depends(get_current_user),
):
    """Validate the user's typed answer using the language-specific NLP backend.

    Returns the AnswerResult enum name in lowercase and an optional feedback string.
    Returns HTTP 422 (not 500) when the language code has no registered backend.
    """
    try:
        answer_result, feedback = await validate_answer_async(
            body.language_code,
            body.user_input,
            body.correct_answer,
            body.card_context,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language: {body.language_code}",
        ) from exc

    return {
        "answer_result": answer_result.name.lower(),
        "feedback": feedback,
    }


@router.post("/learn")
async def learn(
    body: LearnRequest,
    user: dict = Depends(get_current_user),
):
    """Add a batch of new cards (vocabulary or grammar) from subscribed lists.

    Reads batch_size from the user's profile (default 5 if no profile row).
    Returns the count of added cards and their new user_card IDs.
    """
    if body.card_type not in ("vocabulary", "grammar"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="card_type must be 'vocabulary' or 'grammar'",
        )
    async with rls_connection(user["id"]) as conn:
        # Read batch_size from user_profiles (default 5 if no row)
        profile_row = await conn.fetchrow(
            "SELECT batch_size FROM user_profiles WHERE id = $1",
            user["id"],
        )
        batch_size = int(profile_row["batch_size"]) if profile_row else 5

        if body.card_type == "grammar":
            result = await add_grammar_learn_batch(
                conn, user["id"], body.language_id, batch_size
            )
        else:
            result = await add_learn_batch(
                conn, user["id"], body.language_id, batch_size
            )

    return result
