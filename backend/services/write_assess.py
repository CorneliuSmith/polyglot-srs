"""Write — the handwriting assessor (docs/plans/handwriting.md, §4.3).

Free writing has no stroke template to match against, so the ink is READ:
the client renders the canvas to a PNG and this module asks a vision-capable
model what it says, whether that matches the expected text, and how legible
it is. Two things shape the call:

**The transcription is always returned.** A verdict without it is a black
box: when the model misreads a wobbly д as а, the learner must see "read as
…" and know the fail was a misread, not a mistake. Every other field is
downstream of the transcription, so it is also the field the model has to
commit to first.

**Confidence is its own field.** A beginner's Devanagari or Thai is exactly
where a reader — human or model — is least sure, and "I'm not sure I read
this right" is a different message from "this is wrong". Low confidence is
never shown as a fail.

The per-letter *stroke* verdict (form, order, direction) is not here: that
needs the script's authored templates and runs on the device (§4.1–4.2).
"""
from __future__ import annotations

import base64
import logging
import re

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.ink_method import method_line

logger = logging.getLogger("write")

# A 1000×400 canvas exports to a few kilobytes of PNG; a photo of a page
# would be megabytes. The cap is generous for ink and a hard wall for
# anything else — the endpoint reads one byte past it and stops.
MAX_IMAGE_BYTES = 1_500_000
MAX_EXPECTED_CHARS = 400
CONFIDENCE = ("low", "medium", "high")

def _assess_tool(explain_in: str) -> dict:
    """The tool schema, with the language every note is written in named
    in the field descriptions as well as the system prompt: with it only
    in the prompt, a Spanish-support learner once got the word diff in
    Spanish and the letterform notes in English."""
    return {
    "name": "emit_assessment",
    "description": "Read the handwriting and report on it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "transcription": {
                "type": "string",
                "description": (
                    "Exactly what is written, as text, in the language's own "
                    "script. Transcribe what is there — never what was "
                    "expected. Empty if nothing legible is written."
                ),
            },
            "matches_target": {
                "type": "boolean",
                "description": (
                    "Whether the writing says the expected text (ignoring "
                    "handwriting quality). False when no expected text was "
                    "given and the writing has a spelling or grammar error; "
                    "true when it is correct."
                ),
            },
            "word_diffs": {
                "type": "array",
                "description": (
                    "Words that differ from the expected text (or, with no "
                    "expected text, words with an error). Empty when it "
                    "matches."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "expected": {"type": "string",
                                     "description": "The expected word, exactly."},
                        "written": {
                            "type": "string",
                            "description": (
                                "Exactly the letters you read for that word — "
                                "never a qualifier like '(approx)', never a "
                                "description."
                            ),
                        },
                        "note": {
                            "type": "string",
                            "description": f"One short line, written in {explain_in}.",
                        },
                    },
                    "required": ["expected", "written", "note"],
                    "additionalProperties": False,
                },
            },
            "legibility": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": (
                    "How easily a native reader could read this at speed: "
                    "1 illegible, 3 readable with effort, 5 clear."
                ),
            },
            "letterform_notes": {
                "type": "array",
                "description": (
                    "At most two notes on letterforms that cost a reader "
                    "something — the most useful two, not every flaw. Each "
                    f"names the letter and says what to change, in {explain_in}."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "letter": {"type": "string"},
                        "note": {"type": "string"},
                    },
                    "required": ["letter", "note"],
                    "additionalProperties": False,
                },
            },
            "confidence": {
                "type": "string",
                "enum": list(CONFIDENCE),
                "description": (
                    "How sure you are of the transcription itself. Low when "
                    "letters could be read more than one way."
                ),
            },
        },
        "required": ["transcription", "matches_target", "word_diffs",
                     "legibility", "letterform_notes", "confidence"],
        "additionalProperties": False,
    },
    }


def _system_prompt(language_name: str, support_language: str | None,
                   style: str | None, known: list[str] = ()) -> str:
    explain_in = support_language or "English"
    known_line = (
        "\n\nKnown forms of THIS writer, confirmed legible by them — read "
        "them as written and do not flag them as ambiguous or as faults: "
        + "; ".join(known) + "."
    ) if known else ""
    style_line = {
        "cursive": (
            f" The learner is writing {language_name} in joined cursive "
            f"handwriting, which is how native writers write it; judge "
            f"cursive forms as correct, not as deviations from print."
        ),
        "print": f" The learner is writing {language_name} in unjoined print letters.",
    }.get(style or "", "")
    return (
        f"You are a careful native reader of handwritten {language_name} "
        f"grading a learner's handwriting in a language-learning app."
        f"{style_line} You are shown an image of ink drawn on a blank "
        f"canvas with a finger, mouse or pen — expect an adult learner's "
        f"hand, not calligraphy.\n\n"
        f"First transcribe exactly what is written, in {language_name}'s own "
        f"script. Never 'correct' the transcription toward what was expected; "
        f"if a letter is ambiguous, transcribe your best reading and lower "
        f"your confidence. Then compare it to the expected text if one was "
        f"given, judge legibility as a reader would, and name at most two "
        f"letterforms that would cost a reader something, with what to "
        f"change. Write every note in {explain_in}, short and plain. Judge "
        f"the hand, not the person; a wobbly line is not a fault if the "
        f"letter is unambiguous. When reference samples of this writer's own "
        f"hand are shown before the canvas, use them: the same person wrote "
        f"the canvas, and a letter shaped as in the references is that "
        f"letter.{known_line}"
    )


