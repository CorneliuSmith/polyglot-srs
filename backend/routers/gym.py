"""The Gym (WP25): chosen-form conjugation & declension practice.

The learner picks form CATEGORIES (present tense, accusative case…) —
never individual words — and drills them through mixed cram sessions.
Categories are grammar points, curated per language in data/gym/{code}.json
with plain-language labels, a hover usage line, and a real example drill.
A language without a manifest simply has no Gym (uninflected languages).

Sessions reuse the Quick-Cram machinery: the client sends the selected
point ids to GET /api/review/cram — ungraded, nothing touches SRS state.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection
from backend.services.gym_manifest import load_manifest as _load_manifest

router = APIRouter()


@router.get("/manifest")
async def gym_manifest(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """The Gym picker for one language: columns (verbs | nouns | adjectives)
    of selectable form categories. Each entry resolves to a live grammar
    point (same visibility gate as cram, so a selected category always has
    drills) and carries a `familiar` flag — whether the learner already has
    that point in their reviews — so the UI can lead with known ground."""
    try:
        uuid.UUID(language_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid language id",
        ) from exc

    async with rls_connection(user["id"]) as conn:
        code = await conn.fetchval(
            "SELECT code FROM languages WHERE id = $1", language_id
        )
        if not code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown language"
            )
        manifest = _load_manifest(code)
        if not manifest:
            return {"columns": []}

        titles = [
            e["point"] for col in manifest.get("columns", [])
            for e in col.get("entries", [])
        ]
        rows = await conn.fetch(
            """
            SELECT gp.id, gp.title, gp.level,
                   (SELECT count(*) FROM drill_sentences ds
                     WHERE ds.grammar_point_id = gp.id) AS drills,
                   EXISTS (SELECT 1 FROM user_cards uc
                            WHERE uc.user_id = $3
                              AND uc.card_type = 'grammar'
                              AND uc.card_id = gp.id) AS familiar
            FROM grammar_points gp
            JOIN languages l ON l.id = gp.language_id
            WHERE gp.language_id = $1
              AND gp.title = ANY($2::text[])
              AND (gp.reviewed = true
                   OR (l.grammar_review_policy = 'ai_ok'
                       AND gp.ai_check_status = 'pass'))
            """,
            language_id, titles, user["id"],
        )

    by_title = {r["title"]: r for r in rows}
    columns = []
    for col in manifest.get("columns", []):
        entries = []
        for e in col.get("entries", []):
            r = by_title.get(e["point"])
            if not r or not r["drills"]:
                continue
            entries.append({
                "point_id": str(r["id"]),
                "label": e["label"],
                "usage": e.get("usage"),
                "example": e.get("example"),
                "level": r["level"],
                "drills": r["drills"],
                "nonstandard": bool(e.get("nonstandard")),
                "familiar": r["familiar"],
            })
        if entries:
            columns.append({
                "kind": col.get("kind"),
                "label": col.get("label"),
                "entries": entries,
            })
    return {"columns": columns}
