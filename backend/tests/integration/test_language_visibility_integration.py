"""Language visibility (owner, 2026-07-27): admin hides/shows a language in
learner-facing pickers without touching its content. Real Postgres."""
from __future__ import annotations

from backend.repositories.languages import get_all_languages, set_language_visibility

from .conftest import requires_db

pytestmark = requires_db


async def test_new_languages_default_visible(pool):
    async with pool.privileged_connection() as conn:
        lang_id = await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "RETURNING id",
            "vis1", "VIS1",
        )
    rows = await get_all_languages(pool.get_pool())
    row = next(r for r in rows if str(r["id"]) == str(lang_id))
    assert row["is_visible"] is True


async def test_hide_then_show(pool):
    async with pool.privileged_connection() as conn:
        lang_id = str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "RETURNING id",
            "vis2", "VIS2",
        ))
        assert await set_language_visibility(conn, lang_id, False) is True

    rows = await get_all_languages(pool.get_pool())
    row = next(r for r in rows if str(r["id"]) == lang_id)
    assert row["is_visible"] is False

    async with pool.privileged_connection() as conn:
        assert await set_language_visibility(conn, lang_id, True) is True
    rows = await get_all_languages(pool.get_pool())
    row = next(r for r in rows if str(r["id"]) == lang_id)
    assert row["is_visible"] is True


async def test_unknown_language_returns_false(pool):
    async with pool.privileged_connection() as conn:
        ok = await set_language_visibility(
            conn, "00000000-0000-0000-0000-000000000000", False
        )
    assert ok is False
