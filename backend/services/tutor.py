"""AI tutor service — per-language tutoring agents powered by the Claude API.

Each language gets a tutor persona with real linguistic expertise (the same
grammar dimensions the NLP backends model), and every conversation is
grounded in two layers of learner data:

  1. SRS failure data — the cards they keep getting wrong (queried per turn).
  2. Durable learner memory — a global profile (native language, goals,
     interests) plus a per-language profile (proficiency, qualitative error
     patterns) and a rolling session summary, so the tutor remembers the
     student across sessions.

Memory is read at the start of every turn (grounding) and written two ways
(hybrid): the tutor's `remember` tool locks in high-salience facts mid-chat,
and a cheaper post-session summarizer folds the conversation into the profile
and a fresh session summary. This is the agent analogue of reading/writing
markdown context files in a Claude project.

Prompt structure (ordered for prompt caching — stable prefix first):
  system[0]  shared tutor charter + per-language linguistics brief (cached)
  system[1]  learner memory (profiles + summary) + SRS weak areas (volatile)
  messages   the chat history from the client
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic

from backend.config import get_settings

MAX_HISTORY_MESSAGES = 40
MAX_MESSAGE_CHARS = 4000
MAX_TOOL_ITERATIONS = 4

_LANGUAGE_BRIEFS: dict[str, str] = {
    "ru": (
        "Language: Russian.\n"
        "You are an expert in Slavic linguistics. Key teaching dimensions: the "
        "six grammatical cases and their declension patterns; verb aspect pairs "
        "(imperfective/perfective) and when each is used; gender and animacy; "
        "verbs of motion. When the learner confuses an aspect partner, contrast "
        "the pair with minimal-pair example sentences. Always show stress marks "
        "when introducing new words. Register: flag the ты/вы distinction and "
        "mark colloquial vs bookish forms."
    ),
    "ar": (
        "Language: Modern Standard Arabic.\n"
        "You are an expert in Semitic linguistics. Key teaching dimensions: the "
        "trilateral root system (e.g. ك-ت-ب) and verb forms I–X; broken vs sound "
        "plurals; dual number; the three cases. Use tashkeel (diacritics) as a "
        "learning aid when introducing words, but never penalize the learner "
        "for omitting them. Connect new words to roots the learner already "
        "knows. Register: distinguish MSA from dialect, and note when a word is "
        "literary vs everyday; tell the learner when MSA would sound stilted."
    ),
    "en": (
        "Language: English.\n"
        "You are an expert in English as a second language. Key teaching "
        "dimensions: the article system (the/a/an — hardest for Russian and "
        "Arabic speakers), irregular verbs, and phrasal verbs. Accept both "
        "British and American spellings. Teach articles through contrastive "
        "examples rather than rules. Register: contrast formal/written English "
        "with everyday conversational usage and contractions."
    ),
    "sw": (
        "Language: Swahili.\n"
        "You are an expert in Bantu linguistics. Key teaching dimensions: the "
        "noun class system (ki-/vi-, m-/wa-, m-/mi-, ji-/ma- and agreement "
        "across the sentence); verb morphology (subject prefix + tense marker "
        "+ stem, e.g. ni-na-soma); and how adjectives and verbs agree with "
        "noun classes. Decompose conjugated verbs into their morphemes so the "
        "learner sees the system, not memorized strings. Register: distinguish "
        "Standard (Coastal) Swahili from colloquial urban speech and note "
        "Arabic-derived formal vocabulary."
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
        "they accidentally typed so they hear why tone matters. Register: note "
        "proverb/idiom usage (highly valued in Yoruba) and honorific pronouns."
    ),
    "tr": (
        "Language: Turkish.\n"
        "You are an expert in Turkic linguistics. Key teaching dimensions: "
        "agglutination and suffix ordering; two- and four-way vowel harmony "
        "(and how it selects suffix variants like -lar/-ler, -da/-de); the six "
        "cases; and the dotted/dotless i distinction. When the learner gets a "
        "suffix wrong, walk through the harmony rule that selects the correct "
        "variant rather than just giving the answer. Register: flag the formal "
        "-iyor/-makta written style vs spoken forms and polite siz address."
    ),
    "ha": (
        "Language: Hausa.\n"
        "You are an expert in Chadic (Afro-Asiatic) linguistics. Key teaching "
        "dimensions: grammatical gender (masculine/feminine) and how it drives "
        "agreement; the many irregular/broken plural patterns; the hooked "
        "consonants ɓ, ɗ, ƙ and glottalized ʼy as distinct letters; and the "
        "tense-aspect-mood pronoun sets (completive, continuous, future) that "
        "carry most of the grammar. Tone and vowel length are real but unwritten "
        "— teach them by ear, never mark the learner wrong for omitting them. "
        "Register: note Standard (Kano) Hausa vs regional forms and the heavy "
        "use of greetings/honorifics in everyday speech."
    ),
    "xh": (
        "Language: Xhosa.\n"
        "You are an expert in Bantu (Nguni) linguistics, specializing in Xhosa. "
        "Key teaching dimensions: the noun class system (um-/aba-, um-/imi-, "
        "ili-/ama-, isi-/izi-, in-/izin-, ulu-, ubu-, uku-) and the concord "
        "agreement it forces on verbs and adjectives; agglutinating verb "
        "morphology (subject concord + tense + object concord + root); and the "
        "three click consonants written c (dental), q (palatal), x (lateral). "
        "Decompose words into morphemes so the learner sees the class system, "
        "and treat clicks as ordinary letters in writing. Register: note "
        "hlonipha (respect) vocabulary and standard vs colloquial usage."
    ),
}

_TUTOR_CHARTER = """\
You are a private language tutor inside PolyglotSRS, a spaced-repetition \
language learning app. The learner reviews flashcards daily; you are the \
paid coaching add-on that turns their data into progress.

