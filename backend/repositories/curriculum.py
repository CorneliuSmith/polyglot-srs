"""Grammar curriculum (path) repository — the browsable, readable syllabus.

The path is the product's spine: every visible grammar point in order (CEFR
level, then display_order), each readable outside of reviews, with the
learner's own status overlaid (already in their reviews or not). Visibility
follows the same per-language review policy as learning: human-reviewed points
always show; AI-passed drafts show only when the language's policy is 'ai_ok'.
"""
from __future__ import annotations

import json

import asyncpg

from backend.services.extract import ANSWER_MARKER
from backend.services.references import clean_references
from backend.services.srs_stages import stage_for


async def resolve_related(
    conn: asyncpg.Connection, language_id: str, raw_related
) -> list[dict]:
    """Resolve authored Related entries ({title, contrast?}) to live points.

    Titles resolve within the same language; each resolved entry carries the
    learner's named stage for that point (None if not yet studied). Entries
    whose title doesn't match a point are skipped silently — an authoring
    rename shows up as a missing tile, never an error.
    """
    if isinstance(raw_related, str):
        try:
            raw_related = json.loads(raw_related)
        except (json.JSONDecodeError, TypeError):
            raw_related = []
    entries = [
        e for e in (raw_related or []) if isinstance(e, dict) and e.get("title")
    ]
    if not entries:
        return []
    rows = await conn.fetch(
        """
        SELECT gp.id, gp.title, gp.level, gp.function_note,
               uc.id AS user_card_id, uc.state, uc.stability
        FROM grammar_points gp
        LEFT JOIN user_cards uc
               ON uc.card_type = 'grammar' AND uc.card_id = gp.id
              AND NOT (uc.is_suspended AND uc.repetitions = 0)
        WHERE gp.language_id = $1 AND gp.title = ANY($2::text[])
        """,
        language_id,
        [e["title"] for e in entries],
    )
    by_title = {r["title"]: r for r in rows}
    out = []
    for e in entries:
        r = by_title.get(e["title"])
        if r is None:
            continue
        out.append({
            "id": str(r["id"]),
            "title": r["title"],
            "level": r["level"],
            "function_note": r["function_note"],
            "contrast": e.get("contrast"),
            "stage": (
                stage_for("grammar", r["state"], r["stability"])
                if r["user_card_id"] else None
            ),
        })
    return out


async def get_read_ref_keys(
    conn: asyncpg.Connection, grammar_point_id: str
) -> list[str]:
    """Reference keys (url, or title for offline books) the user marked read."""
    rows = await conn.fetch(
        "SELECT ref_key FROM user_reference_reads WHERE grammar_point_id = $1",
        grammar_point_id,
    )
    return [r["ref_key"] for r in rows]


async def set_reference_read(
    conn: asyncpg.Connection,
    user_id: str,
    grammar_point_id: str,
    ref_key: str,
    read: bool,
) -> None:
    """Mark one resource read (or unread) for this user. Idempotent."""
    if read:
        await conn.execute(
            """
            INSERT INTO user_reference_reads (user_id, grammar_point_id, ref_key)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            user_id, grammar_point_id, ref_key,
        )
    else:
        await conn.execute(
            """
            DELETE FROM user_reference_reads
            WHERE user_id = $1 AND grammar_point_id = $2 AND ref_key = $3
            """,
            user_id, grammar_point_id, ref_key,
        )


async def get_curriculum(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> list[dict]:
    """Return the ordered grammar path with the learner's status per point."""
    rows = await conn.fetch(
        """
        SELECT
            gp.id,
            gp.title,
            gp.level,
            gp.function_note,
            gp.reviewed,
            EXISTS (
                SELECT 1 FROM drill_sentences ds WHERE ds.grammar_point_id = gp.id
            ) AS has_drills,
            EXISTS (
                SELECT 1 FROM user_cards uc
                WHERE uc.user_id = $1 AND uc.card_type = 'grammar' AND uc.card_id = gp.id
            ) AS learned
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.language_id = $2
          AND (gp.reviewed = true
               OR (l.grammar_review_policy = 'ai_ok' AND gp.ai_check_status = 'pass'))
        ORDER BY gp.level ASC NULLS LAST, gp.display_order ASC, gp.title ASC
        """,
        user_id,
        language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "title": r["title"],
            "level": r["level"],
            "function_note": r["function_note"],
            "reviewed": r["reviewed"],
            # learnable = quizzable: browsing is open, quizzing needs drills
            "learnable": r["has_drills"],
            "learned": r["learned"],
        }
        for r in rows
    ]


