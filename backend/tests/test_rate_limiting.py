"""RC1 Phase 1 Sprint 3 — API Protection & HTTP Security, Part C tests:
global rate limiting.

Note on identity: RateLimitMiddleware classifies scope from the RAW
Authorization header on the actual HTTP request (it runs before FastAPI's
dependency injection) — the shared `client` fixture's admin dependency
override fakes identity only for the route handler, not for any header
the TestClient actually sends, so plain `client.get(...)` calls with no
Authorization header are correctly classified "anonymous" here regardless
of that override. "authenticated"/"login"/"refresh" scope tests use
`real_auth_client()` with a genuine Bearer token instead — same pattern
tests/test_refresh_sessions.py already established.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from tests.conftest import real_auth_client

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
DASHBOARD_URL = "/api/v1/dashboard/summary"
PASSWORD = "Testpass1!"


def _register(client: TestClient) -> str:
    email = f"ratelimit_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(REGISTER_URL, json={
        "email": email, "password": PASSWORD, "full_name": "Rate Limit Tester", "role": "project_manager",
    })
    assert r.status_code == 201, r.text
    return email


def test_anonymous_scope_rate_limit_headers(client: TestClient):
    # The shared `client` fixture's dependency override fakes identity
    # for the route handler (so this succeeds, 200) but sends no real
    # Authorization header — RateLimitMiddleware runs before dependency
    # injection and sees none, so it's still classified "anonymous".
    r = client.get(DASHBOARD_URL)
    assert r.status_code == 200
    assert r.headers["X-RateLimit-Limit"] == str(settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS)
    assert int(r.headers["X-RateLimit-Remaining"]) == settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS - 1


def test_anonymous_scope_429_after_limit_exceeded(client: TestClient):
    for _ in range(settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS):
        client.get(DASHBOARD_URL)
    r = client.get(DASHBOARD_URL)
    assert r.status_code == 429
    assert r.json() == {"detail": "Too many requests. Please slow down and try again."}


def test_429_response_has_retry_after_and_standard_headers(client: TestClient):
    for _ in range(settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS):
        client.get(DASHBOARD_URL)
    r = client.get(DASHBOARD_URL)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) > 0
    assert r.headers["X-RateLimit-Remaining"] == "0"
    assert r.headers["X-RateLimit-Limit"] == str(settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS)


def test_healthz_is_exempt_from_rate_limiting(client: TestClient):
    for _ in range(settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS + 5):
        r = client.get("/api/healthz")
        assert r.status_code == 200


def test_authenticated_scope_uses_its_own_higher_limit(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = c.post(LOGIN_URL, json={"email": email, "password": PASSWORD}).json()
        r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert r.status_code == 200
        assert r.headers["X-RateLimit-Limit"] == str(settings.RATE_LIMIT_AUTHENTICATED_MAX_REQUESTS)


def test_login_scope_rate_limited_independently_of_existing_ip_throttle(client: TestClient):
    """Independent, additional layer on top of the existing Sprint 1/2
    login IP throttle (app/core/login_security.py) — must not have been
    modified by this sprint; both layers can 429, this test only proves
    the NEW global-rate-limit scope kicks in on its own configured
    threshold."""
    email = _register(client)
    with real_auth_client() as c:
        last = None
        for _ in range(settings.RATE_LIMIT_LOGIN_MAX_REQUESTS + 2):
            last = c.post(LOGIN_URL, json={"email": email, "password": "wrong-password"})
        assert last.status_code == 429
        assert "Retry-After" in last.headers


def test_refresh_scope_rate_limited_independently(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = c.post(LOGIN_URL, json={"email": email, "password": PASSWORD}).json()
        last = None
        for _ in range(settings.RATE_LIMIT_REFRESH_MAX_REQUESTS + 2):
            # Deliberately reuse the same (by then invalid/rotated) token —
            # the point here is exhausting the REFRESH rate-limit scope,
            # not exercising a successful rotation chain.
            last = c.post(REFRESH_URL, json={"refresh_token": login["refresh_token"]})
        assert last.status_code == 429


def test_upload_scope_classified_independently_of_authenticated_scope(client: TestClient):
    """A multipart request must be classified into the "upload" scope
    (its own configured limit), not "authenticated" — proven by its
    X-RateLimit-Limit header matching RATE_LIMIT_UPLOAD_MAX_REQUESTS.
    Uses a throwaway endpoint path (no real document needs to exist);
    RateLimitMiddleware classifies by Content-Type alone, before routing,
    so a 404 from the router afterward doesn't affect the header."""
    email = _register(client)
    with real_auth_client() as c:
        login = c.post(LOGIN_URL, json={"email": email, "password": PASSWORD}).json()
        r = c.post(
            "/api/v1/documents/999999/versions",
            headers={"Authorization": f"Bearer {login['access_token']}"},
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert r.headers["X-RateLimit-Limit"] == str(settings.RATE_LIMIT_UPLOAD_MAX_REQUESTS)


def test_rate_limiting_disabled_via_settings(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    for _ in range(settings.RATE_LIMIT_ANONYMOUS_MAX_REQUESTS + 5):
        r = client.get(DASHBOARD_URL)
    assert r.status_code != 429
    assert "X-RateLimit-Limit" not in r.headers
