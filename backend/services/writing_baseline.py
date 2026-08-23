"""Writing-sample baseline (owner, 2026-07-26): during onboarding a learner
can optionally write a sentence or two in the target language "to the best of
their ability", and one small LLM call turns that into a CEFR estimate plus
up to three focus structures — a far stronger placement signal than
multiple-choice for someone who already produces the language.

Token guard, per the owner: the call is only offered to accounts with a tutor
entitlement (paid/granted) or in dev-mock testing — the router gates it, this
module just does the judging. The result primes the tutor's language profile
(`_writing_baseline` + Active Focus), which the assessment tiers already feed
to the Tutor, Reader, and (via level-seated decks) the Gym.
"""

from __future__ import annotations

import json
import logging

from anthropic import AsyncAnthropic, BadRequestError

from backend.config import get_settings
from backend.services.models import resolve_model

logger = logging.getLogger(__name__)

# A paragraph, not a sentence or two. 500 chars capped the sample below the
# length at which real complexity shows up — subordination, tense contrast,
# discourse connectives — so a C1 writer had no room to demonstrate C1 and
# the judge was told to cap at B2 anyway. ~1500 is 200-250 words: enough for
# a genuine paragraph, still one cheap call.
MAX_SAMPLE_CHARS = 1500

CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

_SCHEMA = {
    "type": "object",
    "properties": {
        "level": {
            "type": "string",
            "enum": CEFR_LEVELS,
            "description": "The CEFR level this sample's PRODUCTION "
            "demonstrates.",
        },
        "notes": {
            "type": "string",
            "description": "One encouraging sentence, in English, about what "
            "the sample shows.",
        },
        "focus": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
            "description": "Up to 3 grammar structures/skills to work on "
            "next, named plainly.",
        },
    },
    "required": ["level", "notes", "focus"],
    "additionalProperties": False,
}


def _mock_assess(text: str) -> dict:
    """Deterministic baseline for dev/testing: level scales with how much the
    learner produced, so tests can drive each band."""
    words = len(text.split())
    level = "A1" if words < 6 else "A2" if words < 15 else "B1"
    return {
        "level": level,
        "notes": f"[dev mock] {words} words assessed",
        "focus": ["[dev mock] basic word order"],
    }


async def assess_writing(
    language_code: str,
    language_name: str,
    text: str,
    model: str | None = None,
) -> tuple[dict, dict[str, int]]:
    """Judge one short free-writing sample. Returns
    ({level, notes, focus}, usage token counts). The level is validated
    against the CEFR enum — a malformed reply falls back to A1 with empty
    extras rather than guessing."""
    settings = get_settings()
    text = text.strip()[:MAX_SAMPLE_CHARS]
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_assess(text), {
            "input_tokens": 5, "output_tokens": 20,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
        }

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    call_model = model or resolve_model("semantic_check", language_code)
    system = (
        f"You place ONE free-writing sample by a learner of "
        f"{language_name}. Judge only what the sample demonstrates: the "
        f"CEFR level of their strongest CORRECT production (not their "
        f"mistakes — a B1 writer with typos is still B1), one "
        f"encouraging English sentence about what they can already do, "
        f"and up to 3 structures to focus on next.\n\n"
        f"Judge COMPLEXITY, not just correctness: subordination, tense "
        f"and aspect contrast, discourse connectives, register control "
        f"and idiom are what separate B2 from C1 and above. A learner "
        f"who writes several clause types accurately across a paragraph "
        f"is showing more than one who writes ten flawless simple "
        f"sentences.\n\n"
        f"Cap honestly at what the sample SHOWS. A sentence or two "
        f"cannot demonstrate above B2 however clean it is — say so in "
        f"the notes rather than inferring. A full paragraph that "
        f"genuinely sustains complex structure may reach C1 or C2."
    )

    async def _ask(structured: bool):
        kwargs: dict = {
            "model": call_model,
            "max_tokens": 512,
            "system": system if structured else (
                system + "\n\nReply with ONLY a JSON object, no prose and "
                'no code fences: {"level": one of '
                f"{CEFR_LEVELS}"
                ', "notes": string, "focus": [up to 3 strings]}'
            ),
            "messages": [{"role": "user", "content": text}],
        }
        if structured:
            kwargs["output_config"] = {
                "format": {"type": "json_schema", "schema": _SCHEMA}
            }
        return await client.messages.create(**kwargs)

    try:
        resp = await _ask(structured=True)
    except BadRequestError:
        # The task-#115 lesson, relearned here: a model tier that doesn't
        # accept output_config 400s BEFORE it ever reads the sample, so
        # every real submission died on "Couldn't assess that" while the
        # dev-mock unit tests stayed green. Structured output is an
        # optimization, never a dependency — the same judgement retries as
        # plain JSON.
        logger.warning(
            "writing baseline: structured output rejected, retrying as "
            "plain JSON (model=%s)", call_model, exc_info=True,
        )
        resp = await _ask(structured=False)
    usage = getattr(resp, "usage", None)
    counts = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    raw = next((b.text for b in resp.content if b.type == "text"), "{}").strip()
    # The plain-JSON path sometimes arrives fenced despite instructions.
    if raw.startswith("```") and "{" in raw and "}" in raw:
        raw = raw[raw.index("{"): raw.rindex("}") + 1]
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    level = parsed.get("level")
    return {
        "level": level if level in CEFR_LEVELS else "A1",
        "notes": (parsed.get("notes") or "").strip(),
        "focus": [
            s.strip() for s in (parsed.get("focus") or [])
            if isinstance(s, str) and s.strip()
        ][:3],
    }, counts