async def get_curriculum_point(
    conn: asyncpg.Connection, user_id: str, grammar_point_id: str
) -> dict | None:
    """Full read view of one grammar point (lesson-page shape)."""
    gp = await conn.fetchrow(
        """
        SELECT gp.id, gp.language_id, gp.title, gp.level, gp.function_note,
               gp.explanation, gp.culture_note, gp.reference_links, gp.related,
               gp.reviewed,
               EXISTS (
                   SELECT 1 FROM user_cards uc
                   WHERE uc.user_id = $1 AND uc.card_type = 'grammar'
                     AND uc.card_id = gp.id
               ) AS learned
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $2
          AND (gp.reviewed = true
               OR (l.grammar_review_policy = 'ai_ok' AND gp.ai_check_status = 'pass'))
        """,
        user_id,
        grammar_point_id,
    )
    if gp is None:
        return None
    related = await resolve_related(conn, gp["language_id"], gp["related"])
    read_refs = await get_read_ref_keys(conn, grammar_point_id)
    drills = await conn.fetch(
        "SELECT sentence, answer, translation, hint FROM drill_sentences "
        "WHERE grammar_point_id = $1 ORDER BY display_order ASC",
        grammar_point_id,
    )
    references = []
    if gp["reference_links"]:
        raw = gp["reference_links"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = []
        references = clean_references(raw)
    return {
        "id": str(gp["id"]),
        "title": gp["title"],
        "level": gp["level"],
        "function_note": gp["function_note"],
        "explanation": gp["explanation"],
        "culture_note": gp["culture_note"],
        "reviewed": gp["reviewed"],
        "learned": gp["learned"],
        "learnable": len(drills) > 0,
        "references": references,
        "read_refs": read_refs,
        "related": related,
        "examples": [
            {
                "sentence": d["sentence"].replace(ANSWER_MARKER, d["answer"]),
                "translation": d["translation"],
                "hint": d["hint"],
            }
            for d in drills
        ],
    }


async def learn_point(
    conn: asyncpg.Connection, user_id: str, grammar_point_id: str
) -> dict:
    """Add ONE specific grammar point to the learner's reviews (Bunpro-style).

    Enforces the same gates as batch learning: the point must be visible under
    the language's review policy and must have drills. Idempotent — learning an
    already-learned point is a no-op.
    """
    row = await conn.fetchrow(
        """
        SELECT gp.language_id,
               (gp.reviewed = true
                OR (l.grammar_review_policy = 'ai_ok' AND gp.ai_check_status = 'pass'))
               AS visible,
               EXISTS (
                   SELECT 1 FROM drill_sentences ds WHERE ds.grammar_point_id = gp.id
               ) AS has_drills
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $1
        """,
        grammar_point_id,
    )
    if row is None or not row["visible"]:
        return {"added": False, "reason": "not_found"}
    if not row["has_drills"]:
        return {"added": False, "reason": "no_drills"}
    card_id = await conn.fetchval(
        """
        INSERT INTO user_cards
            (user_id, language_id, card_type, card_id,
             ease_factor, interval, repetitions, streak, lapses, next_review)
        VALUES ($1, $2, 'grammar', $3, 2.5, 0, 0, 0, 0, now())
        ON CONFLICT (user_id, card_type, card_id) DO NOTHING
        RETURNING id
        """,
        user_id,
        row["language_id"],
        grammar_point_id,
    )
    if card_id is None:
        return {"added": False, "reason": "already_learned"}
    return {"added": True, "card_id": str(card_id)}
