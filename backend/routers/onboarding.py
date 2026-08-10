"""Onboarding router — first-run language choice, placement, and setup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.dependencies import get_current_user
from backend.repositories.contributor import get_roles, is_admin
from backend.repositories.onboarding import (
    CEFR_ORDER,
    MAX_ADAPTIVE_ITEMS,
    adaptive_next,
    complete_onboarding,
    estimate_level,
    get_placement_answers,
    get_status,
    lookup_word_glosses,
    placement_history,
    record_placement_attempt,
    sample_placement_items,
    set_learner_level,
)
from backend.repositories.pool import rls_connection
from backend.repositories.tutor import (
    get_language_profile,
    has_tutor_entitlement,
    log_tutor_usage,
    upsert_language_profile,
)
from backend.services.models import resolve_model
from backend.services.nlp import validate_answer_async
from backend.services.nlp.base import AnswerResult
from backend.services.placement_grade import blend_levels, shares_a_sense
from backend.services.rate_limit import tutor_chat_limiter
from backend.services.writing_baseline import MAX_SAMPLE_CHARS, assess_writing

router = APIRouter()

# Below this many graded items, a placement test isn't meaningful — the client
# falls back to self-reported level.
MIN_PLACEMENT_ITEMS = 4
# Answers the NLP layer judges correct (or sloppy-but-right) count as a pass.
_PASSING = {AnswerResult.CORRECT, AnswerResult.CORRECT_SLOPPY}
# The pass mark estimate_level applies at each CEFR level. Named here because
# the result screen now SHOWS the learner the rule that placed them.
PLACEMENT_THRESHOLD = 0.6


async def _grade_entries(
    user_id: str,
    code: str,
    language_id: str,
    entries: list[PlacementAnswer],
    answers: dict[str, dict],
) -> list[dict]:
    """Grade one placement run, item by item, with the evidence kept.

    Returns a row per gradable answer: what was asked, what the learner
    typed, what was expected, whether it counted and WHY. Two things depend
    on that last part. The learner sees it (a bare CEFR letter explains
    nothing about how it was reached), and a valid synonym is rescued here
    rather than silently costing a band:

    the seeds populate `vocabulary.alternatives` for almost nothing, so a
    vocabulary prompt used to accept exactly one headword. Any other real
    word with the same meaning graded as a miss, and the adaptive staircase
    steps DOWN on a miss — so answering "to walk" with the language's other
    word for walking could cost a whole level. A failed vocabulary answer
    is now looked up in the course's own word list, and counts when its
    gloss shares a whole sense with the prompt's.
    """
    graded: list[dict] = []
    for entry in entries:
        key = answers.get(entry.id)
        if key is None or key["level"] is None:
            continue  # not one of ours — ignore rather than error
        typed = (entry.input or "").strip()
        if not typed:
            # "I don't know" is a miss, but it is not a wrong ANSWER, and
            # showing it as one reads like the app misread them.
            graded.append({
                "id": entry.id, "kind": key.get("kind") or "vocabulary",
                "level": key["level"], "prompt": key.get("prompt"),
                "expected": key["answer"], "typed": "",
                "correct": False, "verdict": "skipped",
            })
            continue
        try:
            result, _ = await validate_answer_async(
                code, typed, key["answer"],
                {"answer_alternatives": key.get("alternatives") or []},
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail=f"Unsupported language: {code}"
            ) from exc
        correct = result in _PASSING
        graded.append({
            "id": entry.id, "kind": key.get("kind") or "vocabulary",
            "level": key["level"], "prompt": key.get("prompt"),
            "expected": key["answer"], "typed": typed,
            "correct": correct,
            "verdict": (
                "correct" if result is AnswerResult.CORRECT
                else "typo" if correct
                else "wrong"
            ),
        })

    # Synonym rescue, for the vocabulary misses only — one lookup, and none
    # at all on a clean run.
    rescuable = [
        g for g in graded
        if not g["correct"] and g["kind"] == "vocabulary"
        and g["typed"] and g["prompt"]
    ]
    if rescuable:
        async with rls_connection(user_id) as conn:
            glosses = await lookup_word_glosses(
                conn, language_id, [g["typed"] for g in rescuable]
            )
        for g in rescuable:
            gloss = glosses.get(g["typed"].lower())
            if gloss and shares_a_sense(g["prompt"], gloss):
                g["correct"] = True
                g["verdict"] = "synonym"
                # What they typed IS an answer to the question asked; say so
                # rather than leaving the expected word looking like a
                # correction.
                g["accepted_as"] = gloss
    return graded


def _tally(graded: list[dict]) -> tuple[dict[str, list[int]], dict[str, list[str]]]:
    """Per-level (correct, total) and the missed ids by kind."""
    per_level: dict[str, list[int]] = {}
    missed: dict[str, list[str]] = {"grammar": [], "vocabulary": []}
    for g in graded:
        tally = per_level.setdefault(g["level"], [0, 0])
        tally[1] += 1
        if g["correct"]:
            tally[0] += 1
        else:
            missed[g["kind"]].append(g["id"])
    return per_level, missed


def _breakdown(graded: list[dict]) -> list[dict]:
    """The per-question evidence the result screen shows (owner: "I want
    users to be able to understand why they received a rating")."""
    return [
        {
            "kind": g["kind"], "level": g["level"], "prompt": g["prompt"],
            "typed": g["typed"], "expected": g["expected"],
            "correct": g["correct"], "verdict": g["verdict"],
            "accepted_as": g.get("accepted_as"),
        }
        for g in graded
    ]


class PlacementAnswer(BaseModel):
    id: str
    input: str


class ScorePlacement(BaseModel):
    answers: list[PlacementAnswer]


class AdaptiveHistory(BaseModel):
    history: list[PlacementAnswer] = Field(default_factory=list, max_length=32)


class SetLevel(BaseModel):
    language_id: str
    level: str


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


@router.get("/placement/{language_id}/history")
async def placement_history_for_language(
    language_id: str, user: dict = Depends(get_current_user)
):
    """Has this learner placed in this language before, and how did it go?

    The dashboard asks this the first time a learner opens a language: no
    attempts means offer the test, attempts means show the retake entry in
    settings with the previous estimate to compare against.
    """
    async with rls_connection(user["id"]) as conn:
        return await placement_history(conn, user["id"], language_id)


@router.get("/placement/{language_id}")
async def get_placement(language_id: str, user: dict = Depends(get_current_user)):
    """Return placement prompts for a language, or signal self-report fallback.

    Each item shows an English definition; the learner types the word in the
    target language. Answers are validated server-side on submit.
    """
    async with rls_connection(user["id"]) as conn:
        history = await placement_history(conn, user["id"], language_id)
        items = await sample_placement_items(
            conn, language_id, variant=history["attempts"]
        )
    if len(items) < MIN_PLACEMENT_ITEMS:
        # Not enough graded content to place — let the client self-report.
        return {"available": False, "items": []}
    return {
        "available": True,
        "items": items,
        "attempt": history["attempts"] + 1,
        "previous_level": history["last_level"],
    }


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
        # The variant is the count of FINISHED attempts, and an attempt is
        # only recorded once the run completes — so every round of a single
        # run samples the same pool, and the next run steps to fresh items.
        history = await placement_history(conn, user["id"], language_id)
        pool = await sample_placement_items(
            conn, language_id, variant=history["attempts"]
        )
        if len(pool) < MIN_PLACEMENT_ITEMS:
            return {
                "available": False, "done": True,
                "estimated_level": None, "per_level": {}, "asked": 0,
            }
        answers = await get_placement_answers(
            conn, language_id, [a.id for a in body.history]
        )

    pool_by_id = {it["id"]: it for it in pool}
    rows = await _grade_entries(
        user["id"], code, language_id,
        [e for e in body.history if e.id in pool_by_id],
        answers,
    )
    # Which items they got WRONG — the half of the result the app used to
    # throw away, and the only thing that says what to work on.
    per_level, missed = _tally(rows)
    graded: list[tuple[dict, bool]] = [
        (pool_by_id[r["id"]], r["correct"]) for r in rows if r["id"] in pool_by_id
    ]

    nxt = adaptive_next(pool, graded)
    if nxt is None:
        estimated = estimate_level(
            {lvl: (c, t) for lvl, (c, t) in per_level.items()}
        )
        async with rls_connection(user["id"]) as conn:
            await record_placement_attempt(
                conn, user["id"], language_id,
                estimated_level=estimated, items_asked=len(graded),
                per_level={
                    lvl: {"correct": c, "total": t}
                    for lvl, (c, t) in per_level.items()
                },
                missed_grammar_ids=missed["grammar"],
                missed_vocabulary_ids=missed["vocabulary"],
            )
        return {
            "available": True, "done": True,
            "estimated_level": estimated,
            "per_level": {
                lvl: {"correct": c, "total": t}
                for lvl, (c, t) in per_level.items()
            },
            "asked": len(graded),
            "attempt": history["attempts"] + 1,
            "previous_level": history["last_level"],
            # The evidence behind the letter (owner: "I want users to be
            # able to understand why they received a rating").
            "breakdown": _breakdown(rows),
            "threshold": PLACEMENT_THRESHOLD,
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

    # Tally correct/total per CEFR level using the language's NLP validator
    # (plus the synonym rescue — see _grade_entries).
    rows = await _grade_entries(
        user["id"], code, language_id, body.answers, answers
    )
    per_level, missed = _tally(rows)

    estimated = estimate_level({lvl: (c, t) for lvl, (c, t) in per_level.items()})
    async with rls_connection(user["id"]) as conn:
        previous = await placement_history(conn, user["id"], language_id)
        await record_placement_attempt(
            conn, user["id"], language_id,
            estimated_level=estimated, items_asked=len(body.answers),
            per_level={
                lvl: {"correct": c, "total": t}
                for lvl, (c, t) in per_level.items()
            },
            missed_grammar_ids=missed["grammar"],
            missed_vocabulary_ids=missed["vocabulary"],
        )
    return {
        "estimated_level": estimated,
        "per_level": {lvl: {"correct": c, "total": t} for lvl, (c, t) in per_level.items()},
        "attempt": previous["attempts"] + 1,
        "previous_level": previous["last_level"],
        "breakdown": _breakdown(rows),
        "threshold": PLACEMENT_THRESHOLD,
    }


class WritingSample(BaseModel):
    language_id: str
    language_code: str = Field(min_length=2, max_length=8)
    text: str = Field(min_length=1, max_length=MAX_SAMPLE_CHARS)
    # The staircase result this sample follows, when it was taken as the
    # final question of a placement run. Blended into the verdict below.
    quiz_level: str | None = None


async def _writing_assessment_available(conn, user_id: str, language_id: str) -> bool:
    """Token guard (owner): the writing assessment spends a model call, so
    it's only offered to accounts with a tutor entitlement (paid or
    owner-granted) — or in dev-mock, where no key is spent.

    Admins are always offered it: the owner runs the API key, and gating
    their own testing surface behind a plan they don't hold is how the
    recommendations feature stayed invisible to the person building it.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return True
    if not settings.anthropic_api_key:
        return False
    if is_admin(await get_roles(conn, user_id)):
        return True
    return await has_tutor_entitlement(conn, user_id, language_id)


@router.get("/writing-sample/availability")
async def writing_sample_availability(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Whether the optional write-something baseline is offered to this
    account (drives whether onboarding shows the textarea at all)."""
    async with rls_connection(user["id"]) as conn:
        available = await _writing_assessment_available(
            conn, user["id"], language_id
        )
    return {"available": available}


@router.post("/writing-sample")
async def writing_sample(
    body: WritingSample,
    user: dict = Depends(get_current_user),
):
    """Assess an optional free-writing sample and use it as the level
    baseline (owner request): one small model call returns a CEFR estimate,
    an encouraging note, and up to 3 focus structures. The result also
    PRIMES the tutor's language profile (_writing_baseline + Active Focus),
    which the assessment tiers feed to the Tutor and Reader — so the AI
    surfaces start at the learner's level instead of cold at A1."""
    async with rls_connection(user["id"]) as conn:
        if not await _writing_assessment_available(
            conn, user["id"], body.language_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The writing assessment isn't available on this account.",
            )
        language_name = await conn.fetchval(
            "SELECT name FROM languages WHERE id = $1", body.language_id
        )
    if language_name is None:
        raise HTTPException(status_code=404, detail="Unknown language.")
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — slow down a moment.",
        )

    result, usage = await assess_writing(
        body.language_code, language_name, body.text
    )

    async with rls_connection(user["id"]) as conn:
        lang = await get_language_profile(conn, user["id"], body.language_id)
        profile = lang["profile"]
        profile["_writing_baseline"] = {
            "level": result["level"],
            "notes": result["notes"],
        }
        # Seed Active Focus from the sample only when the tutor hasn't set
        # its own yet — the tutor's live judgement always outranks a
        # one-shot baseline.
        if result["focus"] and not profile.get("_active_focus"):
            profile["_active_focus"] = [
                {"structure": s, "reason": "from your writing sample"}
                for s in result["focus"]
            ]
        await upsert_language_profile(
            conn, user["id"], body.language_id, profile
        )
        await log_tutor_usage(
            conn, user["id"], body.language_id,
            resolve_model("semantic_check", body.language_code),
            usage=usage, kind="writing_baseline",
        )
    # Taken as the final question of a placement run, the sample doesn't
    # merely sit beside the quiz — it decides, within a band (owner: the
    # writing sample "is the best way to determine placement"). See
    # services/placement_grade.blend_levels for why it's clamped.
    return {
        **result,
        "quiz_level": body.quiz_level,
        "blended_level": blend_levels(body.quiz_level, result["level"]),
    }


@router.put("/level")
async def set_level(
    body: SetLevel,
    user: dict = Depends(get_current_user),
):
    """Change the learner's level after onboarding (Settings → Your level).

    Re-seats which decks feed Learn with SET semantics: raising the level
    adds the missing decks, lowering removes the ones above it. Cards
    already learned and their history are never touched.
    """
    if body.level not in CEFR_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"level must be one of {list(CEFR_ORDER)}",
        )
    async with rls_connection(user["id"]) as conn:
        return await set_learner_level(
            conn, user["id"], body.language_id, body.level
        )


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
