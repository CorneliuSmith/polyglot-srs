"""Retention: prune the append-only AI-usage tables on a daily sweep.

`tutor_sessions` (one row per tutor conversation, the practice log) and
`tutor_usage` (one row per model call, the cost ledger) only ever grew:
every read of them is windowed, so nothing noticed, but a learner's rows
from a year ago ride in every backup and every full scan forever (brief
item 6, step 4). The windows the readers actually use set the floor —
the allowance reads the current month, the admin cost views clamp at a
year — and the retention sits above both:

- tutor_sessions older than 180 days
- tutor_usage older than 13 months

Both tables are probed before the DELETE (a privileged connection runs
inside one transaction, and a statement against a missing table poisons
everything after it), so a database that does not have them yet is a
no-op, not an error.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

TUTOR_SESSIONS_DAYS = 180
TUTOR_USAGE_MONTHS = 13

SWEEP_SECONDS = 24 * 60 * 60
# Let the pool and the schema check settle before the first pass.
FIRST_SWEEP_DELAY_SECONDS = 5 * 60

# (table, age predicate) — the interval is a literal, never a parameter,
# so the statement stays a plain DELETE the planner can use the
# created_at index for.
RULES = (
    ("tutor_sessions", f"created_at < now() - interval '{TUTOR_SESSIONS_DAYS} days'"),
    ("tutor_usage", f"created_at < now() - interval '{TUTOR_USAGE_MONTHS} months'"),
)


def _deleted(tag: str) -> int:
    """asyncpg's status tag: 'DELETE 42' → 42."""
    try:
        return int(tag.rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def sweep_retention(conn) -> dict[str, int]:
    """Apply every rule once. Returns {table: rows deleted}; a table that
    isn't there yet is reported as 0 and skipped."""
    out: dict[str, int] = {}
    for table, predicate in RULES:
        present = await conn.fetchval(f"SELECT to_regclass('public.{table}')")
        if present is None:
            out[table] = 0
            continue
        tag = await conn.execute(f"DELETE FROM {table} WHERE {predicate}")
        out[table] = _deleted(tag)
    return out


async def retention_loop() -> None:
    """Background task started from the app lifespan. Never raises."""
    from backend.repositories.pool import privileged_connection

    logger.info("retention loop started (every %ds)", SWEEP_SECONDS)
    await asyncio.sleep(FIRST_SWEEP_DELAY_SECONDS)
    while True:
        try:
            async with privileged_connection() as conn:
                counts = await sweep_retention(conn)
            if any(counts.values()):
                logger.info("retention: pruned %s", counts)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("retention sweep failed: %s", exc)
        await asyncio.sleep(SWEEP_SECONDS)
