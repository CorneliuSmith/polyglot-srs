"""Contributor repository — roles and specialist grammar authoring.

Reads (roles, grammar listing) run under the user's RLS connection. Writes
(saving an explanation, approving, granting a role) run under a privileged
connection AFTER the router has checked the caller's role in the app layer.
"""

from __future__ import annotations

import json

import asyncpg

from backend.services.references import clean_references


async def get_roles(conn: asyncpg.Connection, user_id: str) -> list[dict]:
    """Return the user's contributor roles (empty if none)."""
    rows = await conn.fetch(
        "SELECT language_id, role FROM contributor_roles WHERE user_id = $1",
        user_id,
    )
    return [
        {
            "language_id": str(r["language_id"]) if r["language_id"] else None,
            "role": r["role"],
        }
        for r in rows
    ]


def is_admin(roles: list[dict]) -> bool:
    return any(r["role"] == "admin" for r in roles)


def can_contribute(roles: list[dict], language_id: str) -> bool:
    """True if the user may edit grammar for *language_id* (admin or matching contributor)."""
    if is_admin(roles):
        return True
    return any(
        r["role"] == "contributor"
        and (r["language_id"] is None or r["language_id"] == language_id)
        for r in roles
    )


async def list_grammar_points(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """List a language's grammar points with their current explanation state."""
    rows = await conn.fetch(
        """
        SELECT id, title, level, explanation, culture_note,
               explanation_source, reviewed, reference_links
        FROM grammar_points
        WHERE language_id = $1
        ORDER BY display_order ASC, title ASC
        """,
        language_id,
    )

    def _refs(raw):
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = []
        return clean_references(raw)

    return [
        {
            "id": str(r["id"]),
            "title": r["title"],
            "level": r["level"],
            "explanation": r["explanation"],
            "culture_note": r["culture_note"],
            "explanation_source": r["explanation_source"],
            "reviewed": r["reviewed"],
            "references": _refs(r["reference_links"]),
        }
        for r in rows
    ]


async def get_point_language(conn: asyncpg.Connection, point_id: str) -> str | None:
    """Return the language_id of a grammar point, or None if it doesn't exist."""
    lid = await conn.fetchval(
        "SELECT language_id FROM grammar_points WHERE id = $1", point_id
    )
    return str(lid) if lid else None


async def get_point_language_and_code(
    conn: asyncpg.Connection, point_id: str
) -> tuple[str, str] | None:
    """Return (language_id, language_code) for a grammar point, or None."""
    row = await conn.fetchrow(
        """
        SELECT gp.language_id, l.code
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $1
        """,
        point_id,
    )
    if row is None:
        return None
    return str(row["language_id"]), row["code"]


async def create_grammar_point(
    conn: asyncpg.Connection,
    language_id: str,
    title: str,
    level: str | None,
    explanation: str | None,
    culture_note: str | None,
    references: list | None,
    submitted_by: str,
) -> str | None:
    """Create a contributor grammar point (privileged). None if the title exists."""
    next_order = await conn.fetchval(
        "SELECT COALESCE(MAX(display_order), 0) + 1 FROM grammar_points WHERE language_id = $1",
        language_id,
    )
    pid = await conn.fetchval(
        """
        INSERT INTO grammar_points
            (language_id, title, explanation, culture_note, level,
             display_order, explanation_source, reviewed,
             reference_links, explanation_submitted_by)
        VALUES ($1, $2, $3, $4, $5, $6, 'contributor', false, $7::jsonb, $8)
        ON CONFLICT (language_id, title) DO NOTHING
        RETURNING id
        """,
        language_id, title, explanation, culture_note, level, next_order,
        json.dumps(clean_references(references), ensure_ascii=False), submitted_by,
    )
    return str(pid) if pid else None


async def list_drills(conn: asyncpg.Connection, point_id: str) -> list[dict]:
    """List a grammar point's drill sentences for editing."""
    rows = await conn.fetch(
        """
        SELECT id, sentence, answer, translation, hint, display_order
        FROM drill_sentences
        WHERE grammar_point_id = $1
        ORDER BY display_order ASC
        """,
        point_id,
    )
    return [
        {
            "id": str(r["id"]),
            "sentence": r["sentence"],
            "answer": r["answer"],
            "translation": r["translation"],
            "hint": r["hint"],
            "display_order": r["display_order"],
        }
        for r in rows
    ]


async def add_drill(
    conn: asyncpg.Connection,
    point_id: str,
    sentence: str,
    answer: str,
    translation: str | None,
    hint: str | None,
) -> str:
    """Insert a drill sentence (privileged). Adding a drill marks the point unreviewed."""
    next_order = await conn.fetchval(
        "SELECT COALESCE(MAX(display_order), 0) + 1 FROM drill_sentences WHERE grammar_point_id = $1",
        point_id,
    )
    drill_id = await conn.fetchval(
        """
        INSERT INTO drill_sentences
            (grammar_point_id, sentence, answer, translation, hint, display_order)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        point_id, sentence, answer, translation or None, hint or None, next_order,
    )
    await conn.execute(
        "UPDATE grammar_points SET reviewed = false WHERE id = $1", point_id
    )
    return str(drill_id)


async def delete_drill(conn: asyncpg.Connection, drill_id: str) -> bool:
    """Delete a drill sentence (privileged)."""
    result = await conn.execute(
        "DELETE FROM drill_sentences WHERE id = $1", drill_id
    )
    return result.endswith("1")


async def save_explanation(
    conn: asyncpg.Connection,
    point_id: str,
    explanation: str,
    culture_note: str,
    submitted_by: str,
    references: list | None = None,
) -> bool:
    """Save a contributor explanation + references (privileged). Pending review."""
    refs = clean_references(references)
    result = await conn.execute(
        """
        UPDATE grammar_points
        SET explanation = $2,
            culture_note = NULLIF($3, ''),
            reference_links = $5::jsonb,
            explanation_source = 'contributor',
            reviewed = false,
            explanation_submitted_by = $4
        WHERE id = $1
        """,
        point_id, explanation, culture_note, submitted_by,
        json.dumps(refs, ensure_ascii=False),
    )
    return result.endswith("1")


async def approve_explanation(conn: asyncpg.Connection, point_id: str) -> bool:
    """Mark a grammar point's explanation reviewed (privileged, admin-only)."""
    result = await conn.execute(
        "UPDATE grammar_points SET reviewed = true WHERE id = $1", point_id
    )
    return result.endswith("1")


async def grant_role(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str | None,
    role: str,
) -> None:
    """Grant a contributor/admin role (privileged, admin-only)."""
    await conn.execute(
        """
        INSERT INTO contributor_roles (user_id, language_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, language_id, role) DO NOTHING
        """,
        user_id, language_id, role,
    )
