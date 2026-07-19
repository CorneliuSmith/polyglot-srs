"""Opt-in email review reminders: the sweep and the mailer's safe default."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.services import email as email_mod
from backend.services import reminders


def _settings(**kw):
    return type("S", (), {"app_url": "https://app.example", **kw})()


class TestSweep:
    @pytest.mark.asyncio
    async def test_unconfigured_is_a_noop(self):
        # No RESEND_API_KEY → don't query, don't stamp, don't spam logs.
        conn = AsyncMock()
        with patch.object(reminders, "email_configured", return_value=False):
            assert await reminders.sweep_due_reminders(conn) == 0
        conn.fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sends_and_stamps_only_users_with_due_cards(self):
        conn = AsyncMock()
        conn.fetch.return_value = [
            {"id": "u1", "email": "a@b.c", "due": 3},
            {"id": "u2", "email": "d@e.f", "due": 0},   # nothing due → no mail
            {"id": "u3", "email": None, "due": 5},      # no address → skipped
        ]
        sent: list[tuple[str, str]] = []

        async def fake_send(to, subject, html):
            sent.append((to, subject))
            return True

        with patch.object(reminders, "email_configured", return_value=True), \
             patch.object(reminders, "send_email", side_effect=fake_send), \
             patch.object(reminders, "get_settings", return_value=_settings()):
            n = await reminders.sweep_due_reminders(conn)
        assert n == 1
        assert sent == [("a@b.c", "3 reviews ready on PolyglotSRS")]
        conn.execute.assert_awaited_once()  # last_reminder_at stamped once

    @pytest.mark.asyncio
    async def test_failed_send_is_not_stamped(self):
        # A mail hiccup must retry on the next tick, not eat the day's send.
        conn = AsyncMock()
        conn.fetch.return_value = [{"id": "u1", "email": "a@b.c", "due": 2}]
        with patch.object(reminders, "email_configured", return_value=True), \
             patch.object(reminders, "send_email", new=AsyncMock(return_value=False)), \
             patch.object(reminders, "get_settings", return_value=_settings()):
            assert await reminders.sweep_due_reminders(conn) == 0
        conn.execute.assert_not_awaited()


class TestEmail:
    @pytest.mark.asyncio
    async def test_no_key_is_log_only(self):
        with patch.object(email_mod, "get_settings",
                          return_value=_settings(resend_api_key="")):
            assert await email_mod.send_email("a@b.c", "s", "<p>x</p>") is False
