"""Operator cost estimates for speech — the half tutor_costs cannot price.

TTS is billed per character and STT per audio second, so neither fits the
per-token table next door. Prices are Azure list rates for the tier this
app actually uses (`services/tts.py` and `services/stt.py` both run on the
one Azure Speech resource), checked 15 August 2026 against
docs/plans/speak-speech.md. Estimates only, and deliberately gross: the F0
free tier absorbs the first 500,000 characters and 5 audio hours each
month, so a small month's real invoice is lower than what the admin view
shows. Better to overstate the bill than to be surprised by it.

Update the constants when Azure list pricing moves.
"""

from __future__ import annotations

# Azure neural TTS, standard voices. Neural HD ($22) is not used here.
TTS_USD_PER_MILLION_CHARS = 16.0

# Azure fast transcription (batch), the tier services/stt.py calls. Real-time
# streaming is $1.00/hr and is not used — see the plan doc for why.
STT_USD_PER_AUDIO_HOUR = 0.18

# The F0 tier's monthly grant, shown as context rather than subtracted: it
# resets monthly and the cost view's window is arbitrary, so quietly
# deducting it would understate a long window and confuse a short one.
FREE_TIER_TTS_CHARS = 500_000
FREE_TIER_STT_HOURS = 5


def tts_cost_usd(chars: int | None) -> float:
    """List cost of synthesizing *chars* characters of neural speech."""
    return round(max(0, chars or 0) * TTS_USD_PER_MILLION_CHARS / 1_000_000, 6)


def stt_cost_usd(audio_ms: int | None) -> float:
    """List cost of transcribing *audio_ms* milliseconds of learner audio."""
    hours = max(0, audio_ms or 0) / 3_600_000
    return round(hours * STT_USD_PER_AUDIO_HOUR, 6)


def cost_usd(kind: str, chars: int | None, audio_ms: int | None) -> float:
    """Price one aggregated speech row by its kind."""
    if kind == "tts":
        return tts_cost_usd(chars)
    if kind == "stt":
        return stt_cost_usd(audio_ms)
    return 0.0
