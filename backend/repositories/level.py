"""The one rule for the level content is pitched at.

The third of the family: repositories/profile.py decides the help
language, this decides the level, and both exist for the same reason —
more than one derivation claimed to be the truth, and the one the user
could set was not the one the features read. "Your level" in Settings
re-seated deck subscriptions and stored nothing; every AI prompt read a
level derived from card history, fallback A1. A B2 speaker with a young
account got beginner content no matter what they set, and studying more
made the mispitch stickier (the placement priming only applies while
card evidence is thin).

The rule (owner, verbatim intent): **the chosen level anchors the
session, and an explicit ask for harder content is honored ABOVE it —
given, not argued with.**

    chosen_level (Settings / onboarding / placement retake)
        → a FLOOR. Evidence may pitch above it, never silently below it.
    evidence level (cards + placement priming, from assessment.py)
        → may raise the pitch when it outgrows the choice.
    an explicit harder request (Reader's "stretch", a "substantive" ask)
        → applied ON TOP of the resolved level, uncapped. That is the
          caller's job (services/reader.py shift_level); this module's
          job is that the base they shift from is the one the user set.

Missing-migration rule (CLAUDE.md): learner_levels may not exist yet.
Presence is probed with to_regclass — a catalog lookup that NEVER raises
— and cached once seen. Catching UndefinedTableError instead is NOT a
guard here and shipped a real outage: every read path runs inside
rls_connection's transaction (SET LOCAL needs one), and a failed
statement aborts that transaction in Postgres regardless of any Python
except — so the "degraded" tutor/reader/speak request died on its NEXT
query with a 500. cards.py documents this exact trap; this module
learned it the hard way within hours of deploying without it.
"""
from __future__ import annotations

import asyncpg

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Only presence is cached: a migration applied while the app runs is
# picked up on the next probe, no restart (same policy as cards.py).
_TABLE_SEEN = False


async def _table_present(conn: asyncpg.Connection) -> bool:
    global _TABLE_SEEN
    if _TABLE_SEEN:
        return True
    present = bool(await conn.fetchval(
        "SELECT to_regclass('learner_levels') IS NOT NULL"
    ))
    if present:
        _TABLE_SEEN = True
    return present


def resolve(chosen: str | None, evidence: str | None) -> str:
    """max(chosen, evidence) on the CEFR scale — the floor rule."""
    ranked = [
        lvl for lvl in (chosen, evidence) if lvl in CEFR_ORDER
    ]
    if not ranked:
        return evidence or chosen or "A1"
    return max(ranked, key=CEFR_ORDER.index)


def shift_level(level: str, steps: int) -> str:
    """*level* moved *steps* up or down the scale, clamped to its ends.

    The Reader's dials use this: easier = −1, stretch = +1. Positive
    shifts are the owner's "give it to them" — an explicit ask for harder
    content is applied on top of the resolved level, uncapped by evidence.
    """
    if level not in CEFR_ORDER:
        return level
    idx = max(0, min(len(CEFR_ORDER) - 1, CEFR_ORDER.index(level) + steps))
    return CEFR_ORDER[idx]


async def chosen_level(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> str | None:
    """The level the user explicitly set for this course, or None.

    None means "never chosen" — evidence alone decides, which is exactly
    the pre-migration behavior, so an unapplied migration changes nothing.
    """
    if not await _table_present(conn):
        return None
    return await conn.fetchval(
        """SELECT chosen_level FROM learner_levels
            WHERE user_id = $1 AND language_id = $2""",
        user_id, language_id,
    )


async def set_chosen_level(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    level: str,
    source: str = "settings",
) -> bool:
    """Record the user's explicit level. Returns False (rather than
    raising or aborting the surrounding transaction) when the migration
    hasn't landed — the caller's deck re-seating must still happen, so a
    missing table costs persistence, not the whole action."""
    if not await _table_present(conn):
        return False
    await conn.execute(
        """INSERT INTO learner_levels
               (user_id, language_id, chosen_level, source, updated_at)
           VALUES ($1, $2, $3, $4, now())
           ON CONFLICT (user_id, language_id) DO UPDATE SET
               chosen_level = EXCLUDED.chosen_level,
               source = EXCLUDED.source,
               updated_at = now()""",
        user_id, language_id, level, source,
    )
    return True
