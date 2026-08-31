"""The Topic Lens taxonomy — one fixed, app-global set of semantic buckets
(docs/plans/topic-lens.md, owner-approved 2026-08-31).

The slugs here MUST match migration 20261009's CHECK constraint exactly —
test_topics.py parses the migration file and compares, so drift fails CI
rather than failing at the first INSERT. Display names are not here: they
live in the frontend i18n catalogs (decks.topics.<slug>, six locales),
because a bucket's name is learner-facing copy and this module is not.

Two buckets are HIDDEN: every word must classify somewhere ("the", "of",
and "thing" belong to no theme), but they make terrible decks, so topic
view never renders them. Their words stay reachable in level view.
"""
from __future__ import annotations

VISIBLE_TOPICS: tuple[str, ...] = (
    "food_drink",
    "home_living",
    "family_people",
    "relationships_social",
    "body_health",
    "clothing_appearance",
    "travel_transport",
    "city_places",
    "nature_weather_animals",
    "time_dates",
    "numbers_measure",
    "work_professions",
    "school_learning",
    "sports_leisure",
    "arts_media",
    "technology",
    "communication",
    "shopping_money",
    "emotions_mind",
    "society_politics",
    "religion_culture",
    "science_world",
)

HIDDEN_TOPICS: tuple[str, ...] = ("abstract_general", "function_words")

ALL_TOPICS: tuple[str, ...] = VISIBLE_TOPICS + HIDDEN_TOPICS

_ALL = frozenset(ALL_TOPICS)


def valid_topic(slug: str | None) -> str | None:
    """The slug if it names a real bucket, else None.

    None (not an error) on purpose: a stale link or an old cached bundle
    asking for a renamed topic must degrade to a normal draw, never 422 a
    learn session. Callers log the fallback; the learner just learns.
    """
    return slug if slug in _ALL else None
