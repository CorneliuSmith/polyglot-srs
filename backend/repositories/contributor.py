"""Contributor repository — roles and specialist grammar authoring.

Reads (roles, grammar listing) run under the user's RLS connection. Writes
(saving an explanation, approving, granting a role) run under a privileged
connection AFTER the router has checked the caller's role in the app layer.
"""

from __future__ import annotations

import json

import asyncpg

from backend.services.references import clean_references
from backend.services.seeder.morphology_charts import strip_nominal_chips


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


async def get_language_tutor_model(
    conn: asyncpg.Connection, language_id: str
) -> str | None:
    """The language's tutor model override (None = global default)."""
    return await conn.fetchval(
        "SELECT tutor_model FROM languages WHERE id = $1", language_id
    )


async def set_language_tutor_model(
    conn: asyncpg.Connection, language_id: str, model: str | None
) -> None:
    """Set (or clear) a language's tutor model (privileged, admin-only)."""
    await conn.execute(
        "UPDATE languages SET tutor_model = $2 WHERE id = $1",
        language_id, model,
    )


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


async def update_drill(
    conn: asyncpg.Connection,
    drill_id: str,
    point_id: str,
    sentence: str,
    answer: str,
    translation: str | None,
    hint: str | None,
) -> bool:
    """Edit a live drill (privileged). The edit de-certifies the point —
    reviewed flips false so a SECOND reviewer must re-approve before
    learners see the change (nobody self-certifies an edit)."""
    result = await conn.execute(
        """
        UPDATE drill_sentences
        SET sentence = $3, answer = $4, translation = $5, hint = $6
        WHERE id = $1 AND grammar_point_id = $2
        """,
        drill_id, point_id, sentence, answer, translation or None, hint or None,
    )
    if not result.endswith("1"):
        return False
    await conn.execute(
        "UPDATE grammar_points SET reviewed = false WHERE id = $1", point_id
    )
    return True


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


async def list_accounts(conn: asyncpg.Connection) -> list[dict]:
    """Every account with what an admin needs at a glance (privileged;
    router verifies the admin role first): email, joined, plan, roles,
    and how much they've studied."""
    rows = await conn.fetch(
        """
        SELECT u.id, u.email, u.created_at, u.last_sign_in_at,
               up.plan_scope, pl.code AS plan_language,
               up.tutor_access, up.tutor_daily_cap,
               COALESCE(r.roles, '{}') AS roles,
               COALESCE(c.cards, 0) AS cards,
               COALESCE(c.langs, 0) AS languages_studied
        FROM auth.users u
        LEFT JOIN user_profiles up ON up.id = u.id
        LEFT JOIN languages pl ON pl.id = up.plan_language_id
        LEFT JOIN LATERAL (
            SELECT array_agg(DISTINCT cr.role) AS roles
            FROM contributor_roles cr WHERE cr.user_id = u.id
        ) r ON true
        LEFT JOIN LATERAL (
            SELECT count(*) AS cards, count(DISTINCT uc.language_id) AS langs
            FROM user_cards uc WHERE uc.user_id = u.id
        ) c ON true
        ORDER BY u.created_at DESC
        """
    )
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "last_sign_in_at": (
                r["last_sign_in_at"].isoformat() if r["last_sign_in_at"] else None
            ),
            "plan_scope": r["plan_scope"],
            "plan_language": r["plan_language"],
            "tutor_access": r["tutor_access"] or "default",
            "tutor_daily_cap": r["tutor_daily_cap"],
            "roles": list(r["roles"] or []),
            "cards": r["cards"],
            "languages_studied": r["languages_studied"],
        }
        for r in rows
    ]


async def delete_account(conn: asyncpg.Connection, user_id: str) -> bool:
    """Permanently delete an account (privileged; router verifies admin +
    not-self). Deleting the auth.users row cascades through the auth
    schema AND every app table (all carry ON DELETE CASCADE on user_id):
    profile, cards, review history, notes, subscriptions, roles."""
    result = await conn.execute("DELETE FROM auth.users WHERE id = $1", user_id)
    return result.endswith("1")


