"""Write router — handwriting practice (docs/plans/handwriting.md, Phase 1).

Free write: the learner writes on a canvas, the client sends a PNG of the
ink with the text they were asked to write, and a vision-capable model
reads it. Costs ride the tutor allowance the way Speak's turns do — one
assessment is one message, logged kind='write'. The letter-level and
word-level stroke matching of later phases runs on the device and never
comes through here.
"""
from __future__ import annotations

import json
import logging

import anthropic
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel

from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection
from backend.repositories.profile import effective_support_locale
from backend.repositories.strokes import list_exemplars, list_glyphs, manifest
from backend.repositories.tutor import log_tutor_usage
from backend.repositories.write import (
    adapt_enabled,
    baseline_prompts,
    baseline_state,
    habit_counts,
    hand_profile,
    keep_sample,
    known_forms,
    note_habits,
    record_attempt,
    record_baseline,
    record_verdict,
    reference_samples,
    reset_hand,
    sentence_prompts,
    set_adapt,
    word_prompts,
)
from backend.routers.tutor import _get_allowance, _reject_if_unavailable
from backend.services.generate import generation_available
from backend.services.ink_method import summarize_method
from backend.services.models import resolve_model
from backend.services.rate_limit import tutor_chat_limiter
from backend.services.scripts import alphabet_for, script_of, styles_of
from backend.services.write_assess import (
    MAX_EXPECTED_CHARS,
    MAX_IMAGE_BYTES,
    assess_handwriting,
)

logger = logging.getLogger("write")
router = APIRouter()

_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Write isn't available here yet",
)
_STYLES = {"print", "cursive"}
# The strokes ride along as JSON text; a sentence resampled by the client
# is a few kilobytes. The cap refuses only something that is not strokes.
MAX_STROKES_BYTES = 200_000


def _parse_strokes(raw: str | None):
    """The canvas's strokes, or None. Never a reason to refuse a Check."""
    if not raw or len(raw) > MAX_STROKES_BYTES:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, list) else None


