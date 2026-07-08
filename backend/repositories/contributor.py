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
    """True if the user may edit grammar for *language_id*.

    Admins everywhere; contributors and reviewers for their language (a
    reviewer who can approve content can obviously also draft fixes to it).
    """
    if is_admin(roles):
        return True
    return any(
        r["role"] in ("contributor", "reviewer")
        and (r["language_id"] is None or r["language_id"] == language_id)
        for r in roles
    )


def can_review(roles: list[dict], language_id: str) -> bool:
    """True if the user may APPROVE content for *language_id* — the human
    gate that flips reviewed = true. Admins everywhere; reviewers for their
    language (language_id None = all languages)."""
    if is_admin(roles):
        return True
    return any(
        r["role"] == "reviewer"
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
               explanation_source, reviewed, reference_links,
               ai_check_status, ai_check_notes, reviewed_by, reviewed_at
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
            "ai_check_status": r["ai_check_status"],
            "ai_check_notes": r["ai_check_notes"],
            "reviewed_by": str(r["reviewed_by"]) if r["reviewed_by"] else None,
            "reviewed_at": r["reviewed_at"].isoformat() if r["reviewed_at"] else None,
        }
        for r in rows
    ]


async def get_point_for_check(
    conn: asyncpg.Connection, point_id: str
) -> dict | None:
    """Load a grammar point + its drills for the AI semantic review."""
    gp = await conn.fetchrow(
        """
        SELECT gp.title, gp.explanation, l.code AS language_code
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $1
        """,
        point_id,
    )
    if gp is None:
        return None
    drills = await conn.fetch(
        """
        SELECT sentence, answer, translation
        FROM drill_sentences WHERE grammar_point_id = $1
        ORDER BY display_order ASC
        """,
        point_id,
    )
    return {
        "title": gp["title"],
        "explanation": gp["explanation"],
        "language_code": gp["language_code"],
        "drills": [dict(d) for d in drills],
    }


async def save_ai_check(
    conn: asyncpg.Connection, point_id: str, status: str, notes: str
) -> None:
    """Persist the AI semantic-check verdict (privileged)."""
    await conn.execute(
        """
        UPDATE grammar_points
        SET ai_check_status = $2, ai_check_notes = NULLIF($3, ''), ai_checked_at = now()
        WHERE id = $1
        """,
        point_id, status, notes,
    )


async def get_language_policy(conn: asyncpg.Connection, language_id: str) -> str:
    """Return a language's grammar_review_policy ('strict' | 'ai_ok')."""
    policy = await conn.fetchval(
        "SELECT grammar_review_policy FROM languages WHERE id = $1", language_id
    )
    return policy or "strict"


async def set_language_policy(
    conn: asyncpg.Connection, language_id: str, policy: str
) -> bool:
    """Set a language's grammar review policy (privileged, admin-only)."""
    result = await conn.execute(
        "UPDATE languages SET grammar_review_policy = $2 WHERE id = $1",
        language_id, policy,
    )
    return result.endswith("1")


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


async def approve_explanation(
    conn: asyncpg.Connection, point_id: str, reviewer_id: str
) -> bool:
    """Record the human linguist sign-off (privileged, admin-only).

    Marks the point reviewed and stamps who/when — this is the required
    semantic check that gates whether learners ever see the content.
    """
    result = await conn.execute(
        """
        UPDATE grammar_points
        SET reviewed = true, reviewed_by = $2, reviewed_at = now()
        WHERE id = $1
        """,
        point_id, reviewer_id,
    )
    return result.endswith("1")


