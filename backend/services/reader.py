"""WP21: The Reader — comprehensible input on demand.

One Claude call produces a complete reading artifact: a short text on the
learner's topic, level-locked to the grammar and vocabulary they have
actually learned, deliberately seeding a handful of new words in guessable
contexts — plus the token-level gloss map, per-sentence translations, and
the list of grammar structures used. Everything the three-stage reader UI
needs ships in that one response; hovers never cost a second call.

The response is forced through a tool call (`emit_reading`) so the shape
is schema-guaranteed rather than parsed out of prose.
"""

from __future__ import annotations

import logging
from typing import Any

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.repositories.level import shift_level

logger = logging.getLogger("reader")

MAX_TOPIC_CHARS = 120

READING_TOOL: dict[str, Any] = {
    "name": "emit_reading",
    "description": "Return the finished reading in exactly this structure.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short title in the target language."},
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "translation": {"type": "string"},
                        "tokens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "t": {"type": "string",
                                          "description": "The word as it appears, punctuation attached."},
                                    "gloss": {"type": "string",
                                              "description": "Contextual meaning, 1–4 words."},
                                    "new": {"type": "boolean",
                                            "description": "True only on deliberately seeded new words."},
                                },
                                "required": ["t", "gloss"],
                            },
                        },
                    },
                    "required": ["text", "translation", "tokens"],
                },
            },
            "new_words": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string"},
                        "gloss": {"type": "string"},
                        "sentence_index": {"type": "integer"},
                    },
                    "required": ["word", "gloss", "sentence_index"],
                },
            },
            "structures": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Every grammar structure the text uses, named plainly.",
            },
        },
        "required": ["title", "sentences", "new_words", "structures"],
    },
}


# Per-text options: each maps to ONE explicit prompt rule. Bounded lengths so
# "long" can't run away with tokens.
_LENGTH_RULE = {
    "short": "Write 80–120 words",
    "medium": "Write 150–250 words",
    "long": "Write 300–400 words",
}
_VOICE_RULE = {
    "first": " Write in the FIRST person — the narrator is an 'I' telling "
             "their own story.",
    "third": " Write in the THIRD person.",
    "dialogue": " Write it as a DIALOGUE between two named speakers — every "
                "sentence is one speaker's line with the name attached, "
                "natural back-and-forth.",
}
# The complexity dial is a LEVEL SHIFT, not a tone hint. It used to add
# one soft sentence against the HARD CONSTRAINTS cage below, and in a
# language model a hard constraint plus a soft nudge resolves to the hard
# constraint — "stretch" produced the same baby text and the owner said
# so ("the content is sometimes way too simple", "does not actually
# listen to the rules"). Now easier/stretch move the target level itself
# (repositories/level.py shift_level) and the constraint block is
# rewritten per mode. The owner's standing rule: an explicit ask for
# harder content is GIVEN, uncapped — stretch means one full level up
# from wherever they sit, including above their own chosen level.
_COMPLEXITY_SHIFT = {"easier": -1, "level": 0, "stretch": +1}


def _placement_rule(placement: dict | None) -> str:
    """Turn the placement result into a coverage instruction.

    A reading text is the cheapest way to re-expose a structure someone got
    wrong — it can carry it in context without ever looking like a drill. The
    struggled level is the more useful half: it says where the ceiling is, so
    the text can sit at it rather than under it.
    """
    if not placement:
        return ""
    bits: list[str] = []
    struggled = placement.get("struggled_levels") or []
    if struggled:
        bits.append(
            f"On a graded placement test they held {placement.get('ceiling') or 'A1'} "
            f"but fell down at {', '.join(struggled)} — pitch at the ceiling, "
            "not below it."
        )
    structures = placement.get("missed_structures") or []
    if structures:
        bits.append(
            "They got these structures WRONG on that test: "
            f"{'; '.join(structures)}. Work at least one into the text "
            "naturally, in a context that makes it transparent."
        )
    words = placement.get("missed_words") or []
    if words:
        bits.append(f"Words they missed there: {', '.join(words)}.")
    return ("\n- " + " ".join(bits)) if bits else ""


