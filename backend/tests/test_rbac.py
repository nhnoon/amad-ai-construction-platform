"""
RBAC enforcement tests.

Verifies that:
- All authenticated users (any role) can access dashboard and projects.
- Procurement endpoints return 403 for site_engineer and safety_quality_officer.
- Safety endpoints return 403 for procurement_officer.
- Site reports return 403 for procurement_officer and safety_quality_officer.
- Meetings return 403 for site_engineer, procurement_officer, safety_quality_officer.
- Unauthenticated requests return 401.
- Admin always passes.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.deps import get_current_user
from app.models.auth import UserAccount
from app.models.organizations import ProjectMembership
from tests.conftest import TEST_USER_ORGANIZATION_ID, TestingSessionLocal

# admin/executive/project_manager are global-read within their own
# organization (see app/ai/scope.py) — organization_id alone is enough for
# them. Every other role is membership-scoped: it only sees projects it has
# an explicit ProjectMembership on, exactly like a real user would need to
# be assigned to a project before seeing its data. Project 1 is a real
# seeded project belonging to the same demo organization.
_GLOBAL_READ_ROLES = {"admin", "executive", "project_manager"}
_MEMBERSHIP_TEST_PROJECT_ID = 1


def _make_user(role: str) -> UserAccount:
    """Phase 1 regression fix: assign the real seeded demo organization's
    id, same as tests/conftest.py's shared admin override. Without it,
    build_ai_scope() correctly gives global-read roles (admin/executive/
    project_manager) zero accessible projects — organization_id is the
    real source of truth now, not the role name alone."""
    return UserAccount(
        id=8000 + hash(role) % 1000,
        email=f"rbac_test_{role}@construction.ai",
        full_name=f"RBAC Test {role}",
        role=role,
        is_active=True,
        hashed_password="x",
        organization_id=TEST_USER_ORGANIZATION_ID,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _ensure_membership_gated_role_can_see_project_1(user: UserAccount) -> None:
    """Membership-scoped roles (everything except admin/executive/
    project_manager) need a real ProjectMembership row to see anything —
    organization_id alone doesn't grant them access, by design (see
    app/ai/scope.py::build_ai_scope). Persist the transient test user and
    give it a real membership on the real seeded project 1, so the
    "allowed" tests below exercise real (not bypassed) authorization
    logic instead of relying on a role-name shortcut. Idempotent — safe
    to call once per test."""
    if user.role in _GLOBAL_READ_ROLES:
        return
    db = TestingSessionLocal()
    try:
        # hash(role) is randomized per-process (PYTHONHASHSEED), so a row
        # left over from an earlier, differently-seeded test run can share
        # this email with a different id — clear it first so the insert
        # below is idempotent across runs, not just within one.
        db.query(UserAccount).filter(
            UserAccount.email == user.email, UserAccount.id != user.id,
        ).delete(synchronize_session=False)
        db.commit()
        existing_user = db.query(UserAccount).filter(UserAccount.id == user.id).first()
        if existing_user is None:
            db.add(UserAccount(
                id=user.id, email=user.email, full_name=user.full_name,
                role=user.role, is_active=True, hashed_password="x",
                organization_id=user.organization_id,
            ))
            db.flush()
        existing_membership = db.query(ProjectMembership).filter(
            ProjectMembership.user_id == user.id,
            ProjectMembership.project_id == _MEMBERSHIP_TEST_PROJECT_ID,
        ).first()
        if existing_membership is None:
            db.add(ProjectMembership(
                user_id=user.id, project_id=_MEMBERSHIP_TEST_PROJECT_ID,
                role_on_project=user.role, is_active=True,
            ))
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def raw_client_no_override():
    """TestClient with NO dependency overrides — tests real RBAC enforcement."""
    saved = app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        yield c
    if saved is not None:
        app.dependency_overrides[get_current_user] = saved


@pytest.fixture(scope="module", autouse=True)
def _cleanup_rbac_test_users():
    yield
    db = TestingSessionLocal()
    try:
        # ProjectMembership rows cascade-delete with their user (ondelete="CASCADE").
        db.query(UserAccount).filter(UserAccount.email.like("rbac_test_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _client_for_role(role: str) -> TestClient:
    """Create a TestClient that acts as a user with the given role."""
    user = _make_user(role)
    _ensure_membership_gated_role_can_see_project_1(user)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ── Unauthenticated → 401 ─────────────────────────────────────────────────────

def test_unauthenticated_dashboard_returns_401(raw_client_no_override: TestClient):
    r = raw_client_no_override.get("/api/v1/dashboard/summary")
    assert r.status_code == 401


def test_unauthenticated_projects_returns_401(raw_client_no_override: TestClient):
    r = raw_client_no_override.get("/api/v1/projects")
    assert r.status_code == 401


def test_unauthenticated_procurement_returns_401(raw_client_no_override: TestClient):
    r = raw_client_no_override.get("/api/v1/procurement/purchase-requests")
    assert r.status_code == 401


def test_unauthenticated_safety_returns_401(raw_client_no_override: TestClient):
    r = raw_client_no_override.get("/api/v1/projects/1/safety-events")
    assert r.status_code == 401


# ── Admin passes everywhere ───────────────────────────────────────────────────

def test_admin_can_access_dashboard():
    with _client_for_role("admin") as c:
        assert c.get("/api/v1/dashboard/summary").status_code == 200


def test_admin_can_access_procurement():
    with _client_for_role("admin") as c:
        assert c.get("/api/v1/procurement/purchase-requests").status_code == 200


def test_admin_can_access_safety():
    with _client_for_role("admin") as c:
        assert c.get("/api/v1/projects/1/safety-events").status_code == 200


def test_admin_can_access_site_reports():
    with _client_for_role("admin") as c:
        assert c.get("/api/v1/projects/1/site-reports").status_code == 200


def test_admin_can_access_meetings():
    with _client_for_role("admin") as c:
        assert c.get("/api/v1/projects/1/meetings").status_code == 200


# ── Dashboard — all roles allowed ────────────────────────────────────────────

@pytest.mark.parametrize("role", [
    "executive", "project_manager", "site_engineer",
    "procurement_officer", "safety_quality_officer", "viewer",
])
def test_dashboard_accessible_by_all_authenticated_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/dashboard/summary")
        assert r.status_code == 200, f"Role '{role}' should access dashboard, got {r.status_code}"


# ── Projects — all roles allowed ─────────────────────────────────────────────

@pytest.mark.parametrize("role", [
    "executive", "project_manager", "site_engineer",
    "procurement_officer", "safety_quality_officer", "viewer",
])
def test_projects_accessible_by_all_authenticated_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects")
        assert r.status_code == 200, f"Role '{role}' should access projects, got {r.status_code}"


# ── Procurement — restricted ──────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["executive", "project_manager", "procurement_officer"])
def test_procurement_allowed_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/procurement/purchase-requests")
        assert r.status_code == 200, f"Role '{role}' should access procurement, got {r.status_code}"


@pytest.mark.parametrize("role", ["site_engineer", "safety_quality_officer", "viewer"])
def test_procurement_denied_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/procurement/purchase-requests")
        assert r.status_code == 403, f"Role '{role}' should be denied procurement, got {r.status_code}"


# ── Safety & NCR — restricted ─────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["executive", "project_manager", "safety_quality_officer"])
def test_safety_allowed_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects/1/safety-events")
        assert r.status_code == 200, f"Role '{role}' should access safety, got {r.status_code}"


@pytest.mark.parametrize("role", ["procurement_officer", "site_engineer", "viewer"])
def test_safety_denied_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects/1/safety-events")
        assert r.status_code == 403, f"Role '{role}' should be denied safety, got {r.status_code}"


# ── Site reports — restricted ─────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["executive", "project_manager", "site_engineer"])
def test_site_reports_allowed_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects/1/site-reports")
        assert r.status_code == 200, f"Role '{role}' should access site reports, got {r.status_code}"


@pytest.mark.parametrize("role", ["procurement_officer", "safety_quality_officer", "viewer"])
def test_site_reports_denied_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects/1/site-reports")
        assert r.status_code == 403, f"Role '{role}' should be denied site reports, got {r.status_code}"


# ── Meetings — restricted ─────────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["executive", "project_manager"])
def test_meetings_allowed_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects/1/meetings")
        assert r.status_code == 200, f"Role '{role}' should access meetings, got {r.status_code}"


@pytest.mark.parametrize("role", ["site_engineer", "procurement_officer", "safety_quality_officer", "viewer"])
def test_meetings_denied_roles(role: str):
    with _client_for_role(role) as c:
        r = c.get("/api/v1/projects/1/meetings")
        assert r.status_code == 403, f"Role '{role}' should be denied meetings, got {r.status_code}"


# ── Procurement summary ───────────────────────────────────────────────────────

def test_procurement_summary_returns_counts():
    with _client_for_role("procurement_officer") as c:
        r = c.get("/api/v1/procurement/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_purchase_requests" in data
        assert "total_purchase_orders" in data
        assert data["total_purchase_requests"] > 0
        assert data["total_purchase_orders"] > 0


# ── Pagination headers ────────────────────────────────────────────────────────

def test_purchase_requests_returns_total_count_header():
    with _client_for_role("procurement_officer") as c:
        r = c.get("/api/v1/procurement/purchase-requests?limit=5")
        assert r.status_code == 200
        assert "x-total-count" in r.headers
        assert int(r.headers["x-total-count"]) > 5


def test_purchase_orders_returns_total_count_header():
    with _client_for_role("procurement_officer") as c:
        r = c.get("/api/v1/procurement/purchase-orders?limit=5")
        assert r.status_code == 200
        assert "x-total-count" in r.headers
        assert int(r.headers["x-total-count"]) > 5


def test_403_response_has_detail_field():
    """403 responses must include a detail field — not a raw exception."""
    with _client_for_role("viewer") as c:
        r = c.get("/api/v1/procurement/purchase-requests")
        assert r.status_code == 403
        assert "detail" in r.json()
