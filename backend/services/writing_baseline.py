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

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model

MAX_SAMPLE_CHARS = 500

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
    resp = await client.messages.create(
        model=model or resolve_model("semantic_check", language_code),
        max_tokens=512,
        system=(
            f"You place ONE short free-writing sample by a learner of "
            f"{language_name}. Judge only what the sample demonstrates: the "
            f"CEFR level of their strongest CORRECT production (not their "
            f"mistakes — a B1 writer with typos is still B1), one "
            f"encouraging English sentence about what they can already do, "
            f"and up to 3 structures to focus on next. A tiny sample caps "
            f"honestly at what it shows — never infer above B2 from a "
            f"sentence or two."
        ),
        messages=[{"role": "user", "content": text}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    usage = getattr(resp, "usage", None)
    counts = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    raw = next((b.text for b in resp.content if b.type == "text"), "{}")
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
