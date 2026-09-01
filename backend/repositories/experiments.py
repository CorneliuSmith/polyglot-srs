"""Experiments and per-user variant assignment.

Reads and writes `experiments` / `experiment_assignments` (migration
20260930000000). Learner-facing reads run on an RLS connection — a user
sees their own assignment and nobody else's; the admin calls run privileged
after the router has checked the caller is an admin, the same split the
contributor repositories use.

Every read degrades. `list_experiments` is on the profile path, which is
fetched on EVERY page load, so a deployment where the migration has not
landed must serve a profile with no experiments rather than a 500 — the
is_visible outage taught that once already.
"""
from __future__ import annotations

import json

import asyncpg

from backend.repositories.pool import savepoint

_MISSING = (
    asyncpg.exceptions.UndefinedTableError,
    asyncpg.exceptions.UndefinedColumnError,
)


def _loads(value) -> object:
    """asyncpg hands JSONB back as str unless a codec is registered."""
    return json.loads(value) if isinstance(value, str) else value


def _row(row: asyncpg.Record) -> dict:
    d = dict(row)
    d["variants"] = _loads(d.get("variants")) or []
    d["rollout"] = _loads(d.get("rollout")) or {}
    return d


async def list_experiments(conn: asyncpg.Connection) -> list[dict]:
    """Every experiment definition, oldest first. [] when the table isn't
    there — the caller must treat that as "no experiments", not an error."""
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT key, name, description, variants, default_variant,
                       rollout, enabled, learner_choice, created_at, updated_at
                  FROM experiments
                 ORDER BY created_at, key
                """
            )
    except _MISSING:
        return []
    return [_row(r) for r in rows]


async def get_experiment(conn: asyncpg.Connection, key: str) -> dict | None:
    try:
        async with savepoint(conn):
            row = await conn.fetchrow(
                """
                SELECT key, name, description, variants, default_variant,
                       rollout, enabled, learner_choice, created_at, updated_at
                  FROM experiments WHERE key = $1
                """,
                key,
            )
    except _MISSING:
        return None
    return _row(row) if row else None


async def get_assignments(
    conn: asyncpg.Connection, user_id: str
) -> dict[str, dict]:
    """This user's explicit assignments, keyed by experiment.

    {key: {"variant": …, "source": …}} — the source travels with it because
    an admin reading "42 on flat" needs to know how many chose it.
    """
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT experiment_key, variant, source
                  FROM experiment_assignments
                 WHERE user_id = $1
                """,
                user_id,
            )
    except _MISSING:
        return {}
    return {
        r["experiment_key"]: {"variant": r["variant"], "source": r["source"]}
        for r in rows
    }


async def assign_variant(
    conn: asyncpg.Connection,
    user_id: str,
    key: str,
    variant: str,
    *,
    source: str = "admin",
    note: str | None = None,
) -> bool:
    """Pin one user to one variant. Returns False if the table isn't there.

    DO UPDATE, not DO NOTHING: re-assigning is the whole point of the admin
    control — someone who hated the new look gets moved back the moment they
    say so.
    """
    try:
        async with savepoint(conn):
            await conn.execute(
                """
                INSERT INTO experiment_assignments
                    (user_id, experiment_key, variant, source, note)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, experiment_key) DO UPDATE
                   SET variant = EXCLUDED.variant,
                       source = EXCLUDED.source,
                       note = EXCLUDED.note,
                       assigned_at = now()
                """,
                user_id, key, variant, source, note,
            )
    except _MISSING:
        return False
    return True


async def clear_assignment(
    conn: asyncpg.Connection, user_id: str, key: str
) -> bool:
    """Drop the pin, putting this user back under the rollout rule."""
    try:
        async with savepoint(conn):
            await conn.execute(
                "DELETE FROM experiment_assignments "
                " WHERE user_id = $1 AND experiment_key = $2",
                user_id, key,
            )
    except _MISSING:
        return False
    return True


async def update_experiment(
    conn: asyncpg.Connection,
    key: str,
    *,
    enabled: bool | None = None,
    default_variant: str | None = None,
    rollout: dict | None = None,
    learner_choice: bool | None = None,
) -> bool:
    """Patch one experiment. Only the fields passed are touched, so turning
    an experiment off can never also reset the percentage an admin spent a
    week arriving at."""
    sets, args = [], []
    for column, value in (
        ("enabled", enabled),
        ("default_variant", default_variant),
        ("learner_choice", learner_choice),
    ):
        if value is not None:
            args.append(value)
            sets.append(f"{column} = ${len(args)}")
    if rollout is not None:
        args.append(json.dumps(rollout))
        sets.append(f"rollout = ${len(args)}::jsonb")
    if not sets:
        return True
    args.append(key)
    try:
        async with savepoint(conn):
            result = await conn.execute(
                f"UPDATE experiments SET {', '.join(sets)}, updated_at = now() "
                f" WHERE key = ${len(args)}",
                *args,
            )
    except _MISSING:
        return False
    return result.endswith("1")


async def assignment_counts(conn: asyncpg.Connection, key: str) -> list[dict]:
    """How many people are pinned to each variant, and how they got there.

    Only counts EXPLICIT assignments — the bucketed majority is computed,
    not stored, so it cannot be counted from a table. The router reports
    the rollout percentages alongside these.
    """
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT variant, source, count(*) AS n
                  FROM experiment_assignments
                 WHERE experiment_key = $1
                 GROUP BY variant, source
                 ORDER BY variant, source
                """,
                key,
            )
    except _MISSING:
        return []
    return [
        {"variant": r["variant"], "source": r["source"], "count": r["n"]}
        for r in rows
    ]


async def assigned_users(
    conn: asyncpg.Connection, key: str, limit: int = 100
) -> list[dict]:
    """Who is pinned, newest first — the admin panel's roster.

    Joins auth.users for the email, because "3f2a-…-91c" is not a person an
    admin can go and ask about the new look.
    """
    try:
        async with savepoint(conn):
            rows = await conn.fetch(
                """
                SELECT a.user_id, a.variant, a.source, a.note, a.assigned_at,
                       u.email
                  FROM experiment_assignments a
                  JOIN auth.users u ON u.id = a.user_id
                 WHERE a.experiment_key = $1
                 ORDER BY a.assigned_at DESC
                 LIMIT $2
                """,
                key, limit,
            )
    except _MISSING:
        return []
    return [
        {
            "user_id": str(r["user_id"]),
            "email": r["email"],
            "variant": r["variant"],
            "source": r["source"],
            "note": r["note"],
            "assigned_at": r["assigned_at"],
        }
        for r in rows
    ]
