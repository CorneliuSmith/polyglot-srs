"""AI topic classification for the Topic Lens (docs/plans/topic-lens.md).

Sorts vocabulary into the fixed 24-bucket taxonomy so learners can swap
the "what to learn next" axis from CEFR level to meaning. The result is
PROVISIONAL — stored as topic_source='ai' and confirmed by a reviewer
(strict-policy languages hide unconfirmed topics from learners; 'ai_ok'
languages show them).

Mirrors level_estimate.py exactly: batched words+glosses in, a JSON-schema
enum out (the model cannot invent a bucket), words the model skips are
simply omitted and picked up by the next run's WHERE topic IS NULL.

Polyseme rule (a word with several meanings — *orange* the fruit and the
color): ONE bucket, the word's most common everyday sense. Reviewers
adjudicate; the prompt states the rule so the model and the reviewer are
applying the same one.

Dev-mock (TUTOR_DEV_MOCK) returns a deterministic assignment so the
pipeline is testable with no API key.
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model
from backend.services.topic_taxonomy import ALL_TOPICS

_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "topic": {"type": "string", "enum": list(ALL_TOPICS)},
                },
                "required": ["word", "topic"],
                # Required by the API on every object node — without it the
                # call 400s before the model runs (the recs schema shipped
                # that way and never produced a batch).
                "additionalProperties": False,
            },
        },
    },
    "required": ["topics"],
    "additionalProperties": False,
}

_GUIDE = """Buckets and their meaning (assign the word's most common everyday sense):
food_drink: meals, cooking, ingredients, restaurants, taste
home_living: the house, rooms, furniture, chores, daily routines
family_people: family members, life stages, describing people
relationships_social: friendship, love, invitations, celebrations, politeness
body_health: body parts, illness, medicine, fitness
clothing_appearance: garments, style, beauty
travel_transport: trips, vehicles, directions, hotels
city_places: buildings, shops, streets, landmarks
nature_weather_animals: landscapes, plants, animals, seasons, climate
time_dates: clock time, days, months, frequency
numbers_measure: counting, quantities, sizes, measurement
work_professions: professions, offices, business, employment
school_learning: education, studying, exams, languages
sports_leisure: games, hobbies, exercise, play
arts_media: music, film, books, news, television
technology: computers, phones, the internet, machines
communication: speaking, writing, asking, explaining, opinions
shopping_money: buying, prices, banks, possessions
emotions_mind: emotions, personality, thoughts, memory
society_politics: government, law, news events, community
religion_culture: traditions, holidays, religion, history
science_world: basic science, materials, space
abstract_general: very common words belonging to no subject (thing, way, become)
function_words: grammar glue — articles, pronouns, prepositions, conjunctions, particles"""


def _mock_topics(words: list[dict]) -> dict[str, str]:
    """Deterministic assignment for dev/tests."""
    return {w["word"]: ALL_TOPICS[i % len(ALL_TOPICS)]
            for i, w in enumerate(words)}


async def estimate_topics(
    words: list[dict],
    language_name: str,
    language_code: str,
    model: str | None = None,
) -> dict[str, str]:
    """Classify each word into one bucket. Returns {word: topic}; words the
    model skips are omitted (the caller leaves them untagged — the next
    run's WHERE topic IS NULL picks them up)."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_topics(words)

    listing = "\n".join(
        f"- {w['word']}"
        + (f" ({w['part_of_speech']})" if w.get("part_of_speech") else "")
        + (f": {w['definition']}" if w.get("definition") else "")
        for w in words
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model or resolve_model("level_estimate", language_code),
        max_tokens=4096,
        system=(
            "You sort vocabulary for a language course into fixed semantic "
            "buckets. One bucket per word — its most common everyday sense "
            "(orange -> food_drink, not a color). Use abstract_general only "
            "when no theme fits; use function_words for grammar glue.\n\n"
            + _GUIDE
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Classify these {language_name} ({language_code}) words. "
                f"Each line is word (part of speech): English meaning.\n\n"
                f"{listing}"
            ),
        }],
        tools=[{
            "name": "submit_topics",
            "description": "Submit one bucket per word.",
            "input_schema": _SCHEMA,
        }],
        tool_choice={"type": "tool", "name": "submit_topics"},
    )
    out: dict[str, str] = {}
    for block in response.content:
        if block.type == "tool_use":
            for item in block.input.get("topics", []):
                word, topic = item.get("word"), item.get("topic")
                if word and topic in ALL_TOPICS:
                    out[word] = topic
    return out


def dry_run_estimate(word_count: int) -> dict:
    """What a run would cost, before it runs — the same courtesy every
    other generator gives the admin. Rough by design: batch of 75 words in
    ~2k tokens, ~1k out."""
    calls = max(1, (word_count + 74) // 75)
    return {
        "words": word_count,
        "calls": calls,
        "est_cost_usd": round(calls * 0.02, 2),
    }