async def _language(conn, language_id: str) -> tuple[str, str, str | None]:
    row = await conn.fetchrow(
        "SELECT name, code, tutor_model FROM languages WHERE id = $1",
        language_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Unknown language")
    return row["name"], row["code"], row["tutor_model"]


async def _support_language(conn, user_id: str) -> tuple[str | None, str | None]:
    """(locale code, language name) the notes are written in; (None, None)
    means English — the same rule Speak's corrections follow."""
    code = await effective_support_locale(conn, user_id)
    if not code:
        return None, None
    name = await conn.fetchval(
        "SELECT name FROM languages WHERE code = $1", code
    )
    return code, (name or code)


@router.get("/status")
async def write_status(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """Whether the assessor can run here, plus the caller's allowance meter.
    The canvas and the neatness panel work regardless — only Check needs
    the model — so the page opens either way and says which half is off."""
    if not generation_available():
        return {"available": False, "allowance": None}
    allowance = await _get_allowance(user["id"], language_id)
    return {"available": True, "allowance": allowance}


@router.get("/prompts")
async def prompts(
    language_id: str,
    kind: str = "sentence",
    limit: int = 10,
    user: dict = Depends(get_current_user),
):
    """Things to write: sentences to translate (own cards first, then the
    course's beginner lines) or the learner's own words."""
    if kind not in ("sentence", "word"):
        raise HTTPException(status_code=422, detail="kind must be sentence or word")
    async with rls_connection(user["id"]) as conn:
        locale, _ = await _support_language(conn, user["id"])
        fetch = sentence_prompts if kind == "sentence" else word_prompts
        items = await fetch(conn, user["id"], language_id, locale, limit)
    return {"kind": kind, "items": items}


@router.post("/assess")
async def assess(
    image: UploadFile = File(...),
    language_id: str = Form(...),
    expected: str | None = Form(default=None),
    kind: str = Form(default="sentence"),
    style: str | None = Form(default=None),
    strokes: str | None = Form(default=None),
    user: dict = Depends(get_current_user),
):
    """Read one canvas and say what it says, whether that is right, and how
    legible it is. The verdict is logged; the ink is kept only as a sample
    of the writer's hand, and only with their toggle on."""
    stroke_data = _parse_strokes(strokes)
    method = summarize_method(stroke_data) if stroke_data else {}
    if not generation_available():
        raise _UNAVAILABLE
    if kind not in ("sentence", "word", "free"):
        raise HTTPException(status_code=422, detail="kind must be sentence, word or free")
    if style is not None and style not in _STYLES:
        raise HTTPException(status_code=422, detail="style must be print or cursive")
    expected = (expected or "").strip() or None
    if expected and len(expected) > MAX_EXPECTED_CHARS:
        raise HTTPException(status_code=422, detail="That text is too long to write in one go")
    if (image.content_type or "") not in ("image/png", "image/webp", "image/jpeg"):
        raise HTTPException(status_code=422, detail="Send the canvas as a PNG")
    # Bounded read, as Speak's transcribe does: one byte past the cap is
    # enough to know a photo of a page (or a mis-wired client) is coming.
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="That image is too large — send the canvas, not a photo",
        )
    if len(data) < 100:
        raise HTTPException(status_code=422, detail="Write something first")

    async with rls_connection(user["id"]) as conn:
        language_name, code, override_model = await _language(conn, language_id)
        _, support_language = await _support_language(conn, user["id"])
        # The writer's own hand, if they let the reader learn it: a few
        # confirmed samples as references, and the forms they have said
        # are fine. Off, or unmigrated, and this is exactly Phase 1.
        adapt = await adapt_enabled(conn, user["id"])
        references = (await reference_samples(conn, user["id"], language_id)
                      if adapt else [])
        habits = ((await hand_profile(conn, user["id"], language_id))["habits"]
                  if adapt else [])
        known = known_forms(habits)

    allowance = await _get_allowance(user["id"], language_id)
    _reject_if_unavailable(allowance)
    if not await tutor_chat_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You're checking too fast — slow down a moment.",
        )

    # A reader, not a drafter: the assessment task rides the chat tier
    # (vision needs it) and honours the per-language override like the
    # tutor does.
    model = resolve_model("write_assess", code, override_model)
    try:
        result, usage = await assess_handwriting(
            data, language_name, expected,
            support_language=support_language, style=style, model=model,
            references=references, known=known, method=method or None,
        )
    except ValueError as exc:
        logger.error("Write assessment came back malformed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="That didn't come through — try again",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The reader is busy — try again in a moment",
        ) from exc
    except anthropic.APIError as exc:
        logger.error("Anthropic API error (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Write is temporarily unavailable",
        ) from exc

    async with rls_connection(user["id"]) as conn:
        await log_tutor_usage(
            conn, user["id"], language_id, model, usage=usage, kind="write",
        )
        await record_attempt(conn, user["id"], language_id, kind, expected, result)
        again: dict[str, int] = {}
        if adapt:
            # "Your д again — third time": how often each noted letter
            # has been noted before, read BEFORE this check adds to it.
            again = habit_counts(habits, [n["letter"] for n in result["letterform_notes"]])
            # The reader's notes count against their letters (a habit is a
            # note that keeps coming back); a read the reader was sure of
            # and that matched is worth keeping as a sample even before the
            # writer confirms anything — a low-confidence read never is,
            # and a sure match also counts as a right read (§12.1).
            await note_habits(conn, user["id"], language_id,
                              result["letterform_notes"], confirmed_ok=False,
                              legibility=result["legibility"])
            if (expected and result["matches_target"]
                    and result["confidence"] == "high"):
                await keep_sample(conn, user["id"], language_id, expected,
                                  data, confirmed=False, strokes=stroke_data)
                await record_verdict(conn, user["id"], language_id,
                                     read=result["transcription"], wrote=expected)

    used_after = None if allowance["unlimited"] else (allowance["used"] or 0) + 1
    return {
        **result,
        "expected": expected,
        "adapt": adapt,
        "again": again,
        "allowance": {
            **allowance,
            "used": used_after,
            "remaining": (
                None if allowance["unlimited"] or allowance["limit"] is None
                else max(0, allowance["limit"] - used_after)
            ),
        },
    }


@router.post("/confirm")
async def confirm(
    image: UploadFile = File(...),
    language_id: str = Form(...),
    text: str = Form(...),
    letters: str | None = Form(default=None),
    strokes: str | None = Form(default=None),
    read: str | None = Form(default=None),
    source: str = Form(default="confirm"),
    user: dict = Depends(get_current_user),
):
    """"I wrote this": the writer's own word over the reader's. The canvas
    becomes a confirmed sample of their hand, the letters the reader had
    flagged are marked known-fine, and — with *read*, what the reader had
    said — the verdict is recorded: right if the texts agree, otherwise
    wrong with every misread letter counted (§12.1). Costs nothing — no
    model call — and does nothing with the toggle off."""
    text = (text or "").strip()
    if not text or len(text) > MAX_EXPECTED_CHARS:
        raise HTTPException(status_code=422, detail="Say what you wrote")
    if (image.content_type or "") not in ("image/png", "image/webp", "image/jpeg"):
        raise HTTPException(status_code=422, detail="Send the canvas as a PNG")
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES or len(data) < 100:
        raise HTTPException(status_code=422, detail="Send the canvas as a PNG")
    flagged = [x.strip() for x in (letters or "").split(",") if x.strip()][:8]
    async with rls_connection(user["id"]) as conn:
        await _language(conn, language_id)
        if not await adapt_enabled(conn, user["id"]):
            return {"kept": False, "reason": "adapt_off", "samples": 0}
        kept = await keep_sample(conn, user["id"], language_id, text, data,
                                 confirmed=True, strokes=_parse_strokes(strokes),
                                 source="baseline" if source == "baseline" else "confirm")
        if flagged:
            await note_habits(
                conn, user["id"], language_id,
                [{"letter": x, "note": ""} for x in flagged], confirmed_ok=True)
        verdict = (await record_verdict(conn, user["id"], language_id,
                                        read=read, wrote=text)
                   if read is not None else None)
    return {"kept": True, "samples": kept,
            **({"right": verdict["right"], "misread": verdict["misread"],
                "readout": verdict["readout"]} if verdict else {})}


