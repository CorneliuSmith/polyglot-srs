"""Review router — due cards, FSRS submission, NLP validation, and learn."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.cards import (
    add_grammar_learn_batch,
    add_learn_batch,
    add_mixed_learn_batch,
    confirm_learn_batch,
    get_card_detail,
    get_card_details_bulk,
    get_cram_cards,
    get_deck_items,
    get_deck_preview,
    get_due_cards,
    get_generation_context,
    get_learn_decks,
    get_vocab_item,
    reset_deck_progress,
    reset_language_progress,
    set_deck_subscription,
    update_card_srs,
)
from backend.repositories.contributor import add_drill
from backend.repositories.fsrs_weights import get_effective_params
from backend.repositories.pool import privileged_connection, rls_connection
from backend.repositories.review import add_card_feedback, insert_review_log
from backend.repositories.tutor import log_tutor_usage
from backend.services.allowance import get_allowance, reject_if_unavailable
from backend.services.fsrs import (
    AnswerResult,
    CardState,
    fsrs_review,
    map_answer_to_quality,
    map_answer_to_rating,
)
from backend.services.generate import generate_drills, generation_available
from backend.services.models import resolve_model
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
    # The exact sentence the learner was shown (sentences rotate per review);
    # logged so failures are analyzable per-sentence, not just per-card.
    prompt_sentence: str | None = Field(default=None, max_length=1000)


class ValidateAnswerRequest(BaseModel):
    language_code: str
    user_input: str
    correct_answer: str
    card_context: dict | None = None


class LearnRequest(BaseModel):
    language_id: str
    card_type: str = "vocabulary"
    # Learn from one specific deck (CEFR level) instead of everything
    # subscribed — the deck rows on the dashboard pass this.
    level: str | None = None


class CardFeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ConfirmLearnRequest(BaseModel):
    card_ids: list[str] = Field(min_length=1, max_length=100)


async def _support_locale(conn, user_id: str) -> str | None:
    """The learner's chosen support language (localizes English cards)."""
    return await conn.fetchval(
        "SELECT support_locale FROM user_profiles WHERE id = $1", user_id
    )


