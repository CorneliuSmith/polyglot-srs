"""Schema validation tests — require a running Supabase/PostgreSQL instance."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping DB integration tests",
)

EXPECTED_TABLES = [
    "languages",
    "grammar_points",
    "vocabulary",
    "translations",
    "content_lists",
    "content_list_items",
    "drill_sentences",
    "user_profiles",
    "user_cards",
    "review_log",
]


@pytest.mark.asyncio
async def test_all_tables_exist():
    """Verify all 10 schema tables exist."""
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        table_names = {r["table_name"] for r in rows}
        for t in EXPECTED_TABLES:
            assert t in table_names, f"Missing table: {t}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_language_seed_data():
    """Verify ru/ar/en seed data with correct RTL flags."""
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch("SELECT code, rtl FROM languages")
        by_code = {r["code"]: r["rtl"] for r in rows}
        assert by_code.get("ru") is False
        assert by_code.get("ar") is True
        assert by_code.get("en") is False
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_language_parameterization():
    """Verify language_id column exists on key tables."""
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        for table in ["grammar_points", "vocabulary", "content_lists", "user_cards"]:
            rows = await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = $1 "
                "AND column_name = 'language_id'",
                table,
            )
            assert len(rows) == 1, f"Missing language_id on {table}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_morphology_jsonb():
    """Verify vocabulary.morphology is jsonb type."""
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        row = await conn.fetchrow(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'vocabulary' "
            "AND column_name = 'morphology'"
        )
        assert row is not None, "vocabulary.morphology column missing"
        assert row["data_type"] == "jsonb"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_translations_unique_constraint():
    """Verify UNIQUE constraint on (vocabulary_id, locale)."""
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND table_name = 'translations' "
            "AND constraint_type = 'UNIQUE'"
        )
        assert len(rows) >= 1, "No UNIQUE constraint on translations"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_drill_sentences_fk():
    """Verify drill_sentences.grammar_point_id FK exists."""
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND table_name = 'drill_sentences' "
            "AND constraint_type = 'FOREIGN KEY'"
        )
        assert len(rows) >= 1, "No FK on drill_sentences"
    finally:
        await conn.close()
