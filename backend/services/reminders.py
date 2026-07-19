"""Opt-in daily email reminders for due reviews.

A learner turns reminders on in Account → Learner and picks an hour (stored
in UTC). An in-process sweep runs every 15 minutes: for each opted-in user
whose hour has arrived and who hasn't been reminded today, count their due
cards and — only if there's something to review — send one email. The
last_reminder_at stamp is written only on an accepted send, so a transient
mail failure retries on the next tick and a quiet day sends nothing.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from backend.config import get_settings
from backend.services.email import email_configured, send_email

logger = logging.getLogger(__name__)

SWEEP_SECONDS = 15 * 60


def _reminder_html(due: int, app_url: str) -> str:
    return (
        f"<p>You have <b>{due}</b> review{'s' if due != 1 else ''} ready on "
        f"PolyglotSRS.</p>"
        f'<p><a href="{app_url}/review">Start reviewing</a> — a few minutes '
        f"now is what moves words into long-term memory.</p>"
        f'<p style="color:#888;font-size:12px">You get this because email '
        f"reminders are on in Account &rarr; Learner. Turn them off there "
        f"any time.</p>"
    )


async def sweep_due_reminders(conn) -> int:
    """One pass. Returns how many reminder emails were accepted."""
    if not email_configured():
        return 0  # log-only mode: don't burn last_reminder stamps
    now = datetime.now(UTC)
    rows = await conn.fetch(
        """
        SELECT p.id, u.email,
               (SELECT count(*) FROM user_cards uc
                 WHERE uc.user_id = p.id
                   AND NOT uc.is_suspended
                   AND uc.next_review <= now()) AS due
        FROM user_profiles p
        JOIN auth.users u ON u.id = p.id
        WHERE p.reminder_opt_in
          AND p.reminder_hour_utc = $1
          AND (p.last_reminder_at IS NULL
               OR p.last_reminder_at < date_trunc('day', now()))
        """,
        now.hour,
    )
    app_url = getattr(get_settings(), "app_url", "").rstrip("/")
    sent = 0
    for r in rows:
        if not r["email"] or not r["due"]:
            continue
        ok = await send_email(
            r["email"],
            f"{r['due']} review{'s' if r['due'] != 1 else ''} ready on PolyglotSRS",
            _reminder_html(r["due"], app_url),
        )
        if ok:
            await conn.execute(
                "UPDATE user_profiles SET last_reminder_at = now() WHERE id = $1",
                r["id"],
            )
            sent += 1
    return sent


async def reminder_loop() -> None:
    """Background task started from the app lifespan. Never raises."""
    from backend.repositories.pool import privileged_connection

    logger.info("email reminder loop started (every %ds)", SWEEP_SECONDS)
    while True:
        try:
            async with privileged_connection() as conn:
                n = await sweep_due_reminders(conn)
            if n:
                logger.info("reminders: sent %d", n)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("reminder sweep failed: %s", exc)
        await asyncio.sleep(SWEEP_SECONDS)
