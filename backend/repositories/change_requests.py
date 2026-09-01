"""Card change requests — votable staff suggestions on live content.

Contributor-domain: every function runs on the privileged connection AFTER
the router verifies the caller's role for the request's language (same
pattern as review notes / grammar authoring).
"""
from __future__ import annotations

import json

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
    quote: str | None = None,
    quote_context: dict | None = None,
) -> str:
    """*quote* is the exact span a reviewer selected (Review Mode), and
    *quote_context* the surface-specific detail — offsets, surrounding text,
    which tutor message. Both are snapshots: a tutor reply is never stored,
    and a card's quote has to outlive the edit it is asking for."""
    return str(await conn.fetchval(
        """
        INSERT INTO card_change_requests
            (author_id, language_id, target_type, target_id, target_label,
             field, issue, suggestion, quote, quote_context)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
        RETURNING id
        """,
        author_id, language_id, target_type, target_id, target_label,
        field, issue, suggestion or None,
        (quote or "").strip() or None,
        json.dumps(quote_context or {}),
    ))


def _as_dict(value) -> dict:
    """asyncpg hands jsonb back as text unless a codec is registered."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return {}
    return {}


async def list_requests(
    conn: asyncpg.Connection,
    language_id: str,
    viewer_id: str,
    status: str = "open",
) -> list[dict]:
    """Requests for a language with vote tallies and the viewer's own vote.

    Author email is resolved so the board reads without a second call.

    `is_advisory` marks a request raised by someone whose only standing for
    this language is *tester* — testers may raise and read the board but
    never vote or resolve, so triage has to be able to tell their input
    apart from a full contributor's. It is DERIVED from the author's roles
    rather than stored: adding a column would need a migration, and
    migrations here are owner-applied. The trade-off is that it reflects the
    author's roles *now*, not at the time of writing — acceptable, since
    promoting a tester should indeed retire the advisory marking.
    """
    rows = await conn.fetch(
        """
        SELECT cr.id, cr.target_type, cr.target_id, cr.target_label,
               cr.field, cr.issue, cr.suggestion, cr.status,
               cr.quote, cr.quote_context,
               cr.created_at, cr.author_id,
               au.email AS author_email,
               NOT EXISTS (
                   SELECT 1 FROM contributor_roles r
                    WHERE r.user_id = cr.author_id
                      AND r.role IN ('admin', 'contributor', 'reviewer')
                      AND (r.language_id IS NULL
                           OR r.language_id = cr.language_id)
               ) AS is_advisory,
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
            # The words the reviewer actually objected to — what the board
            # shows, so triage never has to guess which clause was meant.
            "quote": r["quote"],
            "quote_context": _as_dict(r["quote_context"]),
            "author_email": r["author_email"],
            # Raised by a tester: read it, weigh it, but it carries no vote.
            "is_advisory": bool(r["is_advisory"]),
            "score": int(r["score"]),
            "upvotes": int(r["upvotes"]),
            "downvotes": int(r["downvotes"]),
            "my_vote": int(r["my_vote"]) if r["my_vote"] is not None else 0,
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


# The card a request is ABOUT, per target_type. A reviewer cannot judge
# "gives the answer away" on a hint without the sentence and answer next to
# it (owner: "it is hard to decide when you don't see the full card") — the
# board used to show a bare label and the complaint, and nothing else.
#
# Three of the seven target types have no row to fetch. 'tutor_message' and
# 'reading' are generated per learner and never stored, so the QUOTE captured
# at flag time is the whole record; 'other' names nothing in particular.
# Those degrade to what the request already carries rather than erroring —
# the same reason target_id is nullable.
#
# Every statement selects the same six columns under the same names, so one
# loop below reads them all. `context` is whatever situates the item: the
# grammar point a drill belongs to, the word an example illustrates.
_CARD_SQL: dict[str, str] = {
    "drill": """
        SELECT d.id, d.sentence, d.answer, d.hint, d.translation,
               gp.title AS context, gp.level
          FROM drill_sentences d
          JOIN grammar_points gp ON gp.id = d.grammar_point_id
         WHERE d.id = ANY($1::uuid[])
    """,
    "example_sentence": """
        SELECT e.id, e.sentence, NULL::text AS answer, NULL::text AS hint,
               e.translation, v.word AS context, v.level
          FROM example_sentences e
          JOIN vocabulary v ON v.id = e.vocabulary_id
         WHERE e.id = ANY($1::uuid[])
    """,
    "vocabulary": """
        SELECT v.id, v.word AS sentence, NULL::text AS answer,
               v.reading AS hint,
               (SELECT t.definition FROM translations t
                 WHERE t.vocabulary_id = v.id
                 ORDER BY (t.locale = 'en') DESC LIMIT 1) AS translation,
               v.part_of_speech AS context, v.level
          FROM vocabulary v
         WHERE v.id = ANY($1::uuid[])
    """,
    "grammar_point": """
        SELECT gp.id, gp.title AS sentence, NULL::text AS answer,
               NULL::text AS hint, gp.explanation AS translation,
               NULL::text AS context, gp.level
          FROM grammar_points gp
         WHERE gp.id = ANY($1::uuid[])
    """,
}

_CARD_FIELDS = ("sentence", "answer", "hint", "translation", "context", "level")


async def load_cards(conn: asyncpg.Connection, requests: list[dict]) -> None:
    """Attach a `card` to each request that names one, in place.

    Grouped by target_type so this is one query per KIND present, not one
    per request — a board of 200 rows spanning four kinds costs four
    queries.

    A target that has since been deleted simply gets no card. The request
    outlives the row it was raised against, and "the card this was about is
    gone" is a legitimate thing for the board to show; it is also why the
    card is optional on the way out rather than making the request
    unrenderable.
    """
    # Read every field with .get(): this function attaches OPTIONAL context
    # and must never be the reason a board fails to render. A row without a
    # target_type simply gets no card.
    by_type: dict[str, list[str]] = {}
    for r in requests:
        target_type = r.get("target_type")
        if r.get("target_id") and target_type in _CARD_SQL:
            by_type.setdefault(target_type, []).append(r["target_id"])

    found: dict[tuple[str, str], dict] = {}
    for target_type, ids in by_type.items():
        rows = await conn.fetch(_CARD_SQL[target_type], ids)
        for row in rows:
            found[(target_type, str(row["id"]))] = {
                f: row[f] for f in _CARD_FIELDS
            }

    for r in requests:
        r["card"] = found.get(
            (r.get("target_type") or "", r.get("target_id") or "")
        )


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