@router.get("/due")
async def get_due(
    language_id: str,
    limit: int = 20,
    card_type: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Return due cards for the user's active language, sorted by next_review ASC.

    *limit* is the learner's chosen session size (clamped 1–100).
    *card_type* optionally scopes the session: 'grammar' or 'vocabulary'
    (the dashboard's Grammar Only / Vocab Only reviews).
    """
    if card_type is not None and card_type not in ("vocabulary", "grammar"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="card_type must be 'vocabulary' or 'grammar'",
        )
    limit = max(1, min(limit, 100))
    async with rls_connection(user["id"]) as conn:
        support = await _support_locale(conn, user["id"])
        cards = await get_due_cards(
            conn, language_id, limit=limit, support_locale=support,
            card_type=card_type,
        )
    return cards


MAX_CRAM_POINTS = 12


@router.get("/cram")
async def cram(
    point_ids: str,
    count: int | None = None,
    user: dict = Depends(get_current_user),
):
    """Quick-Cram (WP13f): ungraded practice cards for a set of grammar points.

    *point_ids* is a comma-separated list (an item plus its Related set).
    *count* (Gym) is the total number of questions the learner asked for — the
    session round-robins across the chosen forms and draws that many drills
    (capped at what's authored, up to 100). Omitted for the Related/point crams,
    which keep the small default. Nothing here touches SRS state — the cards
    carry synthetic ids the submit endpoint would reject.
    """
    import uuid as _uuid

    ids = [p.strip() for p in point_ids.split(",") if p.strip()]
    if not ids or len(ids) > MAX_CRAM_POINTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"point_ids must list 1–{MAX_CRAM_POINTS} grammar points",
        )
    try:
        for p in ids:
            _uuid.UUID(p)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="point_ids must be UUIDs",
        ) from None
    async with rls_connection(user["id"]) as conn:
        support = await _support_locale(conn, user["id"])
        return await get_cram_cards(
            conn, ids, support_locale=support, count=count
        )


class GymGenerateRequest(BaseModel):
    point_ids: list[str] = Field(min_length=1)


# Limits (owner: "try to limit them"): one generate call tops up a few forms
# with a handful of drills each and costs ONE message from the learner's
# allowance — on-demand variety is cheap and bounded, not a firehose. The
# baseline seeded corpus (forms x multiple drills = hundreds) is the main path.
GYM_GEN_MAX_POINTS = 3
GYM_GEN_PER_POINT = 4


@router.post("/gym/generate")
async def gym_generate(
    body: GymGenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Learner-triggered: generate a few EXTRA drill variations for the chosen
    Gym forms, drawing from the learner's tutor allowance (WP41).

    Cost scales with the work: ONE message per FORM topped up (not per drill),
    capped to what the allowance actually covers so a run can never overdraw —
    if you ask for 3 forms with 2 messages left, we top up 2 and stop. Generated
    drills are verified (maker-checker), tagged source='ai', and added to the
    shared pool WITHOUT de-certifying the form. A human still vets 'ai' drills.
    """
    if not generation_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="On-demand generation isn't enabled.",
        )
    ids = list(dict.fromkeys(body.point_ids))[:GYM_GEN_MAX_POINTS]

    async with rls_connection(user["id"]) as conn:
        contexts = [
            c for c in [await get_generation_context(conn, pid) for pid in ids] if c
        ]
    if not contexts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such forms.")

    language_id = contexts[0]["language_id"]
    # Draws the learner's allowance — reject early when it's exhausted, before
    # spending anything (the UI warns before it ever gets here).
    allowance = await get_allowance(user["id"], language_id)
    reject_if_unavailable(allowance)

    # Cost = one message per form, but never spend more than what's left.
    if allowance["unlimited"]:
        contexts = contexts[:GYM_GEN_MAX_POINTS]
    else:
        contexts = contexts[: min(len(contexts), allowance["remaining"])]

    model = resolve_model("grammar_maker", contexts[0]["language_code"])
    generated = 0
    charged = 0
    async with privileged_connection() as conn:
        for ctx in contexts:
            drills = await generate_drills(
                {
                    "title": ctx["title"],
                    "explanation": ctx["explanation"],
                    "examples": ctx["examples"],
                },
                GYM_GEN_PER_POINT, ctx["language_name"], ctx["language_code"],
            )
            for d in drills:
                # created_by = the requester: they get these drills in their own
                # Gym right away, but they stay private to them until a reviewer
                # approves them for everyone.
                await add_drill(
                    conn, ctx["point_id"], d["sentence"], d["answer"],
                    d.get("translation"), d.get("hint"),
                    source="ai", origin_detail=model, decertify=False,
                    created_by=user["id"],
                )
                generated += 1
            # One message per form topped up (regardless of drill yield).
            await log_tutor_usage(conn, user["id"], language_id, model, kind="gym_gen")
            charged += 1

    remaining = (
        None if allowance["unlimited"]
        else max(0, allowance["remaining"] - charged)
    )
    return {
        "generated": generated,
        "charged": charged,
        "remaining": remaining,
        "unlimited": allowance["unlimited"],
    }


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
        support = await _support_locale(conn, user["id"])
        detail = await get_card_detail(conn, card_id, support_locale=support)
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
            "SELECT language_id, stability, difficulty, state, interval, "
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

        # Resolve the most specific fitted weights for this user + language.
        params = await get_effective_params(conn, user["id"], str(row["language_id"]))
        result = fsrs_review(card, rating, elapsed_days, now=now, params=params)

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
            prompt_sentence=body.prompt_sentence,
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


@router.get("/decks")
async def decks(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Return the language's learn decks (per-level lists) with progress.

    Bunpro-style deck rows: each content list with its learnable total, the
    user's started count, and whether it's in their learn queue (subscribed).
    """
    async with rls_connection(user["id"]) as conn:
        return {"decks": await get_learn_decks(conn, user["id"], language_id)}


@router.get("/decks/{list_id}/preview")
async def deck_preview(
    list_id: str,
    user: dict = Depends(get_current_user),
):
    """Peek inside a deck (its first items) before adding it to the queue."""
    async with rls_connection(user["id"]) as conn:
        preview = await get_deck_preview(conn, list_id)
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return preview


class DeckSubscription(BaseModel):
    subscribed: bool


@router.get("/decks/{list_id}/items")
async def deck_items(
    list_id: str,
    user: dict = Depends(get_current_user),
):
    """The deck browser: every item in the deck, in path order, with ids
    so each row can open its detail view."""
    async with rls_connection(user["id"]) as conn:
        locale = await _support_locale(conn, user["id"])
        listing = await get_deck_items(conn, list_id, support_locale=locale)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return listing


@router.get("/vocab/{vocab_id}")
async def vocab_item(
    vocab_id: str,
    user: dict = Depends(get_current_user),
):
    """Read-only vocabulary detail for the deck browser (word, definition,
    Forms panel, sample sentences) — no review card required."""
    async with rls_connection(user["id"]) as conn:
        locale = await _support_locale(conn, user["id"])
        item = await get_vocab_item(conn, vocab_id, locale)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")
    return item


@router.post("/decks/{list_id}/subscription")
async def deck_subscription(
    list_id: str,
    body: DeckSubscription,
    user: dict = Depends(get_current_user),
):
    """Add or remove a deck from the learn queue.

    Removing a deck only stops NEW cards — already-learned cards keep their
    review schedule, so no progress is ever lost.
    """
    async with rls_connection(user["id"]) as conn:
        ok = await set_deck_subscription(conn, user["id"], list_id, body.subscribed)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return {"subscribed": body.subscribed}


@router.delete("/decks/{list_id}/progress")
async def reset_deck(
    list_id: str,
    user: dict = Depends(get_current_user),
):
    """Reset the learner's progress for one deck, review history included.

    Destructive and permanent: the frontend confirms before calling. Deck
    subscriptions and user-authored content are untouched.
    """
    async with rls_connection(user["id"]) as conn:
        result = await reset_deck_progress(conn, user["id"], list_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return result


@router.delete("/progress")
async def reset_progress(
    language_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Reset ALL of the learner's studies — one language, or everything.

    Destructive and permanent (cards + review history). Notes, personal
    sentences, and deck subscriptions survive.
    """
    async with rls_connection(user["id"]) as conn:
        return await reset_language_progress(conn, user["id"], language_id)


@router.post("/learn")
async def learn(
    body: LearnRequest,
    user: dict = Depends(get_current_user),
):
    """Add a batch of new cards (vocabulary or grammar) from subscribed lists.

    Reads batch_size from the user's profile (default 5 if no profile row).
    Returns the count of added cards, their new user_card IDs, and a `lessons`
    payload — the full teachable content of each new item (explanation,
    examples, references) so the client can PRESENT the material before the
    first quiz, instead of quizzing on something never seen.
    """
    # 'both' interleaves grammar + vocabulary in one session (whole queue).
    if body.card_type not in ("vocabulary", "grammar", "both"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="card_type must be 'vocabulary', 'grammar', or 'both'",
        )
    async with rls_connection(user["id"]) as conn:
        # Read batch_size from user_profiles (default 5 if no row)
        profile_row = await conn.fetchrow(
            "SELECT batch_size FROM user_profiles WHERE id = $1",
            user["id"],
        )
        batch_size = int(profile_row["batch_size"]) if profile_row else 5

        # Learning from a specific deck is a deliberate act — subscribe the
        # user to that list if they weren't already (otherwise the batch
        # query, which draws from subscriptions, would return nothing). Only
        # single-type learns carry a level; 'both' always draws the queue.
        if body.level and body.card_type in ("vocabulary", "grammar"):
            await conn.execute(
                """
                INSERT INTO user_content_subscriptions (user_id, content_list_id)
                SELECT $1, id FROM content_lists
                WHERE language_id = $2 AND list_type = $3 AND level = $4
                ON CONFLICT (user_id, content_list_id) DO NOTHING
                """,
                user["id"],
                body.language_id,
                body.card_type,
                body.level,
            )

        if body.card_type == "both":
            result = await add_mixed_learn_batch(
                conn, user["id"], body.language_id, batch_size
            )
        elif body.card_type == "grammar":
            result = await add_grammar_learn_batch(
                conn, user["id"], body.language_id, batch_size, body.level
            )
        else:
            result = await add_learn_batch(
                conn, user["id"], body.language_id, batch_size, body.level
            )

        # Bulk-fetch the lesson payloads: per-card fetching is an N+1 that
        # makes "Preparing your new items…" hang for seconds on a pooled
        # (high-latency) database connection.
        support = await _support_locale(conn, user["id"])
        details = await get_card_details_bulk(
            conn, result["items"], support_locale=support
        )
        lessons = [
            {"card_id": card_id, **details[card_id]}
            for card_id in result["items"]
            if card_id in details
        ]

    return {**result, "lessons": lessons}


@router.post("/learn/confirm")
async def confirm_learn(
    body: ConfirmLearnRequest,
    user: dict = Depends(get_current_user),
):
    """Activate cards after the lesson walkthrough (teach-before-quiz gate).

    The learn batch creates cards suspended; nothing reaches the review queue
    until the learner has actually paged through the lessons and the client
    confirms. Abandoned walkthroughs stay suspended and are re-taught by the
    next learn batch.
    """
    async with rls_connection(user["id"]) as conn:
        confirmed = await confirm_learn_batch(conn, user["id"], body.card_ids)
    return {"confirmed": confirmed}
