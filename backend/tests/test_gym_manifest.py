"""Gym manifest access (backend/services/gym_manifest.py)."""
from __future__ import annotations

from backend.services.gym_manifest import (
    load_manifest,
    nonstandard_point_titles,
)


def test_load_manifest_none_for_uninflected_language():
    # A language without a curated manifest has no Gym.
    assert load_manifest("sw") is None


def test_load_manifest_reads_columns():
    manifest = load_manifest("ru")
    assert manifest is not None
    assert manifest["language"] == "ru"
    assert manifest["columns"]


def test_nonstandard_titles_flags_pattern_breakers():
    titles = nonstandard_point_titles("ru")
    # Verbs of motion are marked non-standard in the Russian manifest.
    assert any("motion" in t.lower() for t in titles)
    # A plainly regular category is not flagged.
    assert "Past tense (-л)" not in titles


def test_nonstandard_titles_empty_without_manifest():
    assert nonstandard_point_titles("sw") == frozenset()
