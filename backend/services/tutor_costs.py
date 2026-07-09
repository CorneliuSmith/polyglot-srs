"""Operator cost estimates for tutor usage (WP9b).

List prices in USD per million tokens. These feed the admin cost view only —
learners are never billed per token (tiers are flat-priced). Update the table
when Anthropic list pricing changes; unknown models fall back to the most
expensive known price so estimates err high, never low.
"""

from __future__ import annotations

# model id -> (input $/Mtok, output $/Mtok)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-fable-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}
_FALLBACK_PRICING = (5.0, 25.0)

# Prompt-cache token prices, relative to the model's input price. The tutor
# caches its charter block, so most turns are dominated by cheap cache reads.
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


def estimate_cost_usd(
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cache_write_tokens: int | None = 0,
    cache_read_tokens: int | None = 0,
) -> float:
    """Estimated USD cost of the given token counts at list pricing."""
    in_price, out_price = MODEL_PRICING.get(model or "", _FALLBACK_PRICING)
    cost = (
        (input_tokens or 0) * in_price
        + (cache_write_tokens or 0) * in_price * CACHE_WRITE_MULTIPLIER
        + (cache_read_tokens or 0) * in_price * CACHE_READ_MULTIPLIER
        + (output_tokens or 0) * out_price
    ) / 1_000_000
    return round(cost, 6)
