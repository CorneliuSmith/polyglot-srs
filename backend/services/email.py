"""Transactional email via Resend.

Log-only when RESEND_API_KEY is unset, so the reminder feature ships and is
testable before the mail account exists. api.resend.com is reachable from
the deploy (unlike *.supabase.co — see the egress quirk); short timeouts
keep a mail hiccup from ever wedging the caller.
"""
from __future__ import annotations

import logging

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)


def email_configured() -> bool:
    return bool(getattr(get_settings(), "resend_api_key", ""))


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send one email. Returns True only on an accepted delivery."""
    settings = get_settings()
    key = getattr(settings, "resend_api_key", "")
    if not key:
        logger.info("email (log-only, no RESEND_API_KEY): to=%s subject=%r", to, subject)
        return False
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {key}"},
                json={"from": settings.resend_from, "to": [to],
                      "subject": subject, "html": html},
            )
    except httpx.HTTPError as exc:
        logger.warning("email send failed (%s): %s", type(exc).__name__, exc)
        return False
    if resp.status_code >= 400:
        logger.warning("email rejected (%s): %s", resp.status_code, resp.text[:200])
        return False
    return True
