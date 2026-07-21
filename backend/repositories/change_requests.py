"""Card change requests — votable staff suggestions on live content.

Contributor-domain: every function runs on the privileged connection AFTER
the router verifies the caller's role for the request's language (same
pattern as review notes / grammar authoring).
"""
from __future__ import annotations

import asyncpg


async def create_request(
    conn: asyncpg.Connection,
    author_id: str,
    language_id: str,
    target_type: str,
    target_id: str | None,
    target_label: str | None,
    field: str,
    issue: str,
    suggestion: str | None,
) -> str:
    return str(await conn.fetchval(
        """
        INSERT INTO card_change_requests
            (author_id, language_id, target_type, target_id, target_label,
             field, issue, suggestion)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        author_id, language_id, target_type, target_id, target_label,
        field, issue, suggestion or None,
    ))


async def list_requests(
    conn: asyncpg.Connection,
    language_id: str,
    viewer_id: str,
    status: str = "open",
) -> list[dict]:
    """Requests for a language with vote tallies and the viewer's own vote.

    Author email is resolved so the board reads without a second call.
    """
    rows = await conn.fetch(
        """
        SELECT cr.id, cr.target_type, cr.target_id, cr.target_label,
               cr.field, cr.issue, cr.suggestion, cr.status,
               cr.created_at, cr.author_id,
               au.email AS author_email,
               COALESCE(SUM(v.vote), 0)                                  AS score,
               COUNT(v.vote) FILTER (WHERE v.vote = 1)                   AS upvotes,
               COUNT(v.vote) FILTER (WHERE v.vote = -1)                  AS downvotes,
               MAX(v.vote) FILTER (WHERE v.user_id = $3)                 AS my_vote
        FROM card_change_requests cr
        LEFT JOIN card_change_request_votes v ON v.request_id = cr.id
        LEFT JOIN auth.users au ON au.id = cr.author_id
        WHERE cr.language_id = $1 AND cr.status = $2
        GROUP BY cr.id, au.email
        ORDER BY COALESCE(SUM(v.vote), 0) DESC, cr.created_at DESC
        """,
        language_id, status, viewer_id,
    )
    return [
        {
            "id": str(r["id"]),
            "target_type": r["target_type"],
            "target_id": str(r["target_id"]) if r["target_id"] else None,
            "target_label": r["target_label"],
            "field": r["field"],
            "issue": r["issue"],
            "suggestion": r["suggestion"],
            "status": r["status"],
            "author_email": r["author_email"],
            "score": int(r["score"]),
            "upvotes": int(r["upvotes"]),
            "downvotes": int(r["downvotes"]),
            "my_vote": int(r["my_vote"]) if r["my_vote"] is not None else 0,
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def cast_vote(
    conn: asyncpg.Connection, request_id: str, user_id: str, vote: int
) -> bool:
    """Set (vote = ±1) or clear (vote = 0) the caller's vote. Idempotent."""
    exists = await conn.fetchval(
        "SELECT 1 FROM card_change_requests WHERE id = $1", request_id
    )
    if not exists:
        return False
    if vote == 0:
        await conn.execute(
            "DELETE FROM card_change_request_votes WHERE request_id = $1 AND user_id = $2",
            request_id, user_id,
        )
    else:
        await conn.execute(
            """
            INSERT INTO card_change_request_votes (request_id, user_id, vote)
            VALUES ($1, $2, $3)
            ON CONFLICT (request_id, user_id) DO UPDATE SET vote = EXCLUDED.vote
            """,
            request_id, user_id, vote,
        )
    return True


async def get_request_language(
    conn: asyncpg.Connection, request_id: str
) -> str | None:
    lid = await conn.fetchval(
        "SELECT language_id FROM card_change_requests WHERE id = $1", request_id
    )
    return str(lid) if lid else None


async def resolve_request(
    conn: asyncpg.Connection, request_id: str, resolver_id: str, status: str
) -> bool:
    res = await conn.execute(
        """
        UPDATE card_change_requests
        SET status = $2, resolved_by = $3, resolved_at = now()
        WHERE id = $1 AND status = 'open'
        """,
        request_id, status, resolver_id,
    )
    return res.endswith(" 1")