async def set_account_plan(
    conn: asyncpg.Connection,
    user_id: str,
    plan_scope: str,
    plan_language_id: str | None,
) -> bool:
    """Admin plan override: switch an account between Single and All."""
    result = await conn.execute(
        """
        UPDATE user_profiles
        SET plan_scope = $2,
            plan_language_id = CASE WHEN $2 = 'single'
                                    THEN $3::uuid ELSE NULL END
        WHERE id = $1
        """,
        user_id, plan_scope, plan_language_id,
    )
    return result.endswith("1")


async def create_auth_user(
    conn: asyncpg.Connection, email: str, password: str
) -> str:
    """Create a confirmed email+password auth account via SQL (privileged).

    Fallback for when the GoTrue admin HTTP API is unreachable from the
    server (the deploy's egress to *.supabase.co hangs while the database
    pooler works fine). Writes exactly what /auth/v1/admin/users with
    email_confirm=true writes: a confirmed auth.users row hashed with
    pgcrypto's bf crypt — the same check GoTrue runs at sign-in — plus its
    email identity. Token columns are '' not NULL (GoTrue scans them).
    Raises ValueError on a duplicate email.
    """
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO auth.users
                    (instance_id, id, aud, role, email, encrypted_password,
                     email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
                     created_at, updated_at,
                     confirmation_token, recovery_token,
                     email_change, email_change_token_new)
                VALUES
                    ('00000000-0000-0000-0000-000000000000', gen_random_uuid(),
                     'authenticated', 'authenticated', lower($1),
                     extensions.crypt($2, extensions.gen_salt('bf')),
                     now(), '{"provider": "email", "providers": ["email"]}',
                     '{}', now(), now(), '', '', '', '')
                RETURNING id
                """,
                email, password,
            )
            uid = str(row["id"])
            await conn.execute(
                """
                INSERT INTO auth.identities
                    (id, user_id, provider_id, identity_data, provider,
                     last_sign_in_at, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), $1::uuid, $1,
                     jsonb_build_object('sub', $1, 'email', lower($2),
                                        'email_verified', true),
                     'email', now(), now(), now())
                """,
                uid, email,
            )
    except asyncpg.UniqueViolationError as exc:
        raise ValueError("email already registered") from exc
    return uid


# ── Content suggestions (contributor-proposed card edits) ─────────────────
# The editable text fields a contributor may propose changing on a card.
SUGGESTION_FIELDS = {
    "vocabulary": ("definition", "part_of_speech", "usage_note"),
    "grammar": ("function_note", "explanation", "culture_note"),
}


async def entity_language(
    conn: asyncpg.Connection, entity_type: str, entity_id: str
) -> str | None:
    """The language_id owning a vocabulary row or grammar point, or None."""
    table = "vocabulary" if entity_type == "vocabulary" else "grammar_points"
    lid = await conn.fetchval(
        f"SELECT language_id FROM {table} WHERE id = $1", entity_id
    )
    return str(lid) if lid else None


async def submit_suggestion(
    conn: asyncpg.Connection,
    language_id: str,
    entity_type: str,
    entity_id: str,
    author_id: str,
    proposed: dict,
    note: str | None,
) -> str:
    """Store a proposed edit (pending). Only known fields are kept."""
    allowed = SUGGESTION_FIELDS[entity_type]
    clean = {
        k: (v.strip() if isinstance(v, str) else v)
        for k, v in proposed.items()
        if k in allowed and v is not None and str(v).strip() != ""
    }
    if not clean:
        raise ValueError("no editable fields in proposal")
    row = await conn.fetchrow(
        """
        INSERT INTO content_suggestions
            (language_id, entity_type, entity_id, author_id, proposed, note)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        language_id, entity_type, entity_id, author_id,
        json.dumps(clean, ensure_ascii=False), (note or "").strip() or None,
    )
    return str(row["id"])


