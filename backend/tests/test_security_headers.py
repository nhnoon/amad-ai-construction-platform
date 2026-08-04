"""RC1 Phase 1 Sprint 3 — API Protection & HTTP Security, Part A/B tests:
security headers and Content-Security-Policy.
"""
import re

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_security_headers_present_on_response(client: TestClient):
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert r.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    # Off by default (Part A: "only if compatible" — see config.py) —
    # must not appear unless explicitly enabled.
    assert "Cross-Origin-Embedder-Policy" not in r.headers


def test_security_headers_present_on_error_responses_too(client: TestClient):
    """Headers must land on every response, including ones the router
    never reaches — proves SecurityHeadersMiddleware wraps the layers
    below it (rate limit / request protection / password gate), not just
    successful application responses."""
    r = client.get("/api/v1/this-route-does-not-exist")
    assert r.status_code == 404
    assert "X-Frame-Options" in r.headers
    assert "Content-Security-Policy" in r.headers


def test_security_headers_disabled_via_settings(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "SECURITY_HEADERS_ENABLED", False)
    r = client.get("/api/healthz")
    assert "X-Frame-Options" not in r.headers
    assert "Content-Security-Policy" not in r.headers


def test_individual_header_can_be_disabled(client: TestClient, monkeypatch):
    """Part A: 'do not duplicate headers already emitted by proxies' —
    each header must be independently toggleable."""
    monkeypatch.setattr(settings, "HSTS_ENABLED", False)
    r = client.get("/api/healthz")
    assert "Strict-Transport-Security" not in r.headers
    assert "X-Frame-Options" in r.headers  # everything else unaffected


def test_csp_present_and_strict_by_default(client: TestClient):
    r = client.get("/api/healthz")
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_csp_report_only_mode(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CSP_REPORT_ONLY", True)
    r = client.get("/api/healthz")
    assert "Content-Security-Policy" not in r.headers
    assert "Content-Security-Policy-Report-Only" in r.headers


def test_docs_inline_script_nonce_matches_csp_header(client: TestClient):
    """Part B: 'prefer nonce-based if practical' — Swagger UI's one
    inline <script> (its SwaggerUIBundle initializer) must carry the same
    nonce the CSP header's script-src actually allows, with no
    'unsafe-inline' fallback needed."""
    r = client.get("/api/docs")
    assert r.status_code == 200
    csp = r.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp

    match = re.search(r'<script nonce="([^"]+)">', r.text)
    assert match is not None, "expected a nonce-carrying inline <script> tag"
    nonce = match.group(1)
    assert f"'nonce-{nonce}'" in csp
    # The CDN-hosted bundle itself must still be reachable via an origin
    # allowance, not a nonce (it's a separate <script src=...> tag).
    assert settings.CSP_SWAGGER_CDN_ORIGIN in csp


def test_redoc_inline_style_nonce_matches_csp_header(client: TestClient):
    r = client.get("/api/redoc")
    assert r.status_code == 200
    csp = r.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp

    match = re.search(r'<style nonce="([^"]+)">', r.text)
    assert match is not None, "expected a nonce-carrying inline <style> tag"
    nonce = match.group(1)
    assert f"'nonce-{nonce}'" in csp


def test_production_csp_has_no_dev_cdn_allowances():
    """Development and production may differ (Part B) — production's CSP
    must not carry the Swagger/ReDoc CDN allowances at all, since /docs
    and /redoc are unregistered routes there (RC1 Phase 0, Finding 5)."""
    from app.core.security_headers import build_csp

    prod_csp = build_csp(nonce="x", environment="production")
    assert settings.CSP_SWAGGER_CDN_ORIGIN not in prod_csp
    assert settings.CSP_REDOC_FONTS_CSS_ORIGIN not in prod_csp

    dev_csp = build_csp(nonce="x", environment="development")
    assert settings.CSP_SWAGGER_CDN_ORIGIN in dev_csp
