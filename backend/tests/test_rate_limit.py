"""Tests for the in-memory rate limiter."""
import time

from backend.services.rate_limit import RateLimiter


def test_allows_up_to_max_then_blocks():
    rl = RateLimiter(max_calls=2, per_seconds=60)
    assert rl.allow("u") is True
    assert rl.allow("u") is True
    assert rl.allow("u") is False  # third in window blocked


def test_per_key_independent():
    rl = RateLimiter(max_calls=1, per_seconds=60)
    assert rl.allow("a") is True
    assert rl.allow("b") is True   # different user unaffected
    assert rl.allow("a") is False


def test_window_slides():
    rl = RateLimiter(max_calls=1, per_seconds=0.05)
    assert rl.allow("u") is True
    assert rl.allow("u") is False
    time.sleep(0.06)
    assert rl.allow("u") is True   # window expired


def test_reset_clears_state():
    rl = RateLimiter(max_calls=1, per_seconds=60)
    rl.allow("u")
    rl.reset()
    assert rl.allow("u") is True