async def _current_fields(
    conn: asyncpg.Connection, entity_type: str, entity_id: str
) -> dict:
    """The card's current values for the suggestable fields (for the diff)."""
    if entity_type == "vocabulary":
        r = await conn.fetchrow(
            """
            SELECT v.word, v.part_of_speech, v.usage_note,
                   (SELECT definition FROM translations
                     WHERE vocabulary_id = v.id AND locale = 'en' LIMIT 1) AS definition
            FROM vocabulary v WHERE v.id = $1
            """,
            entity_id,
        )
        if not r:
            return {}
        return {"title": r["word"], "definition": r["definition"],
                "part_of_speech": r["part_of_speech"], "usage_note": r["usage_note"]}
    r = await conn.fetchrow(
        "SELECT title, function_note, explanation, culture_note "
        "FROM grammar_points WHERE id = $1", entity_id,
    )
    if not r:
        return {}
    return {"title": r["title"], "function_note": r["function_note"],
            "explanation": r["explanation"], "culture_note": r["culture_note"]}


async def list_suggestions(
    conn: asyncpg.Connection, language_id: str, status_filter: str = "pending"
) -> list[dict]:
    """Pending suggestions for a language, each with current vs proposed."""
    rows = await conn.fetch(
        """
        SELECT s.id, s.entity_type, s.entity_id, s.proposed, s.note,
               s.status, s.created_at
        FROM content_suggestions s
        WHERE s.language_id = $1 AND s.status = $2
        ORDER BY s.created_at ASC
        LIMIT 100
        """,
        language_id, status_filter,
    )
    out = []
    for r in rows:
        current = await _current_fields(conn, r["entity_type"], str(r["entity_id"]))
        proposed = r["proposed"]
        if isinstance(proposed, str):
            proposed = json.loads(proposed)
        out.append({
            "id": str(r["id"]),
            "entity_type": r["entity_type"],
            "entity_id": str(r["entity_id"]),
            "card_title": current.get("title"),
            "current": {k: v for k, v in current.items() if k != "title"},
            "proposed": proposed,
            "note": r["note"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return out


async def get_suggestion(conn: asyncpg.Connection, suggestion_id: str) -> dict | None:
    """Raw suggestion row (for the router's language + status checks)."""
    r = await conn.fetchrow(
        "SELECT id, language_id, entity_type, entity_id, proposed, status "
        "FROM content_suggestions WHERE id = $1", suggestion_id,
    )
    if not r:
        return None
    proposed = r["proposed"]
    if isinstance(proposed, str):
        proposed = json.loads(proposed)
    return {"id": str(r["id"]), "language_id": str(r["language_id"]),
            "entity_type": r["entity_type"], "entity_id": str(r["entity_id"]),
            "proposed": proposed, "status": r["status"]}


async def _apply_to_entity(
    conn: asyncpg.Connection, entity_type: str, entity_id: str, proposed: dict
) -> None:
    """Write an approved proposal onto the live card."""
    allowed = SUGGESTION_FIELDS[entity_type]
    fields = {k: v for k, v in proposed.items() if k in allowed}
    if entity_type == "vocabulary":
        if "part_of_speech" in fields:
            await conn.execute(
                "UPDATE vocabulary SET part_of_speech = $1 WHERE id = $2",
                fields["part_of_speech"], entity_id,
            )
            # a POS change can retire wrong-sense gender/number chips
            m = await conn.fetchval(
                "SELECT morphology FROM vocabulary WHERE id = $1", entity_id)
            if isinstance(m, str):
                m = json.loads(m) if m else {}
            new = strip_nominal_chips(m, fields["part_of_speech"])
            if new != m:
                await conn.execute(
                    "UPDATE vocabulary SET morphology = $1 WHERE id = $2",
                    json.dumps(new, ensure_ascii=False), entity_id)
        if "usage_note" in fields:
            await conn.execute(
                "UPDATE vocabulary SET usage_note = $1 WHERE id = $2",
                fields["usage_note"], entity_id,
            )
        if "definition" in fields:
            await conn.execute(
                """
                INSERT INTO translations (vocabulary_id, locale, definition)
                VALUES ($1, 'en', $2)
                ON CONFLICT (vocabulary_id, locale)
                    DO UPDATE SET definition = EXCLUDED.definition
                """,
                entity_id, fields["definition"],
            )
    else:  # grammar
        cols = [k for k in ("function_note", "explanation", "culture_note")
                if k in fields]
        if cols:
            sets = ", ".join(f"{c} = ${i + 2}" for i, c in enumerate(cols))
            await conn.execute(
                f"UPDATE grammar_points SET {sets} WHERE id = $1",
                entity_id, *[fields[c] for c in cols],
            )


async def approve_suggestion(
    conn: asyncpg.Connection, suggestion_id: str, reviewer_id: str
) -> bool:
    """Apply a pending suggestion to the card and mark it approved."""
    s = await get_suggestion(conn, suggestion_id)
    if not s or s["status"] != "pending":
        return False
    async with conn.transaction():
        await _apply_to_entity(conn, s["entity_type"], s["entity_id"], s["proposed"])
        await conn.execute(
            """
            UPDATE content_suggestions
            SET status = 'approved', reviewer_id = $2, resolved_at = now()
            WHERE id = $1
            """,
            suggestion_id, reviewer_id,
        )
    return True


async def reject_suggestion(
    conn: asyncpg.Connection, suggestion_id: str, reviewer_id: str,
    review_note: str | None,
) -> bool:
    """Mark a pending suggestion rejected (nothing is applied)."""
    result = await conn.execute(
        """
        UPDATE content_suggestions
        SET status = 'rejected', reviewer_id = $2, review_note = $3,
            resolved_at = now()
        WHERE id = $1 AND status = 'pending'
        """,
        suggestion_id, reviewer_id, (review_note or "").strip() or None,
    )
    return result.endswith("1")


async def admin_engagement_users(
    conn: asyncpg.Connection, days: int = 30
) -> list[dict]:
    """Per-user engagement drill-down for the admin panel (privileged conn).

    One row per account: identity, when they joined, when they were last
    active anywhere, and their activity counts inside the window — the
    detail behind the aggregate tiles. Same activity tables, no new
    tracking.
    """
    rows = await conn.fetch(
        """
        SELECT u.id, u.email, p.created_at AS joined,
          (SELECT count(*) FROM review_log rl
            WHERE rl.user_id = u.id
              AND rl.created_at > now() - make_interval(days => $1)) AS reviews,
          (SELECT COALESCE(sum(rl.time_taken_ms), 0) FROM review_log rl
            WHERE rl.user_id = u.id
              AND rl.created_at > now() - make_interval(days => $1)) AS review_ms,
          (SELECT count(*) FROM tutor_usage tu
            WHERE tu.user_id = u.id
              AND tu.created_at > now() - make_interval(days => $1)) AS tutor_messages,
          (SELECT count(*) FROM readings r
            WHERE r.user_id = u.id
              AND r.created_at > now() - make_interval(days => $1)) AS readings,
          (SELECT count(*) FROM user_cards uc
            WHERE uc.user_id = u.id
              AND uc.created_at > now() - make_interval(days => $1)) AS cards_started,
          (SELECT count(*) FROM user_cards uc
            WHERE uc.user_id = u.id) AS cards_total,
          (SELECT max(t) FROM (
              SELECT max(created_at) AS t FROM review_log WHERE user_id = u.id
              UNION ALL SELECT max(created_at) FROM tutor_usage WHERE user_id = u.id
              UNION ALL SELECT max(created_at) FROM readings WHERE user_id = u.id
              UNION ALL SELECT max(created_at) FROM user_cards WHERE user_id = u.id
          ) acts) AS last_active,
          (SELECT COALESCE(array_agg(DISTINCT l.code), '{}') FROM user_cards uc
            JOIN languages l ON uc.language_id = l.id
            WHERE uc.user_id = u.id) AS languages
        FROM auth.users u
        LEFT JOIN user_profiles p ON p.id = u.id
        ORDER BY last_active DESC NULLS LAST
        LIMIT 200
        """,
        days,
    )
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "joined": r["joined"].isoformat() if r["joined"] else None,
            "last_active": r["last_active"].isoformat() if r["last_active"] else None,
            "reviews": r["reviews"],
            "review_minutes": round((r["review_ms"] or 0) / 60_000),
            "tutor_messages": r["tutor_messages"],
            "readings": r["readings"],
            "cards_started": r["cards_started"],
            "cards_total": r["cards_total"],
            "languages": list(r["languages"] or []),
        }
        for r in rows
    ]


async def admin_timeseries(conn: asyncpg.Connection, days: int = 30) -> list[dict]:
    """Daily activity series for the admin analytics charts (WP26a).

    One row per calendar day (UTC): distinct active users across every
    activity table, review count, study minutes, and new signups. All
    from tables normal use writes — no extra tracking.
    """
    rows = await conn.fetch(
        """
        SELECT day::date AS day,
          (SELECT count(DISTINCT u) FROM (
              SELECT user_id AS u FROM review_log
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
              UNION SELECT user_id FROM tutor_usage
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
              UNION SELECT user_id FROM readings
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
              UNION SELECT user_id FROM user_cards
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
          ) acts) AS active_users,
          (SELECT count(*) FROM review_log
            WHERE (created_at AT TIME ZONE 'UTC')::date = day) AS reviews,
          (SELECT COALESCE(sum(time_taken_ms), 0) / 60000 FROM review_log
            WHERE (created_at AT TIME ZONE 'UTC')::date = day) AS minutes,
          (SELECT count(*) FROM user_profiles
            WHERE (created_at AT TIME ZONE 'UTC')::date = day) AS new_users
        FROM generate_series(
            (now() AT TIME ZONE 'UTC')::date - ($1 - 1),
            (now() AT TIME ZONE 'UTC')::date,
            interval '1 day'
        ) AS day
        ORDER BY day
        """,
        days,
    )
    return [
        {
            "date": r["day"].isoformat(),
            "active_users": int(r["active_users"]),
            "reviews": int(r["reviews"]),
            "minutes": int(r["minutes"]),
            "new_users": int(r["new_users"]),
        }
        for r in rows
    ]


def compute_cohort_grid(
    signups: list[tuple[str, str]],
    activity: set[tuple[str, str]],
) -> list[dict]:
    """Weekly retention grid (WP26b), pure so it's unit-testable.

    *signups*: (user_id, iso signup-week-start); *activity*: distinct
    (user_id, iso activity-week-start). Week 0 is the signup week itself.
    """
    from datetime import date, timedelta

    cohorts: dict[str, list[str]] = {}
    for uid, wk in signups:
        cohorts.setdefault(wk, []).append(uid)

    grid = []
    for wk in sorted(cohorts):
        members = cohorts[wk]
        start = date.fromisoformat(wk)
        weeks = []
        for offset in range(8):
            target = (start + timedelta(weeks=offset)).isoformat()
            returned = sum(1 for uid in members if (uid, target) in activity)
            weeks.append(returned)
        grid.append({"cohort_week": wk, "size": len(members), "returned": weeks})
    return grid


async def admin_cohorts(conn: asyncpg.Connection, weeks: int = 8) -> list[dict]:
    """Signup-cohort retention (WP26b): of each week's signups, how many
    were active in week 0, 1, 2…  Small data — aggregate in Python."""
    signup_rows = await conn.fetch(
        """
        SELECT id, date_trunc('week', created_at AT TIME ZONE 'UTC')::date AS wk
        FROM user_profiles
        WHERE created_at > now() - make_interval(weeks => $1)
        """,
        weeks,
    )
    activity_rows = await conn.fetch(
        """
        SELECT DISTINCT user_id,
               date_trunc('week', created_at AT TIME ZONE 'UTC')::date AS wk
        FROM (
            SELECT user_id, created_at FROM review_log
            UNION ALL SELECT user_id, created_at FROM tutor_usage
            UNION ALL SELECT user_id, created_at FROM readings
            UNION ALL SELECT user_id, created_at FROM user_cards
        ) acts
        WHERE created_at > now() - make_interval(weeks => $1)
        """,
        weeks,
    )
    signups = [(str(r["id"]), r["wk"].isoformat()) for r in signup_rows]
    activity = {(str(r["user_id"]), r["wk"].isoformat()) for r in activity_rows}
    return compute_cohort_grid(signups, activity)


async def admin_engagement_user_detail(
    conn: asyncpg.Connection, user_id: str, days: int = 30
) -> list[dict]:
    """Per-language activity for ONE account (privileged conn) — what an
    admin sees when they expand a row in the engagement users table.
    review_log carries no language_id, so reviews route through the card.
    """
    rows = await conn.fetch(
        """
        SELECT l.code, l.name,
          (SELECT count(*) FROM user_cards uc
            WHERE uc.user_id = $1 AND uc.language_id = l.id) AS cards_total,
          (SELECT count(*) FROM review_log rl
            JOIN user_cards uc2 ON uc2.id = rl.card_id
            WHERE rl.user_id = $1 AND uc2.language_id = l.id
              AND rl.created_at > now() - make_interval(days => $2)) AS reviews,
          (SELECT COALESCE(sum(rl.time_taken_ms), 0) FROM review_log rl
            JOIN user_cards uc2 ON uc2.id = rl.card_id
            WHERE rl.user_id = $1 AND uc2.language_id = l.id
              AND rl.created_at > now() - make_interval(days => $2)) AS review_ms,
          (SELECT count(*) FROM tutor_usage tu
            WHERE tu.user_id = $1 AND tu.language_id = l.id
              AND tu.created_at > now() - make_interval(days => $2)) AS tutor_messages,
          (SELECT count(*) FROM readings r
            WHERE r.user_id = $1 AND r.language_id = l.id
              AND r.created_at > now() - make_interval(days => $2)) AS readings,
          (SELECT max(uc3.last_review) FROM user_cards uc3
            WHERE uc3.user_id = $1 AND uc3.language_id = l.id) AS last_review
        FROM languages l
        WHERE EXISTS (SELECT 1 FROM user_cards uc0
                       WHERE uc0.user_id = $1 AND uc0.language_id = l.id)
           OR EXISTS (SELECT 1 FROM tutor_usage tu0
                       WHERE tu0.user_id = $1 AND tu0.language_id = l.id)
           OR EXISTS (SELECT 1 FROM readings r0
                       WHERE r0.user_id = $1 AND r0.language_id = l.id)
        ORDER BY cards_total DESC
        """,
        user_id, days,
    )
    return [
        {
            "code": r["code"],
            "name": r["name"],
            "cards_total": r["cards_total"],
            "reviews": r["reviews"],
            "review_minutes": round((r["review_ms"] or 0) / 60_000),
            "tutor_messages": r["tutor_messages"],
            "readings": r["readings"],
            "last_review": r["last_review"].isoformat() if r["last_review"] else None,
        }
        for r in rows
    ]


# ── Translation review queue (what the AI maker-checker wouldn't apply) ───
async def list_translation_reviews(
    conn: asyncpg.Connection, status_filter: str = "pending"
) -> list[dict]:
    """Pending AI-translation rejects, with the card's word + current gloss."""
    rows = await conn.fetch(
        """
        SELECT r.id, r.locale, r.proposed, r.reason, r.status, r.created_at,
               v.word,
               (SELECT definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                   AS current_definition
        FROM translation_reviews r
        JOIN vocabulary v ON r.vocabulary_id = v.id
        WHERE r.status = $1
        ORDER BY r.locale, r.created_at
        LIMIT 200
        """,
        status_filter,
    )
    return [
        {
            "id": str(r["id"]), "locale": r["locale"], "word": r["word"],
            "proposed": r["proposed"], "reason": r["reason"],
            "current_definition": r["current_definition"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def resolve_translation_review(
    conn: asyncpg.Connection, review_id: str, approve: bool
) -> str:
    """Approve (apply the proposed gloss to its real locale) or reject.

    'en-hint' rows are flagged ENGLISH definitions, so they apply to 'en';
    every other row applies to its own support locale. Returns
    'ok' | 'not_found' | 'not_pending' | 'empty'.
    """
    r = await conn.fetchrow(
        "SELECT id, vocabulary_id, locale, proposed, status "
        "FROM translation_reviews WHERE id = $1",
        review_id,
    )
    if not r:
        return "not_found"
    if r["status"] != "pending":
        return "not_pending"
    if approve:
        proposed = (r["proposed"] or "").strip()
        if not proposed:
            return "empty"
        target = "en" if r["locale"] == "en-hint" else r["locale"]
        await conn.execute(
            """
            INSERT INTO translations (vocabulary_id, locale, definition)
            VALUES ($1, $2, $3)
            ON CONFLICT (vocabulary_id, locale)
                DO UPDATE SET definition = EXCLUDED.definition
            """,
            r["vocabulary_id"], target, proposed,
        )
    await conn.execute(
        "UPDATE translation_reviews SET status = $2 WHERE id = $1",
        review_id, "approved" if approve else "rejected",
    )
    return "ok"


async def admin_engagement(conn: asyncpg.Connection, days: int = 30) -> dict:
    """App-wide engagement snapshot for the admin panel (privileged conn).

    Answers "who is using the app, doing what, for how long" from the
    activity tables already written by normal use — review_log (reviews +
    per-answer time), tutor_usage (tutor messages), readings (Reader
    sessions), user_cards (cards started). No new tracking: this is a read
    over existing data. All users, all languages.
    """
    since_expr = f"now() - interval '{int(days)} days'"

    totals = await conn.fetchrow(
        f"""
        SELECT
          (SELECT count(*) FROM user_profiles) AS total_users,
          (SELECT count(*) FROM user_profiles
             WHERE created_at > {since_expr}) AS new_users,
          (SELECT count(*) FROM review_log
             WHERE created_at > {since_expr}) AS reviews,
          (SELECT COALESCE(sum(time_taken_ms), 0) FROM review_log
             WHERE created_at > {since_expr}) AS review_ms,
          (SELECT count(*) FROM tutor_usage
             WHERE created_at > {since_expr}) AS tutor_messages,
          (SELECT count(*) FROM readings
             WHERE created_at > {since_expr}) AS readings,
          (SELECT count(*) FROM user_cards
             WHERE created_at > {since_expr}) AS cards_started
        """
    )

    # Active users per window: anyone with ANY activity (review / tutor /
    # reading / new card) in the window.
    active = await conn.fetchrow(
        """
        SELECT
          count(DISTINCT u) FILTER (WHERE t > now() - interval '1 day')  AS d1,
          count(DISTINCT u) FILTER (WHERE t > now() - interval '7 days')  AS d7,
          count(DISTINCT u) FILTER (WHERE t > now() - interval '30 days') AS d30
        FROM (
          SELECT user_id AS u, created_at AS t FROM review_log
          UNION ALL SELECT user_id, created_at FROM tutor_usage
          UNION ALL SELECT user_id, created_at FROM readings
          UNION ALL SELECT user_id, created_at FROM user_cards
        ) acts
        """
    )

    # Distinct users who touched each feature in the window — which features
    # are actually pulling their weight.
    feature_users = await conn.fetchrow(
        f"""
        SELECT
          (SELECT count(DISTINCT user_id) FROM review_log
             WHERE created_at > {since_expr}) AS review_users,
          (SELECT count(DISTINCT user_id) FROM tutor_usage
             WHERE created_at > {since_expr}) AS tutor_users,
          (SELECT count(DISTINCT user_id) FROM readings
             WHERE created_at > {since_expr}) AS reader_users
        """
    )

    # Which languages people are actually studying (by active cards).
    top_langs = await conn.fetch(
        """
        SELECT l.code, l.name, count(DISTINCT uc.user_id) AS learners,
               count(*) AS cards
        FROM user_cards uc JOIN languages l ON uc.language_id = l.id
        GROUP BY l.code, l.name
        ORDER BY learners DESC, cards DESC
        LIMIT 8
        """
    )

    review_ms = int(totals["review_ms"] or 0)
    return {
        "days": days,
        "total_users": totals["total_users"],
        "new_users": totals["new_users"],
        "active_users": {
            "d1": active["d1"], "d7": active["d7"], "d30": active["d30"],
        },
        "reviews": totals["reviews"],
        "review_hours": round(review_ms / 3_600_000, 1),
        "tutor_messages": totals["tutor_messages"],
        "readings": totals["readings"],
        "cards_started": totals["cards_started"],
        "feature_users": {
            "review": feature_users["review_users"],
            "tutor": feature_users["tutor_users"],
            "reader": feature_users["reader_users"],
        },
        "top_languages": [
            {"code": r["code"], "name": r["name"],
             "learners": r["learners"], "cards": r["cards"]}
            for r in top_langs
        ],
    }
