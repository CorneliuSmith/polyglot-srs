"""Speak — the conversation partner and the end-of-session breakdown.

Design notes live in docs/plans/speak.md; the two that shape this file:

**One model call per turn.** The call returns BOTH the partner's reply and
the structured list of what the learner got wrong. Two calls would double
the latency, and the reply is better when the model has already noticed the
mistake — it can steer the conversation somewhere the learner can succeed.

**Latency is the product.** Above about three seconds it stops feeling like
conversation and becomes turn-taking with a form. That is why the reply is
capped short, why history is trimmed, and why the summary is a separate call
that happens once, at the end, when nobody is waiting to speak.

Stage 1 is text-only and flow-mode-only: errors are collected silently every
turn and shown all at once when the learner is done.
"""
from __future__ import annotations

import json
import logging
from collections import Counter

from anthropic import AsyncAnthropic

from backend.config import get_settings

logger = logging.getLogger("speak")

MAX_TURN_CHARS = 2000
MAX_TOPIC_CHARS = 120

# How many previous turns ride along as context. Ten turns of a beginner
# conversation is a few hundred tokens — cheap — and further back than that
# stops informing the next reply. The DB keeps every turn regardless; this
# only bounds what the model is shown.
MAX_HISTORY_TURNS = 10

# Errors the summary groups under. A closed list keeps "subject pronouns"
# from arriving as four different labels across one session and splitting
# into four one-off findings the learner can't act on.
ERROR_TYPES = (
    "agreement", "verb_form", "word_order", "word_choice",
    "preposition", "article", "gender", "pronoun", "spelling", "register",
)

_TURN_TOOL = {
    "name": "emit_turn",
    "description": "Reply to the learner and record what they got wrong.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": (
                    "Your conversational reply, in the target language. One "
                    "to three sentences. End with a question or an opening "
                    "that gives them something to say back."
                ),
            },
            "reply_translation": {
                "type": "string",
                "description": (
                    "Your reply, in the learner's support language. Natural "
                    "and complete — what a person would actually say, not a "
                    "word-for-word gloss. It is shown only when the learner "
                    "asks for it, so it never has to be short."
                ),
            },
            "errors": {
                "type": "array",
                "description": (
                    "Mistakes in the learner's message, MOST IMPEDING FIRST "
                    "— the one that most gets in the way of being understood "
                    "leads the list, because in coach mode only that one is "
                    "shown and the rest wait for the end. Empty list when the "
                    "message was fine. Do not invent errors to seem useful, "
                    "and do not flag informal-but-correct speech."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": list(ERROR_TYPES)},
                        "learner_said": {
                            "type": "string",
                            "description": "Their exact words, quoted short.",
                        },
                        "should_be": {
                            "type": "string",
                            "description": "The corrected form, same length.",
                        },
                        "note": {
                            "type": "string",
                            "description": (
                                "One short sentence on why, in the learner's "
                                "support language. No grammar jargon they "
                                "would not already know."
                            ),
                        },
                    },
                    "required": ["type", "learner_said", "should_be", "note"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["reply", "reply_translation", "errors"],
        "additionalProperties": False,
    },
}

_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "groups": {
            "type": "array",
            "description": (
                "The recurring problems, most frequent first. Group by what "
                "the learner needs to understand, not by error type label — "
                "three pronoun slips are ONE group."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "A short name, e.g. 'Subject pronouns'.",
                    },
                    "note": {
                        "type": "string",
                        "description": (
                            "Two sentences at most: what they did and the "
                            "rule, in their support language."
                        ),
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Their own phrases, quoted.",
                    },
                    "count": {"type": "integer"},
                    "card": {
                        "type": "object",
                        "description": (
                            "A card the learner may choose to keep, built "
                            "from THEIR OWN sentence with the mistake fixed "
                            "— not a textbook example. Practising the "
                            "sentence they actually tried to say is the "
                            "whole point."
                        ),
                        "properties": {
                            "sentence": {
                                "type": "string",
                                "description": (
                                    "Their sentence, corrected, in full. The "
                                    "answer below must appear in it "
                                    "word-for-word."
                                ),
                            },
                            "answer": {
                                "type": "string",
                                "description": (
                                    "The single word from that sentence that "
                                    "was wrong — this is what gets blanked "
                                    "out, so spell it exactly as it appears."
                                ),
                            },
                            "translation": {
                                "type": "string",
                                "description": (
                                    "What the sentence means, in the "
                                    "learner's support language."
                                ),
                            },
                        },
                        "required": ["sentence", "answer", "translation"],
                        "additionalProperties": False,
                    },
                },
                "required": ["label", "note", "examples", "count", "card"],
                "additionalProperties": False,
            },
        },
        "vocabulary": {
            "type": "array",
            "description": (
                "Words and short phrases worth keeping from this "
                "conversation — ones the partner used that the learner "
                "visibly did not have, or reached for and missed. Empty is "
                "a fine answer."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "meaning": {
                        "type": "string",
                        "description": "In the learner's support language.",
                    },
                    "example": {
                        "type": "string",
                        "description": (
                            "A short sentence from THIS conversation using "
                            "the term, containing it word-for-word. Lets the "
                            "word be practised in the context they met it in "
                            "rather than as a bare pair."
                        ),
                    },
                },
                "required": ["term", "meaning", "example"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["groups", "vocabulary"],
    "additionalProperties": False,
}


def _usage(response) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }


