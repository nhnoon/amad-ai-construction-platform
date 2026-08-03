"""Tests for admin/organizations.py tenant scoping (RC1 Phase 0 — Security
Remediation, Finding 1).

Before this fix, every handler on this router ignored the caller's own
organization entirely: any tenant's "admin" could list, read, rename,
re-slug, or deactivate ANY organization on the platform. These tests
verify the fix — own-organization access works, foreign-organization
access is hidden as 404, and organization creation (never something a
tenant admin should be able to trigger) is no longer exposed at all.

A second, throwaway organization is created directly via the DB (not
through this router — POST is intentionally gone) for the cross-tenant
checks, with guaranteed cleanup via a fixture finalizer.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.deps import get_current_user, get_current_scope
from app.ai.scope import AIAuthScope
from app.models.auth import UserAccount
from app.models.organizations import Organization
from tests.conftest import TestingSessionLocal, TEST_USER_ORGANIZATION_ID


ORGS_URL = "/api/v1/admin/organizations"


def _viewer_override():
    def _user():
        return UserAccount(
            id=880, email="viewer@test.ai", role="viewer", is_active=True,
            hashed_password="x", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    return _user


@pytest.fixture(scope="module")
def own_org_id() -> int:
    assert TEST_USER_ORGANIZATION_ID is not None, (
        "seeded admin@construction.ai must have an organization_id for these tests"
    )
    return TEST_USER_ORGANIZATION_ID


@pytest.fixture(scope="module")
def foreign_org_id():
    """A throwaway organization the mocked admin test user does NOT belong
    to. Created directly via the DB, since org creation is intentionally
    no longer exposed on this router — see
    test_create_organization_endpoint_no_longer_exists below. Cleaned up
    unconditionally."""
    db = TestingSessionLocal()
    org = Organization(
        name="RC1 Foreign Org",
        slug=f"rc1-foreign-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    org_id = org.id
    db.close()

    yield org_id

    db = TestingSessionLocal()
    db.query(Organization).filter(Organization.id == org_id).delete()
    db.commit()
    db.close()


def test_list_organizations_returns_only_own_org(client: TestClient, own_org_id: int, foreign_org_id: int):
    r = client.get(ORGS_URL)
    assert r.status_code == 200
    ids = [o["id"] for o in r.json()]
    assert ids == [own_org_id]
    assert foreign_org_id not in ids


def test_get_own_organization_succeeds(client: TestClient, own_org_id: int):
    r = client.get(f"{ORGS_URL}/{own_org_id}")
    assert r.status_code == 200
    assert r.json()["id"] == own_org_id


def test_get_foreign_organization_returns_404(client: TestClient, foreign_org_id: int):
    r = client.get(f"{ORGS_URL}/{foreign_org_id}")
    assert r.status_code == 404


def test_get_organization_not_found(client: TestClient):
    r = client.get(f"{ORGS_URL}/999999")
    assert r.status_code == 404


def test_update_own_organization_name(client: TestClient, own_org_id: int):
    original_name = client.get(f"{ORGS_URL}/{own_org_id}").json()["name"]
    try:
        r = client.patch(f"{ORGS_URL}/{own_org_id}", json={"name": "Amad Demo (RC1 test)"})
        assert r.status_code == 200
        assert r.json()["name"] == "Amad Demo (RC1 test)"
    finally:
        # restore -- this is a shared, real seeded org other tests may rely on
        client.patch(f"{ORGS_URL}/{own_org_id}", json={"name": original_name})


def test_update_foreign_organization_returns_404_and_does_not_modify(client: TestClient, foreign_org_id: int):
    r = client.patch(f"{ORGS_URL}/{foreign_org_id}", json={"name": "Hijacked", "is_active": False})
    assert r.status_code == 404

    db = TestingSessionLocal()
    org = db.query(Organization).filter(Organization.id == foreign_org_id).first()
    db.close()
    assert org.name == "RC1 Foreign Org"
    assert org.is_active is True


def test_create_organization_endpoint_no_longer_exists(client: TestClient):
    r = client.post(ORGS_URL, json={"name": "New Tenant", "slug": f"new-tenant-{uuid.uuid4().hex[:6]}"})
    # POST is not registered on this router at all anymore -- 405 (path
    # matches other methods) is the expected FastAPI/Starlette behavior;
    # 404 is also accepted in case routing details change. A 2xx/201 would
    # mean a tenant admin can still provision another tenant, which this
    # test exists specifically to prevent regressing.
    assert r.status_code in (404, 405)


def test_non_admin_cannot_access_organizations(client: TestClient):
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _viewer_override()
    try:
        r = client.get(ORGS_URL)
        assert r.status_code == 403
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        elif get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


def _no_org_admin_scope() -> AIAuthScope:
    return AIAuthScope(
        organization_id=None, user_id=999999, user_role="admin",
        accessible_project_ids=(), project_membership_roles={},
    )


def test_admin_with_no_organization_sees_empty_list_not_every_org(client: TestClient, foreign_org_id: int):
    """Edge case: an admin whose own account has organization_id=None must
    get an empty list -- never a platform-wide list of every organization,
    which would recreate the exact bug this sprint fixes."""
    original = app.dependency_overrides.get(get_current_scope)
    app.dependency_overrides[get_current_scope] = _no_org_admin_scope
    try:
        r = client.get(ORGS_URL)
        assert r.status_code == 200
        assert r.json() == []
    finally:
        if original is not None:
            app.dependency_overrides[get_current_scope] = original
        elif get_current_scope in app.dependency_overrides:
            del app.dependency_overrides[get_current_scope]


def test_admin_with_no_organization_cannot_reach_foreign_org_by_id(client: TestClient, foreign_org_id: int):
    original = app.dependency_overrides.get(get_current_scope)
    app.dependency_overrides[get_current_scope] = _no_org_admin_scope
    try:
        r = client.get(f"{ORGS_URL}/{foreign_org_id}")
        assert r.status_code == 404
    finally:
        if original is not None:
            app.dependency_overrides[get_current_scope] = original
        elif get_current_scope in app.dependency_overrides:
            del app.dependency_overrides[get_current_scope]