class AdaptRequest(BaseModel):
    adapt: bool


class ResetRequest(BaseModel):
    language_id: str | None = None


@router.get("/profile")
async def profile(language_id: str, user: dict = Depends(get_current_user)):
    """The hand profile for one language: the toggle, the habits, how many
    samples are kept. `available` is false without migration 20261019."""
    async with rls_connection(user["id"]) as conn:
        return await hand_profile(conn, user["id"], language_id)


@router.put("/profile")
async def set_profile(body: AdaptRequest, user: dict = Depends(get_current_user)):
    """The account toggle. Off deletes everything kept, in every language."""
    async with rls_connection(user["id"]) as conn:
        await set_adapt(conn, user["id"], body.adapt)
    return {"adapt": body.adapt}


@router.post("/profile/reset")
async def reset_profile(body: ResetRequest, user: dict = Depends(get_current_user)):
    """Forget what the reader learned — one language, or all of them."""
    async with rls_connection(user["id"]) as conn:
        await reset_hand(conn, user["id"], body.language_id)
    return {"reset": body.language_id or "all"}


class BaselineDone(BaseModel):
    language_id: str
    covered: int | None = None
    total: int | None = None
    neatness: dict | None = None


@router.get("/baseline")
async def baseline(language_id: str, user: dict = Depends(get_current_user)):
    """The baseline session's prompts (§12.2): eight of the course's
    beginner sentences chosen to show every letter in every form, with
    how much of the script they cover; whether a session may run today;
    when the last one was."""
    async with rls_connection(user["id"]) as conn:
        _, code, _ = await _language(conn, language_id)
        locale, _ = await _support_language(conn, user["id"])
        state = await baseline_state(conn, user["id"], language_id)
        adapt = await adapt_enabled(conn, user["id"])
        picked = await baseline_prompts(conn, user["id"], language_id, code, locale)
    return {**state, "adapt": adapt, "allowed": state["allowed"] and adapt,
            "prompts": picked["items"], "covered": picked["covered"],
            "total": picked["total"]}


@router.post("/baseline/done")
async def baseline_done(body: BaselineDone, user: dict = Depends(get_current_user)):
    """The writer finished the eight: stamp the profile."""
    async with rls_connection(user["id"]) as conn:
        await _language(conn, body.language_id)
        stats = await record_baseline(
            conn, user["id"], body.language_id,
            {"covered": body.covered, "total": body.total}
            if body.covered is not None else None,
            neatness=body.neatness)
    return {"baseline_at": stats.get("baseline_at"), "baselines": stats.get("baselines", 0)}


@router.get("/alphabet")
async def alphabet(language_id: str, user: dict = Depends(get_current_user)):
    """The course's script, the styles it is written in, and its letters
    with their forms — the frame of the stroke library."""
    async with rls_connection(user["id"]) as conn:
        _, code, _ = await _language(conn, language_id)
    script = script_of(code)
    return {"code": code, "script": script, "styles": styles_of(script),
            "letters": alphabet_for(code)}


@router.get("/manifest")
async def write_manifest(language_id: str, user: dict = Depends(get_current_user)):
    """How much of the course's stroke library exists — per style, authored
    and reviewed — so the Write page knows whether guided Letters can run."""
    async with rls_connection(user["id"]) as conn:
        _, code, _ = await _language(conn, language_id)
        return await manifest(conn, code, script_of(code))


@router.get("/glyphs")
async def glyphs(language_id: str, style: str | None = None,
                 user: dict = Depends(get_current_user)):
    """The reviewed stroke templates a learner traces (and the reviewed
    exemplar sentences they watch). Drafts never reach here."""
    async with rls_connection(user["id"]) as conn:
        _, code, _ = await _language(conn, language_id)
        script = script_of(code)
        return {"script": script,
                "glyphs": await list_glyphs(conn, script, style, reviewed_only=True),
                "exemplars": await list_exemplars(conn, script, style, reviewed_only=True)}

