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
# The admin operations digest runs early, before the learner mail: it is the
# one that can need a reply the same day (someone is waiting for access).
ADMIN_DIGEST_HOUR_UTC = 7
# The recs engine runs the hour BEFORE the digest, so the digest always
# carries this week's fresh picks rather than last week's.
RECS_HOUR_UTC = 15
# Batches drafted per pass — bounds one sweep's model spend; stragglers are
# picked up on the following days' passes.
RECS_BATCH_CAP = 25

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


def picks_html(*, language_name: str, items: list[dict], app_url: str) -> str:
    """The weekly picks email. Same block the digest embeds — every pick
    leads with WHY it fits — plus its own shell for learners who don't take
    the digest. Pure function of its inputs, like digest_html."""
    return (
        f'<div style="{_WRAPPER}">'
        f'<div style="{_CARD}">'
        f'<p style="margin:0 0 4px;font-size:16px;font-weight:700">'
        f"Your weekly {escape(language_name)} picks</p>"
        f'<p style="{_MUTED}">Fresh this week, matched to your current level '
        f"and the interests in your profile.</p>"
        f"</div>"
        f"{_reco_block(items)}"
        f'<div style="text-align:center;margin:4px 0 12px">'
        f'<a href="{escape(app_url)}/recommendations" '
        f'style="display:inline-block;background:#166534;color:#ffffff;'
        f'text-decoration:none;font-weight:600;font-size:15px;'
        f'padding:12px 22px;border-radius:10px">See all your picks</a></div>'
        f'<p style="{_MUTED};text-align:center">'
        f"You're getting this because Recommendations are on in your "
        f'settings. <a href="{escape(app_url)}/recommendations" '
        f'style="color:#6b7280">Adjust your profile or turn them off</a>.</p>'
        f"</div>"
    )


def admin_digest_html(
    *,
    trial_pending: int,
    trial_samples: list[dict],
    languages: list[dict],
    app_feedback: int,
    app_url: str,
) -> str:
    """The admin's operations digest — what is waiting, and where.

    Same shell as the learner emails; different question. Every section is
    omitted when its count is zero, and the sweep does not send at all when
    everything is zero: an email that usually says "nothing to do" is the
    one people filter away, and then the one that mattered goes with it.

    Pure function of its inputs, so the whole email can be rendered and read
    in a test without a mail account or a database.
    """
    blocks: list[str] = []

    if trial_pending:
        # First, and named individually: these are people waiting on a reply
        # from a human, which no other queue here is.
        who = "".join(
            f'<div style="padding:8px 0;border-top:1px solid #f3f4f6;font-size:14px">'
            f'{escape(str(s.get("name") or s.get("email") or ""))}'
            + (
                f'<span style="{_MUTED};display:block">'
                f'{escape(str(s.get("email") or ""))}</span>'
                if s.get("name") and s.get("email")
                else ""
            )
            + (
                f'<div style="margin:4px 0 0;font-size:13px;color:#3f6212;'
                f'background:#f7fee7;border-radius:8px;padding:8px">'
                f'{escape(str(s["note"]))}</div>'
                if s.get("note")
                else ""
            )
            + "</div>"
            for s in trial_samples[:5]
        )
        more = (
            f'<p style="{_MUTED};margin-top:8px">'
            f"and {trial_pending - len(trial_samples[:5])} more</p>"
            if trial_pending > len(trial_samples[:5])
            else ""
        )
        blocks.append(
            f'<div style="{_CARD}">'
            f'<div style="font-size:16px;font-weight:700;margin:0 0 4px">'
            f"{trial_pending} "
            f"{'person is' if trial_pending == 1 else 'people are'} "
            f"waiting for access</div>"
            f'<p style="{_MUTED}">Approve or reject them in Workspace &rarr; '
            f"Admin &rarr; People.</p>"
            f"{who}{more}"
            f'<div style="margin:12px 0 0">'
            f'<a href="{escape(app_url)}/contribute?tab=admin&amp;section=people" '
            f'style="display:inline-block;background:#166534;color:#ffffff;'
            f"text-decoration:none;font-weight:600;font-size:15px;"
            f'padding:12px 22px;border-radius:10px">Open trial requests</a></div>'
            f"</div>"
        )

    busy = [lang for lang in languages if lang.get("total")]
    if busy:
        rows = "".join(
            f'<div style="padding:8px 0;border-top:1px solid #f3f4f6;font-size:14px">'
            f'{escape(str(lang.get("name") or ""))}'
            f'<span style="float:right;font-weight:700">{int(lang["total"])}</span>'
            f"</div>"
            for lang in busy[:12]
        )
        total = sum(int(lang["total"]) for lang in busy)
        blocks.append(
            f'<div style="{_CARD}">'
            f'<div style="font-size:16px;font-weight:700;margin:0 0 4px">'
            f"{total} waiting for review</div>"
            f'<p style="{_MUTED}">Across '
            f"{len(busy)} language{'s' if len(busy) != 1 else ''}.</p>"
            f"{rows}"
            f'<div style="margin:12px 0 0">'
            f'<a href="{escape(app_url)}/contribute?tab=review" '
            f'style="color:#166534;font-weight:600;font-size:14px;'
            f'text-decoration:none">Open the review queues &rarr;</a></div>'
            f"</div>"
        )

    if app_feedback:
        blocks.append(
            f'<div style="{_CARD}">'
            f'<div style="font-size:16px;font-weight:700;margin:0 0 4px">'
            f"{app_feedback} report{'s' if app_feedback != 1 else ''} "
            f"about the app itself</div>"
            f'<p style="{_MUTED}">These belong to no course, so they appear in '
            f"no language's queue.</p>"
            f'<div style="margin:12px 0 0">'
            f'<a href="{escape(app_url)}/contribute?tab=review&amp;queue=feedback-queue" '
            f'style="color:#166534;font-weight:600;font-size:14px;'
            f'text-decoration:none">Open the feedback queue &rarr;</a></div>'
            f"</div>"
        )

    return (
        f'<div style="{_WRAPPER}">'
        f'<div style="{_CARD}">'
        f'<p style="margin:0 0 4px;font-size:16px;font-weight:700">'
        f"What's waiting for you</p>"
        f'<p style="{_MUTED}">Sent only when something is actually waiting — '
        f"no news means nothing is.</p>"
        f"</div>"
        + "".join(blocks)
        + f'<p style="{_MUTED};text-align:center;margin-top:16px">'
        f"You're getting this because your account holds the admin role.</p>"
        f"</div>"
    )