def _system_prompt(
    language_name: str,
    level: str,
    topic: str | None,
    support_language: str | None,
    opened_with: str | None = None,
) -> str:
    """The partner's brief.

    The level cap is the load-bearing line. Without an explicit instruction
    the model writes B2 prose at an A2 learner and the session turns into a
    listening test they fail — so the ceiling is stated as a rule about
    sentence length and tense range, not as a CEFR label the model is left
    to interpret.
    """
    explain_in = support_language or "English"
    topic_line = (
        f"You are talking about: {topic}."
        if topic else
        "No topic was chosen — open with something everyday and easy to "
        "answer, and follow where they take it."
    )
    # A partner-opened session has no user turn before the assistant's first
    # line, and the messages list must start with the learner — so the line
    # rides here instead. Without it the partner asks its opening question a
    # second time, having no memory of asking it.
    if opened_with:
        topic_line += (
            f'\n\nYou have already opened the conversation with: '
            f'"{opened_with}". Do not greet them again or repeat that '
            f'question — their message is the answer to it.'
        )
    return (
        f"You are a friendly {language_name} conversation partner for a "
        f"learner at CEFR level {level}. This is a spoken-style chat, not a "
        f"lesson.\n\n"
        f"{topic_line}\n\n"
        "How you talk:\n"
        f"- Reply ONLY in {language_name}. Never translate yourself.\n"
        f"- Stay at {level} or a touch above — short sentences, common "
        "words, tenses a learner at this level has met. If you would need a "
        "structure above their level, say the simpler thing instead.\n"
        "- One to three sentences. You are a partner, not a monologue.\n"
        "- Always give them a way back in: ask something, or leave an "
        "obvious opening.\n"
        "- If you nudge them to try a word or form, never include the "
        "answer in the same message — an ask that answers itself tests "
        "nothing. The word can appear in your NEXT reply, after their "
        "attempt.\n"
        "- React to what they actually said. Never say 'good job' — you are "
        "a person having a conversation, not a teacher marking them.\n"
        "- If you cannot understand them, say so naturally and ask again in "
        "simpler words. Do not guess wildly.\n\n"
        "What you record:\n"
        "- Alongside your reply, list what they got wrong. The learner does "
        "NOT see this now; it is collected for the end of the session.\n"
        "- Only real mistakes. Informal, clipped, or regional-but-correct "
        "speech is not an error. An empty list is a good answer.\n"
        f"- Write the notes in {explain_in}.\n"
        "- Judge only what they wrote. Never flag spelling of a word they "
        "typed on a keyboard they may not have."
    )


def _mock_turn(learner_text: str) -> dict:
    """Deterministic partner for tutor_dev_mock — exercises the whole flow
    (reply + error extraction + summary grouping) with no API key."""
    errors = []
    if "yo " in f" {learner_text.lower()}":
        errors.append({
            "type": "pronoun",
            "learner_said": "yo",
            "should_be": "(drop it)",
            "note": "[dev mock] The subject pronoun is usually left out.",
        })
    return {
        "reply": f"[dev mock] Interesting — tell me more about that. "
                 f"({len(learner_text)} characters)",
        "reply_translation": "[dev mock] Interesting — tell me more about that.",
        "errors": errors,
    }