def _constraint_block(
    mode: str, target_level: str, structures: str, known_words: str
) -> str:
    """The constraint block, written per mode — because one block for all
    three dials is how "stretch" produced the same text as "easier".

    easier/level keep the cage: known structures, level-locked
    vocabulary. stretch OPENS it — the learner explicitly asked for
    harder, and glosses are one tap away, which is what the Reader's
    gloss machinery is for. Their known words become calibration, not a
    ceiling, and grammar may run a level past their cards.
    """
    if mode == "stretch":
        return f"""HARD CONSTRAINTS:
- Pitch the text at {target_level} — genuinely at it, not beneath it. The \
learner ASKED for harder material; do not soften it back down.
- Grammar: their learned structures ({structures or "the basics"}) are the \
FLOOR, not the limit — use {target_level} constructions beyond them freely.
- Vocabulary: their strongest known words are calibration only, NOT a \
ceiling: {known_words or "(new learner)"}. Unknown words are welcome — \
every word carries a tap-to-reveal gloss, so difficulty costs a tap, not \
comprehension.
- Seed EXACTLY 5–8 genuinely NEW words worth learning at {target_level}. \
Mark them new:true in the tokens and list them in new_words."""
    return f"""HARD CONSTRAINTS:
- Pitch the text at {target_level}.
- Grammar: use ONLY structures the learner has learned: {structures or "the absolute basics (present tense, simple sentences)"}.
- Vocabulary: stay within what a {target_level} learner knows. Their \
strongest known words, for calibration: {known_words or "(new learner — use only top-frequency words)"}.
- Seed EXACTLY 5–8 genuinely NEW words the learner is likely to meet next \
at this level. Each must appear in a context that makes its meaning \
guessable without a dictionary. Mark them new:true in the tokens and list \
them in new_words."""


def _system_prompt(
    language_code: str, gloss_locale: str, learner: dict,
    options: dict | None = None,
) -> str:
    opts = options or {}
    mode = opts.get("complexity") or "level"
    length_rule = _LENGTH_RULE.get(opts.get("length") or "", _LENGTH_RULE["medium"])
    voice_rule = _VOICE_RULE.get(opts.get("voice") or "", "")
    known_words = ", ".join(learner.get("known_words") or [])
    structures = "; ".join(learner.get("learned_structures") or [])
    weak = ", ".join(learner.get("weak_words") or [])
    focus = "; ".join(learner.get("focus") or [])
    level = learner.get("level") or "A1"
    # The dial shifts the LEVEL, uncapped upward (owner: "if the user
    # wants harder content above their level give it to them").
    target_level = shift_level(level, _COMPLEXITY_SHIFT.get(mode, 0))
    placement = _placement_rule(learner.get("placement"))
    constraints = _constraint_block(mode, target_level, structures, known_words)
    return f"""You write reading material for one specific learner inside \
PolyglotSRS, a spaced-repetition language app. Target language: \
{language_code}. The learner's level: {level}. This text is pitched at: \
{target_level}.

{length_rule} on the requested topic — natural, warm, factually \
grounded prose, never a vocabulary exercise dressed as a \
text.{voice_rule}

{constraints}
- Where natural (never forced), re-expose these weak words: {weak or "(none)"} \
and these focus structures: {focus or "(none)"}.{placement}

Then call emit_reading. Token rules: tokens must cover each sentence's \
words in order (punctuation attached to its word); every token carries a \
short contextual gloss in {gloss_locale}; per-sentence translations in \
{gloss_locale}; in structures, name every grammar structure the text uses \
in plain English — reuse the learner's structure names above verbatim \
where they apply, and name anything beyond them honestly (those feed the \
app's curriculum-gap log)."""


