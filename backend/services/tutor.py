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
and a fresh study-session summary when the learner ends or leaves a session.

Prompt structure (ordered for prompt caching — stable prefix first):
  system[0]  shared tutor charter + per-language linguistics brief (cached)
  system[1]  learner memory (profiles + summary) + SRS weak areas (volatile)
  messages   the chat history from the client
"""

from __future__ import annotations

import json
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic

from backend.config import get_settings

MAX_HISTORY_MESSAGES = 40
MAX_MESSAGE_CHARS = 4000
MAX_TOOL_ITERATIONS = 4

# ── Tutor skills (WP15b) ─────────────────────────────────────────────────
# Per-language knowledge lives in skill bundles on disk, one directory per
# language under tutor_skills/:
#   SKILL.md     — the core brief; always in the prompt (kept small).
#   REFERENCE.md — the app's CEFR-staged grammar path (generated from
#                  data/grammar, so coaching uses the learner's card titles).
#   ERRORS.md    — common interference errors + coaching moves.
# REFERENCE/ERRORS load on demand via the consult_reference tool, so deep
# knowledge never bloats the per-turn context (progressive disclosure).
# Derived expertise only — never quotes of licensed resources.

# Languages where tutoring accuracy is the product differentiator and the
# stronger (costlier) model is worth it — the §6 model guide's low-resource
# set. The admin's per-language override (languages.tutor_model) always wins;
# this only picks the DEFAULT when no override is set.
LOW_RESOURCE_LANGUAGES = frozenset({"mi", "sw", "yo", "ha", "xh", "ar"})


def resolve_tutor_model(language_code: str, override: str | None = None) -> str:
    """The model a tutor turn runs on.

    Priority: admin per-language override > low-resource default > global
    default. Cost context: Sonnet-tier is ~40% of Opus per token and handles
    high-resource coaching well; low-resource languages pin the stronger
    model because errors there damage the differentiator.
    """
    if override:
        return override
    settings = get_settings()
    if language_code in LOW_RESOURCE_LANGUAGES:
        return settings.tutor_model_low_resource
    return settings.tutor_model


SKILLS_DIR = Path(__file__).parent / "tutor_skills"

_REFERENCE_TOPICS = {"reference": "REFERENCE.md", "errors": "ERRORS.md"}


@cache
def _load_skill(language_code: str) -> str | None:
    """The always-loaded core brief for a language (None = no tutor)."""
    path = SKILLS_DIR / language_code / "SKILL.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


@cache
def load_reference(language_code: str, topic: str) -> str | None:
    """An on-demand reference file for the consult_reference tool."""
    filename = _REFERENCE_TOPICS.get(topic)
    if filename is None:
        return None
    path = SKILLS_DIR / language_code / filename
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def available_tutors() -> frozenset[str]:
    """Language codes that have a skill bundle (and therefore a tutor)."""
    if not SKILLS_DIR.is_dir():
        return frozenset()
    return frozenset(
        p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")
    )

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
- Weak items with kind=grammar are PATTERNS, not words: drill them with \
fill-in-the-blank sentences that exercise exactly that structure (consult \
the curriculum reference to match the point's name and staging), never as \
vocabulary flashcards.
- Maintain the Active Focus list (shown in the learner's language profile \
as _active_focus, max 5): the structures you are deliberately working on \
across sessions. Open sessions from it, weave its items into practice, add \
a structure with `remember` scope focus_add when a systematic gap appears, \
and retire it with focus_retire once the learner produces it reliably.
- When the learner asks a REFERENCE question (marked in your context): \
answer it directly and stop — no drills, no `remember` calls, no pivot \
back to practice unless they ask.

Your knowledge has two layers. This core brief is always present. Two \
deeper references load on demand through the `consult_reference` tool: \
'reference' is the app's full grammar path in teaching order (the exact \
point titles on the learner's cards — consult it before introducing new \
grammar, so your sequence matches theirs), and 'errors' is the language's \
common learner errors with coaching moves (consult it when a mistake looks \
systematic). Load at most one per turn and only when this brief isn't \
enough — keep the working context small.

When you learn something durable and worth remembering next session — the \
learner's goal or motivation, their native language, an interest to build \
lessons around, or a recurring error pattern — call the `remember` tool. \
Use it sparingly and only for things that should persist; do not record \
transient chat.

Mastery stars: when THIS session gives clear evidence the learner has \
already mastered one of their weak items — they produced the exact \
structure or word correctly, unprompted, more than once — call \
`suggest_mastered` to star that card. The learner reviews your stars and \
decides; their card only advances if they agree, so never present a star \
as a done deal. Star sparingly (at most a couple per session), only items \
from their weak-items list, and never in reference mode.
"""