def _usage(response) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }


_QUALIFIER = re.compile(r"\([^)]*\)|\[[^\]]*\]")


def _bare(value) -> str:
    """A diff word with the model's asides removed: '(approx) ين' is 'ين'.
    A word that is nothing BUT an aside stays as it was, rather than
    becoming an empty cell."""
    text = str(value or "").strip()
    stripped = _QUALIFIER.sub("", text).strip()
    return stripped or text


def normalize_assessment(raw: dict) -> dict:
    """Clamp and trim what the model returned into the shape the client
    is promised. A malformed field degrades to its safest value rather than
    failing the assessment: an out-of-range legibility becomes 3, an
    unknown confidence becomes 'low', and note lists are cut to their caps."""
    transcription = str(raw.get("transcription") or "").strip()
    try:
        legibility = int(raw.get("legibility", 3))
    except (TypeError, ValueError):
        legibility = 3
    legibility = max(1, min(5, legibility))
    confidence = str(raw.get("confidence") or "").strip().lower()
    if confidence not in CONFIDENCE:
        confidence = "low"
    diffs = [
        {"expected": _bare(d.get("expected")),
         "written": _bare(d.get("written")),
         "note": str(d.get("note") or "").strip()}
        for d in (raw.get("word_diffs") or []) if isinstance(d, dict)
    ][:12]
    notes = [
        {"letter": str(n.get("letter") or "").strip(),
         "note": str(n.get("note") or "").strip()}
        for n in (raw.get("letterform_notes") or [])
        if isinstance(n, dict) and (n.get("note") or "").strip()
    ][:2]
    matches = raw.get("matches_target")
    if not isinstance(matches, bool):
        matches = not diffs
    if not transcription:
        # Nothing read: never "correct", never confident.
        matches, confidence = False, "low"
    return {
        "transcription": transcription,
        "matches_target": matches,
        "word_diffs": diffs,
        "legibility": legibility,
        "letterform_notes": notes,
        "confidence": confidence,
    }


def _mock_assessment(expected: str | None) -> dict:
    """Deterministic assessor for tutor_dev_mock: reads back the expected
    text (or a fixed line), passes it, and flags one letterform so the
    notes UI is exercised."""
    text = expected or "[dev mock] nothing expected"
    return normalize_assessment({
        "transcription": text,
        "matches_target": True,
        "word_diffs": [],
        "legibility": 4,
        "letterform_notes": [
            {"letter": text[:1], "note": "[dev mock] Close the loop at the top."},
        ],
        "confidence": "high",
    })


async def assess_handwriting(
    image_png: bytes,
    language_name: str,
    expected: str | None,
    *,
    support_language: str | None = None,
    style: str | None = None,
    model: str | None = None,
    references: list[dict] = (),
    known: list[str] = (),
    method: dict | None = None,
) -> tuple[dict, dict[str, int]]:
    """Read one canvas. Returns (assessment, token counts).

    *references* are the writer's own kept samples — {text, image, method}
    — shown before the canvas so the reader learns this hand; *known* are
    the forms the writer has confirmed legible, which the reader is told
    not to flag; *method* is how THIS canvas was made (ink_method), stated
    to the reader as fact (docs/plans/handwriting.md, §11)."""
    settings = get_settings()
    model = model or settings.tutor_model
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_assessment(expected), {
            "input_tokens": 600, "output_tokens": 80,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
        }

    ask = (
        f"Expected text: {expected}" if expected
        else "No expected text: the learner wrote freely. Transcribe it and "
             "judge its spelling and grammar as well as the handwriting."
    )
    content: list[dict] = []
    for ref in references:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png",
                       "data": base64.b64encode(ref["image"]).decode("ascii")},
        })
        how = method_line(ref.get("method") or {})
        content.append({
            "type": "text",
            "text": f"Reference: this writer's own hand, confirmed. It reads: {ref['text']}"
                    + (f" ({how})" if how else ""),
        })
    content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png",
                   "data": base64.b64encode(image_png).decode("ascii")},
    })
    how = method_line(method or {})
    content.append({
        "type": "text",
        "text": ("Now the canvas to assess. " if references else "")
                + (f"How it was made: {how} " if how else "") + ask,
    })
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=700,
        system=_system_prompt(language_name, support_language, style, list(known)),
        messages=[{"role": "user", "content": content}],
        tools=[_assess_tool(support_language or "English")],
        tool_choice={"type": "tool", "name": "emit_assessment"},
    )
    counts = _usage(response)
    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None or not isinstance(block.input, dict):
        raise ValueError("The assessor returned no structured payload")
    return normalize_assessment(block.input), counts
