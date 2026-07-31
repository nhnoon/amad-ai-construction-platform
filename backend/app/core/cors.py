"""Phase 2 — Security & Authentication Hardening: CORS configuration
validation, factored out of app/main.py so the policy is unit-testable
without booting the whole ASGI app.

Wildcard origins combined with credentials is never allowed. Starlette's
CORSMiddleware treats allow_origins=["*"] + allow_credentials=True as
"reflect any Origin back with credentials enabled", which is equivalent in
practice to trusting every website on the internet with this API's
cookies/auth headers. A real deployment must set ALLOWED_ORIGINS
explicitly (see app/config.py); outside development, a wildcard is
rejected at startup rather than silently downgraded.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedCorsSettings:
    allowed_origins: list[str]
    allow_credentials: bool


def resolve_cors_settings(allowed_origins: list[str], environment: str) -> ResolvedCorsSettings:
    """Validate and resolve the CORS policy to actually hand to
    CORSMiddleware.

    Raises RuntimeError if a wildcard origin is configured outside
    development — that combination must be an explicit, corrected
    configuration change, not something that silently limps along in
    production. Within development, a wildcard is still permitted (for a
    frictionless local setup) but credentials are always disabled in that
    case, so the dangerous pairing can never actually occur.
    """
    wildcard = "*" in allowed_origins
    if wildcard and environment != "development":
        raise RuntimeError(
            "ALLOWED_ORIGINS must not include '*' outside development — "
            "set it to an explicit list of trusted origins."
        )
    return ResolvedCorsSettings(
        allowed_origins=allowed_origins,
        allow_credentials=not wildcard,
    )