def _mock_reading(topic: str) -> dict:
    """Deterministic reading for tutor_dev_mock — exercises the full flow
    (generation, storage, stages, gap log) with no API key."""
    return {
        "title": f"[dev mock] {topic}",
        "sentences": [
            {
                "text": "El gato duerme en la ventana.",
                "translation": "The cat sleeps in the window.",
                "tokens": [
                    {"t": "El", "gloss": "the"},
                    {"t": "gato", "gloss": "cat"},
                    {"t": "duerme", "gloss": "sleeps"},
                    {"t": "en", "gloss": "in"},
                    {"t": "la", "gloss": "the"},
                    {"t": "ventana.", "gloss": "window", "new": True},
                ],
            },
            {
                "text": "Le gusta el sol de la mañana.",
                "translation": "It likes the morning sun.",
                "tokens": [
                    {"t": "Le", "gloss": "to it"},
                    {"t": "gusta", "gloss": "pleases"},
                    {"t": "el", "gloss": "the"},
                    {"t": "sol", "gloss": "sun", "new": True},
                    {"t": "de", "gloss": "of"},
                    {"t": "la", "gloss": "the"},
                    {"t": "mañana.", "gloss": "morning"},
                ],
            },
        ],
        "new_words": [
            {"word": "ventana", "gloss": "window", "sentence_index": 0},
            {"word": "sol", "gloss": "sun", "sentence_index": 1},
        ],
        "structures": ["Present tense", "Gustar and similar verbs",
                       "[dev mock] an uncovered structure"],
    }


def _validate_reading(payload: dict) -> dict:
    """Shape sanity beyond the schema: no empty text, tokens everywhere."""
    sentences = payload.get("sentences") or []
    if not sentences:
        raise ValueError("Reading came back with no sentences")
    for s in sentences:
        if not (s.get("text") or "").strip() or not s.get("tokens"):
            raise ValueError("Reading sentence missing text or tokens")
    return payload


# The contract checker — the anti-trash mechanism (adaptive-sessions
# plan, stage 2). The dials stopped being suggestions the day the owner
# said "does not actually listen to the rules provided": every generated
# text is now GRADED against what was asked — pitched level, length band,
# voice — by one small model call, and a text that flunks is regenerated
# once with the verdict injected. The verdict ships in the reading's
# payload either way (check field), so obedience is observable instead of
# anecdotal. A checker failure (provider hiccup, bad JSON) never blocks
# the reading — ungraded beats undelivered.
_CHECK_TOOL = {
    "name": "emit_check",
    "description": "Report whether the text honors its contract.",
    "input_schema": {
        "type": "object",
        "properties": {
            "level_ok": {"type": "boolean"},
            "level_estimate": {
                "type": "string",
                "enum": ["A1", "A2", "B1", "B2", "C1", "C2"],
            },
            "length_ok": {"type": "boolean"},
            "voice_ok": {"type": "boolean"},
            "note": {"type": "string", "description": "One line on any miss."},
        },
        "required": ["level_ok", "level_estimate", "length_ok", "voice_ok"],
    },
}

_LENGTH_BANDS = {"short": (60, 200), "medium": (130, 330), "long": (250, 500)}


async def _check_reading(
    client: AsyncAnthropic, reading: dict, language_code: str,
    target_level: str, options: dict, model: str,
) -> dict | None:
    """One cheap grading call. None when the check itself failed."""
    opts = options or {}
    text = " ".join(
        s.get("text", "") for s in (reading.get("sentences") or [])
    )
    voice = opts.get("voice") or "any"
    length = opts.get("length") or "medium"
    lo, hi = _LENGTH_BANDS.get(length, _LENGTH_BANDS["medium"])
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=300,
            system=(
                "You grade generated language-learning texts against their "
                "contract. Judge honestly; a text that undershoots its "
                "level is a FAIL even if it is pleasant."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Language: {language_code}. Contract: pitched at "
                    f"{target_level}; length {length} (~{lo}–{hi} words); "
                    f"voice {voice}.\n\nTEXT:\n{text}"
                ),
            }],
            tools=[_CHECK_TOOL],
            tool_choice={"type": "tool", "name": "emit_check"},
        )
        block = next((b for b in response.content if b.type == "tool_use"), None)
        return dict(block.input) if block and isinstance(block.input, dict) else None
    except Exception as exc:  # noqa: BLE001 — grading is best-effort
        logger.warning("reading check failed: %s", exc)
        return None


