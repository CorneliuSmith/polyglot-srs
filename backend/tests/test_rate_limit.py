"""Tests for the rate limiter — in-memory logic, backend selection, and (when
REDIS_TEST_URL is set) the real Redis sliding window."""
import asyncio
import os
import uuid

import pytest

from backend.services.rate_limit import (
    RateLimiter,
    _MemoryBackend,
    _RedisBackend,
)

REDIS_TEST_URL = os.environ.get("REDIS_TEST_URL")
requires_redis = pytest.mark.skipif(
    not REDIS_TEST_URL, reason="set REDIS_TEST_URL to a throwaway Redis to test that backend"
)


# ── in-memory backend (the default) ──────────────────────────────────────────

class TestMemoryBackend:
    @pytest.mark.asyncio
    async def test_allows_up_to_max_then_blocks(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        rl = RateLimiter("t", max_calls=2, per_seconds=60)
        assert await rl.allow("u") is True
        assert await rl.allow("u") is True
        assert await rl.allow("u") is False
        assert isinstance(rl._get_backend(), _MemoryBackend)

    @pytest.mark.asyncio
    async def test_per_key_independent(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        rl = RateLimiter("t", max_calls=1, per_seconds=60)
        assert await rl.allow("a") is True
        assert await rl.allow("b") is True
        assert await rl.allow("a") is False

    @pytest.mark.asyncio
    async def test_window_slides(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        rl = RateLimiter("t", max_calls=1, per_seconds=0.05)
        assert await rl.allow("u") is True
        assert await rl.allow("u") is False
        await asyncio.sleep(0.06)
        assert await rl.allow("u") is True

    def test_reset(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        rl = RateLimiter("t", max_calls=1, per_seconds=60)
        rl.reset()  # creates + clears the memory backend
        assert isinstance(rl._get_backend(), _MemoryBackend)


# ── backend selection ────────────────────────────────────────────────────────

class TestBackendSelection:
    def test_memory_without_redis_url(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert isinstance(RateLimiter("x", 1, 60)._get_backend(), _MemoryBackend)

    def test_redis_when_url_set(self, monkeypatch):
        pytest.importorskip("redis")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6390/0")
        # from_url is lazy — no connection needed to construct.
        assert isinstance(RateLimiter("x", 1, 60)._get_backend(), _RedisBackend)


# ── real Redis backend (skipped unless REDIS_TEST_URL is set) ─────────────────

@requires_redis
class TestRedisBackend:
    @pytest.mark.asyncio
    async def test_sliding_window_blocks_over_limit(self):
        backend = _RedisBackend(REDIS_TEST_URL, "test", max_calls=2, per_seconds=60)
        key = uuid.uuid4().hex
        assert await backend.allow(key) is True
        assert await backend.allow(key) is True
        assert await backend.allow(key) is False

    @pytest.mark.asyncio
    async def test_per_key_independent(self):
        backend = _RedisBackend(REDIS_TEST_URL, "test", max_calls=1, per_seconds=60)
        assert await backend.allow(uuid.uuid4().hex) is True
        assert await backend.allow(uuid.uuid4().hex) is True  # different key

    @pytest.mark.asyncio
    async def test_window_expires(self):
        backend = _RedisBackend(REDIS_TEST_URL, "test_exp", max_calls=1, per_seconds=0.2)
        key = uuid.uuid4().hex
        assert await backend.allow(key) is True
        assert await backend.allow(key) is False
        await asyncio.sleep(0.25)
        assert await backend.allow(key) is True  # old hit expired from the window
