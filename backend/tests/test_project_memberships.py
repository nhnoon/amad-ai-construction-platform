import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.deps import get_current_user
from app.models.auth import UserAccount
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
