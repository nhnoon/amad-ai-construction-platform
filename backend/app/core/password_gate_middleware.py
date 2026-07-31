"""Phase 2 — Security & Authentication Hardening: application-wide
enforcement of "must change password before doing anything else".

The primary mechanism is the gated ``CurrentUser`` dependency alias in
app/core/deps.py, which covers the overwhelming majority of routes since
they already declare a ``CurrentUser``/``CurrentScope`` parameter. This
middleware is the belt-and-suspenders safety net for the small number of
routes that don't (e.g. the deliberately unscoped supplier/subcontractor
catalog endpoints) — it runs for literally every request regardless of
which dependencies a given route declares, so "prevent access to the
application until the password has been changed" holds even there.

Uses its own direct DB session (SessionLocal) rather than FastAPI's
dependency-injected one, since ASGI middleware runs outside the DI system.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..core.security import decode_access_token
from ..database import SessionLocal
from ..models.auth import UserAccount

# Reachable without having completed a first-login/reset password change.
# Everything else under the API prefix is blocked.
_EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/me",
    "/api/v1/auth/change-password",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/healthz",
})


class PasswordChangeRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return await call_next(request)

        token = auth_header[7:].strip()
        payload = decode_access_token(token)
        if payload is None:
            return await call_next(request)
        email = payload.get("sub")
        if not email:
            return await call_next(request)

        db = SessionLocal()
        try:
            user = db.query(UserAccount).filter(UserAccount.email == email).first()
        finally:
            db.close()

        if user is not None and user.must_change_password:
            return JSONResponse(
                status_code=403,
                content={"detail": "password_change_required"},
            )

        return await call_next(request)
