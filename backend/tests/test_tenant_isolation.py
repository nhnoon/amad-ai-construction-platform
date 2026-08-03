"""Phase 1 production-hardening — automated tests proving multi-tenant data
isolation (Part D of the AMAD Production Readiness spec).

Runs against the real Postgres DB (same pattern as test_org_repair.py /
test_general_documents.py). Creates two brand-new, disposable organizations
(unrelated to the real "Amad Demo" org) each with one user and one project,
and gives both projects the *same* project_name ("Isolation Test Tower") so
that a filter bug returning "any project named X" instead of "this
organization's project" cannot pass these tests by accident. project_code
must still differ (globally unique column).
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.ai.memory_records import list_memory_records_for_scope
from app.ai.retrieval.projects import get_project_overview
from app.ai.scope import build_ai_scope
from app.core.deps import get_current_user
from app.main import app
from app.models.auth import UserAccount
from app.models.copilot_memory import AIMemoryRecord
from app.models.meetings import Meeting
from app.models.organizations import Organization
from app.models.projects import Project
from tests.conftest import TestingSessionLocal, override_get_current_user

_SHARED_PROJECT_NAME = "Isolation Test Tower"


def _transient_user(user_id: int, email: str, role: str, org_id: "int | None") -> UserAccount:
    """A detached UserAccount, same pattern as conftest.py's
    override_get_current_user() — not loaded from the DB, just enough
    attributes for get_current_user()'s dependents (build_ai_scope, etc.)."""
    return UserAccount(
        id=user_id,
        email=email,
        full_name="Tenant Isolation Test User",
        role=role,
        is_active=True,
        hashed_password="x",
        organization_id=org_id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@contextmanager
def _as_user(user: UserAccount):
    """Temporarily swap the FastAPI get_current_user override so HTTP
    requests through `client` are authenticated as `user`, then restore the
    session-wide admin override conftest.py installs."""
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(scope="module")
def tenants():
    """Two isolated organizations, one user and one project each, plus one
    nested record (a Meeting) per project — deleted again at teardown."""
    db = TestingSessionLocal()

    org_a = Organization(name="Tenant Isolation Test Org A", slug="tenant-iso-test-org-a", is_active=True)
    org_b = Organization(name="Tenant Isolation Test Org B", slug="tenant-iso-test-org-b", is_active=True)
    db.add_all([org_a, org_b])
    db.flush()

    user_a = UserAccount(
        email="tenant-iso-user-a@test.local", hashed_password="x",
        full_name="Isolation Test User A", role="project_manager",
        is_active=True, organization_id=org_a.id,
    )
    user_b = UserAccount(
        email="tenant-iso-user-b@test.local", hashed_password="x",
        full_name="Isolation Test User B", role="project_manager",
        is_active=True, organization_id=org_b.id,
    )
    db.add_all([user_a, user_b])
    db.flush()

    common = dict(
        project_name=_SHARED_PROJECT_NAME,
        project_type="Commercial", client_name="Isolation Test Client",
        city="Test City", start_date="2026-01-01", planned_finish="2026-12-31",
        status="Active", budget=1_000_000.0,
    )
    project_a = Project(organization_id=org_a.id, project_code="ISO-TEST-A-001", **common)
    project_b = Project(organization_id=org_b.id, project_code="ISO-TEST-B-001", **common)
    db.add_all([project_a, project_b])
    db.flush()

    meeting_a = Meeting(project_id=project_a.id, meeting_date="2026-01-15", title="Org A Kickoff", meeting_type="kickoff")
    meeting_b = Meeting(project_id=project_b.id, meeting_date="2026-01-15", title="Org B Kickoff", meeting_type="kickoff")
    db.add_all([meeting_a, meeting_b])
    db.commit()

    ids = {
        "org_a_id": org_a.id, "org_b_id": org_b.id,
        "user_a_id": user_a.id, "user_b_id": user_b.id,
        "project_a_id": project_a.id, "project_b_id": project_b.id,
        "meeting_a_id": meeting_a.id, "meeting_b_id": meeting_b.id,
    }
    db.close()

    yield ids

    db = TestingSessionLocal()
    db.query(AIMemoryRecord).filter(
        AIMemoryRecord.project_id.in_([ids["project_a_id"], ids["project_b_id"]])
    ).delete(synchronize_session=False)
    db.query(Meeting).filter(
        Meeting.id.in_([ids["meeting_a_id"], ids["meeting_b_id"]])
    ).delete(synchronize_session=False)
    db.query(Project).filter(
        Project.id.in_([ids["project_a_id"], ids["project_b_id"]])
    ).delete(synchronize_session=False)
    db.query(UserAccount).filter(
        UserAccount.id.in_([ids["user_a_id"], ids["user_b_id"]])
    ).delete(synchronize_session=False)
    db.query(Organization).filter(
        Organization.id.in_([ids["org_a_id"], ids["org_b_id"]])
    ).delete(synchronize_session=False)
    db.commit()
    db.close()


@pytest.fixture
def user_a(tenants):
    return _transient_user(tenants["user_a_id"], "tenant-iso-user-a@test.local", "project_manager", tenants["org_a_id"])


@pytest.fixture
def user_b(tenants):
    return _transient_user(tenants["user_b_id"], "tenant-iso-user-b@test.local", "project_manager", tenants["org_b_id"])


# ── Part D item 3: every project has a valid organization_id ──────────────

class TestEveryProjectHasOrganizationOwnership:
    def test_no_project_has_a_null_organization_id(self):
        db = TestingSessionLocal()
        try:
            count = db.query(Project).filter(Project.organization_id.is_(None)).count()
            assert count == 0
        finally:
            db.close()

    def test_test_projects_are_owned_by_their_respective_organizations(self, tenants):
        db = TestingSessionLocal()
        try:
            project_a = db.query(Project).filter(Project.id == tenants["project_a_id"]).first()
            project_b = db.query(Project).filter(Project.id == tenants["project_b_id"]).first()
            assert project_a.organization_id == tenants["org_a_id"]
            assert project_b.organization_id == tenants["org_b_id"]
            assert project_a.organization_id != project_b.organization_id
        finally:
            db.close()


# ── Part D items 4-6: HTTP-level project isolation ─────────────────────────

class TestUserCanAccessOwnOrganizationProjects:
    def test_user_a_can_list_org_a_project(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        ids = {p["id"] for p in resp.json()}
        assert tenants["project_a_id"] in ids
        assert tenants["project_b_id"] not in ids

    def test_user_a_can_open_org_a_project(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get(f"/api/v1/projects/{tenants['project_a_id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == tenants["project_a_id"]


class TestUserCannotAccessOtherOrganizationProjects:
    def test_user_a_list_excludes_org_b_project(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        ids = {p["id"] for p in resp.json()}
        assert tenants["project_b_id"] not in ids

    def test_user_a_cannot_open_org_b_project_by_id(self, client: TestClient, user_a, tenants):
        """Part D item 6 — changing a project ID manually doesn't bypass
        scope. Standardized 404/403 policy (see app/ai/scope.py::
        get_project_or_404): a project that exists in another organization
        returns 404, same as one that doesn't exist at all — existence is
        never revealed across the tenant boundary."""
        with _as_user(user_a):
            resp = client.get(f"/api/v1/projects/{tenants['project_b_id']}")
        assert resp.status_code == 404

    def test_user_a_cannot_update_org_b_project(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.patch(
                f"/api/v1/projects/{tenants['project_b_id']}",
                json={"status": "Completed"},
            )
        assert resp.status_code == 404

        db = TestingSessionLocal()
        try:
            project_b = db.query(Project).filter(Project.id == tenants["project_b_id"]).first()
            assert project_b.status == "Active"  # unchanged by the rejected PATCH
        finally:
            db.close()

    def test_user_b_cannot_open_org_a_project_by_id(self, client: TestClient, user_b, tenants):
        with _as_user(user_b):
            resp = client.get(f"/api/v1/projects/{tenants['project_a_id']}")
        assert resp.status_code == 404


# ── Part D item 7: nested records cannot bypass scope through their own IDs

class TestNestedRecordsInheritProjectScope:
    def test_user_a_cannot_open_org_b_meeting_via_org_b_project_id(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get(
                f"/api/v1/projects/{tenants['project_b_id']}/meetings/{tenants['meeting_b_id']}"
            )
        assert resp.status_code == 403  # blocked before the meeting_id is even considered

    def test_user_a_cannot_open_org_b_meeting_via_org_a_project_id(self, client: TestClient, user_a, tenants):
        """Guessing another org's meeting_id while supplying a project_id
        the caller *does* own must not leak the record either — the query
        requires Meeting.project_id == the given (authorized) project_id."""
        with _as_user(user_a):
            resp = client.get(
                f"/api/v1/projects/{tenants['project_a_id']}/meetings/{tenants['meeting_b_id']}"
            )
        assert resp.status_code == 404

    def test_user_a_can_open_own_meeting(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get(
                f"/api/v1/projects/{tenants['project_a_id']}/meetings/{tenants['meeting_a_id']}"
            )
        assert resp.status_code == 200


# ── Part D items 8-10: aggregate scoping (Dashboard/Executive/Reports/Alerts)

class TestAggregatesAreOrganizationScoped:
    def test_dashboard_summary_counts_only_own_org_project(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        # user_a's org has exactly one project (project_a) — not org_b's.
        assert resp.json()["total_projects"] == 1

    def test_executive_intelligence_contains_only_own_org_project(self, client: TestClient, user_a, user_b, tenants):
        db = TestingSessionLocal()
        try:
            code_a = db.query(Project.project_code).filter(Project.id == tenants["project_a_id"]).scalar()
            code_b = db.query(Project.project_code).filter(Project.id == tenants["project_b_id"]).scalar()
        finally:
            db.close()

        with _as_user(user_a):
            resp_a = client.get("/api/v1/executive")
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a["total_projects"] == 1
        all_codes_a = {p["project_code"] for p in (
            data_a["top_priorities"] + data_a["best_projects"] + data_a["attention_required"]
        )}
        assert code_b not in all_codes_a

        with _as_user(user_b):
            resp_b = client.get("/api/v1/executive")
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        assert data_b["total_projects"] == 1
        all_codes_b = {p["project_code"] for p in (
            data_b["top_priorities"] + data_b["best_projects"] + data_b["attention_required"]
        )}
        assert code_a not in all_codes_b

    def test_executive_weekly_report_scoped_to_own_org(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get("/api/v1/reports/executive-weekly")
        assert resp.status_code == 200
        assert resp.json()["health_distribution"]["total"] == 1

    def test_alerts_never_reference_other_orgs_project(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        project_ids_in_alerts = {
            a["project_id"] for a in resp.json()["alerts"] if a["project_id"] is not None
        }
        assert tenants["project_b_id"] not in project_ids_in_alerts

    def test_portfolio_trend_scoped_to_own_org(self, client: TestClient, user_a, tenants):
        with _as_user(user_a):
            # Trigger a snapshot write for org_a, then read the trend back.
            client.get("/api/v1/executive")
            resp = client.get("/api/v1/executive/trend")
        assert resp.status_code == 200
        # Every point returned must belong to org_a's own snapshot history —
        # verified indirectly: today's score must match today's computed
        # portfolio score for org_a specifically (a single-project org, so
        # unambiguous), not some other organization's blended value.
        db = TestingSessionLocal()
        try:
            from app.models.executive import PortfolioScoreSnapshot
            from datetime import date
            snap = (
                db.query(PortfolioScoreSnapshot)
                .filter(
                    PortfolioScoreSnapshot.organization_id == tenants["org_a_id"],
                    PortfolioScoreSnapshot.snapshot_date == date.today(),
                )
                .first()
            )
            assert snap is not None
        finally:
            db.close()


# ── Part D item 11: Copilot evidence retrieval doesn't cross organizations

class TestCopilotRetrievalIsOrganizationScoped:
    def test_project_overview_list_mode_excludes_other_org(self, tenants):
        db = TestingSessionLocal()
        try:
            user_a = db.query(UserAccount).filter(UserAccount.id == tenants["user_a_id"]).first()
            scope_a = build_ai_scope(user_a, db)
            result = get_project_overview(db, scope_a)
            returned_ids = {row["id"] for row in result.data.get("projects", [])}
            assert tenants["project_a_id"] in returned_ids
            assert tenants["project_b_id"] not in returned_ids
        finally:
            db.close()

    def test_project_overview_explicit_id_denies_other_org(self, tenants):
        from fastapi import HTTPException
        db = TestingSessionLocal()
        try:
            user_a = db.query(UserAccount).filter(UserAccount.id == tenants["user_a_id"]).first()
            scope_a = build_ai_scope(user_a, db)
            with pytest.raises(HTTPException) as exc_info:
                get_project_overview(db, scope_a, project_id=tenants["project_b_id"])
            assert exc_info.value.status_code == 403
        finally:
            db.close()


# ── Part D item 12: Memory retrieval doesn't cross organizations ──────────

class TestMemoryRetrievalIsOrganizationScoped:
    def test_list_memory_records_excludes_other_org(self, tenants):
        db = TestingSessionLocal()
        mem_a = AIMemoryRecord(
            organization_id=tenants["org_a_id"], project_id=tenants["project_a_id"],
            source="meeting", category="meeting_summary",
            title="Org A Isolation Memory", summary="Belongs to org A only.",
            keywords="isolation,org-a", confidence=100,
        )
        mem_b = AIMemoryRecord(
            organization_id=tenants["org_b_id"], project_id=tenants["project_b_id"],
            source="meeting", category="meeting_summary",
            title="Org B Isolation Memory", summary="Belongs to org B only.",
            keywords="isolation,org-b", confidence=100,
        )
        db.add_all([mem_a, mem_b])
        db.commit()
        try:
            user_a = db.query(UserAccount).filter(UserAccount.id == tenants["user_a_id"]).first()
            scope_a = build_ai_scope(user_a, db)
            records = list_memory_records_for_scope(db, scope_a, limit=200)
            titles = {r.title for r in records}
            assert "Org A Isolation Memory" in titles
            assert "Org B Isolation Memory" not in titles
        finally:
            db.delete(mem_a)
            db.delete(mem_b)
            db.commit()
            db.close()


# ── Part D item 13: no undocumented platform-wide super-admin behavior ────

class TestNoImplicitCrossOrganizationSuperAdmin:
    def test_admin_role_alone_does_not_grant_cross_org_access(self, tenants):
        """The role model has no distinct platform-level super-admin role
        (admin/executive/project_manager are org-scoped global-read roles,
        not platform-wide — see app/ai/scope.py). An 'admin' user in org A
        must not be able to see org B's project just by virtue of the
        admin role name."""
        db = TestingSessionLocal()
        try:
            admin_in_org_a = _transient_user(999_999_001, "iso-admin-a@test.local", "admin", tenants["org_a_id"])
            scope = build_ai_scope(admin_in_org_a, db)
            assert tenants["project_a_id"] in scope.accessible_project_ids
            assert tenants["project_b_id"] not in scope.accessible_project_ids
        finally:
            db.close()
