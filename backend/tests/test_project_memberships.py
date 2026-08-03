import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.deps import get_current_user
from app.core.security import hash_password
from app.models.auth import UserAccount
from app.models.organizations import Organization
from tests.conftest import TestingSessionLocal
from datetime import datetime, timezone

USERS_URL = "/api/v1/admin/users"
PROJECTS_URL = "/api/v1/projects"


def _role_override(role: str):
    def _user():
        return UserAccount(
            id=991, email=f"{role}@member.ai", role=role, is_active=True,
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


@pytest.fixture(scope="module")
def project_id(client: TestClient):
    r = client.get(PROJECTS_URL)
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) > 0
    return projects[0]["id"]


@pytest.fixture(scope="module")
def member_user(client: TestClient):
    email = f"member_{uuid.uuid4().hex[:6]}@test.ai"
    r = client.post(USERS_URL, json={
        "email": email,
        "role": "site_engineer",
    })
    assert r.status_code == 201
    # Phase 2 — Security & Authentication Hardening: POST /admin/users now
    # returns {"user": {...}, "temporary_password": "..."} (server-generated
    # password) instead of a flat user object — unwrap it so every existing
    # member_user["id"]-style access below keeps working unchanged.
    return r.json()["user"]


def test_list_memberships_empty(client: TestClient, project_id: int):
    r = client.get(f"{PROJECTS_URL}/{project_id}/memberships")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_add_project_membership(client: TestClient, project_id: int, member_user: dict):
    r = client.post(f"{PROJECTS_URL}/{project_id}/memberships", json={
        "user_id": member_user["id"],
        "role_on_project": "site_engineer",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == member_user["id"]
    assert data["project_id"] == project_id
    assert data["role_on_project"] == "site_engineer"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_membership_appears_in_list(client: TestClient, project_id: int, member_user: dict):
    r = client.get(f"{PROJECTS_URL}/{project_id}/memberships")
    assert r.status_code == 200
    user_ids = [m["user_id"] for m in r.json()]
    assert member_user["id"] in user_ids


def test_add_duplicate_membership(client: TestClient, project_id: int, member_user: dict):
    r = client.post(f"{PROJECTS_URL}/{project_id}/memberships", json={
        "user_id": member_user["id"],
        "role_on_project": "site_engineer",
    })
    assert r.status_code == 409


def test_membership_invalid_project(client: TestClient):
    r = client.post(f"{PROJECTS_URL}/999999/memberships", json={
        "user_id": 1, "role_on_project": "viewer",
    })
    assert r.status_code == 404


def test_membership_invalid_user(client: TestClient, project_id: int):
    r = client.post(f"{PROJECTS_URL}/{project_id}/memberships", json={
        "user_id": 999999, "role_on_project": "viewer",
    })
    assert r.status_code == 404


def test_remove_project_membership(client: TestClient, project_id: int, member_user: dict):
    r = client.delete(f"{PROJECTS_URL}/{project_id}/memberships/{member_user['id']}")
    assert r.status_code == 204


def test_membership_removed_from_list(client: TestClient, project_id: int, member_user: dict):
    r = client.get(f"{PROJECTS_URL}/{project_id}/memberships")
    assert r.status_code == 200
    user_ids = [m["user_id"] for m in r.json()]
    assert member_user["id"] not in user_ids


def test_remove_nonexistent_membership(client: TestClient, project_id: int):
    r = client.delete(f"{PROJECTS_URL}/{project_id}/memberships/999999")
    assert r.status_code == 404


def test_viewer_cannot_add_membership(client: TestClient, project_id: int):
    original = _set_override(_role_override("viewer"))
    try:
        r = client.post(f"{PROJECTS_URL}/{project_id}/memberships", json={
            "user_id": 1, "role_on_project": "viewer",
        })
        assert r.status_code == 403
    finally:
        _restore_override(original)


# ─────────────────────────────────────────────────────────────────────────
# RC1 Phase 0 — Security Remediation (Finding 4): cross-organization
# membership injection. Before this fix, add_membership only checked that
# body.user_id existed at all -- a user from ANY organization could be
# granted membership on this project. These throwaway fixtures (a second
# organization, a foreign-org user, and a same-org-but-inactive user) are
# created directly via the DB, with guaranteed cleanup, and are never used
# outside this test module.
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def foreign_org_user_id(project_id: int):
    """A real, active user who exists but belongs to a different
    organization than project_id's project."""
    db = TestingSessionLocal()
    foreign_org = Organization(
        name="RC1 Membership Foreign Org",
        slug=f"rc1-membership-foreign-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(foreign_org)
    db.commit()
    db.refresh(foreign_org)

    foreign_user = UserAccount(
        email=f"rc1-foreign-org-user-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password=hash_password("irrelevant-not-used-for-login"),
        full_name="RC1 Foreign Org User",
        role="site_engineer",
        is_active=True,
        organization_id=foreign_org.id,
    )
    db.add(foreign_user)
    db.commit()
    db.refresh(foreign_user)
    user_id = foreign_user.id
    org_id = foreign_org.id
    db.close()

    yield user_id

    db = TestingSessionLocal()
    db.query(UserAccount).filter(UserAccount.id == user_id).delete()
    db.query(Organization).filter(Organization.id == org_id).delete()
    db.commit()
    db.close()


@pytest.fixture
def inactive_same_org_user_id():
    """A real, inactive user in the same organization as the mocked admin
    test user (see conftest.py's TEST_USER_ORGANIZATION_ID)."""
    from tests.conftest import TEST_USER_ORGANIZATION_ID

    db = TestingSessionLocal()
    inactive_user = UserAccount(
        email=f"rc1-inactive-user-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password=hash_password("irrelevant-not-used-for-login"),
        full_name="RC1 Inactive User",
        role="site_engineer",
        is_active=False,
        organization_id=TEST_USER_ORGANIZATION_ID,
    )
    db.add(inactive_user)
    db.commit()
    db.refresh(inactive_user)
    user_id = inactive_user.id
    db.close()

    yield user_id

    db = TestingSessionLocal()
    db.query(UserAccount).filter(UserAccount.id == user_id).delete()
    db.commit()
    db.close()


def test_add_membership_cross_org_user_rejected_as_404(
    client: TestClient, project_id: int, foreign_org_user_id: int
):
    r = client.post(f"{PROJECTS_URL}/{project_id}/memberships", json={
        "user_id": foreign_org_user_id, "role_on_project": "viewer",
    })
    # Same hide-cross-tenant-existence policy as everywhere else in this
    # app: a user that exists in another organization is indistinguishable
    # from a user that doesn't exist at all.
    assert r.status_code == 404

    # And no membership row was actually created.
    memberships = client.get(f"{PROJECTS_URL}/{project_id}/memberships").json()
    assert foreign_org_user_id not in [m["user_id"] for m in memberships]


def test_add_membership_inactive_user_rejected_as_409(
    client: TestClient, project_id: int, inactive_same_org_user_id: int
):
    r = client.post(f"{PROJECTS_URL}/{project_id}/memberships", json={
        "user_id": inactive_same_org_user_id, "role_on_project": "viewer",
    })
    assert r.status_code == 409

    memberships = client.get(f"{PROJECTS_URL}/{project_id}/memberships").json()
    assert inactive_same_org_user_id not in [m["user_id"] for m in memberships]
