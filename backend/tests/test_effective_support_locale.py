"""The one rule for the help language — repositories/profile.py.

These exist because there used to be no rule: each surface read the raw
support_locale column and improvised, and the globe wrote that column as a
side effect of changing the interface. The observed result was an
all-English page whose Speak partner coached in French. Every case below
is a state a real account can be in.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

from backend.repositories.profile import (
    effective_support_locale,
    effective_support_sql,
)


def _conn(row):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=row)
    return conn


class TestTheRule:
    async def test_an_explicit_choice_wins_over_the_interface(self):
        # A French speaker learning English: interface English, help French.
        # This is a real decision and nothing may override it.
        conn = _conn({"support_locale": "fr", "ui_language": "en"})
        assert await effective_support_locale(conn, "u1") == "fr"

    async def test_automatic_follows_the_interface(self):
        # Nothing chosen: the help language IS the interface language,
        # derived at read time — no stored state to go stale.
        conn = _conn({"support_locale": None, "ui_language": "fr"})
        assert await effective_support_locale(conn, "u1") == "fr"

    async def test_automatic_with_an_english_interface_is_english(self):
        conn = _conn({"support_locale": None, "ui_language": "en"})
        assert await effective_support_locale(conn, "u1") is None

    async def test_explicit_english_beats_a_foreign_interface(self):
        # The case that made 'en' a storable value: a French-interface
        # learner who wants ENGLISH glosses. When 'en' doubled as the
        # reset sentinel this wish was inexpressible — asking for English
        # snapped them back to automatic, i.e. French.
        conn = _conn({"support_locale": "en", "ui_language": "fr"})
        assert await effective_support_locale(conn, "u1") is None

    async def test_a_wholly_unset_profile_is_english(self):
        conn = _conn({"support_locale": None, "ui_language": None})
        assert await effective_support_locale(conn, "u1") is None

    async def test_a_missing_profile_is_english(self):
        conn = _conn(None)
        assert await effective_support_locale(conn, "u1") is None


class TestTheSqlTwin:
    def test_the_scan_expression_matches_the_python_rule(self):
        # The auto-translate loop scans thousands of profiles with SQL; a
        # scan that filters differently from the request paths would tell
        # a learner their session is coming in French while stocking it in
        # nothing. The fragment must encode the same precedence.
        assert effective_support_sql("p") == (
            "COALESCE(p.support_locale, p.ui_language)"
        )
        assert "support_locale" in effective_support_sql()
