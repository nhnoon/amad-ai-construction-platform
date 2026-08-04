"""RC1 Phase 1 Sprint 4 — Enterprise Audit Logging tests.

audit_logs is DB-level append-only/immutable (see migration 0021's
trigger) — rows created here can never be deleted, so this file uses
WATERMARK-BASED ISOLATION (query rows with id > a watermark captured
before the action under test) rather than watermark-based CLEANUP like
every other table in tests/conftest.py. Deliberate, not an oversight —
see that file's cleanup_test_data docstring for why audit_logs is NOT in
its DELETE list (a DELETE there would itself violate the immutability
trigger and break every test's teardown).

Where a Sprint 2/3/5 test file already established a direct-service-call
pattern against a real seeded project/org (_REAL_PROJECT_ID=1, TEST_USER_ID
— see tests/test_workflow_engine.py, test_ownership_engine.py,
test_approval_engine.py), this file reuses that exact pattern rather than
re-deriving a new one: record_audit_event() fires identically whether its
caller was reached via HTTP or a direct function call, so a direct call
is just as valid a test of the actual instrumented code path.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.ai.approval_engine import approve, create_approval_request
from app.ai.ownership_engine import assign_project_risk, unassign_project_risk
from app.ai.scope import AIAuthScope, build_ai_scope
from app.ai.workflow_engine import update_project_risk
from app.core.audit_log import AuditAction, AuditEntityType, AuditResult, record_audit_event
from app.models.audit import AuditLog
from app.models.auth import UserAccount
from app.models.claims import ChangeOrder
from app.models.projects import ProjectRisk
from app.schemas.projects import ProjectRiskUpdate
from tests.conftest import TEST_USER_ID, TEST_USER_ORGANIZATION_ID, TestingSessionLocal, real_auth_client

_REAL_PROJECT_ID = 1
_ORG_A = TEST_USER_ORGANIZATION_ID

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
AUDIT_URL = "/api/v1/audit"
PASSWORD = "Testpass1!"


def _scope(user_id: int = TEST_USER_ID, org_id: int = _ORG_A, role: str = "admin") -> AIAuthScope:
    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"audit-scope-{user_id}@test.local", full_name="Audit Scope Test",
            role=role, is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        return build_ai_scope(user, db)
    finally:
        db.close()


def _watermark() -> int:
    db = TestingSessionLocal()
    try:
        return db.execute(sa.text("SELECT COALESCE(MAX(id), 0) FROM audit_logs")).scalar()
    finally:
        db.close()


def _rows_since(watermark: int) -> list[AuditLog]:
    db = TestingSessionLocal()
    try:
        return (
            db.query(AuditLog)
            .filter(AuditLog.id > watermark)
            .order_by(AuditLog.id.asc())
            .all()
        )
    finally:
        db.close()


def _register(client: TestClient, role="project_manager", password=PASSWORD) -> str:
    email = f"audit_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(REGISTER_URL, json={
        "email": email, "password": password, "full_name": "Audit Tester", "role": role,
    })
    assert r.status_code == 201, r.text
    return email


def _login(real_client: TestClient, email: str, password=PASSWORD) -> dict:
    r = real_client.post(LOGIN_URL, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _activate(real_client: TestClient, login: dict, password=PASSWORD) -> dict:
    """Clears must_change_password (Phase 2's gate) so the caller can
    reach non-exempt endpoints like GET /audit — same pattern as
    tests/test_refresh_sessions.py's own _activate helper. Returns the
    fresh login dict (change-password reissues an access token)."""
    r = real_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"current_password": password, "new_password": "Changed1!"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return {**login, "access_token": data["access_token"], "user": data["user"]}


@pytest.fixture
def risk():
    db = TestingSessionLocal()
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Audit Test Risk", status="open")
    db.add(row)
    db.commit()
    db.refresh(row)
    rid = row.id
    db.close()
    return rid


@pytest.fixture
def change_order():
    db = TestingSessionLocal()
    row = ChangeOrder(project_id=_REAL_PROJECT_ID, co_number=f"AUDIT-CO-{uuid.uuid4().hex[:6]}", description="Audit test CO", value=1000.0, status="Pending")
    db.add(row)
    db.commit()
    db.refresh(row)
    cid = row.id
    db.close()
    return cid


# ─────────────────────────────────────────────────────────────────────────
# Authentication events
# ─────────────────────────────────────────────────────────────────────────

def test_login_success_creates_audit_event(client: TestClient):
    email = _register(client)
    wm = _watermark()
    with real_auth_client() as c:
        r = c.post(LOGIN_URL, json={"email": email, "password": PASSWORD})
        assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.LOGIN and r.result == AuditResult.SUCCESS]
    assert len(matches) == 1
    assert matches[0].entity_type == AuditEntityType.USER_ACCOUNT
    assert matches[0].actor_user_id is not None
    assert matches[0].ip_address is not None


def test_login_failure_creates_audit_event(client: TestClient):
    email = _register(client)
    wm = _watermark()
    with real_auth_client() as c:
        r = c.post(LOGIN_URL, json={"email": email, "password": "wrong-password"})
        assert r.status_code == 401

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.LOGIN and r.result == AuditResult.FAILURE]
    assert len(matches) == 1
    assert matches[0].reason == "incorrect_credentials"


def test_logout_creates_audit_event(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        wm = _watermark()
        r = c.post("/api/v1/auth/logout", json={"refresh_token": login["refresh_token"]})
        assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.LOGOUT]
    assert len(matches) == 1
    assert matches[0].result == AuditResult.SUCCESS


def test_logout_all_creates_audit_event(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        wm = _watermark()
        r = c.post("/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.LOGOUT_ALL]
    assert len(matches) == 1
    assert matches[0].after_state == {"revoked_count": matches[0].after_state["revoked_count"]}


def test_refresh_creates_audit_event(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        wm = _watermark()
        r = c.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.REFRESH and r.result == AuditResult.SUCCESS]
    assert len(matches) == 1


def test_password_change_creates_audit_event(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        wm = _watermark()
        r = c.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {login['access_token']}"},
            json={"current_password": PASSWORD, "new_password": "Changed1!"},
        )
        assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.PASSWORD_CHANGE]
    assert len(matches) == 1
    assert matches[0].result == AuditResult.SUCCESS


# ─────────────────────────────────────────────────────────────────────────
# Workflow events (status change + assign/unassign)
# ─────────────────────────────────────────────────────────────────────────

def test_workflow_status_change_creates_audit_event(risk):
    wm = _watermark()
    db = TestingSessionLocal()
    update_project_risk(db, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="mitigating", mitigation="testing"))
    db.close()

    matches = [
        r for r in _rows_since(wm)
        if r.action == AuditAction.STATUS_CHANGE and r.entity_type == AuditEntityType.PROJECT_RISK and r.entity_id == risk
    ]
    assert len(matches) == 1
    assert matches[0].before_state == {"status": "open"}
    assert matches[0].after_state == {"status": "mitigating"}
    assert matches[0].project_id == _REAL_PROJECT_ID
    assert matches[0].organization_id == _ORG_A


def test_assignment_creates_audit_event(risk):
    wm = _watermark()
    db = TestingSessionLocal()
    assign_project_risk(db, _scope(), _REAL_PROJECT_ID, risk, TEST_USER_ID)
    db.close()

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.ASSIGN and r.entity_type == AuditEntityType.PROJECT_RISK]
    assert len(matches) == 1
    assert matches[0].after_state == {"owner_id": TEST_USER_ID}


def test_unassignment_creates_audit_event(risk):
    db = TestingSessionLocal()
    assign_project_risk(db, _scope(), _REAL_PROJECT_ID, risk, TEST_USER_ID)
    db.close()

    wm = _watermark()
    db = TestingSessionLocal()
    unassign_project_risk(db, _scope(), _REAL_PROJECT_ID, risk)
    db.close()

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.UNASSIGN and r.entity_type == AuditEntityType.PROJECT_RISK]
    assert len(matches) == 1
    assert matches[0].before_state == {"owner_id": TEST_USER_ID}
    assert matches[0].after_state == {"owner_id": None}


# ─────────────────────────────────────────────────────────────────────────
# Approval events
# ─────────────────────────────────────────────────────────────────────────

def test_approve_creates_audit_event(change_order):
    db = TestingSessionLocal()
    approval = create_approval_request(db, _scope(), entity_type="change_order", entity_id=change_order)
    approval_id = approval.id
    db.close()

    wm = _watermark()
    db = TestingSessionLocal()
    approve(db, _scope(), approval_id, review_note="looks good")
    db.close()

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.APPROVE and r.entity_type == AuditEntityType.APPROVAL_REQUEST]
    assert len(matches) == 1
    assert matches[0].entity_id == approval_id
    assert matches[0].reason == "looks good"
    assert matches[0].after_state == {"status": "Approved"}


# ─────────────────────────────────────────────────────────────────────────
# Document events
# ─────────────────────────────────────────────────────────────────────────

def test_document_upload_creates_audit_event(client: TestClient):
    wm = _watermark()
    r = client.post("/api/v1/documents", json={"project_id": _REAL_PROJECT_ID, "title": "Audit Doc", "doc_type": "drawing"})
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.DOCUMENT_UPLOAD and r.entity_id == doc_id]
    assert len(matches) == 1
    assert matches[0].result == AuditResult.SUCCESS


def test_document_archive_and_restore_create_audit_events(client: TestClient):
    r = client.post("/api/v1/documents", json={"project_id": _REAL_PROJECT_ID, "title": "Audit Doc 2", "doc_type": "drawing"})
    doc_id = r.json()["id"]

    wm = _watermark()
    r = client.post(f"/api/v1/documents/{doc_id}/archive")
    assert r.status_code == 200
    r = client.post(f"/api/v1/documents/{doc_id}/unarchive")
    assert r.status_code == 200

    rows = _rows_since(wm)
    archive_matches = [r for r in rows if r.action == AuditAction.DOCUMENT_ARCHIVE and r.entity_id == doc_id]
    restore_matches = [r for r in rows if r.action == AuditAction.DOCUMENT_RESTORE and r.entity_id == doc_id]
    assert len(archive_matches) == 1
    assert len(restore_matches) == 1


# ─────────────────────────────────────────────────────────────────────────
# Admin events
# ─────────────────────────────────────────────────────────────────────────

def test_user_create_creates_audit_event(client: TestClient):
    wm = _watermark()
    email = f"audit_admin_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/admin/users", json={"email": email, "full_name": "New Guy", "role": "viewer"})
    assert r.status_code == 201, r.text
    new_user_id = r.json()["user"]["id"]

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.USER_CREATE and r.entity_id == new_user_id]
    assert len(matches) == 1


def test_user_disable_creates_distinct_audit_action(client: TestClient):
    email = f"audit_disable_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/admin/users", json={"email": email, "full_name": "Disable Me", "role": "viewer"})
    user_id = r.json()["user"]["id"]

    wm = _watermark()
    r = client.patch(f"/api/v1/admin/users/{user_id}", json={"is_active": False})
    assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.entity_id == user_id]
    assert len(matches) == 1
    assert matches[0].action == AuditAction.USER_DISABLE


# ─────────────────────────────────────────────────────────────────────────
# Notification events
# ─────────────────────────────────────────────────────────────────────────

def test_notification_read_creates_audit_event(client: TestClient):
    from app.models.notifications import Notification

    db = TestingSessionLocal()
    note = Notification(
        organization_id=_ORG_A, recipient_user_id=TEST_USER_ID, event_type="assigned",
        entity_type="project_risk", entity_id=1, title="Audit test notification", message="test", severity="info",
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    note_id = note.id
    db.close()

    wm = _watermark()
    r = client.patch(f"/api/v1/notifications/{note_id}/read")
    assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.NOTIFICATION_READ and r.entity_id == note_id]
    assert len(matches) == 1


def test_notification_read_all_creates_one_summary_audit_event(client: TestClient):
    wm = _watermark()
    r = client.post("/api/v1/notifications/read-all")
    assert r.status_code == 200

    matches = [r for r in _rows_since(wm) if r.action == AuditAction.NOTIFICATION_READ_ALL]
    assert len(matches) == 1
    assert "updated_count" in matches[0].after_state


# ─────────────────────────────────────────────────────────────────────────
# Immutability / append-only
# ─────────────────────────────────────────────────────────────────────────

def test_audit_rows_cannot_be_updated():
    wm = _watermark()
    record_audit_event(entity_type="test", action="test_action", result=AuditResult.SUCCESS)
    row = _rows_since(wm)[0]

    db = TestingSessionLocal()
    with pytest.raises(Exception, match="immutable"):
        db.execute(sa.text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"), {"id": row.id})
        db.commit()
    db.rollback()
    db.close()


def test_audit_rows_cannot_be_deleted():
    wm = _watermark()
    record_audit_event(entity_type="test", action="test_action", result=AuditResult.SUCCESS)
    row = _rows_since(wm)[0]

    db = TestingSessionLocal()
    with pytest.raises(Exception, match="immutable"):
        db.execute(sa.text("DELETE FROM audit_logs WHERE id = :id"), {"id": row.id})
        db.commit()
    db.rollback()
    db.close()


def test_append_only_no_api_route_can_modify_or_delete(client: TestClient):
    """No route anywhere under /api/v1/audit accepts PATCH/PUT/DELETE —
    the query API is read-only by construction, not just by convention."""
    for method in ("patch", "put", "delete"):
        r = getattr(client, method)(f"{AUDIT_URL}/1")
        assert r.status_code in (404, 405)


# ─────────────────────────────────────────────────────────────────────────
# Failed audit persistence must never fail the business operation
# ─────────────────────────────────────────────────────────────────────────

def test_failed_audit_persistence_does_not_fail_business_operation(client: TestClient, monkeypatch):
    from app.core import audit_log as audit_log_module

    class _ExplodingSessionLocal:
        def __call__(self):
            raise RuntimeError("simulated audit DB outage")

    monkeypatch.setattr(audit_log_module, "SessionLocal", _ExplodingSessionLocal())

    # A real mutating request that would normally also write an audit
    # row — must still succeed end-to-end despite the audit layer being
    # completely broken.
    r = client.post("/api/v1/documents", json={"project_id": _REAL_PROJECT_ID, "title": "Resilience Doc", "doc_type": "drawing"})
    assert r.status_code == 201, r.text


def test_record_audit_event_never_raises_directly():
    """Direct unit check of the same guarantee, independent of any route."""
    from app.core import audit_log as audit_log_module

    original = audit_log_module.SessionLocal
    try:
        audit_log_module.SessionLocal = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        record_audit_event(entity_type="test", action="test_action", result=AuditResult.SUCCESS)  # must not raise
    finally:
        audit_log_module.SessionLocal = original


# ─────────────────────────────────────────────────────────────────────────
# Tenant isolation
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def other_organization():
    from app.models.organizations import Organization

    db = TestingSessionLocal()
    org = Organization(name=f"Audit Test Org {uuid.uuid4().hex[:6]}", slug=f"audit-test-{uuid.uuid4().hex[:8]}")
    db.add(org)
    db.commit()
    db.refresh(org)
    oid = org.id
    db.close()
    return oid


def test_query_api_never_returns_cross_tenant_events(client: TestClient, other_organization):
    """org A's admin (the shared mocked client fixture) must never see
    a DIFFERENT, real organization's audit events, even ones that exist
    in the table."""
    other_org_wm = _watermark()
    record_audit_event(
        entity_type=AuditEntityType.USER_ACCOUNT, action=AuditAction.LOGIN, result=AuditResult.SUCCESS,
        organization_id=other_organization, actor_user_id=TEST_USER_ID,
    )
    assert len(_rows_since(other_org_wm)) == 1  # sanity: the row really exists

    r = client.get(AUDIT_URL, params={"limit": 200})
    assert r.status_code == 200
    assert all(row["organization_id"] != other_organization for row in r.json())


def test_normal_user_sees_only_own_actions(client: TestClient):
    """Non-manager roles (Sprint 4's authorization design — see
    app/api/v1/audit.py's module docstring): actor is always forced to
    self, regardless of who else acted in the same organization."""
    email_a = _register(client, role="site_engineer")
    email_b = _register(client, role="site_engineer")

    with real_auth_client() as c:
        login_a = _activate(c, _login(c, email_a))
        login_b = _login(c, email_b)  # a second user's login also writes an audit row in the same org

        r = c.get(AUDIT_URL, headers={"Authorization": f"Bearer {login_a['access_token']}"}, params={"limit": 200})
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert all(row["actor_user_id"] == login_a["user"]["id"] for row in rows)
        assert not any(row["actor_user_id"] == login_b["user"]["id"] for row in rows)


def test_manager_sees_organization_wide_events(client: TestClient):
    email_engineer = _register(client, role="site_engineer")
    email_manager = _register(client, role="project_manager")

    with real_auth_client() as c:
        login_engineer = _login(c, email_engineer)
        login_manager = _activate(c, _login(c, email_manager))

        r = c.get(AUDIT_URL, headers={"Authorization": f"Bearer {login_manager['access_token']}"}, params={"limit": 200})
        assert r.status_code == 200
        actor_ids = {row["actor_user_id"] for row in r.json()}
        assert login_engineer["user"]["id"] in actor_ids
        assert login_manager["user"]["id"] in actor_ids


# ─────────────────────────────────────────────────────────────────────────
# Pagination / sorting / filters
# ─────────────────────────────────────────────────────────────────────────

def test_pagination_headers_and_limits(client: TestClient):
    for _ in range(5):
        record_audit_event(
            entity_type="test", action="pagination_test", result=AuditResult.SUCCESS,
            organization_id=_ORG_A, actor_user_id=TEST_USER_ID,
        )
    r = client.get(AUDIT_URL, params={"action": "pagination_test", "limit": 2, "skip": 0})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert int(r.headers["X-Total-Count"]) >= 5
    assert r.headers["X-Limit"] == "2"
    assert r.headers["X-Offset"] == "0"

    r2 = client.get(AUDIT_URL, params={"action": "pagination_test", "limit": 2, "skip": 2})
    assert r2.status_code == 200
    ids_page1 = {row["id"] for row in r.json()}
    ids_page2 = {row["id"] for row in r2.json()}
    assert ids_page1.isdisjoint(ids_page2)


def test_sorting_ascending_and_descending(client: TestClient):
    # audit_logs is permanent (append-only — see module docstring), so a
    # fixed literal action name would accumulate rows across repeated
    # test runs and could exceed `limit` below, silently comparing two
    # DIFFERENT windows instead of the same rows in reverse order. A
    # unique-per-run action name keeps this test run self-contained.
    action = f"sort_test_{uuid.uuid4().hex[:8]}"
    for i in range(3):
        record_audit_event(
            entity_type="test", action=action, result=AuditResult.SUCCESS,
            organization_id=_ORG_A, actor_user_id=TEST_USER_ID, entity_id=i,
        )
    r_desc = client.get(AUDIT_URL, params={"action": action, "sort_by": "timestamp", "sort_order": "desc", "limit": 10})
    r_asc = client.get(AUDIT_URL, params={"action": action, "sort_by": "timestamp", "sort_order": "asc", "limit": 10})
    assert r_desc.status_code == 200 and r_asc.status_code == 200
    ids_desc = [row["id"] for row in r_desc.json()]
    ids_asc = [row["id"] for row in r_asc.json()]
    assert ids_desc == list(reversed(ids_asc))


def test_filters_by_action_and_result(client: TestClient):
    record_audit_event(
        entity_type="test", action="filter_test_a", result=AuditResult.SUCCESS,
        organization_id=_ORG_A, actor_user_id=TEST_USER_ID,
    )
    record_audit_event(
        entity_type="test", action="filter_test_b", result=AuditResult.FAILURE,
        organization_id=_ORG_A, actor_user_id=TEST_USER_ID,
    )
    r = client.get(AUDIT_URL, params={"action": "filter_test_a"})
    assert r.status_code == 200
    assert all(row["action"] == "filter_test_a" for row in r.json())
    assert len(r.json()) >= 1

    r2 = client.get(AUDIT_URL, params={"result": "failure", "action": "filter_test_b"})
    assert r2.status_code == 200
    assert all(row["result"] == "failure" for row in r2.json())


def test_filter_by_entity_type_and_entity_id(client: TestClient):
    # Unique-per-run entity_type (see test_sorting_ascending_and_descending's
    # comment on why a fixed literal would accumulate across runs).
    entity_type = f"filter_entity_test_{uuid.uuid4().hex[:8]}"
    record_audit_event(
        entity_type=entity_type, action="x", result=AuditResult.SUCCESS,
        organization_id=_ORG_A, actor_user_id=TEST_USER_ID, entity_id=424242,
    )
    r = client.get(AUDIT_URL, params={"entity_type": entity_type, "entity_id": 424242})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["entity_id"] == 424242


def test_filter_by_project_id(client: TestClient):
    record_audit_event(
        entity_type="test", action="project_filter_test", result=AuditResult.SUCCESS,
        organization_id=_ORG_A, actor_user_id=TEST_USER_ID, project_id=_REAL_PROJECT_ID,
    )
    r = client.get(AUDIT_URL, params={"project_id": _REAL_PROJECT_ID, "action": "project_filter_test"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert all(row["project_id"] == _REAL_PROJECT_ID for row in r.json())


def test_filter_by_date_range(client: TestClient):
    wm = _watermark()
    record_audit_event(
        entity_type="test", action="date_range_test", result=AuditResult.SUCCESS,
        organization_id=_ORG_A, actor_user_id=TEST_USER_ID,
    )
    created = _rows_since(wm)[0]

    future = (created.created_at.replace(year=created.created_at.year + 1)).isoformat()
    r = client.get(AUDIT_URL, params={"action": "date_range_test", "start_date": future})
    assert r.status_code == 200
    assert r.json() == []

    past = (created.created_at.replace(year=created.created_at.year - 1)).isoformat()
    r2 = client.get(AUDIT_URL, params={"action": "date_range_test", "start_date": past})
    assert r2.status_code == 200
    assert len(r2.json()) >= 1
