"""RC1 Phase 1 Sprint 3 — nonce-aware replacements for FastAPI's default
/docs (Swagger UI) and /redoc routes.

FastAPI's built-in docs routes (registered automatically when docs_url/
redoc_url are passed to the FastAPI(...) constructor) render one small
inline <script> (Swagger UI's SwaggerUIBundle initializer) or <style>
(ReDoc's body-margin reset) tag with no way to inject a nonce. Per Part
B's "prefer nonce-based if practical": app/main.py always passes
docs_url=None/redoc_url=None to the FastAPI constructor (so the default,
non-nonce-aware routes are never registered) and calls
register_docs_routes() below instead, outside production only — the
result renders byte-for-byte the same HTML FastAPI's own
get_swagger_ui_html/get_redoc_html would produce, just with that one
inline tag carrying request.state.csp_nonce (set by
SecurityHeadersMiddleware before the route runs — see
app/core/security_headers.py) so the CSP header's script-src/style-src
nonce actually matches, and neither page needs 'unsafe-inline'.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from starlette.responses import HTMLResponse


def _nonce_for(request: Request) -> str:
    return getattr(request.state, "csp_nonce", "")


def register_docs_routes(app: FastAPI, *, docs_url: str, redoc_url: str, openapi_url: str) -> None:
    @app.get(docs_url, include_in_schema=False)
    async def custom_swagger_ui(request: Request) -> HTMLResponse:
        html = get_swagger_ui_html(openapi_url=openapi_url, title=f"{app.title} — Swagger UI")
        nonce = _nonce_for(request)
        # Targets exactly the one inline `<script>` tag (SwaggerUIBundle's
        # initializer). The CDN-loaded bundle itself is
        # `<script src="...">` — a distinct string — so this can't
        # accidentally match that tag instead.
        body = html.body.decode("utf-8").replace("<script>", f'<script nonce="{nonce}">', 1)
        return HTMLResponse(body)

    @app.get(redoc_url, include_in_schema=False)
    async def custom_redoc(request: Request) -> HTMLResponse:
        html = get_redoc_html(openapi_url=openapi_url, title=f"{app.title} — ReDoc")
        nonce = _nonce_for(request)
        # Targets exactly the one inline `<style>` tag (ReDoc's
        # body-margin reset) — same reasoning as above.
        body = html.body.decode("utf-8").replace("<style>", f'<style nonce="{nonce}">', 1)
        return HTMLResponse(body)
