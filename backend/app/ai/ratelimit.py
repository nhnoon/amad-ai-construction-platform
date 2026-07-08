"""In-memory per-user rate limiter for AI endpoints.

Uses a sliding-window counter.  Redis is optional — this runs in-process
and is reset when the server restarts.  Sufficient for Phase 3A; a shared
Redis-backed rate limiter can be added in Phase 3B.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._lock = threading.Lock()
        self._windows: dict[int, deque[float]] = defaultdict(deque)

    def is_allowed(self, user_id: int) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            dq = self._windows[user_id]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self._max:
                return False
            dq.append(now)
            return True

    def reset(self, user_id: int) -> None:
        with self._lock:
            self._windows.pop(user_id, None)


_ai_rate_limiter = SlidingWindowRateLimiter(max_requests=20, window_seconds=60)


def get_ai_rate_limiter() -> SlidingWindowRateLimiter:
    return _ai_rate_limiter
