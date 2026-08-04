"""RC1 Phase 1 Sprint 4 — Enterprise Audit Logging: ambient per-request
context (client IP, User-Agent, a correlation request_id) for
record_audit_event() (app/core/audit_log.py) to read, without threading a
`Request` object through every service function it's called from.

Many of the functions Sprint 4 instruments (app/ai/workflow_engine.py,
app/ai/ownership_engine.py, app/ai/approval_engine.py) are several layers
below the route handler and take no `Request` parameter today — adding
one to every one of those signatures, and to every route wrapper that
calls them, would be a much larger and more invasive change than this
feature calls for ("audit logging must observe the system — not change
it"). A contextvar set once per request by RequestContextMiddleware,
readable from anywhere in that request's call stack (including inside
FastAPI's threadpool for synchronous `def` route handlers — anyio's
`to_thread.run_sync`, which Starlette/FastAPI use for those, correctly
copies the current context into the worker thread), is the standard,
minimally-invasive way to make this available deep in the stack.

Also sets X-Request-ID on every response — useful independently of audit
logging for correlating a user's bug report with server-side logs.
"""
from __future__ import annotations

import secrets
from contextvars import ContextVar
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .login_security import client_ip_from_request

REQUEST_ID_HEADER = "X-Request-ID"


@dataclass(frozen=True)
class RequestContext:
    ip_address: str | None
    user_agent: str | None
    request_id: str | None


_current: ContextVar["RequestContext | None"] = ContextVar("audit_request_context", default=None)


def get_request_context() -> RequestContext | None:
    return _current.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # A caller-supplied X-Request-ID is honored (lets a client
        # correlate its own logs with ours across a multi-request flow)
        # but never trusted blindly for anything security-sensitive —
        # it's audit metadata, not an authorization input.
        request_id = request.headers.get(REQUEST_ID_HEADER) or secrets.token_hex(16)
        request.state.request_id = request_id

        context = RequestContext(
            ip_address=client_ip_from_request(request),
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
        )
        token = _current.set(context)
        try:
            response = await call_next(request)
        finally:
            _current.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