async def speak_turn(
    language_name: str,
    level: str,
    history: list[dict],
    learner_text: str,
    topic: str | None = None,
    support_language: str | None = None,
    model: str | None = None,
    opened_with: str | None = None,
) -> tuple[dict, dict[str, int]]:
    """One conversational turn.

    *history* is [{"learner_text": …, "partner_text": …}, …] oldest first.
    Returns ({"reply": str, "errors": [...]}, token counts).
    """
    settings = get_settings()
    model = model or settings.tutor_model

    if getattr(settings, "tutor_dev_mock", False):
        return _mock_turn(learner_text), {
            "input_tokens": 8, "output_tokens": 30,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
        }

    messages: list[dict] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": turn["learner_text"]})
        messages.append({"role": "assistant", "content": turn["partner_text"]})
    messages.append({"role": "user", "content": learner_text})

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=_system_prompt(
            language_name, level, topic, support_language, opened_with
        ),
        messages=messages,
        tools=[_TURN_TOOL],
        tool_choice={"type": "tool", "name": "emit_turn"},
    )
    counts = _usage(response)
    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None or not isinstance(block.input, dict):
        raise ValueError("Speak turn returned no structured payload")
    reply = (block.input.get("reply") or "").strip()
    if not reply:
        raise ValueError("Speak turn came back with an empty reply")
    errors = [
        e for e in (block.input.get("errors") or [])
        if isinstance(e, dict) and e.get("learner_said") and e.get("should_be")
    ]
    # The translation rides along in the SAME call — the reason this feature
    # costs nothing at read time. A second request per line would put a
    # spinner between the learner and the one thing they didn't understand.
    return {
        "reply": reply,
        "reply_translation": (block.input.get("reply_translation") or "").strip(),
        "errors": errors,
    }, counts


def _fallback_groups(errors: list[dict]) -> list[dict]:
    """Group by error type without a model call.

    Used when the summary call fails or is skipped. Cruder than the model's
    grouping — it can only group by the type label — but a learner who
    finished a session always gets their breakdown. Losing the summary is
    the one failure this feature cannot afford: it is the entire payoff for
    the conversation they just had.
    """
    by_type: dict[str, list[dict]] = {}
    for err in errors:
        by_type.setdefault(err.get("type") or "other", []).append(err)
    groups = []
    for kind, items in sorted(
        by_type.items(), key=lambda kv: len(kv[1]), reverse=True
    ):
        groups.append({
            "label": kind.replace("_", " ").capitalize(),
            "note": items[0].get("note") or "",
            "examples": [
                f"{i['learner_said']} → {i['should_be']}" for i in items[:4]
            ],
            "count": len(items),
            # No card. A per-turn error records the phrase that was wrong,
            # not the whole sentence it sat in, so there is nothing here to
            # build a cloze from. Offering a broken card is worse than
            # offering none.
            "card": None,
        })
    return groups


def _usable_card(card) -> dict | None:
    """Keep a card only if it can actually become one.

    The card endpoint blanks *answer* out of *sentence* and rejects the save
    when the answer isn't a whole word there. Checking it here means the
    learner never meets an Add button that 422s when they press it — the
    button is simply absent for groups that cannot produce a card.
    """
    if not isinstance(card, dict):
        return None
    sentence = (card.get("sentence") or "").strip()
    answer = (card.get("answer") or "").strip()
    if not sentence or not answer:
        return None
    if answer.lower() not in sentence.lower():
        return None
    return {
        "sentence": sentence,
        "answer": answer,
        "translation": (card.get("translation") or "").strip(),
    }


