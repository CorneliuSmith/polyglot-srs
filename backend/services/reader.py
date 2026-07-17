"""WP21: The Reader — comprehensible input on demand.

One Claude call produces a complete reading artifact: a short text on the
learner's topic, level-locked to the grammar and vocabulary they have
actually learned, deliberately seeding a handful of new words in guessable
contexts — plus the token-level gloss map, per-sentence translations, and
the list of grammar structures used. Everything the three-stage reader UI
needs ships in that one response; hovers never cost a second call.

The response is forced through a tool call (`emit_reading`) so the shape
is schema-guaranteed rather than parsed out of prose.
"""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from backend.config import get_settings

MAX_TOPIC_CHARS = 120

READING_TOOL: dict[str, Any] = {
    "name": "emit_reading",
    "description": "Return the finished reading in exactly this structure.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short title in the target language."},
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "translation": {"type": "string"},
                        "tokens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "t": {"type": "string",
                                          "description": "The word as it appears, punctuation attached."},
                                    "gloss": {"type": "string",
                                              "description": "Contextual meaning, 1–4 words."},
                                    "new": {"type": "boolean",
                                            "description": "True only on deliberately seeded new words."},
                                },
                                "required": ["t", "gloss"],
                            },
                        },
                    },
                    "required": ["text", "translation", "tokens"],
                },
            },
            "new_words": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string"},
                        "gloss": {"type": "string"},
                        "sentence_index": {"type": "integer"},
                    },
                    "required": ["word", "gloss", "sentence_index"],
                },
            },
            "structures": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Every grammar structure the text uses, named plainly.",
            },
        },
        "required": ["title", "sentences", "new_words", "structures"],
    },
}


def _system_prompt(language_code: str, gloss_locale: str, learner: dict) -> str:
    known_words = ", ".join(learner.get("known_words") or [])
    structures = "; ".join(learner.get("learned_structures") or [])
    weak = ", ".join(learner.get("weak_words") or [])
    focus = "; ".join(learner.get("focus") or [])
    level = learner.get("level") or "A1"
    return f"""You write reading material for one specific learner inside \
PolyglotSRS, a spaced-repetition language app. Target language: \
{language_code}. The learner's level: {level}.

Write 150–250 words on the requested topic — natural, warm, factually \
grounded prose, never a vocabulary exercise dressed as a text.

HARD CONSTRAINTS:
- Grammar: use ONLY structures the learner has learned: {structures or "the absolute basics (present tense, simple sentences)"}.
- Vocabulary: stay within what a {level} learner knows. Their strongest \
known words, for calibration: {known_words or "(new learner — use only top-frequency words)"}.
- Seed EXACTLY 5–8 genuinely NEW words the learner is likely to meet next \
at this level. Each must appear in a context that makes its meaning \
guessable without a dictionary. Mark them new:true in the tokens and list \
them in new_words.
- Where natural (never forced), re-expose these weak words: {weak or "(none)"} \
and these focus structures: {focus or "(none)"}.

Then call emit_reading. Token rules: tokens must cover each sentence's \
words in order (punctuation attached to its word); every token carries a \
short contextual gloss in {gloss_locale}; per-sentence translations in \
{gloss_locale}; in structures, name every grammar structure the text uses \
in plain English — reuse the learner's structure names above verbatim \
where they apply, and name anything beyond them honestly (those feed the \
app's curriculum-gap log)."""


def _mock_reading(topic: str) -> dict:
    """Deterministic reading for tutor_dev_mock — exercises the full flow
    (generation, storage, stages, gap log) with no API key."""
    return {
        "title": f"[dev mock] {topic}",
        "sentences": [
            {
                "text": "El gato duerme en la ventana.",
                "translation": "The cat sleeps in the window.",
                "tokens": [
                    {"t": "El", "gloss": "the"},
                    {"t": "gato", "gloss": "cat"},
                    {"t": "duerme", "gloss": "sleeps"},
                    {"t": "en", "gloss": "in"},
                    {"t": "la", "gloss": "the"},
                    {"t": "ventana.", "gloss": "window", "new": True},
                ],
            },
            {
                "text": "Le gusta el sol de la mañana.",
                "translation": "It likes the morning sun.",
                "tokens": [
                    {"t": "Le", "gloss": "to it"},
                    {"t": "gusta", "gloss": "pleases"},
                    {"t": "el", "gloss": "the"},
                    {"t": "sol", "gloss": "sun", "new": True},
                    {"t": "de", "gloss": "of"},
                    {"t": "la", "gloss": "the"},
                    {"t": "mañana.", "gloss": "morning"},
                ],
            },
        ],
        "new_words": [
            {"word": "ventana", "gloss": "window", "sentence_index": 0},
            {"word": "sol", "gloss": "sun", "sentence_index": 1},
        ],
        "structures": ["Present tense", "Gustar and similar verbs",
                       "[dev mock] an uncovered structure"],
    }


def _validate_reading(payload: dict) -> dict:
    """Shape sanity beyond the schema: no empty text, tokens everywhere."""
    sentences = payload.get("sentences") or []
    if not sentences:
        raise ValueError("Reading came back with no sentences")
    for s in sentences:
        if not (s.get("text") or "").strip() or not s.get("tokens"):
            raise ValueError("Reading sentence missing text or tokens")
    return payload


async def generate_reading(
    language_code: str,
    topic: str,
    learner: dict,
    gloss_locale: str = "en",
    model: str | None = None,
) -> tuple[dict, dict[str, int]]:
    """Generate one reading. Returns (reading, usage token counts)."""
    settings = get_settings()
    model = model or settings.tutor_model

    if getattr(settings, "tutor_dev_mock", False):
        return _validate_reading(_mock_reading(topic)), {
            "input_tokens": 10, "output_tokens": 50,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
        }

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=8192,
        system=_system_prompt(language_code, gloss_locale, learner),
        messages=[{
            "role": "user",
            "content": f"Please write me something to read about: {topic}",
        }],
        tools=[READING_TOOL],
        tool_choice={"type": "tool", "name": "emit_reading"},
    )
    usage = getattr(response, "usage", None)
    counts = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None or not isinstance(tool_use.input, dict):
        raise ValueError("Reading generation returned no structured payload")
    return _validate_reading(tool_use.input), counts


async def explain_sentence(
    language_code: str,
    sentence: str,
    translation: str,
    level: str,
    model: str | None = None,
) -> tuple[str, dict[str, int]]:
    """Stage-3 on-demand explanation of one sentence's grammar."""
    settings = get_settings()
    model = model or settings.tutor_model

    if getattr(settings, "tutor_dev_mock", False):
        return (
            f"[dev mock] '{sentence}' breaks down word by word; the "
            f"structure is level-appropriate for {level}.",
            {"input_tokens": 5, "output_tokens": 20,
             "cache_write_tokens": 0, "cache_read_tokens": 0},
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=(
            f"You explain one {language_code} sentence to a {level} learner. "
            "Under 120 words: what each part does grammatically and why the "
            "sentence means what it means. Plain English, no jargon the "
            "level doesn't know yet."
        ),
        messages=[{
            "role": "user",
            "content": f"Sentence: {sentence}\nIt means: {translation}",
        }],
    )
    usage = getattr(response, "usage", None)
    counts = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    reply = next((b.text for b in response.content if b.type == "text"), "")
    return reply, counts
