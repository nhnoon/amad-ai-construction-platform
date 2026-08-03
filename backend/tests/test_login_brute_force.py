"""Phase 2 — Security & Authentication Hardening: login rate limiting
(Goal 3) and account lockout (Goal 4).

Uses a dedicated, disposable user for the lockout tests — never the
shared seeded demo accounts other tests rely on being able to log into.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.login_security import login_ip_rate_limiter
from tests.conftest import TestingSessionLocal

LOGIN_URL = "/api/v1/auth/login"
USERS_URL = "/api/v1/admin/users"


@pytest.fixture
def lockout_test_user(client: TestClient):
    """A real, disposable user for deliberately failing logins against —
    never the shared demo admin, so this can't lock other tests out."""
    email = f"lockout-test-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(USERS_URL, json={"email": email, "role": "viewer"})
    assert r.status_code == 201
    return {"email": email, "password": r.json()["temporary_password"]}


class TestLoginRateLimiting:
    def test_exceeding_ip_rate_limit_returns_429(self, client: TestClient):
        login_ip_rate_limiter.reset_all()
        last_status = None
        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS + 1):
            resp = client.post(LOGIN_URL, json={"email": "nobody@nowhere.com", "password": "whatever123"})
            last_status = resp.status_code
        assert last_status == 429

    def test_rate_limit_applies_before_credential_check(self, client: TestClient):
        """Even a correct password gets 429 once the IP window is
        exhausted — the throttle runs before any DB/credential work."""
        login_ip_rate_limiter.reset_all()
        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            client.post(LOGIN_URL, json={"email": "nobody@nowhere.com", "password": "whatever123"})
        resp = client.post(LOGIN_URL, json={"email": "admin@construction.ai", "password": "whatever-real-or-not"})
        assert resp.status_code == 429


class TestAccountLockout:
    def test_lockout_after_max_failed_attempts(self, client: TestClient, lockout_test_user):
        login_ip_rate_limiter.reset_all()
        email = lockout_test_user["email"]
        for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
            resp = client.post(LOGIN_URL, json={"email": email, "password": "WrongPassword1!"})
            assert resp.status_code == 401

        # One more attempt — even with the correct password — is now locked.
        locked_resp = client.post(LOGIN_URL, json={"email": email, "password": lockout_test_user["password"]})
        assert locked_resp.status_code == 423

    def test_lockout_does_not_leak_whether_password_was_correct(self, client: TestClient, lockout_test_user):
        login_ip_rate_limiter.reset_all()
        email = lockout_test_user["email"]
        for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
            client.post(LOGIN_URL, json={"email": email, "password": "WrongPassword1!"})

        correct_pw_resp = client.post(LOGIN_URL, json={"email": email, "password": lockout_test_user["password"]})
        wrong_pw_resp = client.post(LOGIN_URL, json={"email": email, "password": "SomethingElse1!"})
        assert correct_pw_resp.status_code == wrong_pw_resp.status_code == 423

    def test_successful_login_resets_failed_attempts(self, client: TestClient, lockout_test_user):
        login_ip_rate_limiter.reset_all()
        email = lockout_test_user["email"]
        password = lockout_test_user["password"]

        # A couple of failures, then a success — should NOT be anywhere
        # near locked afterward.
        client.post(LOGIN_URL, json={"email": email, "password": "WrongPassword1!"})
        client.post(LOGIN_URL, json={"email": email, "password": "WrongPassword1!"})
        ok_resp = client.post(LOGIN_URL, json={"email": email, "password": password})
        assert ok_resp.status_code == 200

        db = TestingSessionLocal()
        try:
            from app.models.auth import UserAccount
            user = db.query(UserAccount).filter(UserAccount.email == email).first()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None
        finally:
            db.close()

    def test_lockout_automatically_expires(self, client: TestClient, lockout_test_user):
        """Simulates the lockout window having already elapsed (rather
        than sleeping for real minutes in the test suite) by setting
        locked_until into the past directly — proves the unlock is
        time-based, not something that needs a manual admin action."""
        login_ip_rate_limiter.reset_all()
        email = lockout_test_user["email"]
        password = lockout_test_user["password"]

        for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
            client.post(LOGIN_URL, json={"email": email, "password": "WrongPassword1!"})
        still_locked = client.post(LOGIN_URL, json={"email": email, "password": password})
        assert still_locked.status_code == 423

        db = TestingSessionLocal()
        try:
            from app.models.auth import UserAccount
            user = db.query(UserAccount).filter(UserAccount.email == email).first()
            user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        finally:
            db.close()

        unlocked_resp = client.post(LOGIN_URL, json={"email": email, "password": password})
        assert unlocked_resp.status_code == 200
