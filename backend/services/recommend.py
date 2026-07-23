"""Personalized immersion recommendations (owner request).

Given a learner's level, known-vocabulary size, and self-described interests,
draft a small batch of real books / films / series / podcasts IN the target
language for them to stretch into beyond the app. One model call per weekly
batch; gated to paid tutor accounts by the caller.

Dev-mock (TUTOR_DEV_MOCK) returns a deterministic batch so the pipeline is
testable with no API key — same convention as services/generate.py.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model

MEDIA_TYPES = ("book", "film", "series", "podcast")

_RECO_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": list(MEDIA_TYPES)},
                    "title": {"type": "string"},
                    "creator": {
                        "type": "string",
                        "description": "Author, director, showrunner, or host.",
                    },
                    "year": {"type": "string"},
                    "blurb": {
                        "type": "string",
                        "description": "One or two sentences on what it is.",
                    },
                    "why": {
                        "type": "string",
                        "description": "Why it fits THIS learner — their interests "
                        "and their level.",
                    },
                    "level": {
                        "type": "string",
                        "description": "The CEFR band it suits, e.g. 'A2–B1'.",
                    },
                },
                "required": ["type", "title", "blurb", "why", "level"],
            },
        },
    },
    "required": ["picks"],
}


def _mock_recs(language_name: str, media_types: list[str]) -> list[dict]:
    """Deterministic sample batch for dev/tests (no API key)."""
    types = media_types or list(MEDIA_TYPES)
    catalogue = {
        "book": {
            "type": "book", "title": f"A short {language_name} novel",
            "creator": "A well-known author", "year": "—",
            "blurb": "A widely loved, accessible novel.",
            "why": "Matches your interests and stretches your reading a notch.",
            "level": "A2–B1",
        },
        "film": {
            "type": "film", "title": f"A {language_name} film",
            "creator": "A celebrated director", "year": "—",
            "blurb": "A modern classic with clear, everyday dialogue.",
            "why": "Good listening practice just above your current level.",
            "level": "B1",
        },
        "series": {
            "type": "series", "title": f"A {language_name} series",
            "creator": "—", "year": "—",
            "blurb": "Short episodes, contemporary speech.",
            "why": "Bite-sized immersion you can keep up with.",
            "level": "A2–B1",
        },
        "podcast": {
            "type": "podcast", "title": f"A {language_name} podcast",
            "creator": "—", "year": "—",
            "blurb": "Slow, clear conversations for learners.",
            "why": "Trains your ear on natural rhythm at your level.",
            "level": "A2",
        },
    }
    return [catalogue[t] for t in types if t in catalogue][:4] or [catalogue["book"]]


async def generate_recommendations(
    *,
    language_name: str,
    language_code: str,
    level: str | None,
    learned_count: int,
    about: str,
    genres: list[str],
    media_types: list[str],
    model: str | None = None,
) -> list[dict]:
    """Draft a batch of immersion picks calibrated to the learner. Returns a
    list of pick dicts (may be empty if the model returns nothing usable)."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_recs(language_name, media_types)

    types = media_types or list(MEDIA_TYPES)
    level_str = level or "beginner (early A1)"
    interests = about.strip() or "(not specified)"
    genre_str = ", ".join(genres) if genres else "(no genre preference given)"

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("recommend", language_code),
        max_tokens=1500,
        system=(
            f"You recommend authentic {language_name} media — books, films, "
            f"series, and podcasts — for a language learner to immerse in beyond "
            f"their app. Recommend only REAL, verifiable works that genuinely "
            f"exist in {language_name} (or are widely available dubbed/translated "
            f"into it); never invent titles. Calibrate difficulty to the "
            f"learner's level: pick things a notch above where they are so they "
            f"stretch without drowning. Match their stated interests and genres. "
            f"Give 3–4 picks, spread across the requested media types. For each: "
            f"a short blurb of what it is, a sentence on why it fits THIS learner "
            f"(their interests and level), and the CEFR band it suits. Keep it "
            f"appealing and specific — not generic textbook fare."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Learner profile\n"
                f"- Target language: {language_name}\n"
                f"- Current level (CEFR ceiling): {level_str}\n"
                f"- Known vocabulary: about {learned_count} words\n"
                f"- Interests / about them: {interests}\n"
                f"- Preferred genres: {genre_str}\n"
                f"- Wants recommendations for: {', '.join(types)}\n"
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _RECO_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        picks = json.loads(text).get("picks", [])
    except (json.JSONDecodeError, TypeError):
        picks = []
    # Keep only the requested media types, cap the batch.
    wanted = set(types)
    picks = [p for p in picks if p.get("type") in wanted] or picks
    return picks[:4]
