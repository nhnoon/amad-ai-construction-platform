"""Tests for API docs/OpenAPI schema production gating (RC1 Phase 0 —
Security Remediation, Finding 5).

The shared `app`/`client` fixtures (see conftest.py) are already
constructed once, at import time, with docs enabled for the dev
ENVIRONMENT the test suite runs under (see test_health.py's
test_docs_available / test_openapi_schema for that coverage) — FastAPI
bakes docs_url/redoc_url/openapi_url into the app at construction time, so
that global app instance cannot be used to also exercise the production
case. These tests instead: (1) unit-test the pure resolver function
app.main._docs_urls directly, and (2) build a second, throwaway FastAPI
app using that same function with environment="production" to prove the
routes are genuinely unregistered (404), not merely unlinked.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import _docs_urls


def test_docs_urls_disabled_in_production():
    assert _docs_urls("production") == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }


def test_docs_urls_enabled_outside_production():
    for environment in ("development", "test", "staging"):
        urls = _docs_urls(environment)
        assert urls == {
            "docs_url": "/api/docs",
            "redoc_url": "/api/redoc",
            "openapi_url": "/api/openapi.json",
        }


def test_docs_actually_404_in_a_production_configured_app():
    prod_app = FastAPI(**_docs_urls("production"))
    with TestClient(prod_app) as c:
        assert c.get("/api/docs").status_code == 404
        assert c.get("/api/redoc").status_code == 404
        assert c.get("/api/openapi.json").status_code == 404


def test_docs_reachable_in_a_development_configured_app():
    dev_app = FastAPI(**_docs_urls("development"))
    with TestClient(dev_app) as c:
        assert c.get("/api/docs").status_code == 200
        assert c.get("/api/redoc").status_code == 200
        assert c.get("/api/openapi.json").status_code == 200