async def list_feedback(
    conn: asyncpg.Connection, language_id: str, status_filter: str = "open"
) -> list[dict]:
    """List learner feedback for a language (privileged read after role check)."""
    rows = await conn.fetch(
        """
        SELECT f.id, f.card_type, f.content_id, f.message, f.status, f.created_at,
               COALESCE(gp.title, v.word) AS card_title
        FROM card_feedback f
        LEFT JOIN grammar_points gp
               ON f.card_type = 'grammar' AND gp.id = f.content_id
        LEFT JOIN vocabulary v
               ON f.card_type = 'vocabulary' AND v.id = f.content_id
        WHERE f.language_id = $1 AND f.status = $2
        ORDER BY f.created_at DESC
        LIMIT 100
        """,
        language_id, status_filter,
    )
    return [
        {
            "id": str(r["id"]),
            "card_type": r["card_type"],
            "content_id": str(r["content_id"]),
            "card_title": r["card_title"],
            "message": r["message"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_feedback_language(
    conn: asyncpg.Connection, feedback_id: str
) -> str | None:
    """Return the language_id of a feedback row, or None."""
    lid = await conn.fetchval(
        "SELECT language_id FROM card_feedback WHERE id = $1", feedback_id
    )
    return str(lid) if lid else None


async def resolve_feedback(conn: asyncpg.Connection, feedback_id: str) -> bool:
    """Mark a feedback item resolved (privileged)."""
    result = await conn.execute(
        "UPDATE card_feedback SET status = 'resolved' WHERE id = $1", feedback_id
    )
    return result.endswith("1")


async def add_review_note(
    conn: asyncpg.Connection,
    grammar_point_id: str,
    author_id: str,
    note: str,
) -> str:
    """File a reviewer note against a point (privileged, after role check)."""
    return str(await conn.fetchval(
        """
        INSERT INTO point_review_notes (grammar_point_id, author_id, note)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        grammar_point_id, author_id, note,
    ))


async def list_review_notes(
    conn: asyncpg.Connection,
    language_id: str,
    *,
    include_resolved: bool = False,
) -> list[dict]:
    """Reviewer notes for a language's points, newest first (privileged)."""
    rows = await conn.fetch(
        """
        SELECT n.id, n.grammar_point_id, gp.title AS point_title, gp.level,
               n.note, n.status, n.created_at, u.email AS author_email
        FROM point_review_notes n
        JOIN grammar_points gp ON gp.id = n.grammar_point_id
        JOIN auth.users u ON u.id = n.author_id
        WHERE gp.language_id = $1
          AND ($2 OR n.status = 'open')
        ORDER BY n.created_at DESC
        LIMIT 200
        """,
        language_id, include_resolved,
    )
    return [
        {
            "id": str(r["id"]),
            "grammar_point_id": str(r["grammar_point_id"]),
            "point_title": r["point_title"],
            "level": r["level"],
            "note": r["note"],
            "status": r["status"],
            "author_email": r["author_email"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_note_language(
    conn: asyncpg.Connection, note_id: str
) -> str | None:
    """The language a note belongs to (for the resolve role check)."""
    row = await conn.fetchval(
        """
        SELECT gp.language_id
        FROM point_review_notes n
        JOIN grammar_points gp ON gp.id = n.grammar_point_id
        WHERE n.id = $1
        """,
        note_id,
    )
    return str(row) if row else None


async def resolve_review_note(
    conn: asyncpg.Connection, note_id: str, resolver_id: str
) -> bool:
    """Mark a note resolved (privileged, after role check)."""
    result = await conn.execute(
        """
        UPDATE point_review_notes
        SET status = 'resolved', resolved_at = now(), resolved_by = $2
        WHERE id = $1 AND status = 'open'
        """,
        note_id, resolver_id,
    )
    return result.endswith("1")


async def grant_role(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str | None,
    role: str,
) -> None:
    """Grant a contributor/reviewer/admin role (privileged, admin-only)."""
    await conn.execute(
        """
        INSERT INTO contributor_roles (user_id, language_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, language_id, role) DO NOTHING
        """,
        user_id, language_id, role,
    )


async def revoke_role(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str | None,
    role: str,
) -> bool:
    """Remove one role row (privileged, admin-only). True if a row existed."""
    result = await conn.execute(
        """
        DELETE FROM contributor_roles
        WHERE user_id = $1 AND language_id IS NOT DISTINCT FROM $2 AND role = $3
        """,
        user_id, language_id, role,
    )
    return result.endswith("1")


async def list_all_roles(conn: asyncpg.Connection) -> list[dict]:
    """Every role grant with the holder's email (privileged, admin-only)."""
    rows = await conn.fetch(
        """
        SELECT cr.user_id, u.email, cr.language_id, l.code AS language_code,
               cr.role, cr.created_at
        FROM contributor_roles cr
        JOIN auth.users u ON u.id = cr.user_id
        LEFT JOIN languages l ON l.id = cr.language_id
        ORDER BY u.email, cr.role
        """
    )
    return [
        {
            "user_id": str(r["user_id"]),
            "email": r["email"],
            "language_id": str(r["language_id"]) if r["language_id"] else None,
            "language_code": r["language_code"],
            "role": r["role"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def find_user_by_email(
    conn: asyncpg.Connection, email: str
) -> str | None:
    """Resolve an account email to its user id (privileged, admin-only)."""
    row = await conn.fetchval(
        "SELECT id FROM auth.users WHERE lower(email) = lower($1)", email.strip()
    )
    return str(row) if row else None
