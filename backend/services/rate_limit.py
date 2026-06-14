"""Lightweight per-user rate limiting for the paid AI endpoints.

In-memory sliding window — protects against a buggy or hostile client running
up Claude API cost on the tutor and AI-review endpoints. Single-process only;
for a multi-worker deployment back this with Redis (same interface).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_calls: int, per_seconds: float):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record a hit for *key*; return False if it exceeds the window."""
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


# Tutor chat: interactive, allow a brisk pace but cap runaway loops.
tutor_chat_limiter = RateLimiter(max_calls=20, per_seconds=60)
# AI semantic review / generation: heavier calls, tighter cap.
ai_review_limiter = RateLimiter(max_calls=10, per_seconds=60)
