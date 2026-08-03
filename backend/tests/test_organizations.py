import uuid
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.deps import get_current_user
from app.models.auth import UserAccount


ORGS_URL = "/api/v1/admin/organizations"


def _viewer_override():
    def _user():
        return UserAccount(
            id=880, email="viewer@test.ai", role="viewer", is_active=True,
            hashed_password="x", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    return _user


def test_list_organizations_as_admin(client: TestClient):
    r = client.get(ORGS_URL)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_organization(client: TestClient):
    slug = f"test-org-{uuid.uuid4().hex[:6]}"
    r = client.post(ORGS_URL, json={"name": "Test Construction Co.", "slug": slug})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Construction Co."
    assert data["slug"] == slug
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_create_organization_duplicate_slug(client: TestClient):
    slug = f"dup-{uuid.uuid4().hex[:6]}"
    client.post(ORGS_URL, json={"name": "Org A", "slug": slug})
    r = client.post(ORGS_URL, json={"name": "Org B", "slug": slug})
    assert r.status_code == 409


def test_create_organization_invalid_slug(client: TestClient):
    r = client.post(ORGS_URL, json={"name": "Bad Slug", "slug": "Invalid Slug!"})
    assert r.status_code == 422


def test_get_organization(client: TestClient):
    slug = f"get-{uuid.uuid4().hex[:6]}"
    created = client.post(ORGS_URL, json={"name": "Get Test Org", "slug": slug}).json()
    r = client.get(f"{ORGS_URL}/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]
    assert r.json()["slug"] == slug


def test_get_organization_not_found(client: TestClient):
    r = client.get(f"{ORGS_URL}/999999")
    assert r.status_code == 404


def test_update_organization_name(client: TestClient):
    slug = f"upd-{uuid.uuid4().hex[:6]}"
    created = client.post(ORGS_URL, json={"name": "Before", "slug": slug}).json()
    r = client.patch(f"{ORGS_URL}/{created['id']}", json={"name": "After"})
    assert r.status_code == 200
    assert r.json()["name"] == "After"
    assert r.json()["slug"] == slug


def test_update_organization_deactivate(client: TestClient):
    slug = f"deact-{uuid.uuid4().hex[:6]}"
    created = client.post(ORGS_URL, json={"name": "Active Org", "slug": slug}).json()
    r = client.patch(f"{ORGS_URL}/{created['id']}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False


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