Teaching method: favor comprehensible input slightly above the learner's \
level, contrastive minimal pairs, and spaced re-exposure to weak items. \
Prioritize production (getting them to say/write it) over recognition. \
Introduce register explicitly — when a word or form is formal, colloquial, \
or regional, say so, because learners need to know what's safe to use where.

How to tutor:
- Use the learner's study performance (below) to set the session's ambition: \
if accuracy is low or the streak just broke, consolidate; if they're strong, \
push into new material.
- Coach on the learner's weak items (provided below) before anything else. \
Weave those exact words into short practice exchanges, fill-in-the-blank \
drills, and example sentences.
- Use what you know about the learner (their profile and the summary of past \
sessions, below) to personalize: pick topics they care about, account for \
their native language's interference, and pick up where you left off.
- Keep turns short and interactive: one concept or drill per message, then \
ask the learner to produce language. Never lecture for more than a short \
paragraph.
- Correct errors by showing the contrast between what they said and the \
target form, then have them retry a similar item.
- Use English for explanations, the target language for practice. Calibrate \
difficulty to the CEFR levels of their weak items.
- Be encouraging but honest — name the pattern behind their errors when you \
see one (e.g. "you keep missing the locative case").

When you learn something durable and worth remembering next session — the \
learner's goal or motivation, their native language, an interest to build \
lessons around, or a recurring error pattern — call the `remember` tool. \
Use it sparingly and only for things that should persist; do not record \
transient chat.
"""

# The `remember` tool is the live half of the hybrid memory strategy.
REMEMBER_TOOL: dict[str, Any] = {
    "name": "remember",
    "description": (
        "Save a durable fact about the learner for future sessions. Use only "
        "for things worth remembering next time, not transient conversation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["global", "language"],
                "description": (
                    "global = true across all languages the learner studies "
                    "(native language, why they're learning, other languages, "
                    "broad preferences). language = specific to the current "
                    "language (proficiency, a recurring error pattern, a topic "
                    "covered)."
                ),
            },
            "key": {
                "type": "string",
                "description": "Short snake_case label, e.g. motivation, native_language, error_pattern, interest.",
            },
            "value": {
                "type": "string",
                "description": "The fact to remember, stated concisely.",
            },
        },
        "required": ["scope", "key", "value"],
    },
}


def _format_memory(
    user_profile: dict | None,
    language_profile: dict | None,
    session_summary: str | None,
    weak_areas: list[dict],
    study_stats: dict | None = None,
) -> str:
    """Build the volatile learner-context block (memory + SRS data)."""
    parts: list[str] = []

    if study_stats:
        parts.append(
            "Study performance in this language (from the app's SRS):\n"
            + json.dumps(study_stats, ensure_ascii=False, indent=1)
        )
    if user_profile:
        parts.append(
            "Learner profile (applies across all their languages):\n"
            + json.dumps(user_profile, ensure_ascii=False, indent=1)
        )
    if language_profile:
        parts.append(
            "Learner profile for this language (proficiency, error patterns, "
            "topics covered):\n"
            + json.dumps(language_profile, ensure_ascii=False, indent=1)
        )
    if session_summary:
        parts.append(f"Summary of recent sessions:\n{session_summary}")

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
        parts.append(
            "Current weak items (from their SRS review history, worst first):\n"
            + json.dumps(items, ensure_ascii=False, indent=1)
        )

    if not parts:
        return (
            "You don't know anything about this learner yet, and they have no "
            "recorded weak items. Run a short diagnostic conversation at their "
            "level to find gaps and learn about their goals, then drill what "
            "you discover (and `remember` what's worth keeping)."
        )
    return "\n\n".join(parts)


def build_system_blocks(
    language_code: str,
    weak_areas: list[dict],
    user_profile: dict | None = None,
    language_profile: dict | None = None,
    session_summary: str | None = None,
    study_stats: dict | None = None,
) -> list[dict[str, Any]]:
    """Build the system prompt blocks for a tutor conversation.

    Block 0 (charter + linguistics brief) is stable per language and carries a
    cache_control marker. Block 1 (learner memory + SRS weak items) varies per
    user and per turn, so it sits after the cache breakpoint.
    """
    brief = _LANGUAGE_BRIEFS.get(language_code)
    if brief is None:
        raise ValueError(f"No tutor available for language code '{language_code}'")

    return [
        {
            "type": "text",
            "text": f"{_TUTOR_CHARTER}\n{brief}",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": _format_memory(
                user_profile, language_profile, session_summary,
                weak_areas, study_stats,
            ),
        },
    ]


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


def merge_remembered(
    user_profile: dict,
    language_profile: dict,
    remembered: list[dict],
) -> tuple[dict, dict]:
    """Fold `remember` tool outputs into the two profile dicts (pure).

    Returns new (user_profile, language_profile). Repeated keys are collected
    into a list so the tutor can record several error patterns or interests
    without overwriting earlier ones.
    """
    user = dict(user_profile)
    lang = dict(language_profile)
    for note in remembered:
        scope = note.get("scope")
        key = note.get("key")
        value = note.get("value")
        if not key or value is None:
            continue
        target = user if scope == "global" else lang
        existing = target.get(key)
        if existing is None:
            target[key] = value
        elif isinstance(existing, list):
            if value not in existing:
                existing.append(value)
        elif existing != value:
            target[key] = [existing, value]
    return user, lang


async def tutor_chat(
    language_code: str,
    messages: list[dict],
    weak_areas: list[dict],
    user_profile: dict | None = None,
    language_profile: dict | None = None,
    session_summary: str | None = None,
    study_stats: dict | None = None,
) -> tuple[str, list[dict]]:
    """Run one tutor turn.

    Returns (reply_text, remembered) where `remembered` is the list of
    `remember` tool payloads ({"scope", "key", "value"}) the tutor emitted
    this turn, for the caller to persist.
    """
    settings = get_settings()
    history = sanitize_history(messages)
    if not history:
        raise ValueError("Conversation must contain at least one user message")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = build_system_blocks(
        language_code, weak_areas, user_profile, language_profile,
        session_summary, study_stats,
    )
    convo: list[dict[str, Any]] = list(history)
    remembered: list[dict] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = await client.messages.create(
            model=settings.tutor_model,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=system,
            messages=convo,
            tools=[REMEMBER_TOOL],
        )

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            reply = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return reply, remembered

        # Echo the assistant turn back verbatim (preserves thinking blocks),
        # then answer each remember call so the model can continue.
        convo.append({"role": "assistant", "content": response.content})
        results = []
        for tu in tool_uses:
            if tu.name == "remember" and isinstance(tu.input, dict):
                remembered.append({
                    "scope": tu.input.get("scope"),
                    "key": tu.input.get("key"),
                    "value": tu.input.get("value"),
                })
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": "Saved.",
            })
        convo.append({"role": "user", "content": results})

    # Tool loop exhausted — make one final non-tool call for the reply.
    response = await client.messages.create(
        model=settings.tutor_model,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system,
        messages=convo,
    )
    reply = next((b.text for b in response.content if b.type == "text"), "")
    return reply, remembered


_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "user_profile_updates": {
            "type": "object",
            "description": (
                "Global facts learned this session (native language, goals, "
                "motivation, interests). Keys are snake_case labels; values are "
                "concise strings. Empty object if nothing new."
            ),
            "additionalProperties": {"type": "string"},
        },
        "language_profile_updates": {
            "type": "object",
            "description": (
                "Facts specific to this language (proficiency, recurring error "
                "patterns, topics covered). Empty object if nothing new."
            ),
            "additionalProperties": {"type": "string"},
        },
        "session_summary": {
            "type": "string",
            "description": (
                "A concise running summary of where the learner is: what was "
                "practiced, what they struggled with, and what to pick up next "
                "session. Rewrites (does not append to) the prior summary."
            ),
        },
    },
    "required": [
        "user_profile_updates",
        "language_profile_updates",
        "session_summary",
    ],
    "additionalProperties": False,
}


async def summarize_session(
    language_code: str,
    messages: list[dict],
    user_profile: dict | None = None,
    language_profile: dict | None = None,
    prior_summary: str | None = None,
) -> dict:
    """Post-session memory extraction on a cheaper model.

    Reads the transcript plus current memory and returns structured updates:
        {"user_profile_updates": {...},
         "language_profile_updates": {...},
         "session_summary": "..."}
    """
    settings = get_settings()
    history = sanitize_history(messages)
    if not history:
        return {
            "user_profile_updates": {},
            "language_profile_updates": {},
            "session_summary": prior_summary or "",
        }

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    system = (
        "You maintain a language learner's memory for a tutoring app. Given the "
        "current profile and a tutoring transcript, extract only durable facts "
        "worth keeping for next session and write a concise running summary. Do "
        "not invent facts the transcript doesn't support. Keep the summary "
        "focused on proficiency, struggles, and what to do next."
    )
    context = {
        "language": language_code,
        "current_user_profile": user_profile or {},
        "current_language_profile": language_profile or {},
        "prior_summary": prior_summary or "",
    }

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.tutor_summary_model,
        max_tokens=1024,
        system=system,
        messages=[{
            "role": "user",
            "content": (
                f"Current memory:\n{json.dumps(context, ensure_ascii=False)}\n\n"
                f"Session transcript:\n{transcript}"
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _SUMMARY_SCHEMA}},
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {
            "user_profile_updates": {},
            "language_profile_updates": {},
            "session_summary": prior_summary or "",
        }
    return {
        "user_profile_updates": data.get("user_profile_updates") or {},
        "language_profile_updates": data.get("language_profile_updates") or {},
        "session_summary": data.get("session_summary") or (prior_summary or ""),
    }
