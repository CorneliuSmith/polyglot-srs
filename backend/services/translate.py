"""Maker–checker translation of English course content into a support locale.

A learner studying English *from* their language sees the gloss in that
language. Many locales are thin or empty. This fills them with a two-pass AI:

  Maker   — generates the L1 gloss for a batch of English words, given each
            word's English definition, part of speech, and a real example so
            it picks the RIGHT sense (not "a → bishop").
  Checker — grades each maker gloss against the English sense and, when it
            can, returns a corrected final. Verdict drives the gate:
              ok / fixed  → apply the final gloss
              reject      → queue it for a human, never auto-apply.

Both passes are batched (many words per call) to keep the run affordable, and
use structured JSON output. Mock mode (TUTOR_DEV_MOCK) returns deterministic
stubs so the pipeline is testable with no API key.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model

_MAKER_SCHEMA = {
    "type": "object",
    "properties": {
        "glosses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "gloss": {"type": "string",
                              "description": "The word/short phrase a native "
                              "speaker of the target language would use for THIS "
                              "sense. No English, no notes."},
                },
                "required": ["i", "gloss"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["glosses"],
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
                    "final": {"type": "string",
                              "description": "The gloss to store: unchanged when "
                              "ok, corrected when fixed, empty when reject."},
                    "note": {"type": "string",
                             "description": "Why, when fixed or reject. Empty otherwise."},
                },
                "required": ["i", "verdict", "final", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def translations_available() -> bool:
    settings = get_settings()
    return bool(settings.anthropic_api_key) or getattr(settings, "tutor_dev_mock", False)


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def _mock_glosses(items: list[dict]) -> list[dict]:
    # deterministic stub: echo the English word tagged, so tests can assert flow
    return [{"i": it["i"], "gloss": f"[{it['word']}]"} for it in items]


def _mock_verdicts(items: list[dict]) -> list[dict]:
    # first item of every batch is rejected so the queue path is exercised
    out = []
    for n, it in enumerate(items):
        if n == 0:
            out.append({"i": it["i"], "verdict": "reject", "final": "",
                        "note": "[dev mock] flagged for review"})
        else:
            out.append({"i": it["i"], "verdict": "ok", "final": it["gloss"], "note": ""})
    return out


async def make_glosses(target_language: str, items: list[dict],
                       model: str | None = None) -> dict[int, str]:
    """Maker: {i -> gloss} for each item {i, word, definition, pos, example}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {g["i"]: g["gloss"] for g in _mock_glosses(items)}
    lines = "\n".join(
        f'{it["i"]}. "{it["word"]}" ({it.get("pos") or "?"}) — {it.get("definition") or ""}'
        + (f'  e.g. {it["example"]}' if it.get("example") else "")
        for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You are a professional lexicographer translating English headwords "
            f"into {target_language} for a language-learning app. For each "
            f"numbered English word, give the single word or short phrase a "
            f"native {target_language} speaker would use for THAT specific sense "
            f"(use the definition and example to disambiguate). Match the part of "
            f"speech. Output {target_language} only — no English, no explanations."
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _MAKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {g["i"]: (g.get("gloss") or "").strip()
            for g in data.get("glosses", []) if (g.get("gloss") or "").strip()}


async def check_glosses(target_language: str, items: list[dict],
                        model: str | None = None) -> dict[int, dict]:
    """Checker: {i -> {verdict, final, note}} for items {i, word, definition, gloss}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {v["i"]: v for v in _mock_verdicts(items)}
    lines = "\n".join(
        f'{it["i"]}. English "{it["word"]}" ({it.get("definition") or ""}) '
        f'→ proposed {target_language}: "{it["gloss"]}"'
        for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You are a strict bilingual reviewer checking English→{target_language} "
            f"glosses for a learner app. For each item decide: 'ok' if the gloss is "
            f"the correct sense, natural, and right part of speech; 'fixed' if it is "
            f"close but you can correct it (put the correction in final); 'reject' if "
            f"it is wrong-sense, unnatural, or you are unsure (final empty). Be "
            f"conservative — reject rather than guess."
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


async def maker_check_batch(target_language: str, items: list[dict],
                            maker_model: str | None = None,
                            checker_model: str | None = None) -> list[dict]:
    """Run maker then checker over a batch. Returns per-item results:
    {i, word, gloss, verdict, note} where gloss is the final to store (or '')."""
    made = await make_glosses(target_language, items, maker_model)
    checkable = [
        {**it, "gloss": made[it["i"]]} for it in items if it["i"] in made
    ]
    if not checkable:
        return []
    verdicts = await check_glosses(target_language, checkable, checker_model)
    results = []
    for it in checkable:
        v = verdicts.get(it["i"], {"verdict": "reject", "final": "", "note": "no verdict"})
        store = it["gloss"] if v["verdict"] == "ok" else v["final"]
        results.append({
            "i": it["i"], "word": it["word"],
            "gloss": store if v["verdict"] in ("ok", "fixed") else "",
            "verdict": v["verdict"], "note": v["note"],
        })
    return results


async def review_definitions(target_language: str, items: list[dict],
                             model: str | None = None) -> list[dict]:
    """Clarity pass over EXISTING card definitions/hints (not a translation).

    Catches misleading wording — e.g. a Russian imperfective glossed
    "to speak, to talk (perfective поговорить)", which reads like it wants the
    perfective. items: {i, word, definition}. Returns per item
    {i, word, verdict, definition, note}: 'ok' keep as-is, 'fixed' use the
    reworded `definition`, 'reject' → empty (queue for a human).
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return [{"i": it["i"], "word": it["word"],
                 "verdict": "ok", "definition": it["definition"], "note": ""}
                for it in items]
    lines = "\n".join(
        f'{it["i"]}. "{it["word"]}" — {it["definition"]}' for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You review flash-card definitions for learners of {target_language}. "
            "For each, judge CLARITY, not translation: is it unambiguous and not "
            "misleading? A common fault is a parenthetical that reads like an "
            "instruction — e.g. an imperfective verb glossed '...(perfective X)' "
            "looks like it's asking for X. Verdict 'ok' if it's clear; 'fixed' if "
            "you can reword it clearly (keep the meaning, put any partner/aspect "
            "note in plain words, e.g. 'to speak (imperfective; pairs with X)') and "
            "put it in `final`; 'reject' if you're unsure. Keep it concise."
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _CHECKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    by_i = {}
    for v in data.get("verdicts", []):
        verdict = v.get("verdict")
        if verdict not in ("ok", "fixed", "reject"):
            verdict = "reject"
        by_i[v["i"]] = (verdict, (v.get("final") or "").strip(), (v.get("note") or "").strip())
    out = []
    for it in items:
        verdict, final, note = by_i.get(it["i"], ("reject", "", "no verdict"))
        definition = it["definition"] if verdict == "ok" else final
        out.append({"i": it["i"], "word": it["word"], "verdict": verdict,
                    "definition": definition if verdict in ("ok", "fixed") else "",
                    "note": note})
    return out
