"""AI tutor service — per-language tutoring agents powered by the Claude API.

Each language gets a tutor persona with real linguistic expertise (the same
grammar dimensions the NLP backends model), and every conversation is
grounded in the learner's actual SRS failure data: the system prompt carries
the cards they keep getting wrong, so the tutor drills weaknesses instead of
making generic conversation.

Prompt structure (ordered for prompt caching — stable prefix first):
  system[0]  shared tutor charter + per-language linguistics brief (cached)
  system[1]  learner context: weak cards, failure counts (volatile, per-user)
  messages   the chat history from the client
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic

from backend.config import get_settings

MAX_HISTORY_MESSAGES = 40
MAX_MESSAGE_CHARS = 4000

_LANGUAGE_BRIEFS: dict[str, str] = {
    "ru": (
        "Language: Russian.\n"
        "You are an expert in Slavic linguistics. Key teaching dimensions: the "
        "six grammatical cases and their declension patterns; verb aspect pairs "
        "(imperfective/perfective) and when each is used; gender and animacy; "
        "verbs of motion. When the learner confuses an aspect partner, contrast "
        "the pair with minimal-pair example sentences. Always show stress marks "
        "when introducing new words."
    ),
    "ar": (
        "Language: Modern Standard Arabic.\n"
        "You are an expert in Semitic linguistics. Key teaching dimensions: the "
        "trilateral root system (e.g. ك-ت-ب) and verb forms I–X; broken vs sound "
        "plurals; dual number; the three cases. Use tashkeel (diacritics) as a "
        "learning aid when introducing words, but never penalize the learner "
        "for omitting them. Connect new words to roots the learner already knows."
    ),
    "en": (
        "Language: English.\n"
        "You are an expert in English as a second language. Key teaching "
        "dimensions: the article system (the/a/an — hardest for Russian and "
        "Arabic speakers), irregular verbs, and phrasal verbs. Accept both "
        "British and American spellings. Teach articles through contrastive "
        "examples rather than rules."
    ),
    "sw": (
        "Language: Swahili.\n"
        "You are an expert in Bantu linguistics. Key teaching dimensions: the "
        "noun class system (ki-/vi-, m-/wa-, m-/mi-, ji-/ma- and agreement "
        "across the sentence); verb morphology (subject prefix + tense marker "
        "+ stem, e.g. ni-na-soma); and how adjectives and verbs agree with "
        "noun classes. Decompose conjugated verbs into their morphemes so the "
        "learner sees the system, not memorized strings."
    ),
    "yo": (
        "Language: Yoruba.\n"
        "You are an expert in Niger-Congo linguistics, specializing in Yoruba. "
        "Key teaching dimensions: the three-tone system (high ́, mid "
        "unmarked, low ̀) and how tone alone distinguishes words (ọkọ "
        "husband / ọkọ̀ vehicle / oko farm); the underdotted vowels ẹ and ọ "
        "and consonant ṣ as distinct phonemes; vowel harmony; serial verb "
        "constructions; and subject pronouns + the rich aspect particles "
        "(ti, ń, máa, yóò). Always write fully diacritized Yoruba. When the "
        "learner omits or mistakes tone marks, contrast the minimal pair "
        "they accidentally typed so they hear why tone matters."
    ),
    "tr": (
        "Language: Turkish.\n"
        "You are an expert in Turkic linguistics. Key teaching dimensions: "
        "agglutination and suffix ordering; two- and four-way vowel harmony "
        "(and how it selects suffix variants like -lar/-ler, -da/-de); the six "
        "cases; and the dotted/dotless i distinction. When the learner gets a "
        "suffix wrong, walk through the harmony rule that selects the correct "
        "variant rather than just giving the answer."
    ),
}

_TUTOR_CHARTER = """\
You are a private language tutor inside PolyglotSRS, a spaced-repetition \
language learning app. The learner reviews flashcards daily; you are the \
paid coaching add-on that turns their failure data into progress.

How to tutor:
- Coach on the learner's weak items (provided below) before anything else. \
Weave those exact words into short practice exchanges, fill-in-the-blank \
drills, and example sentences.
- Keep turns short and interactive: one concept or drill per message, then \
ask the learner to produce language. Never lecture for more than a short \
paragraph.
- Correct errors by showing the contrast between what they said and the \
target form, then have them retry a similar item.
- Use English for explanations, the target language for practice. Calibrate \
difficulty to the CEFR levels of their weak items.
- Be encouraging but honest — name the pattern behind their errors when you \
see one (e.g. "you keep missing the locative case").
"""


def build_system_blocks(
    language_code: str,
    weak_areas: list[dict],
) -> list[dict[str, Any]]:
    """Build the system prompt blocks for a tutor conversation.

    The first block (charter + linguistics brief) is stable per language and
    carries a cache_control marker; the learner-context block varies per user
    and request, so it comes after the cache breakpoint.
    """
    brief = _LANGUAGE_BRIEFS.get(language_code)
    if brief is None:
        raise ValueError(f"No tutor available for language code '{language_code}'")

    stable_block = {
        "type": "text",
        "text": f"{_TUTOR_CHARTER}\n{brief}",
        "cache_control": {"type": "ephemeral"},
    }

    if weak_areas:
        items = []
        for area in weak_areas:
            morph = area.get("morphology")
            if isinstance(morph, str):
                try:
                    morph = json.loads(morph)
                except (json.JSONDecodeError, TypeError):
                    morph = {}
            items.append({
                "word": area.get("word"),
                "meaning": area.get("definition"),
                "part_of_speech": area.get("part_of_speech"),
                "recent_failures": int(area.get("recent_failures") or 0),
                "total_lapses": int(area.get("lapses") or 0),
                "morphology": morph or {},
            })
        context_text = (
            "Learner's current weak items (from their SRS review history, "
            "worst first):\n"
            + json.dumps(items, ensure_ascii=False, indent=1)
        )
    else:
        context_text = (
            "The learner has no recorded weak items yet. Run a short "
            "diagnostic conversation at their level to find gaps, then drill "
            "what you discover."
        )

    return [stable_block, {"type": "text", "text": context_text}]


def sanitize_history(messages: list[dict]) -> list[dict[str, str]]:
    """Validate and bound the client-supplied chat history.

    Keeps only user/assistant roles with non-empty string content, truncates
    oversized messages, caps history length, and ensures the conversation
    starts with a user turn.
    """
    cleaned: list[dict[str, str]] = []
    for msg in messages[-MAX_HISTORY_MESSAGES:]:
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()[:MAX_MESSAGE_CHARS]
        if content:
            cleaned.append({"role": role, "content": content})

    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


async def tutor_chat(
    language_code: str,
    messages: list[dict],
    weak_areas: list[dict],
) -> str:
    """Run one tutor turn and return the assistant's reply text."""
    settings = get_settings()
    history = sanitize_history(messages)
    if not history:
        raise ValueError("Conversation must contain at least one user message")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.tutor_model,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=build_system_blocks(language_code, weak_areas),
        messages=history,
    )

    return next(
        (block.text for block in response.content if block.type == "text"),
        "",
    )
