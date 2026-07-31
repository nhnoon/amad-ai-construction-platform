"""Login brute-force protection (Phase 2 — Security & Authentication
Hardening).

Two independent layers, deliberately separate:

- IP-based sliding-window throttle (this module) — checked first, before
  any database lookup, so a flood of requests can't even reach credential
  verification. In-memory and per-process, same trade-off as the existing
  AI rate limiter (app/ai/ratelimit.py, not reused here to keep this
  module fully independent of the AI package) — reset on restart, which is
  acceptable for a login throttle since the DB-persisted per-account
  lockout below is what actually has to survive restarts.
- Per-account lockout — DB-persisted directly on UserAccount
  (failed_login_attempts / locked_until, see migration 0014), applied in
  app/api/v1/auth.py::login. Not implemented here because it needs a
  database session and has to survive process restarts.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from ..config import settings


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._lock = threading.Lock()
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            dq = self._windows[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self._max:
                return False
            dq.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._windows.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._windows.clear()


login_ip_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)


def get_login_ip_rate_limiter() -> SlidingWindowRateLimiter:
    return login_ip_rate_limiter


def client_ip_from_request(request) -> str:
    """Best-effort client IP for rate-limit keying. Trusts
    X-Forwarded-For's first hop only when present (reverse-proxy
    deployments); falls back to the direct connection's address. Not a
    substitute for a properly configured trusted-proxy allowlist in a real
    production deployment (see the Phase 2 report's remaining risks)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
