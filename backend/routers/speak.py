"""Speak router — conversation practice (docs/plans/speak.md, stage 1).

Costs ride the tutor allowance, the way Reader and Gym do: one turn counts
as one message, logged kind='speak'. The end-of-session summary is logged
kind='speak_summary', which tracks its cost without charging the learner
for finishing — being shown what you got wrong should never be the thing
you run out of.
"""

from __future__ import annotations

import base64
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
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.assessment import get_assessment_summary
from backend.repositories.pool import rls_connection
from backend.repositories.profile import effective_support_locale
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
from backend.repositories.speech import record_speech_event
from backend.repositories.tutor import log_tutor_usage
from backend.routers.tutor import _get_allowance, _reject_if_unavailable
from backend.services.generate import generation_available
from backend.services.rate_limit import (
    stt_limiter,
    tts_limiter,
    tutor_chat_limiter,
)
from backend.services.speak import (
    MAX_TOPIC_CHARS,
    MAX_TURN_CHARS,
    speak_opening,
    speak_turn,
    summarize_speak_session,
)
from backend.services.stt import (
    MAX_AUDIO_BYTES,
    locale_for,
    transcribe,
    transcription_available,
)
from backend.services.tts import SLOW_RATE, synthesize, voice_for
from backend.services.tutor import resolve_tutor_model

logger = logging.getLogger("speak")
router = APIRouter()

# flow  — corrections wait for the summary.
# coach — ONE correction per turn, then the conversation moves on.
_MODES = "^(flow|coach)$"


class StartRequest(BaseModel):
    language_id: str
    language_code: str = Field(min_length=2, max_length=8)
    mode: str = Field(default="flow", pattern=_MODES)
    topic: str | None = Field(default=None, max_length=MAX_TOPIC_CHARS)


class TurnRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=MAX_TURN_CHARS)
    # How long they spoke, when they spoke. Absent on a typed turn — the
    # summary's speaking share counts measured audio only, rather than
    # inventing a duration from a character count.
    audio_ms: int | None = Field(default=None, ge=0, le=10 * 60 * 1000)


class SayRequest(BaseModel):
    session_id: str
    turn_index: int = Field(ge=0)
    # "Say that again" replays the same line slower. Comprehension failure
    # is the commonest reason a conversation dies and without this the
    # learner's only recovery is to quit.
    slow: bool = False


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


def _model_history(turns: list[dict]) -> tuple[list[dict], str | None]:
    """The transcript split into what the model can be sent, and what it
    has to be told.

    A partner-opened session starts with a turn nobody spoke — empty learner
    text, a real partner line. The messages list has to begin with the
    learner, so that line cannot ride along as a pair. Dropping it silently
    would leave the partner with no memory of its own opening question and
    it would ask again. So the pairs go to `messages` and the opener goes
    into the system prompt.
    """
    pairs = [
        {"learner_text": t["learner_text"], "partner_text": t["partner_text"]}
        for t in turns
        if (t["learner_text"] or "").strip()
    ]
    opener = next(
        (t["partner_text"] for t in turns
         if not (t["learner_text"] or "").strip()),
        None,
    )
    return pairs, opener