CONSULT_TOOL: dict[str, Any] = {
    "name": "consult_reference",
    "description": (
        "Load a deeper reference for the current language: 'reference' = the "
        "app's full grammar path in teaching order (use before introducing "
        "new grammar); 'errors' = common learner errors and coaching moves "
        "(use when a mistake looks systematic). Load at most one per turn."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "enum": ["reference", "errors"],
                "description": "Which reference to load.",
            },
        },
        "required": ["topic"],
    },
}


# WP19(e): the tutor STARS cards it believes are already mastered; the
# learner confirms (or dismisses) in the UI. The tool only records the
# suggestion — SRS state never moves without the learner's explicit accept.
SUGGEST_MASTERED_TOOL: dict[str, Any] = {
    "name": "suggest_mastered",
    "description": (
        "Star a flashcard you believe the learner has already mastered, "
        "based on evidence from THIS session (they produced the word or "
        "structure correctly, unprompted, more than once). The learner "
        "will be asked to confirm; nothing changes without their "
        "agreement. Use sparingly — at most a couple per session, and "
        "only for items on their weak-items list."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "item": {
                "type": "string",
                "description": (
                    "The word or grammar point title EXACTLY as it appears "
                    "in the learner's weak-items list (that is the card's "
                    "name — a paraphrase won't match)."
                ),
            },
            "kind": {
                "type": "string",
                "enum": ["vocabulary", "grammar"],
                "description": "Which kind of card the item is.",
            },
            "evidence": {
                "type": "string",
                "description": (
                    "One sentence of evidence from this session, quoted or "
                    "paraphrased — the learner sees this next to the star."
                ),
            },
        },
        "required": ["item", "kind", "evidence"],
    },
}


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
                "enum": ["global", "language", "focus_add", "focus_retire"],
                "description": (
                    "global = true across all languages the learner studies "
                    "(native language, why they're learning, other languages, "
                    "broad preferences). language = specific to the current "
                    "language (proficiency, a recurring error pattern, a topic "
                    "covered). focus_add = put a grammar structure on the "
                    "Active Focus list (key = the structure's name, value = "
                    "why it needs focused work; max 5 — retire something "
                    "first if full). focus_retire = remove a mastered "
                    "structure (key = its name, value = evidence of mastery)."
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
            item = {
                # 'vocabulary' = a word; 'grammar' = a grammar point/pattern
                "kind": area.get("kind") or "vocabulary",
                "word": area.get("word"),
                "meaning": area.get("definition"),
                "part_of_speech": area.get("part_of_speech"),
                "recent_failures": int(area.get("recent_failures") or 0),
                "total_lapses": int(area.get("lapses") or 0),
                "morphology": morph or {},
            }
            if area.get("level"):
                item["cefr_level"] = area["level"]
            items.append(item)
        parts.append(
            "Current weak items (from their SRS review history, worst first; "
            "kind=grammar means a grammar pattern to coach, not a word):\n"
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
    mode: str = "practice",
) -> list[dict[str, Any]]:
    """Build the system prompt blocks for a tutor conversation.

    Block 0 (charter + linguistics brief) is stable per language and carries a
    cache_control marker. Block 1 (learner memory + SRS weak items) varies per
    user and per turn, so it sits after the cache breakpoint.
    """
    brief = _load_skill(language_code)
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
            )
            + (
                "\n\nMODE: the learner flagged this as a REFERENCE question — "
                "answer it directly; no drills, no memory writes."
                if mode == "reference" else ""
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
        if scope == "_mastery":
            # Mastery stars are suggestion rows, not profile facts — the
            # router persists them separately. Never fold into a profile.
            continue
        if scope in ("focus_add", "focus_retire"):
            # WP18b: the Active Focus list — a bounded, tutor-managed set of
            # grammar structures under deliberate work (≈ the owner's 📍
            # "Active Focus" in claude_grammar.md). Bounded FIFO at 5.
            focus = [
                f for f in lang.get("_active_focus") or []
                if isinstance(f, dict) and f.get("structure")
            ]
            if scope == "focus_add":
                focus = [f for f in focus if f["structure"] != key]
                focus.append({"structure": key, "reason": value})
                lang["_active_focus"] = focus[-5:]
            else:
                lang["_active_focus"] = [
                    f for f in focus if f["structure"] != key
                ]
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


def _empty_usage() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
    }


