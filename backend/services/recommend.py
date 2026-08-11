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
import logging

from anthropic import AsyncAnthropic, BadRequestError

from backend.config import get_settings
from backend.services.models import resolve_model

logger = logging.getLogger(__name__)

MEDIA_TYPES = ("book", "film", "series", "podcast", "music")

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
                        "description": "Author, director, showrunner, host, "
                        "or artist/band. Empty string if genuinely unknown.",
                    },
                    "year": {
                        "type": "string",
                        "description": "Release/publication year, or an empty "
                        "string if unknown. Never invent one.",
                    },
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
                    "genre": {
                        "type": "string",
                        "description": "The work's genre — 'crime drama', "
                        "'indie folk', 'true crime'. Short; empty string if "
                        "it doesn't fit one.",
                    },
                },
                # EVERY property is required. Strict structured output has two
                # rules this schema broke, and each one 400s the call before
                # the model runs: object nodes must forbid extra keys, and
                # `required` must cover every property. Optional keys are
                # expressed as "may be an empty string" instead — which is how
                # every schema in this codebase that actually works is built.
                "required": ["type", "title", "creator", "year", "blurb",
                             "why", "level", "genre"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["picks"],
    "additionalProperties": False,
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
        "music": {
            "type": "music", "title": f"A {language_name} singer-songwriter",
            "creator": "A lyric-forward artist", "year": "—",
            "blurb": "Clear diction, lyric-forward songs.",
            "why": "Song lyrics repeat core vocabulary naturally.",
            "level": "A2–B1", "genre": "indie folk",
        },
    }
    return [catalogue[t] for t in types if t in catalogue][:4] or [catalogue["book"]]


def _parse_picks(text: str) -> list[dict]:
    """The picks out of a model reply, structured or not.

    The fallback path (see generate_recommendations) gets prose-mode JSON,
    which can arrive fenced or with a sentence in front of it, so the object
    is located rather than assumed to be the whole body.
    """
    raw = (text or "").strip()
    if raw.startswith("```"):
        # ```json … ``` → the body between the fences.
        fenced = raw[3:]
        raw = fenced.split("```", 1)[0]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return []
        try:
            data = json.loads(raw[start:end + 1])
        except (json.JSONDecodeError, TypeError):
            return []
    picks = data.get("picks") if isinstance(data, dict) else None
    return [p for p in (picks or []) if isinstance(p, dict)]


def _reaction_lines(reactions: list[dict]) -> str:
    """The learner's reactions to earlier picks, one per line, for the
    prompt: "Loved 'X' (5/5)", "Finished 'Y'", "Didn't click with 'Z' (2/5)"."""
    lines = []
    for r in reactions:
        title = r.get("title")
        if not title:
            continue
        rating = r.get("rating")
        if rating is not None:
            verb = ("Loved" if rating >= 4
                    else "Was lukewarm on" if rating == 3
                    else "Didn't click with")
            lines.append(f"- {verb} '{title}' ({rating}/5)")
        elif r.get("done"):
            lines.append(f"- Finished '{title}'")
    return "\n".join(lines)


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
    exclude_titles: list[str] | None = None,
    reactions: list[dict] | None = None,
) -> list[dict]:
    """Draft a batch of immersion picks calibrated to the learner. Returns a
    list of pick dicts (may be empty if the model returns nothing usable).

    exclude_titles: everything already recommended — a batch that repeats
    last month's picks reads as the engine not paying attention.
    reactions: [{title, rating, done}] from the learner's feedback, so a
    5-star series pulls the next batch toward more of the same."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_recs(language_name, media_types)

    types = media_types or list(MEDIA_TYPES)
    level_str = level or "beginner (early A1)"
    interests = about.strip() or "(not specified)"
    genre_str = ", ".join(genres) if genres else "(no genre preference given)"
    exclusions = (
        "\nAlready recommended — do NOT pick any of these again:\n"
        + "\n".join(f"- {t}" for t in exclude_titles)
        if exclude_titles
        else ""
    )
    reaction_block = _reaction_lines(reactions or [])
    reaction_txt = (
        f"\nTheir reactions to earlier picks (steer toward what they loved, "
        f"away from what didn't land):\n{reaction_block}"
        if reaction_block
        else ""
    )

    system = (
        f"You recommend authentic {language_name} media — books, films, "
        f"series, podcasts, and music — for a language learner to immerse in beyond "
        f"their app. Recommend only REAL, verifiable works that genuinely "
        f"exist in {language_name} (or are widely available dubbed/translated "
        f"into it); never invent titles. Calibrate difficulty to the "
        f"learner's level: pick things a notch above where they are so they "
        f"stretch without drowning. Match their stated interests and genres. "
        f"Give 3–4 picks, spread across the requested media types. For each: "
        f"a short blurb of what it is, a sentence on why it fits THIS learner "
        f"(their interests and level), the CEFR band it suits, and its genre. "
        f"For music, favour artists with clear diction and lyric-forward "
        f"songs — lyrics are the learning material. Keep it appealing and "
        f"specific — not generic textbook fare."
    )
    prompt = (
        f"Learner profile\n"
        f"- Target language: {language_name}\n"
        f"- Current level (CEFR ceiling): {level_str}\n"
        f"- Known vocabulary: about {learned_count} words\n"
        f"- Interests / about them: {interests}\n"
        f"- Preferred genres: {genre_str}\n"
        f"- Wants recommendations for: {', '.join(types)}\n"
        f"{exclusions}{reaction_txt}"
    )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    call_model = model or resolve_model("recommend", language_code)
    try:
        resp = await client.messages.create(
            model=call_model, max_tokens=1500, system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "format": {"type": "json_schema", "schema": _RECO_SCHEMA}
            },
        )
    except BadRequestError:
        # A schema the API won't accept must not be the end of the feature.
        # This is exactly how recommendations stayed broken for weeks: one
        # strict-mode rule the schema didn't satisfy, a 400 before the model
        # ever ran, and no batch ever produced. Ask for the same JSON in
        # plain prose instead and parse it — a validated shape is nice, a
        # working feature is the point.
        logger.warning(
            "recommendations: schema rejected by the API, retrying as plain "
            "JSON (model=%s)", call_model, exc_info=True,
        )
        resp = await client.messages.create(
            model=call_model, max_tokens=1500,
            system=(
                system + " Reply with ONLY a JSON object, no prose and no "
                'code fences: {"picks": [{"type": one of '
                f'{list(MEDIA_TYPES)}, "title": string, "creator": string, '
                '"year": string, "blurb": string, "why": string, "level": '
                'string, "genre": string}]}'
            ),
            messages=[{"role": "user", "content": prompt}],
        )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    picks = _parse_picks(text)
    # Keep only the requested media types, cap the batch.
    wanted = set(types)
    picks = [p for p in picks if p.get("type") in wanted] or picks
    return picks[:4]
