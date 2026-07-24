"""Content audit log + rollback (review-workflow solidification).

One append-only timeline (`content_change_log`) of every staff action on a
piece of content, with before/after snapshots on edits. `log_change` is called
from the privileged-connection mutators in `contributor.py`; the router exposes
a per-card history and an admin feed, and `revert_change` re-applies a prior
snapshot to roll an edit back.

Everything runs on the privileged connection after an app-layer role check —
the same trust model as the other review tables.
"""
from __future__ import annotations

import json

import asyncpg

# Per entity type: (table, {column: is_jsonb}) — the fields a revert may restore
# from a `before` snapshot. Column names are a fixed whitelist (never user
# input), so building the SET clause dynamically is safe.
_REVERT_COLUMNS: dict[str, tuple[str, dict[str, bool]]] = {
    "example_sentence": ("example_sentences", {
        "sentence": False, "translation": False, "reviewed": False,
        "flagged": False, "flag_reason": False,
        "suggested_translation": False, "suggestion_reason": False,
    }),
    "drill": ("drill_sentences", {
        "sentence": False, "answer": False, "translation": False,
        "hint": False, "reviewed": False,
    }),
    "grammar_point": ("grammar_points", {
        "explanation": False, "culture_note": False, "reviewed": False,
        "reference_links": True,
    }),
    "vocabulary": ("vocabulary", {"level": False, "level_source": False}),
}


async def log_change(
    conn: asyncpg.Connection,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: str | None = None,
    language_id: str | None = None,
    field: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    note: str | None = None,
) -> None:
    """Append one audit entry. `before`/`after` are small dicts of the fields
    that changed (before enables rollback). Best-effort: never let an audit
    write break the underlying content operation."""
    try:
        await conn.execute(
            """
            INSERT INTO content_change_log
                (entity_type, entity_id, language_id, actor_id, action, field,
                 before, after, note)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9)
            """,
            entity_type, entity_id, language_id, actor_id, action, field,
            json.dumps(before) if before is not None else None,
            json.dumps(after) if after is not None else None,
            (note or None),
        )
    except Exception:  # noqa: BLE001 - auditing must not break the write
        pass


def _loads(v):
    return json.loads(v) if isinstance(v, str) else v


def _row(r) -> dict:
    return {
        "id": str(r["id"]),
        "entity_type": r["entity_type"],
        "entity_id": str(r["entity_id"]),
        "action": r["action"],
        "field": r["field"],
        "before": _loads(r["before"]),
        "after": _loads(r["after"]),
        "note": r["note"],
        "actor_id": str(r["actor_id"]) if r["actor_id"] else None,
        "actor_email": r["actor_email"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "revertible": r["before"] is not None
        and r["entity_type"] in _REVERT_COLUMNS
        and r["action"] != "reverted",
    }


async def list_entity_changes(
    conn: asyncpg.Connection, entity_type: str, entity_id: str, limit: int = 50
) -> list[dict]:
    """The change timeline for one card (newest first) — the History view."""
    rows = await conn.fetch(
        """
        SELECT l.id, l.entity_type, l.entity_id, l.action, l.field,
               l.before, l.after, l.note, l.actor_id, l.created_at,
               u.email AS actor_email
        FROM content_change_log l
        LEFT JOIN auth.users u ON l.actor_id = u.id
        WHERE l.entity_type = $1 AND l.entity_id = $2
        ORDER BY l.seq DESC
        LIMIT $3
        """,
        entity_type, entity_id, limit,
    )
    return [_row(r) for r in rows]


async def list_recent_changes(
    conn: asyncpg.Connection, language_id: str | None = None, limit: int = 100
) -> list[dict]:
    """The per-language (or global) audit feed for the admin panel."""
    if language_id:
        rows = await conn.fetch(
            """
            SELECT l.id, l.entity_type, l.entity_id, l.action, l.field,
                   l.before, l.after, l.note, l.actor_id, l.created_at,
                   u.email AS actor_email
            FROM content_change_log l
            LEFT JOIN auth.users u ON l.actor_id = u.id
            WHERE l.language_id = $1
            ORDER BY l.seq DESC
            LIMIT $2
            """,
            language_id, limit,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT l.id, l.entity_type, l.entity_id, l.action, l.field,
                   l.before, l.after, l.note, l.actor_id, l.created_at,
                   u.email AS actor_email
            FROM content_change_log l
            LEFT JOIN auth.users u ON l.actor_id = u.id
            ORDER BY l.seq DESC
            LIMIT $1
            """,
            limit,
        )
    return [_row(r) for r in rows]


async def _apply_snapshot(
    conn: asyncpg.Connection, entity_type: str, entity_id: str, snapshot: dict
) -> bool:
    """Write a `before` snapshot back onto the live row. Only whitelisted
    columns for that entity type are touched."""
    spec = _REVERT_COLUMNS.get(entity_type)
    if not spec:
        return False
    table, cols = spec
    sets, vals, i = [], [], 2
    for col, is_json in cols.items():
        if col in snapshot:
            sets.append(f"{col} = ${i}{'::jsonb' if is_json else ''}")
            v = snapshot[col]
            vals.append(json.dumps(v) if (is_json and v is not None) else v)
            i += 1
    if not sets:
        return False
    result = await conn.execute(
        f"UPDATE {table} SET {', '.join(sets)} WHERE id = $1",  # noqa: S608 (whitelisted)
        entity_id, *vals,
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def revert_change(
    conn: asyncpg.Connection, log_id: str, actor_id: str
) -> str:
    """Roll a logged change back by re-applying its `before` snapshot, then log
    a 'reverted' entry. Returns 'ok' | 'not_found' | 'no_snapshot' |
    'not_revertible'."""
    r = await conn.fetchrow(
        "SELECT entity_type, entity_id, language_id, before "
        "FROM content_change_log WHERE id = $1",
        log_id,
    )
    if not r:
        return "not_found"
    before = _loads(r["before"])
    if before is None:
        return "no_snapshot"
    if not await _apply_snapshot(conn, r["entity_type"], str(r["entity_id"]), before):
        return "not_revertible"
    await log_change(
        conn, entity_type=r["entity_type"], entity_id=str(r["entity_id"]),
        actor_id=actor_id, action="reverted",
        language_id=str(r["language_id"]) if r["language_id"] else None,
        after=before, note=f"reverted change {log_id}",
    )
    return "ok"