def _add_usage(total: dict[str, int], usage: Any) -> None:
    """Accumulate an Anthropic usage block into *total*.

    A tool-loop turn makes several API calls; the operator's cost unit is
    the whole turn, so counts are summed across calls.
    """
    if usage is None:
        return
    total["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
    total["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
    total["cache_write_tokens"] += (
        getattr(usage, "cache_creation_input_tokens", 0) or 0
    )
    total["cache_read_tokens"] += getattr(usage, "cache_read_input_tokens", 0) or 0


def _mock_usage(history: list[dict], reply: str) -> dict[str, int]:
    """Deterministic pseudo-usage for dev mock (~4 chars/token) so the admin
    cost view has data to render without an API key."""
    prompt_chars = sum(len(m["content"]) for m in history)
    return {
        "input_tokens": prompt_chars // 4 + 1,
        "output_tokens": len(reply) // 4 + 1,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
    }


def _mock_chat(language_code: str, history: list[dict], weak_areas: list[dict]) -> tuple[str, list[dict]]:
    """Canned tutor turn for dev mock mode — no Claude API call.

    Echoes context so the chat UI is exercised, drills the first weak item if
    present, and supports a `/remember <scope> <key> <value>` command so the
    remember→persist path can be tested deterministically.
    """
    last_user = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )
    remembered: list[dict] = []
    if last_user.startswith("/remember"):
        parts = last_user.split(maxsplit=3)
        if len(parts) == 4 and parts[1] in ("global", "language"):
            remembered.append({"scope": parts[1], "key": parts[2], "value": parts[3]})
            return f"[dev mock] Remembered ({parts[1]}) {parts[2]} = {parts[3]}.", remembered
    # `/star <kind> <item> <evidence>` exercises the mastery-star path
    # (suggest_mastered → suggestion row) deterministically.
    if last_user.startswith("/star"):
        parts = last_user.split(maxsplit=3)
        if len(parts) == 4 and parts[1] in ("vocabulary", "grammar"):
            remembered.append({
                "scope": "_mastery", "key": parts[1],
                "value": parts[2], "evidence": parts[3],
            })
            return f"[dev mock] Starred ({parts[1]}) {parts[2]}.", remembered

    drill = ""
    if weak_areas:
        w = weak_areas[0]
        drill = (
            f' Let\'s drill "{w.get("word")}" ({w.get("definition")}) — '
            "use it in a sentence."
        )
    reply = (
        f"[dev mock tutor — no Claude API call] I'm your {language_code} tutor. "
        f'You said: "{last_user[:120]}".{drill}'
    )
    return reply, remembered


def _execute_tools(
    tool_uses: list[Any], language_code: str, remembered: list[dict]
) -> list[dict]:
    """Run this turn's tool calls (shared by both chat loops).

    `remember` payloads accumulate into *remembered* for the caller to
    persist; `consult_reference` answers from the skill bundle on disk.
    """
    results = []
    for tu in tool_uses:
        content = "Unknown tool."
        if tu.name == "remember" and isinstance(tu.input, dict):
            remembered.append({
                "scope": tu.input.get("scope"),
                "key": tu.input.get("key"),
                "value": tu.input.get("value"),
            })
            content = "Saved."
        elif tu.name == "suggest_mastered" and isinstance(tu.input, dict):
            # Rides the `remembered` accumulator under the reserved
            # "_mastery" scope; the router partitions it out and records a
            # suggestion row for the learner to confirm.
            remembered.append({
                "scope": "_mastery",
                "key": tu.input.get("kind"),
                "value": tu.input.get("item"),
                "evidence": tu.input.get("evidence"),
            })
            content = "Starred — the learner will be asked to confirm."
        elif tu.name == "consult_reference" and isinstance(tu.input, dict):
            content = (
                load_reference(language_code, tu.input.get("topic") or "")
                or "No reference available on that topic."
            )
        results.append({
            "type": "tool_result",
            "tool_use_id": tu.id,
            "content": content,
        })
    return results


async def tutor_chat(
    language_code: str,
    messages: list[dict],
    weak_areas: list[dict],
    user_profile: dict | None = None,
    language_profile: dict | None = None,
    session_summary: str | None = None,
    study_stats: dict | None = None,
    model: str | None = None,
    mode: str = "practice",
) -> tuple[str, list[dict], dict[str, int]]:
    """Run one tutor turn.

    Returns (reply_text, remembered, usage): `remembered` is the list of
    `remember` tool payloads ({"scope", "key", "value"}) the tutor emitted
    this turn, for the caller to persist; `usage` is the turn's token counts
    summed across tool-loop calls (WP9b cost capture). *model* overrides the
    global default (WP15a: per-language tutor models).
    """
    settings = get_settings()
    model = model or settings.tutor_model
    history = sanitize_history(messages)
    if not history:
        raise ValueError("Conversation must contain at least one user message")

    if getattr(settings, "tutor_dev_mock", False):
        reply, remembered = _mock_chat(language_code, history, weak_areas)
        return reply, remembered, _mock_usage(history, reply)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = build_system_blocks(
        language_code, weak_areas, user_profile, language_profile,
        session_summary, study_stats, mode=mode,
    )
    convo: list[dict[str, Any]] = list(history)
    remembered: list[dict] = []
    usage = _empty_usage()

    for _ in range(MAX_TOOL_ITERATIONS):
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=system,
            messages=convo,
            tools=[REMEMBER_TOOL, CONSULT_TOOL, SUGGEST_MASTERED_TOOL],
        )
        _add_usage(usage, getattr(response, "usage", None))

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            reply = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return reply, remembered, usage

        # Echo the assistant turn back verbatim (preserves thinking blocks),
        # then answer each tool call so the model can continue.
        convo.append({"role": "assistant", "content": response.content})
        convo.append({
            "role": "user",
            "content": _execute_tools(tool_uses, language_code, remembered),
        })

    # Tool loop exhausted — make one final non-tool call for the reply.
    response = await client.messages.create(
        model=model,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system,
        messages=convo,
    )
    _add_usage(usage, getattr(response, "usage", None))
    reply = next((b.text for b in response.content if b.type == "text"), "")
    return reply, remembered, usage


