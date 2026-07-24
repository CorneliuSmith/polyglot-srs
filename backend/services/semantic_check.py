"""AI semantic review for grammar content.

The NLP layer proves a drill is *answerable*; this asks an AI linguist whether
the grammar is actually *correct* — is the explanation accurate, is each drill
sentence natural, is each answer the right form? It returns an advisory verdict
(pass | concerns) plus notes. It is NOT a substitute for the human linguist
sign-off; it's a first pass that flags issues for the reviewer.

Mock mode (TUTOR_DEV_MOCK) returns a canned pass so the workflow is testable
with no API key.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model
from backend.services.tutor import _load_skill

_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["pass", "concerns"],
            "description": "pass = grammar, explanation, and all drills look correct; concerns = at least one issue.",
        },
        "notes": {
            "type": "string",
            "description": "Concise reviewer notes: name any incorrect answer, unnatural sentence, or inaccurate explanation, with the fix. Empty if pass.",
        },
    },
    "required": ["status", "notes"],
    "additionalProperties": False,
}


def ai_available() -> bool:
    settings = get_settings()
    return bool(settings.anthropic_api_key) or getattr(settings, "tutor_dev_mock", False)


def _mock_check() -> dict:
    return {
        "status": "pass",
        "notes": "[dev mock] AI semantic check passed — set ANTHROPIC_API_KEY for a real review.",
    }


async def semantic_check_point(
    language_code: str,
    title: str,
    explanation: str | None,
    drills: list[dict],
) -> dict:
    """Run an AI linguist review of a grammar point. Returns {status, notes}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_check()

    brief = _load_skill(language_code) or f"Language code: {language_code}."
    drills_text = "\n".join(
        f"- sentence: {d.get('sentence')}\n  answer: {d.get('answer')}"
        f"\n  translation: {d.get('translation') or '(none)'}"
        for d in drills
    ) or "(no drills)"

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=resolve_model("semantic_check"),
        max_tokens=1024,
        system=(
            "You are a meticulous linguist reviewing beginner grammar content for "
            "correctness. Verify the explanation is accurate, each drill sentence "
            "is natural and grammatical, and each answer is the exactly correct "
            "form for its blank. Report 'concerns' if anything is wrong, naming "
            "the specific item and the fix.\n\n" + brief
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Grammar point: {title}\n"
                f"Explanation: {explanation or '(none provided)'}\n"
                f"Drills:\n{drills_text}"
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    return _parse_verdict(response)


async def semantic_check_vocab(
    language_code: str,
    word: str,
    definition: str | None,
    examples: list[dict],
) -> dict:
    """Run an AI linguist review of a vocabulary word — the vocab twin of
    semantic_check_point. Checks the definition is accurate and each example
    sentence is natural and uses the word correctly. Returns {status, notes}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_check()

    brief = _load_skill(language_code) or f"Language code: {language_code}."
    examples_text = "\n".join(
        f"- {e.get('sentence')}"
        + (f"  ({e.get('translation')})" if e.get("translation") else "")
        for e in examples
    ) or "(no example sentences)"

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=resolve_model("semantic_check"),
        max_tokens=1024,
        system=(
            "You are a meticulous linguist reviewing a beginner vocabulary entry "
            "for correctness. Verify the definition/gloss is accurate for the "
            "word, and that each example sentence is natural, grammatical, and "
            "actually uses the word correctly. Report 'concerns' if anything is "
            "wrong, naming the specific item and the fix.\n\n" + brief
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Word: {word}\n"
                f"Definition: {definition or '(none provided)'}\n"
                f"Example sentences:\n{examples_text}"
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    return _parse_verdict(response)


def _parse_verdict(response) -> dict:
    """Extract the {status, notes} verdict from a model response, failing safe
    to 'concerns' so an unparseable review still reaches the human reviewer."""
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {"status": "concerns", "notes": "AI review could not be parsed; needs human review."}
    status = data.get("status")
    if status not in ("pass", "concerns"):
        status = "concerns"
    return {"status": status, "notes": (data.get("notes") or "").strip()}
