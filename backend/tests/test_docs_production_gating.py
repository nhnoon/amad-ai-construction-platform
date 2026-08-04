"""Tests for API docs/OpenAPI schema production gating (RC1 Phase 0 —
Security Remediation, Finding 5).

RC1 Phase 1 Sprint 3 — API Protection & HTTP Security: `_docs_urls` now
ALWAYS returns docs_url=None/redoc_url=None (even outside production) —
FastAPI's own built-in docs routes render an inline <script>/<style> tag
with no way to attach a CSP nonce, so app/main.py registers nonce-aware
replacements separately via register_docs_routes() (see
app/core/docs_routes.py and app/core/security_headers.py's module
docstring) instead of passing real URLs to the FastAPI constructor.
`openapi_url` is unaffected — the raw JSON schema has no HTML/nonce
concerns and still comes from FastAPI's own built-in route.

The shared `app`/`client` fixtures (see conftest.py) are already
constructed once, at import time, with docs enabled for the dev
ENVIRONMENT the test suite runs under (see test_health.py's
test_docs_available / test_openapi_schema for that coverage) — FastAPI
bakes docs_url/redoc_url/openapi_url into the app at construction time, so
that global app instance cannot be used to also exercise the production
case. These tests instead: (1) unit-test the pure resolver functions
app.main._docs_urls / app.main.docs_enabled directly, and (2) build a
second, throwaway FastAPI app using those same functions (registering
nonce-aware docs routes exactly like app/main.py does) with
environment="production" to prove the routes are genuinely unregistered
(404), not merely unlinked.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.docs_routes import register_docs_routes
from app.main import DOCS_URL, OPENAPI_URL, REDOC_URL, _docs_urls, docs_enabled


def test_docs_urls_disabled_in_production():
    assert _docs_urls("production") == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }
    assert docs_enabled("production") is False


def test_docs_urls_enabled_outside_production():
    for environment in ("development", "test", "staging"):
        urls = _docs_urls(environment)
        # docs_url/redoc_url are always None on the FastAPI constructor
        # itself now — register_docs_routes() is what actually makes them
        # reachable (see module docstring); docs_enabled() is the real
        # source of truth for whether that registration happens.
        assert urls == {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": "/api/openapi.json",
        }
        assert docs_enabled(environment) is True


def test_docs_actually_404_in_a_production_configured_app():
    prod_app = FastAPI(**_docs_urls("production"))
    with TestClient(prod_app) as c:
        assert c.get("/api/docs").status_code == 404
        assert c.get("/api/redoc").status_code == 404
        assert c.get("/api/openapi.json").status_code == 404


def test_docs_reachable_in_a_development_configured_app():
    dev_app = FastAPI(**_docs_urls("development"))
    register_docs_routes(dev_app, docs_url=DOCS_URL, redoc_url=REDOC_URL, openapi_url=OPENAPI_URL)
    with TestClient(dev_app) as c:
        assert c.get("/api/docs").status_code == 200
        assert c.get("/api/redoc").status_code == 200
        assert c.get("/api/openapi.json").status_code == 200
