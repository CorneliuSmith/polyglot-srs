"""AI CEFR level estimation for vocab words with no frequency-based level.

For thin languages a word may exist without frequency data, so the usual
rank→CEFR banding leaves it level-less (and therefore in no deck). This asks the
model where a learner would typically first meet each word. The result is
PROVISIONAL — stored as level_source='ai' and confirmed by a reviewer.

Dev-mock (TUTOR_DEV_MOCK) returns a deterministic banding so the pipeline is
testable with no API key.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model

CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")

_SCHEMA = {
    "type": "object",
    "properties": {
        "levels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "level": {"type": "string", "enum": list(CEFR)},
                },
                "required": ["word", "level"],
            },
        },
    },
    "required": ["levels"],
}


def _mock_levels(words: list[dict]) -> dict[str, str]:
    """Deterministic banding for dev/tests."""
    return {w["word"]: CEFR[i % len(CEFR)] for i, w in enumerate(words)}


async def estimate_levels(
    words: list[dict],
    language_name: str,
    language_code: str,
    model: str | None = None,
) -> dict[str, str]:
    """Estimate a CEFR level per word. Returns {word: level}; words the model
    skips or mislabels are simply omitted (the caller leaves those level-less)."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_levels(words)
    if not words:
        return {}

    listing = "\n".join(
        f"- {w['word']}" + (f"  ({w['definition']})" if w.get("definition") else "")
        for w in words
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("level_estimate", language_code),
        max_tokens=4096,
        system=(
            f"You are an experienced {language_name} teacher grading vocabulary "
            f"by CEFR. For each word, give the level (A1–C2) at which a learner "
            f"would typically FIRST meet it: A1 = the most basic everyday words, "
            f"C2 = rare, literary, or highly specialised. Judge by how common the "
            f"word is and how advanced its meaning is."
        ),
        messages=[{"role": "user", "content": f"Words:\n{listing}"}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        items = json.loads(text).get("levels", [])
    except (json.JSONDecodeError, TypeError):
        items = []
    wanted = {w["word"] for w in words}
    return {
        it["word"]: it["level"]
        for it in items
        if it.get("word") in wanted and it.get("level") in CEFR
    }
