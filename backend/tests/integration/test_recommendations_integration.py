"""Media recommendations: RLS isolation + the profile / history / staleness
repository flow against a real Postgres."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.repositories.recommendations import (
    get_reco_profile,
    insert_recommendation,
    latest_recommendation_at,
    list_recommendations,
    upsert_reco_profile,
)
from backend.services.recommend import _mock_recs, generate_recommendations

from .conftest import requires_db

pytestmark = requires_db


async def _new_user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _language(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def test_profile_defaults_and_roundtrip(pool):
    u = await _new_user(pool, "reco-a@t")
    async with pool.rls_connection(u) as conn:
        # Untouched → feature off, everything empty.
        p = await get_reco_profile(conn, u)
        assert p == {"enabled": False, "about": "", "genres": [], "media_types": []}

        await upsert_reco_profile(
            conn, u, enabled=True, about="I love sci-fi and cooking",
            genres=["sci-fi", "thriller"], media_types=["book", "podcast"],
        )
        p = await get_reco_profile(conn, u)
        assert p["enabled"] is True
        assert p["about"] == "I love sci-fi and cooking"
        assert p["genres"] == ["sci-fi", "thriller"]
        assert p["media_types"] == ["book", "podcast"]

        # Upsert again → updates in place, no duplicate row.
        await upsert_reco_profile(
            conn, u, enabled=False, about="", genres=[], media_types=[],
        )
        p = await get_reco_profile(conn, u)
        assert p["enabled"] is False and p["genres"] == []


async def test_history_and_staleness(pool):
    u = await _new_user(pool, "reco-b@t")
    lang = await _language(pool, "rcb")

    async with pool.rls_connection(u) as conn:
        # No batches yet → stale (never generated).
        assert await latest_recommendation_at(conn, u, lang) is None

        items = _mock_recs("Test", ["book", "film"])
        batch = await insert_recommendation(conn, u, lang, items, "A2")
        assert batch["level"] == "A2"
        assert len(batch["items"]) == 2
        assert batch["items"][0]["type"] == "book"

        # Now there's a fresh batch — within the week.
        last = await latest_recommendation_at(conn, u, lang)
        assert last is not None
        assert datetime.now(UTC) - last < timedelta(days=7)

        hist = await list_recommendations(conn, u, lang)
        assert len(hist) == 1
        assert hist[0]["items"][0]["type"] == "book"

    # Backdate it past the window → should read as stale.
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE media_recommendations SET created_at = now() - interval '8 days' "
            "WHERE user_id = $1",
            u,
        )
    async with pool.rls_connection(u) as conn:
        last = await latest_recommendation_at(conn, u, lang)
        assert datetime.now(UTC) - last >= timedelta(days=7)


async def test_recommendations_are_rls_isolated(pool):
    lang = await _language(pool, "rcc")
    a = await _new_user(pool, "reco-iso-a@t")
    b = await _new_user(pool, "reco-iso-b@t")

    async with pool.rls_connection(a) as conn:
        await insert_recommendation(conn, a, lang, _mock_recs("Test", ["book"]), "B1")
    async with pool.rls_connection(b) as conn:
        await insert_recommendation(conn, b, lang, _mock_recs("Test", ["film"]), "A1")

    # Each learner sees only their own batches + profile.
    async with pool.rls_connection(a) as conn:
        hist = await list_recommendations(conn, a, lang)
        assert len(hist) == 1
        assert hist[0]["items"][0]["type"] == "book"
    async with pool.rls_connection(b) as conn:
        hist = await list_recommendations(conn, b, lang)
        assert len(hist) == 1
        assert hist[0]["items"][0]["type"] == "film"


@pytest.mark.asyncio
async def test_generate_recommendations_dev_mock(monkeypatch):
    # With dev-mock on (no API key), generation returns a deterministic batch
    # limited to the requested media types.
    from backend.services import recommend as mod

    class _S:
        tutor_dev_mock = True

    monkeypatch.setattr(mod, "get_settings", lambda: _S())
    items = await generate_recommendations(
        language_name="Spanish", language_code="es", level="B1",
        learned_count=800, about="films and history",
        genres=["drama"], media_types=["film", "series"],
    )
    assert items
    assert {i["type"] for i in items} <= {"film", "series"}
    assert all("why" in i and "level" in i for i in items)
