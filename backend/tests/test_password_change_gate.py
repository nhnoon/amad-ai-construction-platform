"""Phase 2 — Security & Authentication Hardening: forced first-login
password change (Goal 2).

Uses real registration/login (not the mocked `client` fixture's
dependency_overrides) since the gate depends on a real, DB-persisted
must_change_password flag — the mocked override user never sets that
attribute at all, so it's correctly a no-op there (see
tests/conftest.py's override_get_current_user and the note in
app/core/deps.py::get_current_user_password_changed).
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal, real_auth_client

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
CHANGE_PASSWORD_URL = "/api/v1/auth/change-password"
ME_URL = "/api/v1/auth/me"
USERS_URL = "/api/v1/admin/users"


def _register(client: TestClient) -> tuple[str, str]:
    email = f"gate-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "InitialPass1!"
    r = client.post(REGISTER_URL, json={
        "email": email, "password": password, "role": "project_manager",
    })
    assert r.status_code == 201
    return email, password


class TestNewUserMustChangePassword:
    def test_register_sets_must_change_password_true(self, client: TestClient):
        email = f"registerflag-{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(REGISTER_URL, json={
            "email": email, "password": "Something1!", "role": "viewer",
        })
        assert r.status_code == 201
        assert r.json()["must_change_password"] is True

    def test_admin_created_user_must_change_password_true(self, client: TestClient):
        email = f"adminflag-{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(USERS_URL, json={"email": email, "role": "viewer"})
        assert r.status_code == 201
        assert r.json()["user"]["must_change_password"] is True

    def test_login_response_reports_must_change_password(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            login_resp = raw.post(LOGIN_URL, json={"email": email, "password": password})
            assert login_resp.status_code == 200
            assert login_resp.json()["user"]["must_change_password"] is True


class TestGateBlocksOtherRoutes:
    def test_blocked_from_dashboard_until_changed(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 403
            assert r.json()["detail"] == "password_change_required"

    def test_blocked_from_projects_until_changed(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 403
            assert r.json()["detail"] == "password_change_required"

    def test_me_remains_reachable(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200

    def test_unscoped_catalog_route_also_blocked_via_middleware(self, client: TestClient):
        """Suppliers has no CurrentUser/CurrentScope parameter at all (see
        app/api/v1/procurement.py) — proves the belt-and-suspenders
        middleware, not just the CurrentUser dependency alias, is doing
        real work."""
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.get("/api/v1/procurement/suppliers", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 403
            assert r.json()["detail"] == "password_change_required"


class TestChangePasswordFlow:
    def test_wrong_current_password_rejected(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.post(
                CHANGE_PASSWORD_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": "WrongOne1!", "new_password": "BrandNew1!"},
            )
            assert r.status_code == 401

    def test_weak_new_password_rejected(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.post(
                CHANGE_PASSWORD_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": password, "new_password": "short"},
            )
            assert r.status_code == 422

    def test_successful_change_clears_flag_and_unblocks(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            r = raw.post(
                CHANGE_PASSWORD_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": password, "new_password": "BrandNew1!"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["user"]["must_change_password"] is False
            new_token = data["access_token"]

            dash = raw.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {new_token}"})
            assert dash.status_code == 200

            relogin = raw.post(LOGIN_URL, json={"email": email, "password": "BrandNew1!"})
            assert relogin.status_code == 200
            assert relogin.json()["user"]["must_change_password"] is False

    def test_old_password_no_longer_works_after_change(self, client: TestClient):
        email, password = _register(client)
        with real_auth_client() as raw:
            token = raw.post(LOGIN_URL, json={"email": email, "password": password}).json()["access_token"]
            raw.post(
                CHANGE_PASSWORD_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": password, "new_password": "BrandNew1!"},
            )
            r = raw.post(LOGIN_URL, json={"email": email, "password": password})
            assert r.status_code == 401


class TestExistingUsersUnaffected:
    def test_seeded_admin_does_not_require_password_change(self):
        """Migration 0014 backfills must_change_password=False for every
        pre-existing row — the mocked admin override never sets the
        attribute at all, so it reads as falsy; this test instead checks
        the real, DB-persisted row directly."""
        db = TestingSessionLocal()
        try:
            from app.models.auth import UserAccount
            admin = db.query(UserAccount).filter(UserAccount.email == "admin@construction.ai").first()
            assert admin is not None
            assert admin.must_change_password is False
        finally:
            db.close()
