"""Languages repository — the missing-migration fallback.

`/api/languages` is load-bearing for the whole app: an empty or failing
language list blanks the dashboard. When code that reads
`languages.is_visible` deploys ahead of migration 20260831, the repository
must degrade to everything-visible rather than 500 (the live incident of
2026-07-27).
"""
from unittest.mock import AsyncMock

import asyncpg

from backend.repositories.languages import get_all_languages

ROWS = [
    {"id": "1", "code": "es", "name": "Spanish", "rtl": False, "is_visible": True},
    {"id": "2", "code": "ar", "name": "Arabic", "rtl": True, "is_visible": False},
]


async def test_returns_rows_with_visibility():
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=ROWS)
    langs = await get_all_languages(pool)
    assert langs == ROWS
    assert "is_visible" in pool.fetch.await_args.args[0]


async def test_missing_auto_translate_column_reads_as_off():
    """Only migration 20260913 missing: the listing keeps is_visible and
    reports the auto-translate switch as off — which is also what the
    translate loop itself assumes, so UI and behaviour agree."""
    pool = AsyncMock()
    pool.fetch = AsyncMock(
        side_effect=[
            asyncpg.exceptions.UndefinedColumnError(
                'column "auto_translate_enabled" does not exist'
            ),
            ROWS,
        ]
    )
    langs = await get_all_languages(pool)
    assert [lang["is_visible"] for lang in langs] == [True, False]
    assert all(lang["auto_translate_enabled"] is False for lang in langs)
    retry_sql = pool.fetch.await_args.args[0]
    assert "is_visible" in retry_sql
    assert "auto_translate_enabled" not in retry_sql


async def test_missing_column_falls_back_to_all_visible():
    legacy = [{k: v for k, v in r.items() if k != "is_visible"} for r in ROWS]
    pool = AsyncMock()
    pool.fetch = AsyncMock(
        side_effect=[
            asyncpg.exceptions.UndefinedColumnError(
                'column "auto_translate_enabled" does not exist'
            ),
            asyncpg.exceptions.UndefinedColumnError(
                'column "is_visible" does not exist'
            ),
            legacy,
        ]
    )
    langs = await get_all_languages(pool)
    assert [lang["code"] for lang in langs] == ["es", "ar"]
    assert all(lang["is_visible"] is True for lang in langs)
    assert all(lang["auto_translate_enabled"] is False for lang in langs)
    retry_sql = pool.fetch.await_args.args[0]
    assert "is_visible" not in retry_sql