async def sweep_admin_digests(conn) -> int:
    """Mail every admin ACCOUNT what is waiting for them. Returns sends.

    Owner: "I want an email sent to the admin accounts to like the language
    recommendations." Recipients come from the roles table, not from
    ADMIN_NOTIFY_EMAIL — a config value that was never documented and never
    set, which is how a queue of people asking for access sat unread.

    Silent by design when every queue is empty: a digest that usually says
    "nothing to do" trains its way into a filter, taking the one that
    mattered with it.
    """
    if not email_configured():
        return 0  # log-only mode: don't burn the send stamps
    now = datetime.now(UTC)
    if now.hour != ADMIN_DIGEST_HOUR_UTC:
        return 0
    # One worker per database does the pass, like the recs sweep — two
    # uvicorn workers would otherwise each mail every admin.
    if not await conn.fetchval(
        "SELECT pg_try_advisory_xact_lock(hashtext('admin_digest_sweep'))"
    ):
        return 0

    from backend.repositories.admins import admins_due_for_digest, mark_digest_sent

    # A day minus an hour: the hour gate already makes this daily, and an
    # exact 24h would race its own scheduling drift and skip a day.
    recipients = await admins_due_for_digest(conn, 23)
    if not recipients:
        return 0

    from backend.repositories.contributor import review_inbox_by_language
    from backend.repositories.feedback import open_feedback_by_language
    from backend.repositories.trials import (
        count_pending_trial_requests,
        list_trial_requests,
    )

    trial_pending = await count_pending_trial_requests(conn)
    trial_samples = [
        r for r in (await list_trial_requests(conn) if trial_pending else [])
        if r["status"] == "pending"
    ]
    languages = await review_inbox_by_language(conn)
    app_feedback = sum(
        f["count"] for f in await open_feedback_by_language(conn)
        if f["language_id"] is None
    )
    review_total = sum(int(lang.get("total") or 0) for lang in languages)
    if not (trial_pending or review_total or app_feedback):
        return 0

    app_url = getattr(get_settings(), "app_url", "").rstrip("/")
    html = admin_digest_html(
        trial_pending=trial_pending,
        trial_samples=trial_samples,
        languages=languages,
        app_feedback=app_feedback,
        app_url=app_url,
    )
    waiting = trial_pending + review_total + app_feedback
    subject = f"PolyglotSRS: {waiting} waiting for you"
    sent = 0
    for admin in recipients:
        if await send_email(admin["email"], subject, html):
            await mark_digest_sent(conn, admin["id"])
            sent += 1
    return sent


