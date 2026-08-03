import uuid
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.deps import get_current_user
from app.models.auth import UserAccount
from app.models.organizations import Organization
from tests.conftest import TestingSessionLocal

USERS_URL = "/api/v1/admin/users"
LOGIN_URL = "/api/v1/auth/login"


def _role_override(role: str):
    def _user():
        return UserAccount(
            id=990, email=f"{role}@test.ai", role=role, is_active=True,
            hashed_password="x", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    return _user


def _set_override(fn):
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = fn
    return original


def _restore_override(original):
    if original is not None:
        app.dependency_overrides[get_current_user] = original
    elif get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


def test_admin_can_list_users(client: TestClient):
    r = client.get(USERS_URL)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_admin_can_create_user(client: TestClient):
    email = f"newuser_{uuid.uuid4().hex[:6]}@test.ai"
    r = client.post(USERS_URL, json={
        "email": email,
        "full_name": "New Test User",
        "role": "site_engineer",
    })
    assert r.status_code == 201
    data = r.json()
    # Phase 2 — Security & Authentication Hardening: the admin no longer
    # supplies a temporary password (the previous shared default,
    # "Welcome123!", was the exact vulnerability this phase fixed) — the
    # server generates one and returns it exactly once, alongside the
    # created user.
    assert "temporary_password" in data
    assert len(data["temporary_password"]) >= 16
    user = data["user"]
    assert user["email"] == email
    assert user["full_name"] == "New Test User"
    assert user["role"] == "site_engineer"
    assert user["is_active"] is True
    assert user["must_change_password"] is True
    assert "hashed_password" not in user
    assert "id" in user


def test_create_user_generates_distinct_passwords(client: TestClient):
    """Two separately created users must never receive the same temporary
    password — proof this isn't still a shared default under the hood."""
    email_a = f"distinct_a_{uuid.uuid4().hex[:6]}@test.ai"
    email_b = f"distinct_b_{uuid.uuid4().hex[:6]}@test.ai"
    pw_a = client.post(USERS_URL, json={"email": email_a, "role": "viewer"}).json()["temporary_password"]
    pw_b = client.post(USERS_URL, json={"email": email_b, "role": "viewer"}).json()["temporary_password"]
    assert pw_a != pw_b


def test_create_user_duplicate_email(client: TestClient):
    email = f"dup_{uuid.uuid4().hex[:6]}@test.ai"
    client.post(USERS_URL, json={"email": email, "role": "viewer"})
    r = client.post(USERS_URL, json={"email": email, "role": "viewer"})
    assert r.status_code == 409


def test_create_user_invalid_role(client: TestClient):
    email = f"badrole_{uuid.uuid4().hex[:6]}@test.ai"
    r = client.post(USERS_URL, json={"email": email, "role": "superuser"})
    assert r.status_code == 422


def test_create_user_ignores_client_supplied_organization_id(client: TestClient):
    """organization_id is no longer a field on the request at all — the
    new user must always inherit the creating admin's own organization,
    never an arbitrary client-supplied one (Phase 1's rule, extended here
    to this sibling endpoint during the Phase 2 authentication-routes
    audit)."""
    email = f"orgcheck_{uuid.uuid4().hex[:6]}@test.ai"
    r = client.post(USERS_URL, json={"email": email, "role": "viewer", "organization_id": 999_999})
    assert r.status_code == 201
    assert r.json()["user"]["organization_id"] != 999_999


def test_admin_can_get_user(client: TestClient):
    email = f"getuser_{uuid.uuid4().hex[:6]}@test.ai"
    created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()["user"]
    r = client.get(f"{USERS_URL}/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_admin_can_deactivate_user(client: TestClient):
    email = f"deact_{uuid.uuid4().hex[:6]}@test.ai"
    created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()["user"]
    r = client.patch(f"{USERS_URL}/{created['id']}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_admin_can_change_user_role(client: TestClient):
    email = f"changerole_{uuid.uuid4().hex[:6]}@test.ai"
    created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()["user"]
    r = client.patch(f"{USERS_URL}/{created['id']}", json={"role": "project_manager"})
    assert r.status_code == 200
    assert r.json()["role"] == "project_manager"


def test_admin_can_reset_password(client: TestClient):
    email = f"resetpw_{uuid.uuid4().hex[:6]}@test.ai"
    created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()["user"]
    r = client.post(f"{USERS_URL}/{created['id']}/reset-password")
    assert r.status_code == 200
    data = r.json()
    assert "temporary_password" in data
    assert len(data["temporary_password"]) >= 8
    assert "message" in data


def test_reset_password_sets_must_change_password(client: TestClient):
    email = f"resetflag_{uuid.uuid4().hex[:6]}@test.ai"
    created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()["user"]
    client.post(f"{USERS_URL}/{created['id']}/reset-password")
    r = client.get(f"{USERS_URL}/{created['id']}")
    assert r.json()["must_change_password"] is True


def test_non_admin_cannot_list_users(client: TestClient):
    original = _set_override(_role_override("project_manager"))
    try:
        r = client.get(USERS_URL)
        assert r.status_code == 403
    finally:
        _restore_override(original)


def test_non_admin_cannot_create_user(client: TestClient):
    original = _set_override(_role_override("site_engineer"))
    try:
        email = f"nonadmin_{uuid.uuid4().hex[:6]}@test.ai"
        r = client.post(USERS_URL, json={"email": email, "role": "viewer"})
        assert r.status_code == 403
    finally:
        _restore_override(original)


def test_viewer_cannot_access_admin(client: TestClient):
    original = _set_override(_role_override("viewer"))
    try:
        r = client.get(USERS_URL)
        assert r.status_code == 403
    finally:
        _restore_override(original)


def test_inactive_user_cannot_login(client: TestClient):
    """Create user, deactivate, verify login returns 403."""
    email = f"inactive_{uuid.uuid4().hex[:6]}@test.ai"
    created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()
    temp_password = created["temporary_password"]
    client.patch(f"{USERS_URL}/{created['user']['id']}", json={"is_active": False})
    r = client.post(LOGIN_URL, json={"email": email, "password": temp_password})
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()


def test_user_not_found(client: TestClient):
    r = client.get(f"{USERS_URL}/999999")
    assert r.status_code == 404


class TestCrossOrganizationUserManagementIsBlocked:
    """Phase 2 — Security & Authentication Hardening audit finding: before
    this fix, none of these routes were scoped to the calling admin's
    organization at all — an admin in one org could list, view, edit, or
    reset the password of a user in ANY organization platform-wide. Same
    class of bug Phase 1 fixed for project-scoped resources; "admin" is
    org-scoped in this app (no platform super-admin exists)."""

    @pytest.fixture
    def other_org_user(self):
        db = TestingSessionLocal()
        org = Organization(
            name="Admin Users Isolation Test Org",
            slug=f"admin-users-iso-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        db.add(org)
        db.flush()
        user = UserAccount(
            email=f"otherorg-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="x", role="viewer", is_active=True,
            organization_id=org.id,
        )
        db.add(user)
        db.commit()
        org_id, user_id = org.id, user.id
        yield user_id
        db.query(UserAccount).filter(UserAccount.id == user_id).delete(synchronize_session=False)
        db.query(Organization).filter(Organization.id == org_id).delete(synchronize_session=False)
        db.commit()
        db.close()

    def test_list_users_excludes_other_organizations(self, client: TestClient, other_org_user):
        r = client.get(USERS_URL)
        assert r.status_code == 200
        ids = {u["id"] for u in r.json()}
        assert other_org_user not in ids

    def test_get_user_in_other_organization_is_404(self, client: TestClient, other_org_user):
        r = client.get(f"{USERS_URL}/{other_org_user}")
        assert r.status_code == 404

    def test_update_user_in_other_organization_is_404(self, client: TestClient, other_org_user):
        r = client.patch(f"{USERS_URL}/{other_org_user}", json={"is_active": False})
        assert r.status_code == 404
        db = TestingSessionLocal()
        try:
            user = db.query(UserAccount).filter(UserAccount.id == other_org_user).first()
            assert user.is_active is True  # unchanged
        finally:
            db.close()

    def test_reset_password_in_other_organization_is_404(self, client: TestClient, other_org_user):
        r = client.post(f"{USERS_URL}/{other_org_user}/reset-password")
        assert r.status_code == 404

    def test_update_cannot_reassign_organization_id(self, client: TestClient):
        email = f"orgreassign-{uuid.uuid4().hex[:8]}@example.com"
        created = client.post(USERS_URL, json={"email": email, "role": "viewer"}).json()["user"]
        original_org_id = created["organization_id"]
        r = client.patch(f"{USERS_URL}/{created['id']}", json={"organization_id": 999_999})
        assert r.status_code == 200
        assert r.json()["organization_id"] == original_org_id