async def tutor_chat_stream(
    language_code: str,
    messages: list[dict],
    weak_areas: list[dict],
    user_profile: dict | None = None,
    language_profile: dict | None = None,
    session_summary: str | None = None,
    study_stats: dict | None = None,
    model: str | None = None,
    mode: str = "practice",
):
    """Streaming twin of tutor_chat (WP9d). Yields event dicts:

      {"type": "delta", "text": ...}   — a chunk of assistant text
      {"type": "reset"}                — the streamed text belonged to a
                                         tool-use turn; drop it and expect
                                         fresh deltas (rare: remember calls)
      {"type": "done", "reply": ..., "remembered": [...], "usage": {...}}

    The caller owns persistence (usage log, remembered facts) after "done" —
    and must strip "usage" before forwarding the event to the client.
    """
    settings = get_settings()
    model = model or settings.tutor_model
    history = sanitize_history(messages)
    if not history:
        raise ValueError("Conversation must contain at least one user message")

    if getattr(settings, "tutor_dev_mock", False):
        reply, remembered = _mock_chat(language_code, history, weak_areas)
        # Chunk the canned reply so the streaming UI path is exercised.
        for i in range(0, len(reply), 24):
            yield {"type": "delta", "text": reply[i:i + 24]}
        yield {
            "type": "done", "reply": reply, "remembered": remembered,
            "usage": _mock_usage(history, reply),
        }
        return

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = build_system_blocks(
        language_code, weak_areas, user_profile, language_profile,
        session_summary, study_stats, mode=mode,
    )
    convo: list[dict[str, Any]] = list(history)
    remembered: list[dict] = []
    usage = _empty_usage()

    for iteration in range(MAX_TOOL_ITERATIONS + 1):
        tools = (
            [REMEMBER_TOOL, CONSULT_TOOL, SUGGEST_MASTERED_TOOL]
            if iteration < MAX_TOOL_ITERATIONS else []
        )
        async with client.messages.stream(
            model=model,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=system,
            messages=convo,
            tools=tools,
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "delta", "text": text}
            response = await stream.get_final_message()
        _add_usage(usage, getattr(response, "usage", None))

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            reply = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            yield {
                "type": "done", "reply": reply, "remembered": remembered,
                "usage": usage,
            }
            return

        # The turn ended in tool calls; whatever text streamed belonged to
        # it. Tell the client to drop the buffer, then continue the loop.
        yield {"type": "reset"}
        convo.append({"role": "assistant", "content": response.content})
        convo.append({
            "role": "user",
            "content": _execute_tools(tool_uses, language_code, remembered),
        })


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
    recent_sessions: list[str] | None = None,
) -> dict:
    """Post-session memory extraction on a cheaper model.

    Reads the transcript plus current memory and returns structured updates:
        {"user_profile_updates": {...},
         "language_profile_updates": {...},
         "session_summary": "...",
         "usage": {...}}
    The "usage" key is present only when a model call actually ran (WP9b);
    the caller logs it as a kind='summary' cost row.
    """
    settings = get_settings()
    history = sanitize_history(messages)
    if not history:
        return {
            "user_profile_updates": {},
            "language_profile_updates": {},
            "session_summary": prior_summary or "",
        }

    if getattr(settings, "tutor_dev_mock", False):
        user_turns = [m["content"] for m in history if m["role"] == "user"]
        topics = ", ".join(t[:30] for t in user_turns[:3])
        summary = (
            f"[dev mock] {len(user_turns)} learner turns. "
            f"Topics touched: {topics}."
        )
        return {
            "user_profile_updates": {},
            "language_profile_updates": (
                {"last_session_topics": topics} if topics else {}
            ),
            "session_summary": summary,
            "usage": _mock_usage(history, summary),
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
        # WP18a: the last few APPEND-ONLY session summaries, so long-term
        # continuity survives the rolling summary being rewritten.
        "recent_sessions": recent_sessions or [],
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
    usage = _empty_usage()
    _add_usage(usage, getattr(response, "usage", None))
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {
            "user_profile_updates": {},
            "language_profile_updates": {},
            "session_summary": prior_summary or "",
            "usage": usage,
        }
    return {
        "user_profile_updates": data.get("user_profile_updates") or {},
        "language_profile_updates": data.get("language_profile_updates") or {},
        "session_summary": data.get("session_summary") or (prior_summary or ""),
        "usage": usage,
    }