async def _support_language(conn, user_id: str) -> str | None:
    """The language to write corrections IN. None → English.

    Resolved through the shared rule (repositories/profile.py) — explicit
    Settings choice, else the interface language. This is the function
    that produced the owner's screenshot: it read the raw support_locale
    column, which the globe had frozen to French months of taps ago, so an
    all-English page coached in French. The correction language must never
    be able to disagree with the language the learner is being shown.
    """
    code = await effective_support_locale(conn, user_id)
    if not code:
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

    `speech` answers the two questions the page has to settle before it can
    draw itself: can this course be HEARD, and can it be SPOKEN. They are
    different facts with different answers — Speak can listen to Hebrew,
    Persian, Indonesian and Filipino, which have no neural voice; it cannot
    listen to Latin or Māori, which do have TTS in the reader. A course
    that fails either test keeps the typed path permanently, and the UI
    says which half is missing rather than showing a dead microphone.
    """
    off = {"available": False, "allowance": None, "sessions": [],
           "speech": {"listen": False, "speak": False}}
    if not generation_available():
        return off
    async with rls_connection(user["id"]) as conn:
        if not await tables_ready(conn):
            return off
        try:
            sessions = await list_recent_sessions(conn, user["id"], language_id)
        except SpeakUnavailableError:
            return off
        code = await conn.fetchval(
            "SELECT code FROM languages WHERE id = $1", language_id)
    allowance = await _get_allowance(user["id"], language_id)
    return {
        "available": True,
        "allowance": allowance,
        "sessions": sessions,
        "speech": {
            "listen": bool(
                code and transcription_available() and locale_for(code)
            ),
            "speak": bool(code and voice_for(code)),
        },
    }


@router.post("/transcribe")
async def transcribe_turn(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    # How long they spoke, from the recorder. Optional: an older client
    # that doesn't send it still transcribes fine, the event just lands in
    # the cost ledger with no duration attached.
    audio_ms: int | None = Form(default=None, ge=0, le=10 * 60 * 1000),
    user: dict = Depends(get_current_user),
):
    """Turn one recorded utterance into text. The audio is never kept.

    It is read into memory, sent to the provider, and dropped when this
    function returns — not written to storage, not logged, not retained to
    save a re-record. A recording of someone's voice is biometric data and
    keeping it would make a language app into a processor of it.

    The transcript comes back for the learner to SEE and edit before it is
    sent as a turn; this endpoint deliberately does not chain into /turn.
    ASR mishears an accented beginner, and being corrected for a word you
    did not say is the fastest way to stop trusting the feature.

    The session decides the language, like every other Speak endpoint: a
    client that named its own could aim a recording at another course's
    recognizer.
    """
    try:
        async with rls_connection(user["id"]) as conn:
            session = await get_session(conn, user["id"], session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Unknown session")
            if session["ended_at"]:
                raise HTTPException(
                    status_code=409, detail="That session is already finished"
                )
            _, code, _ = await _language(conn, session["language_id"])
    except SpeakUnavailableError as exc:
        raise _UNAVAILABLE from exc

    if not transcription_available() or not locale_for(code):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Speaking isn't available for this language yet — type it",
        )
    if not await stt_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many recordings — slow down a moment.",
        )

    # Bounded read: an UploadFile is a stream, and .read() with no argument
    # on a mis-wired client is an unbounded allocation. One byte over the
    # cap is enough to know it is over.
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="That recording is too long",
        )
    try:
        text = await transcribe(data, code, audio.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — provider is best-effort
        logger.error("Transcription failed (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="That didn't come through — try again, or type it",
        ) from exc

    # Billed by the second of audio sent, whether or not it contained
    # words — a mis-fired recording costs the same as a sentence. The
    # duration comes from the recorder; the audio itself is already gone.
    await record_speech_event(
        user["id"], code, kind="stt", feature="speak", audio_ms=audio_ms or 0,
    )

    # Silence is not an error. The learner pressed and released without
    # saying anything, or the microphone was muted; "" tells the page to
    # say so rather than posting an empty turn.
    return {"text": text}


@router.post("/say")
async def say(
    body: SayRequest,
    user: dict = Depends(get_current_user),
):
    """The partner's line, out loud.

    A separate path from /api/audio/tts on purpose. That endpoint checks
    the text is one of OURS — a drill sentence, an example, a vocabulary
    word — which is what stops it being an open synthesis proxy. A
    partner's reply is none of those things; it was written seconds ago
    for one learner. So the check here is ownership instead: the text is
    read back out of the caller's own session, and nothing a client sends
    is synthesized.

    Returned inline rather than cached to the CDN. Every line in a
    conversation is unique by construction, so a cache would be a store of
    single-use rows — and a store of one side of somebody's conversation.
    """
    try:
        async with rls_connection(user["id"]) as conn:
            session = await get_session(conn, user["id"], body.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Unknown session")
            _, code, _ = await _language(conn, session["language_id"])
            turns = await list_turns(conn, body.session_id)
    except SpeakUnavailableError as exc:
        raise _UNAVAILABLE from exc

    line = next(
        (t["partner_text"] for t in turns if t["idx"] == body.turn_index), None
    )
    if not line:
        raise HTTPException(status_code=404, detail="Unknown turn")
    if voice_for(code) is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="No voice for this language yet",
        )
    if not await tts_limiter.allow(user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many audio requests — slow down a moment.",
        )
    try:
        clip = await synthesize(line, code, rate=SLOW_RATE if body.slow else None)
    except Exception as exc:  # noqa: BLE001 — provider is best-effort
        logger.error("Speak TTS failed (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Audio generation failed",
        ) from exc

    # Every line here is a fresh synthesis — nothing is cached, so every
    # call is billable, including a "say that again". That is precisely
    # why it has to be recorded: this is the app's least visible spend.
    await record_speech_event(
        user["id"], code, kind="tts", feature="speak", chars=len(line),
    )
    return {"audio_b64": base64.b64encode(clip).decode()}


@router.post("/start")
async def start(
    body: StartRequest,
    user: dict = Depends(get_current_user),
):
    """Open a session, and let the partner speak first if asked.

    The start screen offers "leave it blank and your partner will start".
    That was a promise the code did not keep — the session opened on an
    empty transcript and "Say something to begin", which is the opposite of
    what the learner chose. When no topic is given the partner now opens for
    real, and that opening is stored as the session's first turn so it
    reaches the model's context and the end-of-session summary like any
    other line.

    Naming a topic still costs nothing here: the learner has already said
    what they want to talk about, so there is nothing for the partner to
    break the ice with.
    """
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

    if topic:
        return {"session_id": session_id, "mode": body.mode,
                "topic": topic, "opening": None,
                "opening_translation": None}

    # Best-effort: a partner who cannot think of an opener is a worse
    # session, not a broken one. Fall back to the learner starting rather
    # than failing the whole thing on the doorstep.
    try:
        async with rls_connection(user["id"]) as conn:
            language_name, code, override_model = await _language(
                conn, body.language_id
            )
            learner = await get_assessment_summary(
                conn, user["id"], body.language_id, depth="reading"
            )
            support_language = await _support_language(conn, user["id"])
        model = resolve_tutor_model(code, override_model)
        result, usage = await speak_opening(
            language_name, learner["level"], None, model=model,
            support_language=support_language,
        )
        opening = result["opening"]
        opening_translation = result["opening_translation"]
        async with rls_connection(user["id"]) as conn:
            await log_tutor_usage(
                conn, user["id"], body.language_id, model,
                usage=usage, kind="speak",
            )
            # learner_text is '' — nobody spoke. list_turns keeps it, and
            # _model_messages below drops the empty half so the model sees
            # an assistant-first conversation rather than a blank user turn.
            await append_turn(
                conn, session_id, 0, "", opening, [],
                partner_translation=opening_translation or None,
            )
    except Exception as exc:  # noqa: BLE001 — an opener is not worth a 500
        logger.warning("Speak opener failed, learner starts instead: %s", exc)
        opening = None
        opening_translation = None

    return {"session_id": session_id, "mode": body.mode,
            "topic": topic, "opening": opening,
            "opening_translation": opening_translation or None}


@router.post("/turn")
async def turn(
    body: TurnRequest,
    user: dict = Depends(get_current_user),
):
    """One exchange: they say something, the partner answers.

    In flow mode the errors noticed this turn are stored and never returned:
    the client cannot leak what the learner is not meant to see yet if it is
    never sent.

    In coach mode exactly ONE comes back — the first, which the model was
    asked to make the most impeding. Never a list. A learner corrected three
    times in a turn stops talking, and the other two are not lost: every
    error is stored either way and they all reach the summary.

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
    pairs, opener = _model_history(history)
    try:
        result, usage = await speak_turn(
            language_name,
            learner["level"],
            pairs,
            text,
            topic=session["topic"],
            support_language=support_language,
            model=model,
            opened_with=opener,
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
            conn, user["id"], language_id, model, usage=usage, kind="speak",
        )
        await append_turn(
            conn, body.session_id, len(history), text,
            result["reply"], result["errors"], audio_ms=body.audio_ms,
            partner_translation=result.get("reply_translation") or None,
        )

    errors = result["errors"]
    used_after = None if allowance["unlimited"] else (allowance["used"] or 0) + 1
    return {
        "reply": result["reply"],
        # Sent with the reply, never fetched separately: "what did that
        # mean?" is a tap on something already on the client, not a wait.
        "reply_translation": result.get("reply_translation") or None,
        "turn_index": len(history),
        # Present (possibly null) only in coach mode. Flow sends no key at
        # all, so a client cannot render what it was never given.
        **({"correction": errors[0] if errors else None}
           if session["mode"] == "coach" else {}),
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
                usage=usage, kind="speak_summary",
            )
        await end_session(conn, body.session_id, summary)
    return {"summary": summary, "already_ended": False}