async def summarize_speak_session(
    language_name: str,
    turns: list[dict],
    errors: list[dict],
    support_language: str | None = None,
    model: str | None = None,
) -> tuple[dict, dict[str, int] | None]:
    """The end-of-session breakdown.

    Returns (summary, token counts) — counts are None when no model call ran,
    so the caller knows not to log a cost row.

    A clean session costs nothing: with no errors there is nothing to group,
    and the vocabulary list is not worth a call on its own.
    """
    stats = {
        "turns": len(turns),
        "error_count": len(errors),
        "types": dict(Counter(e.get("type") for e in errors if e.get("type"))),
    }
    if not errors:
        return {"groups": [], "vocabulary": [], "stats": stats}, None

    settings = get_settings()
    model = model or settings.tutor_summary_model

    if getattr(settings, "tutor_dev_mock", False):
        return (
            {"groups": _fallback_groups(errors),
             "vocabulary": [{"term": "[dev mock]", "meaning": "a placeholder",
                             "example": "This is a [dev mock] sentence."}],
             "stats": stats},
            {"input_tokens": 5, "output_tokens": 20,
             "cache_write_tokens": 0, "cache_read_tokens": 0},
        )

    transcript = "\n".join(
        f"learner: {t['learner_text']}\npartner: {t['partner_text']}"
        for t in turns
    )
    explain_in = support_language or "English"
    system = (
        f"You write the end-of-session breakdown for a {language_name} "
        "conversation practice app. You are given the transcript and the "
        "mistakes noticed during it.\n\n"
        "Group the mistakes by what the learner needs to understand, not by "
        "label — three slips of the same underlying rule are ONE group, with "
        "all three quoted as examples. Order by how much each one gets in "
        "the way of being understood.\n"
        f"Write labels and notes in {explain_in}; quote the learner's own "
        "words untranslated. Be brief and unsentimental. Do not praise, do "
        "not score, do not pad the list — two real groups beat six thin ones."
    )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{
                "role": "user",
                "content": (
                    f"Transcript:\n{transcript}\n\n"
                    f"Mistakes noticed:\n"
                    f"{json.dumps(errors, ensure_ascii=False)}"
                ),
            }],
            output_config={
                "format": {"type": "json_schema", "schema": _SUMMARY_SCHEMA}
            },
        )
    except Exception:
        # Never cost the learner their breakdown because the grouping call
        # failed — fall back to the mechanical grouping and log the cause.
        logger.exception("Speak summary call failed; using fallback grouping")
        return {
            "groups": _fallback_groups(errors), "vocabulary": [], "stats": stats
        }, None

    counts = _usage(response)
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Speak summary was not valid JSON; using fallback")
        return {
            "groups": _fallback_groups(errors), "vocabulary": [], "stats": stats
        }, counts

    groups = [
        {**g, "card": _usable_card(g.get("card"))}
        for g in (data.get("groups") or []) if g.get("label")
    ]
    return {
        "groups": groups or _fallback_groups(errors),
        "vocabulary": [
            v for v in (data.get("vocabulary") or []) if v.get("term")
        ],
        "stats": stats,
    }, counts


_OPENING_TOOL = {
    "name": "emit_opening",
    "description": "The partner's first line, plus what it means.",
    "input_schema": {
        "type": "object",
        "properties": {
            "opening": {
                "type": "string",
                "description": (
                    "The opening line, in the language being learned. ONE "
                    "short sentence ending in a question they can answer at "
                    "their level."
                ),
            },
            "opening_translation": {
                "type": "string",
                "description": (
                    "The same line in the learner's support language. Shown "
                    "only if they ask for it."
                ),
            },
        },
        "required": ["opening", "opening_translation"],
        "additionalProperties": False,
    },
}


async def speak_opening(
    language_name: str,
    level: str,
    topic: str | None = None,
    model: str | None = None,
    support_language: str | None = None,
) -> tuple[dict, dict[str, int]]:
    """The partner's first line, when the learner asked it to start.

    "Leave it blank and your partner will start" was a promise the code did
    not keep: the session opened with an empty transcript and "Say something
    to begin", which is the opposite of what the learner chose. This is the
    line that keeps it.

    Deliberately its own call rather than a turn: there is no learner text to
    grade, so the turn tool's whole error-extraction half would be dead
    weight and the model would be invited to invent mistakes in a message
    nobody sent.

    Returns ({"opening": str, "opening_translation": str}, token counts).
    The translation comes back in this same call for the same reason the
    reply's does: the first line is the one a beginner is most likely to
    stall on, and a reveal must not cost a round trip.
    """
    settings = get_settings()
    model = model or settings.tutor_model
    support = support_language or "English"

    if getattr(settings, "tutor_dev_mock", False):
        return {
            "opening": f"[dev mock] ¿{topic or 'Qué tal'}?",
            "opening_translation": f"[dev mock] {topic or 'How are things'}?",
        }, {
            "input_tokens": 4, "output_tokens": 12,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
        }

    about = (
        f"Open a conversation about: {topic}."
        if topic else
        "Open with something everyday and easy to answer."
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=512,
        system=(
            f"You are a friendly {language_name} conversation partner for a "
            f"learner at CEFR level {level}.\n\n{about}\n\n"
            f"The opening line itself must be ONLY {language_name}, ONE "
            "short sentence ending in a question they can answer at their "
            "level. No greeting-plus-question pile-up, no explanation of "
            "what you are doing.\n\n"
            f"Write its translation in {support}."
        ),
        messages=[{"role": "user", "content": "Start the conversation."}],
        tools=[_OPENING_TOOL],
        tool_choice={"type": "tool", "name": "emit_opening"},
    )
    counts = _usage(response)
    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None or not isinstance(block.input, dict):
        raise ValueError("Speak opening returned no structured payload")
    text = (block.input.get("opening") or "").strip()
    if not text:
        raise ValueError("Speak opening came back empty")
    return {
        "opening": text,
        "opening_translation": (
            block.input.get("opening_translation") or ""
        ).strip(),
    }, counts
