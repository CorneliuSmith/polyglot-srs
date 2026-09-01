"""Unit coverage for the auto-translate loop's pure edges.

The interesting behaviour (queries, writes, the review-queue gate) is
integration-tested against real Postgres in
tests/integration/test_auto_translate_integration.py; these pin the two
things a DB can't show: the generalized prompts, and failing closed when
the toggle migration hasn't landed.
"""
from __future__ import annotations

import asyncpg
import pytest

from backend.services.auto_translate import discover_pairs
from backend.services.translate import checker_system, maker_system
from backend.tests.fakes import FakeTransaction


class TestPromptGeneralization:
    def test_english_course_prompt_is_the_original(self):
        """The English-course maker charter must stay byte-identical to the
        prompt the CLI has always sent — same words, same behaviour."""
        assert maker_system("Dutch") == (
            "You are a professional lexicographer translating English headwords "
            "into Dutch for a language-learning app. For each "
            "numbered English word, give the single word or short phrase a "
            "native Dutch speaker would use for THAT specific sense "
            "(use the definition and example to disambiguate). Match the part of "
            "speech. Output Dutch only — no English, no explanations."
        )

    def test_pivot_course_prompt_names_both_languages(self):
        s = maker_system("Arabic", "Spanish")
        assert "Spanish headwords" in s
        assert "into Arabic" in s
        # The pivot rule: the ENGLISH definition disambiguates the sense.
        assert "English definition and example" in s

    def test_checker_charter_generalizes_the_same_way(self):
        assert "English→Dutch" in checker_system("Dutch")
        assert "Spanish→Arabic" in checker_system("Arabic", "Spanish")


class _NoColumnConn:
    def transaction(self):
        return FakeTransaction()
    async def fetch(self, *_args):
        raise asyncpg.exceptions.UndefinedColumnError(
            "column l.auto_translate_enabled does not exist"
        )


@pytest.mark.asyncio
async def test_discover_pairs_fails_closed_without_the_migration():
    """No toggle column → no pairs → no API spend. The safe direction for
    this feature's degrade is 'translate nothing', mirroring how visibility
    degrades toward 'show nothing unreviewed'."""
    assert await discover_pairs(_NoColumnConn()) == []


class TestTextCharters:
    """Titles/labels and explanations get purpose-fit prompts — an
    explanation is a lesson and a title is a label, and neither should ride
    through the example-sentence charter anymore."""

    def test_label_charter_protects_course_language_material(self):
        from backend.services.translate import _TEXT_SYSTEMS
        s = _TEXT_SYSTEMS["label"].format(target="Spanish")
        assert "Spanish" in s
        assert "(el / la)" in s  # course-language material stays verbatim
        assert "example sentences" not in s

    def test_prose_charter_is_for_explanations_not_sentences(self):
        from backend.services.translate import _TEXT_SYSTEMS
        s = _TEXT_SYSTEMS["prose"].format(target="Arabic")
        assert "Arabic" in s
        assert "explanations" in s
        assert "example sentences" not in s
