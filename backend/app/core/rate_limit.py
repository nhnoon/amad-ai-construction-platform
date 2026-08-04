"""RC1 Phase 1 Sprint 3 — API Protection & HTTP Security, Part C: Global
API Rate Limiting.

Independent of, and in addition to, the existing per-IP login throttle +
per-account DB lockout (Phase 2 — Security & Authentication Hardening,
app/core/login_security.py) — this sprint must not modify that behavior,
so RateLimitMiddleware below uses its own separate counters/keys
entirely, never touching login_security.py's state.

Storage is abstracted behind RateLimitStore so a future Redis-backed
implementation (e.g. INCR+EXPIRE or a sliding-window Lua script) can
satisfy the same interface without RateLimitMiddleware — or any other
caller — changing at all. InMemoryRateLimitStore is the only
implementation today, same in-process/resets-on-restart trade-off already
accepted elsewhere in this codebase (app/core/login_security.py's IP
throttle, app/ai/ratelimit.py's AI Copilot limiter).
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from math import ceil

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import settings
from .login_security import client_ip_from_request
from .security import decode_access_token

# Reachable without being subject to rate limiting — an uptime monitor
# hammering the health check every few seconds must never see a 429.
_EXEMPT_PATHS = frozenset({"/api/healthz"})

_LOGIN_PATH = f"{settings.API_V1_PREFIX}/auth/login"
_REFRESH_PATH = f"{settings.API_V1_PREFIX}/auth/refresh"


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    # Seconds until the caller may retry (when rejected) or until the
    # window fully resets (when allowed) — used for both Retry-After and
    # the informational X-RateLimit-Reset header.
    reset_seconds: int


class RateLimitStore(ABC):
    @abstractmethod
    def check(self, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        """Records one request against `key` and reports whether it's
        allowed under a max_requests-per-window_seconds sliding window."""
        ...


class InMemoryRateLimitStore(RateLimitStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._windows[key]
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= max_requests:
                reset_seconds = max(1, ceil(dq[0] + window_seconds - now))
                return RateLimitResult(allowed=False, limit=max_requests, remaining=0, reset_seconds=reset_seconds)

            dq.append(now)
            remaining = max_requests - len(dq)
            reset_seconds = max(0, ceil(dq[0] + window_seconds - now))
            return RateLimitResult(allowed=True, limit=max_requests, remaining=remaining, reset_seconds=reset_seconds)

    def reset_all(self) -> None:
        with self._lock:
            self._windows.clear()


_default_store = InMemoryRateLimitStore()


def get_default_rate_limit_store() -> InMemoryRateLimitStore:
    """The shared, process-wide store RateLimitMiddleware uses by
    default. Exposed so tests can reset_all() between tests — same
    pattern as app/core/login_security.py::login_ip_rate_limiter."""
    return _default_store


def _limits_for_scope(scope: str) -> tuple[int, int]:
    return {
        "login": (settings.RATE_LIMIT_LOGIN_MAX_REQUESTS, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS),
        "refresh": (settings.RATE_LIMIT_REFRESH_MAX_REQUESTS, settings.RATE_LIMIT_REFRESH_WINDOW_SECONDS),
        "upload": (settings.RATE_LIMIT_UPLOAD_MAX_REQUESTS, settings.RATE_LIMIT_UPLOAD_WINDOW_SECONDS),
        "authenticated": (settings.RATE_LIMIT_AUTHENTICATED_MAX_REQUESTS, settings.RATE_LIMIT_AUTHENTICATED_WINDOW_SECONDS),
        "anonymous": (settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS, settings.RATE_LIMIT_ANONYMOUS_WINDOW_SECONDS),
    }[scope]


def classify_request(request: Request) -> tuple[str, str]:
    """Returns (scope, key). Scope is one of "login"/"refresh"/"upload"/
    "authenticated"/"anonymous", picked by priority in that order —
    mutually exclusive, never layered, so exactly one limit applies per
    request. Identity is read the same lightweight way
    app/core/password_gate_middleware.py already does (decode the bearer
    JWT directly, no DB lookup) — a coarse rate-limit bucket key doesn't
    need to verify the user still exists/is active, just to be stable per
    caller."""
    path = request.url.path
    method = request.method
    ip = client_ip_from_request(request)

    if method == "POST" and path == _LOGIN_PATH:
        return "login", f"ip:{ip}"
    if method == "POST" and path == _REFRESH_PATH:
        return "refresh", f"ip:{ip}"

    email: str | None = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        payload = decode_access_token(auth_header[7:].strip())
        if payload:
            email = payload.get("sub")

    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/form-data"):
        return "upload", (f"user:{email}" if email else f"ip:{ip}")

    if email:
        return "authenticated", f"user:{email}"
    return "anonymous", f"ip:{ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, store: RateLimitStore | None = None) -> None:
        super().__init__(app)
        self._store = store or _default_store

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        scope, key = classify_request(request)
        max_requests, window_seconds = _limits_for_scope(scope)
        result = self._store.check(f"{scope}:{key}", max_requests, window_seconds)

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again."},
                headers={
                    "Retry-After": str(result.reset_seconds),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_seconds),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_seconds)
        return response
