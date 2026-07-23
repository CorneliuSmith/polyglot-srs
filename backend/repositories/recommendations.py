"""Media recommendations: the learner's opt-in profile + their weekly batches.

Owner-scoped tables under RLS (media_reco_profile, media_recommendations); the
router always opens an rls_connection so auth.uid() gates every row. jsonb is
written with an explicit ::jsonb cast and decoded on read, matching the tutor
repo's convention (asyncpg returns jsonb as a str).
"""
from __future__ import annotations

import json

import asyncpg


def _load_items(value) -> list:
    if isinstance(value, (list, dict)):
        return value  # already decoded
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []


async def get_reco_profile(conn: asyncpg.Connection, user_id: str) -> dict:
    """The learner's recommendation settings, with sensible defaults when they
    have never touched them (feature off, nothing filled in)."""
    row = await conn.fetchrow(
        "SELECT enabled, about, genres, media_types "
        "FROM media_reco_profile WHERE user_id = $1",
        user_id,
    )
    if not row:
        return {"enabled": False, "about": "", "genres": [], "media_types": []}
    return {
        "enabled": row["enabled"],
        "about": row["about"] or "",
        "genres": list(row["genres"] or []),
        "media_types": list(row["media_types"] or []),
    }


async def upsert_reco_profile(
    conn: asyncpg.Connection,
    user_id: str,
    *,
    enabled: bool,
    about: str,
    genres: list[str],
    media_types: list[str],
) -> None:
    await conn.execute(
        """
        INSERT INTO media_reco_profile
            (user_id, enabled, about, genres, media_types, updated_at)
        VALUES ($1, $2, $3, $4, $5, now())
        ON CONFLICT (user_id) DO UPDATE SET
            enabled = EXCLUDED.enabled,
            about = EXCLUDED.about,
            genres = EXCLUDED.genres,
            media_types = EXCLUDED.media_types,
            updated_at = now()
        """,
        user_id, enabled, about, genres, media_types,
    )


async def latest_recommendation_at(
    conn: asyncpg.Connection, user_id: str, language_id: str
):
    """When the most recent batch for this (learner, language) was made, or None
    — drives the once-a-week freshness check."""
    return await conn.fetchval(
        "SELECT created_at FROM media_recommendations "
        "WHERE user_id = $1 AND language_id = $2 "
        "ORDER BY created_at DESC LIMIT 1",
        user_id, language_id,
    )


async def list_recommendations(
    conn: asyncpg.Connection, user_id: str, language_id: str, limit: int = 50
) -> list[dict]:
    """Every batch for this (learner, language), newest first — the history."""
    rows = await conn.fetch(
        "SELECT id, items, level, created_at FROM media_recommendations "
        "WHERE user_id = $1 AND language_id = $2 "
        "ORDER BY created_at DESC LIMIT $3",
        user_id, language_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "items": _load_items(r["items"]),
            "level": r["level"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def insert_recommendation(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    items: list[dict],
    level: str | None,
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO media_recommendations (user_id, language_id, items, level)
        VALUES ($1, $2, $3::jsonb, $4)
        RETURNING id, items, level, created_at
        """,
        user_id, language_id, json.dumps(items, ensure_ascii=False), level,
    )
    return {
        "id": str(row["id"]),
        "items": _load_items(row["items"]),
        "level": row["level"],
        "created_at": row["created_at"].isoformat(),
    }