async def generate_reading(
    language_code: str,
    topic: str,
    learner: dict,
    gloss_locale: str = "en",
    model: str | None = None,
    options: dict | None = None,
) -> tuple[dict, dict[str, int]]:
    """Generate one reading, graded against its contract.

    Returns (reading, usage token counts). reading["check"] carries the
    grader's verdict ({level_ok, level_estimate, length_ok, voice_ok,
    note, retried}) when grading ran — the observable answer to "did it
    listen to the dials", logged either way.
    """
    settings = get_settings()
    model = model or settings.tutor_model
    opts = options or {}
    mode = opts.get("complexity") or "level"
    target_level = shift_level(
        learner.get("level") or "A1", _COMPLEXITY_SHIFT.get(mode, 0)
    )

    if getattr(settings, "tutor_dev_mock", False):
        return _validate_reading(_mock_reading(topic)), {
            "input_tokens": 10, "output_tokens": 50,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
        }

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _one_attempt(extra: str = "") -> tuple[dict, dict]:
        response = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=_system_prompt(language_code, gloss_locale, learner, options)
            + extra,
            messages=[{
                "role": "user",
                "content": f"Please write me something to read about: {topic}",
            }],
            tools=[READING_TOOL],
            tool_choice={"type": "tool", "name": "emit_reading"},
        )
        usage = getattr(response, "usage", None)
        counts = {
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        }
        tool_use = next(
            (b for b in response.content if b.type == "tool_use"), None
        )
        if tool_use is None or not isinstance(tool_use.input, dict):
            raise ValueError("Reading generation returned no structured payload")
        return _validate_reading(tool_use.input), counts

    reading, counts = await _one_attempt()
    # The cheaper summary-class model grades; the verdict decides one
    # retry, then the second attempt is served regardless — the learner
    # is never held hostage to a perfectionist loop.
    check_model = getattr(settings, "tutor_summary_model", None) or model
    verdict = await _check_reading(
        client, reading, language_code, target_level, opts, check_model
    )
    if verdict and not (
        verdict.get("level_ok")
        and verdict.get("length_ok")
        and verdict.get("voice_ok")
    ):
        logger.info(
            "reading flunked its contract (%s → retrying): %s",
            target_level, verdict,
        )
        retry_note = (
            "\n\nA previous attempt FAILED its contract check: "
            f"{verdict.get('note') or verdict}. Fix exactly that."
        )
        reading, counts2 = await _one_attempt(retry_note)
        for key in counts:
            counts[key] += counts2.get(key, 0)
        verdict = dict(verdict, retried=True)
    if verdict is not None:
        reading["check"] = verdict
        logger.info("reading contract verdict (%s): %s", target_level, verdict)
    return reading, counts


async def explain_sentence(
    language_code: str,
    sentence: str,
    translation: str,
    level: str,
    model: str | None = None,
) -> tuple[str, dict[str, int]]:
    """Stage-3 on-demand explanation of one sentence's grammar."""
    settings = get_settings()
    model = model or settings.tutor_model

    if getattr(settings, "tutor_dev_mock", False):
        return (
            f"[dev mock] '{sentence}' breaks down word by word; the "
            f"structure is level-appropriate for {level}.",
            {"input_tokens": 5, "output_tokens": 20,
             "cache_write_tokens": 0, "cache_read_tokens": 0},
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=(
            f"You explain one {language_code} sentence to a {level} learner. "
            "Under 120 words, no jargon the level doesn't know yet.\n\n"
            "Format exactly like this (the app renders it as a table):\n"
            "One short intro sentence.\n"
            "chunk — its grammatical role, briefly\n"
            "chunk — its role\n"
            "(one line per meaningful chunk, in sentence order)\n"
            "Optionally ONE closing note sentence. No markdown, no bullets."
        ),
        messages=[{
            "role": "user",
            "content": f"Sentence: {sentence}\nIt means: {translation}",
        }],
    )
    usage = getattr(response, "usage", None)
    counts = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    reply = next((b.text for b in response.content if b.type == "text"), "")
    return reply, counts