async def sweep_weekly_recommendations(conn) -> int:
    """Draft the week's picks server-side and email them. Returns batches made.

    Before this, a batch was drafted only when the learner OPENED the
    recommendations page — the client fired the refresh call. Anyone who
    didn't visit got nothing new, and the weekly digest then had nothing
    fresh to carry: "I have never gotten an email on the recs." The engine
    now runs here: for every learner with the feature on whose latest batch
    for their active language is a week old (or who has none), draft a new
    one calibrated to their CURRENT level and progress, spend one unit of
    their monthly AI allowance, and send the picks — each with its reason —
    by email. Skips (no entitlement, exhausted allowance, no provider)
    leave the learner exactly as they were; nothing is marked used.
    """
    from backend.repositories.contributor import get_roles, is_admin
    from backend.repositories.recommendations import (
        get_reco_profile,
        insert_recommendation,
        rated_titles,
        recommended_titles,
    )
    from backend.repositories.tutor import get_study_stats, log_tutor_usage
    from backend.services.allowance import get_allowance
    from backend.services.models import resolve_model
    from backend.services.recommend import generate_recommendations

    now = datetime.now(UTC)
    if now.hour != RECS_HOUR_UTC:
        return 0
    # One worker per database does the pass — every uvicorn worker runs this
    # loop, and two of them drafting the same learner's week would double
    # the spend and the email.
    if not await conn.fetchval(
        "SELECT pg_try_advisory_xact_lock(hashtext('weekly_recs_sweep'))"
    ):
        return 0
    rows = await conn.fetch(
        """
        SELECT p.user_id, up.active_language_id AS language_id, u.email,
               l.code AS language_code, l.name AS language_name, l.tutor_model
        FROM media_reco_profile p
        JOIN user_profiles up ON up.id = p.user_id
        JOIN auth.users u ON u.id = p.user_id
        JOIN languages l ON l.id = up.active_language_id
        WHERE p.enabled
          AND up.active_language_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM media_recommendations r
             WHERE r.user_id = p.user_id
               AND r.language_id = up.active_language_id
               AND r.created_at > now() - interval '7 days')
        ORDER BY p.user_id
        LIMIT $1
        """,
        RECS_BATCH_CAP,
    )
    app_url = getattr(get_settings(), "app_url", "").rstrip("/")
    made = 0
    for r in rows:
        user_id = str(r["user_id"])
        language_id = str(r["language_id"])
        try:
            # Admins draft regardless of plan — same bypass the router's
            # refresh has. Without it the sweep silently skipped the owner
            # every week ("the recommendations never come through"): admin
            # accounts aren't Plus-entitled, and `continue` left no trace.
            roles_admin = is_admin(await get_roles(conn, user_id))
            allowance = await get_allowance(user_id, language_id)
            if not allowance["entitled"] and not roles_admin:
                continue
            if (not roles_admin and not allowance["unlimited"]
                    and allowance["remaining"] <= 0):
                continue
            profile = await get_reco_profile(conn, user_id)
            stats = await get_study_stats(conn, user_id, language_id)
            level = stats.get("highest_level_reached")
            model = resolve_model(
                "recommend", r["language_code"], override=r["tutor_model"]
            )
            items = await generate_recommendations(
                language_name=r["language_name"],
                language_code=r["language_code"],
                level=level,
                learned_count=int(stats.get("learned_cards") or 0),
                about=profile["about"],
                genres=profile["genres"],
                media_types=profile["media_types"],
                model=model,
                exclude_titles=await recommended_titles(
                    conn, user_id, language_id),
                reactions=await rated_titles(conn, user_id, language_id),
            )
            if not items:
                continue
            await insert_recommendation(conn, user_id, language_id, items, level)
            await log_tutor_usage(conn, user_id, language_id, model, kind="recs")
            made += 1
            if email_configured() and r["email"]:
                await send_email(
                    r["email"],
                    f"Your weekly {r['language_name']} picks",
                    picks_html(
                        language_name=r["language_name"],
                        items=items,
                        app_url=app_url,
                    ),
                )
        except Exception as exc:  # noqa: BLE001 — one learner, not the sweep
            logger.warning(
                "weekly recs: drafting for %s failed: %s", user_id, exc
            )
    return made


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
        # Recs first (their hour precedes the digest hour), each pass in its
        # own guarded block so one sweep failing never costs the other.
        try:
            async with privileged_connection() as conn:
                n = await sweep_weekly_recommendations(conn)
            if n:
                logger.info("weekly recommendations: drafted %d", n)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("weekly recommendations sweep failed: %s", exc)
        try:
            async with privileged_connection() as conn:
                n = await sweep_weekly_digests(conn)
            if n:
                logger.info("weekly digests: sent %d", n)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("weekly digest sweep failed: %s", exc)
        # The admin operations digest — its own guarded block, so a learner
        # sweep failing never costs the admin their report and vice versa.
        try:
            async with privileged_connection() as conn:
                n = await sweep_admin_digests(conn)
            if n:
                logger.info("admin digests: sent %d", n)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("admin digest sweep failed: %s", exc)
        await asyncio.sleep(SWEEP_SECONDS)
