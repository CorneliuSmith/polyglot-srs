"""Maker–checker generation of a word's DEFINITION (the gap-fill for words that
have none — low-density languages especially).

Where services/translate.py goes English-word → support-locale *gloss*, this goes
the other way: a word in the language being learned → a clear *definition* in the
learner's language (the support locale; English by default).

  Maker   — given each word (its part of speech and, when we have one, a real
            example sentence to fix the sense), writes a concise definition IN
            THE TARGET LOCALE. Owner's rule for a concept the locale lacks a word
            for: explain it in that locale; if even that isn't possible, give the
            English explanation.
  Checker — grades each definition for accuracy/sense/clarity, one tier up
            (§6: never self-certify): ok / fixed → keep (final); reject → no
            definition, queue for a human.

Batched (many words per call) for economy, structured JSON output, and a
TUTOR_DEV_MOCK path so the pipeline is testable with no API key — same shape as
services/translate.py.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model

_MAKER_SCHEMA = {
    "type": "object",
    "properties": {
        "definitions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "definition": {
                        "type": "string",
                        "description": "A concise definition of the word in the "
                        "target locale (one clause, no the word itself).",
                    },
                },
                "required": ["i", "definition"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["definitions"],
    "additionalProperties": False,
}

_CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["ok", "fixed", "reject"]},
                    "final": {
                        "type": "string",
                        "description": "The definition to store: unchanged when "
                        "ok, corrected when fixed, empty when reject.",
                    },
                    "note": {"type": "string"},
                },
                "required": ["i", "verdict", "final", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def definitions_available() -> bool:
    settings = get_settings()
    return bool(settings.anthropic_api_key) or getattr(settings, "tutor_dev_mock", False)


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def _fallback_rule(locale_language: str) -> str:
    """Owner's rule: prefer the target locale; explain in it if the concept has
    no word there; only then fall back to English."""
    if locale_language.lower().startswith("english"):
        return (
            " If the word names a concept with no single English word, give a "
            "short English explanation of it."
        )
    return (
        f" Write the definition in {locale_language}. If {locale_language} has no "
        f"word for the concept, briefly EXPLAIN it in {locale_language}; only if "
        f"that is impossible, give the English explanation."
    )


def _mock_definitions(items: list[dict]) -> list[dict]:
    return [{"i": it["i"], "definition": f"meaning of {it['word']}"} for it in items]


def _mock_verdicts(items: list[dict]) -> list[dict]:
    # First item of each batch rejected, so the queue path is always exercised.
    out = []
    for n, it in enumerate(items):
        if n == 0:
            out.append({"i": it["i"], "verdict": "reject", "final": "",
                        "note": "[dev mock] flagged for review"})
        else:
            out.append({"i": it["i"], "verdict": "ok",
                        "final": it["definition"], "note": ""})
    return out


async def make_definitions(
    language: str, locale_language: str, items: list[dict],
    model: str | None = None,
) -> dict[int, str]:
    """Maker: {i -> definition} for items {i, word, pos, example}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {d["i"]: d["definition"] for d in _mock_definitions(items)}
    lines = "\n".join(
        f'{it["i"]}. "{it["word"]}" ({it.get("pos") or "?"})'
        + (f'  e.g. {it["example"]}' if it.get("example") else "")
        for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You are a lexicographer writing dictionary definitions of "
            f"{language} words for a language-learning app. For each numbered "
            f"word, give ONE concise definition that captures its core sense "
            f"(use the example to disambiguate when given); match the part of "
            f"speech; do not repeat the word inside its own definition."
            + _fallback_rule(locale_language)
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _MAKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {d["i"]: (d.get("definition") or "").strip()
            for d in data.get("definitions", []) if (d.get("definition") or "").strip()}


async def check_definitions(
    language: str, locale_language: str, items: list[dict],
    model: str | None = None,
) -> dict[int, dict]:
    """Checker: {i -> {verdict, final, note}} for items {i, word, definition}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {v["i"]: v for v in _mock_verdicts(items)}
    lines = "\n".join(
        f'{it["i"]}. {language} "{it["word"]}" → proposed {locale_language} '
        f'definition: "{it["definition"]}"'
        for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You are a strict reviewer of {language} word definitions written "
            f"in {locale_language} for a learner app. For each item decide: 'ok' "
            f"if the definition is accurate, the right sense, and clear; 'fixed' "
            f"if close but you can correct it (put the correction in final); "
            f"'reject' if wrong-sense, unclear, or you are unsure (final empty). "
            f"Be conservative — reject rather than guess."
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _CHECKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    out = {}
    for v in data.get("verdicts", []):
        verdict = v.get("verdict")
        if verdict not in ("ok", "fixed", "reject"):
            verdict = "reject"
        out[v["i"]] = {"verdict": verdict, "final": (v.get("final") or "").strip(),
                       "note": (v.get("note") or "").strip()}
    return out


async def generate_definitions(
    language: str, locale_language: str, items: list[dict],
    maker_model: str | None = None, checker_model: str | None = None,
) -> list[dict]:
    """Maker then checker over a batch. Returns per item
    {i, word, definition, verdict, note} where definition is the final to store
    (empty when reject)."""
    made = await make_definitions(language, locale_language, items, maker_model)
    checkable = [{**it, "definition": made[it["i"]]} for it in items if it["i"] in made]
    if not checkable:
        return []
    verdicts = await check_definitions(language, locale_language, checkable, checker_model)
    results = []
    for it in checkable:
        v = verdicts.get(it["i"], {"verdict": "reject", "final": "", "note": "no verdict"})
        store = it["definition"] if v["verdict"] == "ok" else v["final"]
        results.append({
            "i": it["i"], "word": it["word"],
            "definition": store if v["verdict"] in ("ok", "fixed") else "",
            "verdict": v["verdict"], "note": v["note"],
        })
    return results
