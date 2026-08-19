"""Speech pricing — the half of the AI bill that isn't tokens.

TTS is billed per character and STT per audio second, so neither can be
priced by the per-token table. These are Azure list rates (see
docs/plans/speak-speech.md), and the arithmetic is worth pinning: a
misplaced zero here is the difference between a rounding error and a
month's margin.
"""

import pytest

from backend.services.speech_costs import (
    FREE_TIER_STT_HOURS,
    FREE_TIER_TTS_CHARS,
    cost_usd,
    stt_cost_usd,
    tts_cost_usd,
)


class TestTts:
    def test_a_million_characters_is_list_price(self):
        assert tts_cost_usd(1_000_000) == pytest.approx(16.0)

    def test_a_typical_partner_reply(self):
        # ~1,000 characters, the plan doc's modelled session reply.
        assert tts_cost_usd(1_000) == pytest.approx(0.016)

    def test_nothing_synthesized_costs_nothing(self):
        assert tts_cost_usd(0) == 0
        assert tts_cost_usd(None) == 0

    def test_a_negative_count_cannot_credit_the_bill(self):
        assert tts_cost_usd(-5_000) == 0


class TestStt:
    def test_an_audio_hour_is_list_price(self):
        assert stt_cost_usd(3_600_000) == pytest.approx(0.18)

    def test_two_and_a_half_minutes_of_learner_audio(self):
        # The plan doc's modelled session: $0.008 at the batch tier.
        assert stt_cost_usd(150_000) == pytest.approx(0.0075, abs=0.0005)

    def test_nothing_sent_costs_nothing(self):
        assert stt_cost_usd(0) == 0
        assert stt_cost_usd(None) == 0


class TestRowPricing:
    def test_each_kind_is_priced_by_its_own_unit(self):
        # A TTS row's audio_ms is meaningless and must not be charged for,
        # and an STT row's chars likewise — they share one table.
        assert cost_usd("tts", 1_000_000, 999_999_999) == pytest.approx(16.0)
        assert cost_usd("stt", 999_999_999, 3_600_000) == pytest.approx(0.18)

    def test_an_unknown_kind_is_free_rather_than_guessed(self):
        assert cost_usd("mystery", 1_000_000, 3_600_000) == 0.0


def test_free_tier_is_stated_not_assumed():
    """Shown as context, never deducted: the grant resets monthly and the
    cost view's window does not."""
    assert FREE_TIER_TTS_CHARS == 500_000
    assert FREE_TIER_STT_HOURS == 5


class TestLedgerNeverBreaksPlayback:
    """Accounting is not a feature the learner asked for. A missing table
    or a failed write must cost the operator a log line, never cost the
    learner the audio they already heard."""

    @pytest.mark.asyncio
    async def test_a_missing_table_is_a_warning_not_an_exception(self, caplog):
        import asyncpg

        from backend.repositories.speech import log_speech_usage

        class Conn:
            async def execute(self, *a):
                raise asyncpg.exceptions.UndefinedTableError("no speech_usage")

        await log_speech_usage(Conn(), "u1", "es", "tts", "speak", chars=40)
        assert "not migrated" in caplog.text

    @pytest.mark.asyncio
    async def test_an_unavailable_pool_is_swallowed(self, caplog):
        from unittest.mock import patch

        from backend.repositories.speech import record_speech_event

        with patch("backend.repositories.speech.privileged_connection",
                   side_effect=RuntimeError("pool is gone")):
            # No raise: the caller has already sent the clip.
            await record_speech_event("u1", "es", "tts", "speak", chars=40)
        assert "not recorded" in caplog.text
