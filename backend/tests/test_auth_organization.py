"""Phase 1 production-hardening — /auth/register organization assignment.

Public self-registration is disabled by design (see app/api/v1/auth.py);
this endpoint is an admin-only, admin-created-user flow. A newly created
user must always inherit the creating admin's own organization_id — never
left unset (which would silently orphan the account with zero access once
organization scoping is enforced) and never client-suppliable (there is no
organization_id field on UserRegister at all).
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.models.auth import UserAccount
from app.models.organizations import Organization
from app.models.projects import Project
from tests.conftest import (
    TEST_USER_ORGANIZATION_ID, TestingSessionLocal, override_get_current_user, real_auth_client,
)

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def _transient_admin(user_id: int, org_id: "int | None") -> UserAccount:
    return UserAccount(
        id=user_id, email=f"org-admin-{user_id}@test.local", full_name="Org Test Admin",
        role="admin", is_active=True, hashed_password="x", organization_id=org_id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@contextmanager
def _as_user(user: UserAccount):
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def cleanup_users():
    created_emails: list[str] = []
    yield created_emails
    if created_emails:
        db = TestingSessionLocal()
        db.query(UserAccount).filter(UserAccount.email.in_(created_emails)).delete(synchronize_session=False)
        db.commit()
        db.close()


class TestNewUserInheritsCreatorOrganization:
    def test_new_user_inherits_creator_organization_id(self, client: TestClient, cleanup_users):
        email = f"inherit-org-{uuid.uuid4().hex[:8]}@example.com"
        cleanup_users.append(email)
        resp = client.post(REGISTER_URL, json={
            "email": email, "password": "Testpass1!", "role": "site_engineer",
        })
        assert resp.status_code == 201
        assert resp.json()["organization_id"] == TEST_USER_ORGANIZATION_ID

        db = TestingSessionLocal()
        try:
            row = db.query(UserAccount).filter(UserAccount.email == email).first()
            assert row.organization_id == TEST_USER_ORGANIZATION_ID
        finally:
            db.close()


class TestOrganizationIdCannotBeOverridden:
    def test_organization_id_in_request_body_is_ignored(self, client: TestClient, cleanup_users):
        email = f"override-attempt-{uuid.uuid4().hex[:8]}@example.com"
        cleanup_users.append(email)
        resp = client.post(REGISTER_URL, json={
            "email": email, "password": "Testpass1!", "role": "site_engineer",
            "organization_id": 999_999,  # not a real UserRegister field — must not override anything
        })
        assert resp.status_code == 201
        # Still the creator's own organization, never the attempted value.
        assert resp.json()["organization_id"] == TEST_USER_ORGANIZATION_ID
        assert resp.json()["organization_id"] != 999_999


class TestCreatorWithNoOrganizationCannotCreateUser:
    def test_admin_with_no_organization_is_rejected(self, cleanup_users):
        admin_without_org = _transient_admin(999_999_101, org_id=None)
        with _as_user(admin_without_org):
            with TestClient(app) as c:
                resp = c.post(REGISTER_URL, json={
                    "email": "should-not-be-created@example.com",
                    "password": "Testpass1!", "role": "site_engineer",
                })
        assert resp.status_code == 400
        assert "organization" in resp.json()["detail"].lower()

        db = TestingSessionLocal()
        try:
            row = db.query(UserAccount).filter(UserAccount.email == "should-not-be-created@example.com").first()
            assert row is None
        finally:
            db.close()


class TestNewUserCanOnlyAccessOwnOrganizationData:
    def test_new_user_cannot_see_another_organizations_project(self, client: TestClient, cleanup_users):
        # A second, disposable organization + project — deliberately never
        # linked to the new user, to prove org-scoping actually applies to
        # a freshly created account, not just the seeded demo users.
        db = TestingSessionLocal()
        other_org = Organization(name="Register Isolation Test Org", slug=f"register-iso-{uuid.uuid4().hex[:8]}", is_active=True)
        db.add(other_org)
        db.flush()
        other_project = Project(
            organization_id=other_org.id, project_code=f"REG-ISO-{uuid.uuid4().hex[:6]}",
            project_name="Register Isolation Tower", project_type="Commercial",
            client_name="Test Client", city="Test City", start_date="2026-01-01",
            planned_finish="2026-12-31", status="Active", budget=1_000_000.0,
        )
        db.add(other_project)
        db.commit()
        other_org_id, other_project_id = other_org.id, other_project.id

        email = f"new-user-scope-{uuid.uuid4().hex[:8]}@example.com"
        password = "Testpass1!"
        cleanup_users.append(email)
        try:
            resp = client.post(REGISTER_URL, json={
                "email": email, "password": password, "role": "project_manager",
            })
            assert resp.status_code == 201
            assert resp.json()["organization_id"] == TEST_USER_ORGANIZATION_ID
            assert resp.json()["organization_id"] != other_org_id

            with real_auth_client() as raw:
                login_resp = raw.post(LOGIN_URL, json={"email": email, "password": password})
                assert login_resp.status_code == 200
                token = login_resp.json()["access_token"]

                # Phase 2 — Security & Authentication Hardening: a freshly
                # registered user must change their password before
                # accessing anything else (see tests/test_password_change.py
                # for dedicated coverage of that gate) — complete it here so
                # this test can exercise the actual project-isolation check
                # it's named for.
                change_resp = raw.post(
                    "/api/v1/auth/change-password",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"current_password": password, "new_password": "Changed1!"},
                )
                assert change_resp.status_code == 200
                token = change_resp.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                projects_resp = raw.get("/api/v1/projects", headers=headers)
                assert projects_resp.status_code == 200
                visible_ids = {p["id"] for p in projects_resp.json()}
                assert other_project_id not in visible_ids

                direct_resp = raw.get(f"/api/v1/projects/{other_project_id}", headers=headers)
                assert direct_resp.status_code in (403, 404)
        finally:
            db.query(Project).filter(Project.id == other_project_id).delete(synchronize_session=False)
            db.query(Organization).filter(Organization.id == other_org_id).delete(synchronize_session=False)
            db.commit()
            db.close()
