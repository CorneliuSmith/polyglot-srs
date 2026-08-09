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


async def feedback_table_present(conn: asyncpg.Connection) -> bool:
    """Whether migration 20260922 has landed — to_regclass, never raises
    (a thrown UndefinedTableError would abort the pooled transaction and
    take the whole history read down with it)."""
    return bool(await conn.fetchval(
        "SELECT to_regclass('media_reco_feedback') IS NOT NULL"
    ))


async def list_recommendations(
    conn: asyncpg.Connection, user_id: str, language_id: str, limit: int = 50
) -> list[dict]:
    """Every batch for this (learner, language), newest first — the history.
    Each item carries the learner's feedback (done, rating) when the
    feedback migration has landed; plain items otherwise."""
    rows = await conn.fetch(
        "SELECT id, items, level, created_at FROM media_recommendations "
        "WHERE user_id = $1 AND language_id = $2 "
        "ORDER BY created_at DESC LIMIT $3",
        user_id, language_id, limit,
    )
    feedback: dict[tuple[str, int], dict] = {}
    if rows and await feedback_table_present(conn):
        fb_rows = await conn.fetch(
            """
            SELECT batch_id, item_index, done, rating
            FROM media_reco_feedback
            WHERE user_id = $1 AND batch_id = ANY($2::uuid[])
            """,
            user_id, [r["id"] for r in rows],
        )
        feedback = {
            (str(f["batch_id"]), f["item_index"]):
                {"done": f["done"], "rating": f["rating"]}
            for f in fb_rows
        }
    out = []
    for r in rows:
        batch_id = str(r["id"])
        items = [
            {**item,
             **feedback.get((batch_id, i), {"done": False, "rating": None})}
            for i, item in enumerate(_load_items(r["items"]))
        ]
        out.append({
            "id": batch_id,
            "items": items,
            "level": r["level"],
            "created_at": r["created_at"].isoformat(),
        })
    return out


async def set_reco_feedback(
    conn: asyncpg.Connection,
    user_id: str,
    batch_id: str,
    item_index: int,
    *,
    done: bool,
    rating: int | None,
) -> bool:
    """Record "I finished this" / a 1–5 rating for one pick. Returns False
    when the migration hasn't landed (router 503s naming it) or the batch
    isn't this learner's."""
    if not await feedback_table_present(conn):
        return False
    owned = await conn.fetchval(
        "SELECT 1 FROM media_recommendations WHERE id = $1 AND user_id = $2",
        batch_id, user_id,
    )
    if not owned:
        return False
    await conn.execute(
        """
        INSERT INTO media_reco_feedback
            (user_id, batch_id, item_index, done, rating, updated_at)
        VALUES ($1, $2, $3, $4, $5, now())
        ON CONFLICT (user_id, batch_id, item_index) DO UPDATE SET
            done = EXCLUDED.done,
            rating = EXCLUDED.rating,
            updated_at = now()
        """,
        user_id, batch_id, item_index, done, rating,
    )
    return True


async def recommended_titles(
    conn: asyncpg.Connection, user_id: str, language_id: str, cap: int = 40
) -> list[str]:
    """Every title already recommended to this learner for this language,
    newest batches first — what the engine must NOT pick again."""
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (title) title FROM (
          SELECT jsonb_array_elements(r.items::jsonb)->>'title' AS title,
                 r.created_at
          FROM media_recommendations r
          WHERE r.user_id = $1 AND r.language_id = $2
        ) t
        WHERE title IS NOT NULL AND title <> ''
        ORDER BY title, created_at DESC
        LIMIT $3
        """,
        user_id, language_id, cap,
    )
    return [r["title"] for r in rows]


async def rated_titles(
    conn: asyncpg.Connection, user_id: str, language_id: str, cap: int = 20
) -> list[dict]:
    """The learner's reactions to earlier picks — title, rating, done —
    newest first. Steers the next batch's taste. Empty before the feedback
    migration lands."""
    if not await feedback_table_present(conn):
        return []
    rows = await conn.fetch(
        """
        SELECT r.items::jsonb->(f.item_index)->>'title' AS title,
               f.rating, f.done
        FROM media_reco_feedback f
        JOIN media_recommendations r ON r.id = f.batch_id
        WHERE f.user_id = $1 AND r.language_id = $2
          AND (f.rating IS NOT NULL OR f.done)
        ORDER BY f.updated_at DESC
        LIMIT $3
        """,
        user_id, language_id, cap,
    )
    return [
        {"title": r["title"], "rating": r["rating"], "done": r["done"]}
        for r in rows
        if r["title"]
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


async def mark_recommendations_seen(
    conn: asyncpg.Connection, user_id: str
) -> None:
    """Stamp "the learner has now looked at their picks".

    Drives the once-a-week in-app prompt: a batch created after this stamp is
    one they haven't seen. Server-side rather than localStorage so dismissing
    the prompt on a phone settles it on a laptop too.

    Degrades to a no-op if migration 20260908 hasn't been applied — a missing
    stamp column should cost the prompt, not the page it sits on.
    """
    try:
        await conn.execute(
            """
            INSERT INTO media_reco_profile (user_id, last_seen_at)
            VALUES ($1, now())
            ON CONFLICT (user_id) DO UPDATE SET last_seen_at = now()
            """,
            user_id,
        )
    except asyncpg.exceptions.UndefinedColumnError:
        return


async def unseen_batch(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> dict | None:
    """The learner's newest batch if they haven't looked since it was made,
    else None. What the dashboard prompt renders from."""
    try:
        row = await conn.fetchrow(
            """
            SELECT r.id, r.items, r.level, r.created_at
            FROM media_recommendations r
            JOIN media_reco_profile p ON p.user_id = r.user_id
            WHERE r.user_id = $1
              AND r.language_id = $2
              AND p.enabled
              AND (p.last_seen_at IS NULL OR r.created_at > p.last_seen_at)
            ORDER BY r.created_at DESC
            LIMIT 1
            """,
            user_id, language_id,
        )
    except asyncpg.exceptions.UndefinedColumnError:
        return None
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "items": _load_items(row["items"]),
        "level": row["level"],
        "created_at": row["created_at"].isoformat(),
    }
