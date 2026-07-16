"""Per-user rate limiting for the paid AI endpoints.

Protects against a buggy or hostile client running up Claude API cost on the
tutor and AI-review endpoints. Two backends behind one async interface:

  - Redis (used when REDIS_URL is set): a sliding window over a sorted set,
    enforced atomically by a Lua script — correct across multiple workers.
  - In-memory (the default): a per-process sliding window. Fine for a single
    worker / local dev / tests; the Redis backend is what you deploy behind
    multiple workers.

REDIS_URL is read straight from the environment so this module never has to
construct Settings() (which keeps it usable in unit tests with no config).
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from collections import defaultdict, deque

# Atomic sliding-window limiter. KEYS[1]=bucket; ARGV: now, window, max, member.
# Drops entries older than the window, counts, and adds the new hit only if
# under the limit — all in one round trip so concurrent workers can't race.
_SLIDING_WINDOW_LUA = """
local cutoff = tonumber(ARGV[1]) - tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', cutoff)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[3]) then
  return 0
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('PEXPIRE', KEYS[1], math.ceil(tonumber(ARGV[2]) * 1000))
return 1
"""


class _MemoryBackend:
    def __init__(self, max_calls: int, per_seconds: float):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            dq = self._hits[key]
            cutoff = now - self.per_seconds
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= self.max_calls:
                return False
            dq.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class _RedisBackend:
    def __init__(self, url: str, name: str, max_calls: int, per_seconds: float):
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(url)
        self._script = self._redis.register_script(_SLIDING_WINDOW_LUA)
        self.name = name
        self.max_calls = max_calls
        self.per_seconds = per_seconds

    async def allow(self, key: str) -> bool:
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}"  # unique so equal-score hits don't collide
        result = await self._script(
            keys=[f"ratelimit:{self.name}:{key}"],
            args=[now, self.per_seconds, self.max_calls, member],
        )
        return bool(result)

    def reset(self) -> None:  # pragma: no cover - tests use the memory backend
        pass


class RateLimiter:
    """Async rate limiter that picks Redis or in-memory based on REDIS_URL."""

    def __init__(self, name: str, max_calls: int, per_seconds: float):
        self.name = name
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._backend: _MemoryBackend | _RedisBackend | None = None

    def _get_backend(self):
        if self._backend is None:
            url = os.environ.get("REDIS_URL", "").strip()
            if url:
                self._backend = _RedisBackend(
                    url, self.name, self.max_calls, self.per_seconds
                )
            else:
                self._backend = _MemoryBackend(self.max_calls, self.per_seconds)
        return self._backend

    async def allow(self, key: str) -> bool:
        """Record a hit for *key*; return False if it exceeds the window."""
        return await self._get_backend().allow(key)

    def reset(self) -> None:
        self._get_backend().reset()


# Tutor chat: interactive, allow a brisk pace but cap runaway loops.
tutor_chat_limiter = RateLimiter("tutor_chat", max_calls=20, per_seconds=60)
# TTS cache misses synthesize + upload — cap the generation rate per user
# (cache hits are not limited; they cost one SELECT).
tts_limiter = RateLimiter("tts", max_calls=30, per_seconds=60)
# AI semantic review: heavier calls, tighter cap.
ai_review_limiter = RateLimiter("ai_review", max_calls=10, per_seconds=60)
