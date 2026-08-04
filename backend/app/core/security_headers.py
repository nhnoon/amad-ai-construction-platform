"""RC1 Phase 1 Sprint 3 — API Protection & HTTP Security, Part A/B.

SecurityHeadersMiddleware adds the standard defensive response headers
(HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy, Cross-Origin-Opener-Policy, Cross-Origin-Resource-
Policy, and optionally Cross-Origin-Embedder-Policy) plus a
Content-Security-Policy, to every response. Every header is individually
toggleable via Settings so an operator whose reverse proxy/CDN already
emits some of these can disable just those (Part A: "do not duplicate
headers already emitted by proxies").

CSP design
----------
This backend serves almost no HTML at all — it's a JSON API. The only
HTML it ever returns is the dev-only Swagger UI (/api/docs) and ReDoc
(/api/redoc), both disabled entirely in production (see app/main.py's
_docs_urls). That split lets the policy be genuinely strict:

- Production: `default-src 'none'` plus the minimum `frame-ancestors`/
  `base-uri`/`form-action` lockdown. No CDN allowances of any kind — none
  are needed since no HTML is ever served.
- Development: the same strict baseline, PLUS the specific external
  origins FastAPI's stock (un-self-hosted) Swagger/ReDoc HTML actually
  loads from (see get_swagger_ui_html/get_redoc_html in fastapi.openapi.docs
  — read directly from the installed package to build this list, not
  guessed). Both pages also embed one small inline `<script>`
  (Swagger UI's `SwaggerUIBundle(...)` initializer) or `<style>` (ReDoc's
  body-margin reset) block. Per Part B's "prefer nonce-based if
  practical": app/main.py registers its OWN nonce-aware replacements for
  the default /docs and /redoc routes (docs_url/redoc_url are always
  None on the FastAPI app itself) that patch a per-request nonce into
  that exact inline tag, and this module hands out that same nonce via
  request.state.csp_nonce so the CSP header matches. No `unsafe-inline`
  or `unsafe-eval` is used anywhere, in either environment.
"""
from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings


def _permissions_policy_header() -> str:
    return settings.PERMISSIONS_POLICY


def _hsts_header() -> str:
    parts = [f"max-age={settings.HSTS_MAX_AGE_SECONDS}"]
    if settings.HSTS_INCLUDE_SUBDOMAINS:
        parts.append("includeSubDomains")
    if settings.HSTS_PRELOAD:
        parts.append("preload")
    return "; ".join(parts)


def build_csp(*, nonce: str, environment: str) -> str:
    """Builds the CSP directive string for one response. `nonce` is only
    actually referenced by the two inline tags on the dev-only docs pages
    (see module docstring) — including it in script-src/style-src on
    every response is harmless (a nonce that matches nothing simply never
    authorizes anything) and keeps this function environment-agnostic
    about WHERE the nonce gets used, not just whether one exists.
    """
    script_src = ["'self'", f"'nonce-{nonce}'"]
    style_src = ["'self'", f"'nonce-{nonce}'"]
    img_src = ["'self'", "data:"]
    font_src = ["'self'"]
    connect_src = ["'self'"]

    if environment != "production":
        # Dev-only: the stock FastAPI Swagger/ReDoc HTML's external
        # dependencies (see module docstring). Never added in production,
        # where /docs and /redoc don't exist as routes at all.
        script_src.append(settings.CSP_SWAGGER_CDN_ORIGIN)
        style_src.append(settings.CSP_SWAGGER_CDN_ORIGIN)
        style_src.append(settings.CSP_REDOC_FONTS_CSS_ORIGIN)
        img_src.append(settings.CSP_SWAGGER_FAVICON_ORIGIN)
        font_src.append(settings.CSP_REDOC_FONTS_ORIGIN)

    directives = {
        "default-src": ["'none'"],
        "script-src": script_src,
        "style-src": style_src,
        "img-src": img_src,
        "font-src": font_src,
        "connect-src": connect_src,
        "frame-ancestors": ["'none'"],
        "base-uri": ["'none'"],
        "form-action": ["'self'"],
    }
    return "; ".join(f"{name} {' '.join(values)}" for name, values in directives.items())


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generated before calling the route handler so a nonce-aware
        # route (the custom /docs, /redoc below) can read it back via
        # request.state — see module docstring.
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)

        if not settings.SECURITY_HEADERS_ENABLED:
            return response

        if settings.HSTS_ENABLED:
            response.headers["Strict-Transport-Security"] = _hsts_header()
        if settings.X_FRAME_OPTIONS_ENABLED:
            response.headers["X-Frame-Options"] = settings.X_FRAME_OPTIONS
        if settings.X_CONTENT_TYPE_OPTIONS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if settings.REFERRER_POLICY_ENABLED:
            response.headers["Referrer-Policy"] = settings.REFERRER_POLICY
        if settings.PERMISSIONS_POLICY_ENABLED:
            response.headers["Permissions-Policy"] = _permissions_policy_header()
        if settings.CROSS_ORIGIN_OPENER_POLICY_ENABLED:
            response.headers["Cross-Origin-Opener-Policy"] = settings.CROSS_ORIGIN_OPENER_POLICY
        if settings.CROSS_ORIGIN_RESOURCE_POLICY_ENABLED:
            response.headers["Cross-Origin-Resource-Policy"] = settings.CROSS_ORIGIN_RESOURCE_POLICY
        if settings.CROSS_ORIGIN_EMBEDDER_POLICY_ENABLED:
            response.headers["Cross-Origin-Embedder-Policy"] = settings.CROSS_ORIGIN_EMBEDDER_POLICY

        if settings.CSP_ENABLED:
            header_name = (
                "Content-Security-Policy-Report-Only"
                if settings.CSP_REPORT_ONLY
                else "Content-Security-Policy"
            )
            response.headers[header_name] = build_csp(nonce=nonce, environment=settings.ENVIRONMENT)

        return response
