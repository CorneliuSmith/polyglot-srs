"""Weekly review digest — the week in one email, with that week's picks.

The daily reminder (services/reminders.py) answers "do I have work waiting?".
This answers a different question: "how did my week go, and what should I do
with the language beyond the app?" It is a separate opt-in for that reason —
a learner can want one, both, or neither.

Recommendations ride along rather than getting their own email. They are
generated weekly anyway, and a second message would be one more thing to
unsubscribe from; folded into the digest they are the reward for opening it.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from html import escape

from backend.config import get_settings
from backend.services.email import email_configured, send_email

logger = logging.getLogger(__name__)

SWEEP_SECONDS = 60 * 60  # hourly: the digest is day-granular, not hour-granular
DIGEST_HOUR_UTC = 16

# Inline styles throughout, and a table for the shell: every major mail client
# strips <style> blocks, and several still do not honour flex/grid. This is
# the boring layout that renders the same in Gmail, Outlook and Apple Mail.
_WRAPPER = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
    "Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;padding:8px;"
    "color:#1f2937;line-height:1.5"
)
_CARD = (
    "background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;"
    "padding:16px;margin:0 0 12px"
)
_MUTED = "color:#6b7280;font-size:13px;margin:0"


def _stat_cell(value: str, label: str) -> str:
    return (
        f'<td align="center" style="padding:8px 4px">'
        f'<div style="font-size:22px;font-weight:700;color:#111827">{escape(value)}</div>'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.04em;'
        f'color:#9ca3af">{escape(label)}</div>'
        f"</td>"
    )


def _reco_block(items: list[dict]) -> str:
    """The week's picks. Each one leads with WHY it fits — that line is the
    difference between a recommendation and a list."""
    if not items:
        return ""
    rows = []
    for item in items[:4]:
        title = escape(str(item.get("title") or ""))
        if not title:
            continue
        meta = " · ".join(
            escape(str(item[k]))
            for k in ("type", "creator", "year")
            if item.get(k)
        )
        blurb = escape(str(item.get("blurb") or ""))
        why = escape(str(item.get("why") or ""))
        rows.append(
            f'<div style="padding:12px 0;border-top:1px solid #f3f4f6">'
            f'<div style="font-weight:600;font-size:15px">{title}</div>'
            + (f'<div style="{_MUTED}">{meta}</div>' if meta else "")
            + (f'<div style="margin:6px 0 0;font-size:14px">{blurb}</div>' if blurb else "")
            + (
                f'<div style="margin:6px 0 0;font-size:13px;color:#3f6212;'
                f'background:#f7fee7;border-radius:8px;padding:8px">{why}</div>'
                if why
                else ""
            )
            + "</div>"
        )
    if not rows:
        return ""
    return (
        f'<div style="{_CARD}">'
        f'<div style="font-size:16px;font-weight:700;margin:0 0 4px">'
        f"Something to read, watch or listen to</div>"
        f'<p style="{_MUTED}">Picked for your level and what you told us you like.</p>'
        + "".join(rows)
        + "</div>"
    )


def digest_html(
    *,
    # There is no name on user_profiles today, so this is always "" from the
    # sweep — kept as a parameter because the greeting is the one place a name
    # would land, and threading it later should not mean reshaping the email.
    display_name: str = "",
    reviews: int,
    accuracy: int | None,
    learned: int,
    due: int,
    reco_items: list[dict],
    app_url: str,
) -> str:
    """The whole email. Pure function of its inputs so it can be rendered and
    eyeballed in a test without a mail account or a database."""
    greeting = f"Hi {escape(display_name)}," if display_name else "Hi,"

    if reviews == 0:
        # An empty week must not read as a scolding — that is exactly the
        # email people unsubscribe from.
        opener = (
            "You didn't get to a review this week — that's completely fine. "
            "Picking back up is genuinely easy: even five minutes puts you "
            "back in rhythm."
        )
    else:
        opener = (
            f"You did <b>{reviews}</b> review{'s' if reviews != 1 else ''} this "
            f"week. Here's how the week looked."
        )

    stats = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        ' style="margin:12px 0 4px"><tr>'
        + _stat_cell(str(reviews), "reviews")
        + (_stat_cell(f"{accuracy}%", "accuracy") if accuracy is not None else "")
        + _stat_cell(str(learned), "words learned")
        + "</tr></table>"
    )

    cta_label = (
        f"Review {due} card{'s' if due != 1 else ''}" if due else "Open PolyglotSRS"
    )
    cta = (
        f'<div style="text-align:center;margin:4px 0 0">'
        f'<a href="{escape(app_url)}/review" '
        f'style="display:inline-block;background:#166534;color:#ffffff;'
        f'text-decoration:none;font-weight:600;font-size:15px;'
        f'padding:12px 22px;border-radius:10px">{escape(cta_label)}</a></div>'
    )

    return (
        f'<div style="{_WRAPPER}">'
        f'<div style="{_CARD}">'
        f'<p style="margin:0 0 8px;font-size:16px">{greeting}</p>'
        f'<p style="margin:0;font-size:15px">{opener}</p>'
        f"{stats}{cta}"
        f"</div>"
        f"{_reco_block(reco_items)}"
        f'<p style="{_MUTED};text-align:center;margin-top:16px">'
        f"You're getting this because the weekly review email is on in "
        f"Account &rarr; Learner. "
        f'<a href="{escape(app_url)}/account" style="color:#6b7280">'
        f"Change or turn it off</a>.</p>"
        f"</div>"
    )


async def sweep_weekly_digests(conn) -> int:
    """One pass. Returns how many digests were accepted for delivery.

    Guarded the same way the daily reminder is: the last-sent stamp is
    written only on an accepted send, so a mail outage retries next hour
    instead of silently skipping someone's week.
    """
    if not email_configured():
        return 0  # log-only mode: don't burn last_weekly_digest stamps
    now = datetime.now(UTC)
    if now.hour != DIGEST_HOUR_UTC:
        return 0
    rows = await conn.fetch(
        """
        SELECT p.id, u.email,
               (SELECT count(*) FROM review_log rl
                 WHERE rl.user_id = p.id
                   AND rl.created_at >= now() - interval '7 days')   AS reviews,
               (SELECT count(*) FROM review_log rl
                 WHERE rl.user_id = p.id
                   AND rl.created_at >= now() - interval '7 days'
                   AND rl.answer_result IN ('correct', 'correct_sloppy'))
                                                                     AS correct,
               (SELECT count(*) FROM user_cards uc
                 WHERE uc.user_id = p.id AND uc.repetitions > 0)     AS learned,
               (SELECT count(*) FROM user_cards uc
                 WHERE uc.user_id = p.id
                   AND NOT uc.is_suspended
                   AND uc.next_review <= now())                      AS due,
               (SELECT r.items FROM media_recommendations r
                 WHERE r.user_id = p.id
                 ORDER BY r.created_at DESC LIMIT 1)                 AS reco_items
        FROM user_profiles p
        JOIN auth.users u ON u.id = p.id
        WHERE p.weekly_digest_opt_in
          AND EXTRACT(DOW FROM now()) = p.weekly_digest_dow
          AND (p.last_weekly_digest_at IS NULL
               OR p.last_weekly_digest_at < now() - interval '6 days')
        """,
    )
    app_url = getattr(get_settings(), "app_url", "").rstrip("/")
    sent = 0
    for r in rows:
        if not r["email"]:
            continue
        reviews = int(r["reviews"] or 0)
        accuracy = (
            round(100 * int(r["correct"] or 0) / reviews) if reviews else None
        )
        items = r["reco_items"] or []
        if isinstance(items, str):
            import json  # noqa: PLC0415 — only needed on the JSONB-as-text path

            try:
                items = json.loads(items)
            except ValueError:
                items = []
        ok = await send_email(
            r["email"],
            "Your week in review",
            digest_html(
                display_name="",
                reviews=reviews,
                accuracy=accuracy,
                learned=int(r["learned"] or 0),
                due=int(r["due"] or 0),
                reco_items=list(items),
                app_url=app_url,
            ),
        )
        if ok:
            await conn.execute(
                "UPDATE user_profiles SET last_weekly_digest_at = now() WHERE id = $1",
                r["id"],
            )
            sent += 1
    return sent


async def digest_loop() -> None:
    """Background task started from the app lifespan. Never raises."""
    from backend.repositories.pool import privileged_connection

    logger.info("weekly digest loop started (every %ds)", SWEEP_SECONDS)
    while True:
        try:
            async with privileged_connection() as conn:
                n = await sweep_weekly_digests(conn)
            if n:
                logger.info("weekly digests: sent %d", n)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("weekly digest sweep failed: %s", exc)
        await asyncio.sleep(SWEEP_SECONDS)
