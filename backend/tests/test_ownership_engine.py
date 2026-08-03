"""Tests for the Ownership Engine (Sprint 3 — app/ai/ownership_engine.py).

Real Postgres DB (same pattern as test_workflow_engine.py). Covers:
migration backfill correctness (unambiguous match / ambiguous / no match),
assign, reassign, unassign (self and manager-on-behalf-of-another),
authorization (cross-tenant, unauthorized role, invalid/cross-org/inactive/
no-membership target user), assignment history, query filters (assigned
to me / to a user / unassigned / overdue), that the ownership indexes
this sprint added actually exist (the deterministic way to verify
"do not scan whole tables" rather than relying on the query planner's
row-count-dependent choice of scan type), and backward compatibility of
the existing GET/POST endpoints.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from app.ai.ownership_engine import (
    apply_ownership_filters,
    apply_overdue_filter,
    assign_action_item,
    assign_ncr,
    assign_project_issue,
    assign_project_risk,
    assign_purchase_request,
    assign_safety_event,
    unassign_action_item,
    unassign_ncr,
    unassign_project_issue,
    unassign_project_risk,
    unassign_purchase_request,
    unassign_safety_event,
)
from app.ai.scope import AIAuthScope
from app.models.assignment_history import AssignmentHistory
from app.models.auth import UserAccount
from app.models.meetings import Meeting, MeetingActionItem
from app.models.organizations import Organization, ProjectMembership
from app.models.procurement import PurchaseRequest
from app.models.projects import ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from tests.conftest import TEST_USER_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_ORG_A = 1
_MANAGER_USER_ID = TEST_USER_ID  # real seeded admin — global read, manager authority
_ENGINEER_USER_ID = 4  # real seeded site_engineer (non-manager role), org 1
_PM_FULL_NAME = "Khalid Al-Mansouri"  # real seeded project_manager's full_name, id=3


def _scope(user_id: int = _MANAGER_USER_ID, org_id: int = _ORG_A, role: str = "admin", membership_roles=None) -> AIAuthScope:
    from app.ai.scope import build_ai_scope
    from datetime import datetime as _dt

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"scope-test-{user_id}@test.local", full_name="Scope Test",
            role=role, is_active=True, hashed_password="x", organization_id=org_id,
            created_at=_dt(2026, 1, 1, tzinfo=timezone.utc),
        )
        base = build_ai_scope(user, db)
        if membership_roles:
            return AIAuthScope(
                organization_id=base.organization_id, user_id=base.user_id, user_role=base.user_role,
                accessible_project_ids=tuple(set(base.accessible_project_ids) | set(membership_roles)),
                project_membership_roles={**base.project_membership_roles, **membership_roles},
            )
        return base
    finally:
        db.close()


def _restricted_scope(user_id: int = _ENGINEER_USER_ID) -> AIAuthScope:
    """A real user, own organization, but no accessible projects (no
    membership, non-global-read role) — exercises 403, not 404."""
    return AIAuthScope(organization_id=_ORG_A, user_id=user_id, user_role="site_engineer", accessible_project_ids=(999_999,))


def _cross_org_scope(user_id: int = _MANAGER_USER_ID) -> AIAuthScope:
    return AIAuthScope(organization_id=999, user_id=user_id, user_role="admin", accessible_project_ids=())


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def engineer_membership(db_session):
    """Gives the real site_engineer (id=4) an active membership on project
    1, satisfying the "user has project membership" assignment guard."""
    row = ProjectMembership(user_id=_ENGINEER_USER_ID, project_id=_REAL_PROJECT_ID, role_on_project="site_engineer", is_active=True)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ProjectMembership).filter(ProjectMembership.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def cross_org_user(db_session):
    # A real second Organization row is required — UserAccount.organization_id
    # is a real FK (fk_user_accounts_organization_id_organizations), unlike
    # the pure in-memory AIAuthScope objects _cross_org_scope() builds
    # elsewhere in this file, which need no backing row at all.
    org = Organization(name="Cross Org Test Co", slug=f"cross-org-test-{datetime.now(timezone.utc).timestamp()}")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    user = UserAccount(
        email="cross-org-owner@test.local", hashed_password="x", full_name="Cross Org User",
        role="site_engineer", is_active=True, organization_id=org.id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user.id
    db_session.query(UserAccount).filter(UserAccount.id == user.id).delete()
    db_session.query(Organization).filter(Organization.id == org.id).delete()
    db_session.commit()


@pytest.fixture
def inactive_user(db_session):
    user = UserAccount(
        email="inactive-owner@test.local", hashed_password="x", full_name="Inactive User",
        role="site_engineer", is_active=False, organization_id=_ORG_A,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user.id
    db_session.query(UserAccount).filter(UserAccount.id == user.id).delete()
    db_session.commit()


@pytest.fixture
def risk(db_session):
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Ownership Test Risk", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "project_risk", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(ProjectRisk).filter(ProjectRisk.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def issue(db_session):
    row = ProjectIssue(project_id=_REAL_PROJECT_ID, title="Ownership Test Issue", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "project_issue", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(ProjectIssue).filter(ProjectIssue.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def meeting(db_session):
    row = Meeting(project_id=_REAL_PROJECT_ID, meeting_date="2026-08-02", title="Ownership Test Meeting", meeting_type="site")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(Meeting).filter(Meeting.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def action_item(db_session, meeting):
    row = MeetingActionItem(meeting_id=meeting, project_id=_REAL_PROJECT_ID, description="Ownership test item", owner="Unassigned Text", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "action_item", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(MeetingActionItem).filter(MeetingActionItem.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def safety_event(db_session):
    row = SafetyEvent(project_id=_REAL_PROJECT_ID, subcontractor_id=1, event_date="2026-08-02", severity="Medium", description="Ownership test event", corrective_action="", status="Open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "safety_event", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(SafetyEvent).filter(SafetyEvent.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def ncr(db_session):
    row = NCR(project_id=_REAL_PROJECT_ID, ncr_type="Quality", description="Ownership test NCR", root_cause="Unknown", issue_date="2026-08-02", status="Open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "ncr", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(NCR).filter(NCR.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def purchase_request(db_session):
    row = PurchaseRequest(project_id=_REAL_PROJECT_ID, request_no="OWN-TEST-1", status="Pending Clarification", created_at="2026-08-02")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "purchase_request", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(PurchaseRequest).filter(PurchaseRequest.id == row.id).delete()
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────
# Migration backfill — imports the real migration module (not a
# reimplementation) and calls its function directly against a real
# connection, so this exercises the exact code that ran during
# `alembic upgrade head`.
# ─────────────────────────────────────────────────────────────────────────
def _load_migration_module():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0017_ownership_engine.py"
    spec = importlib.util.spec_from_file_location("migration_0017", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigrationBackfill:
    def test_unambiguous_match_backfills_owner_id(self, db_session, risk):
        db_session.execute(sa_text("UPDATE project_risks SET owner = :o WHERE id = :id"), {"o": _PM_FULL_NAME, "id": risk})
        db_session.commit()

        migration = _load_migration_module()
        migration.backfill_owner_id_from_owner_text(db_session.connection(), "project_risks")
        db_session.commit()

        db_session.expire_all()
        row = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
        assert row.owner_id == 3  # the real seeded project_manager with this full_name
        assert row.owner == _PM_FULL_NAME  # legacy text untouched

    def test_no_match_leaves_owner_id_null(self, db_session, risk):
        db_session.execute(sa_text("UPDATE project_risks SET owner = :o WHERE id = :id"), {"o": "Nobody With This Name", "id": risk})
        db_session.commit()

        migration = _load_migration_module()
        migration.backfill_owner_id_from_owner_text(db_session.connection(), "project_risks")
        db_session.commit()

        db_session.expire_all()
        row = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
        assert row.owner_id is None
        assert row.owner == "Nobody With This Name"  # preserved exactly

    def test_ambiguous_match_leaves_owner_id_null(self, db_session, risk):
        duplicate = UserAccount(
            email="duplicate-name@test.local", hashed_password="x", full_name=_PM_FULL_NAME,
            role="viewer", is_active=True, organization_id=_ORG_A,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(duplicate)
        db_session.commit()
        db_session.refresh(duplicate)
        try:
            db_session.execute(sa_text("UPDATE project_risks SET owner = :o WHERE id = :id"), {"o": _PM_FULL_NAME, "id": risk})
            db_session.commit()

            migration = _load_migration_module()
            migration.backfill_owner_id_from_owner_text(db_session.connection(), "project_risks")
            db_session.commit()

            db_session.expire_all()
            row = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
            assert row.owner_id is None  # ambiguous — must not guess
            assert row.owner == _PM_FULL_NAME
        finally:
            db_session.query(UserAccount).filter(UserAccount.id == duplicate.id).delete()
            db_session.commit()

    def test_empty_owner_text_is_skipped(self, db_session, risk):
        migration = _load_migration_module()
        migration.backfill_owner_id_from_owner_text(db_session.connection(), "project_risks")
        db_session.commit()
        db_session.expire_all()
        row = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
        assert row.owner_id is None
        assert row.owner is None


class TestOwnershipIndexesExist:
    """Deterministic verification that "do not scan whole tables" was
    actually provisioned, rather than relying on the query planner's
    row-count-dependent choice of seq scan vs index scan on any given
    table size."""

    @pytest.mark.parametrize("table", [
        "project_risks", "project_issues", "meeting_action_items",
        "safety_events", "ncrs", "purchase_requests",
    ])
    def test_owner_id_index_exists(self, db_session, table):
        rows = db_session.execute(sa_text(
            "SELECT indexdef FROM pg_indexes WHERE tablename = :t AND indexdef ILIKE '%owner_id%'"
        ), {"t": table}).fetchall()
        assert rows, f"no owner_id index found on {table}"

    @pytest.mark.parametrize("table", [
        "project_risks", "project_issues", "meeting_action_items", "safety_events", "ncrs", "purchase_requests",
    ])
    def test_status_index_exists(self, db_session, table):
        rows = db_session.execute(sa_text(
            "SELECT indexdef FROM pg_indexes WHERE tablename = :t AND indexdef ILIKE '%status%'"
        ), {"t": table}).fetchall()
        assert rows, f"no status index found on {table}"

    def test_due_date_index_exists_on_action_items(self, db_session):
        rows = db_session.execute(sa_text(
            "SELECT indexdef FROM pg_indexes WHERE tablename = 'meeting_action_items' AND indexdef ILIKE '%due_date%'"
        )).fetchall()
        assert rows


class TestSelfAssign:
    def test_anyone_with_project_access_can_self_assign(self, db_session, risk, engineer_membership):
        # engineer_membership gives user 4 a REAL ProjectMembership row —
        # _user_can_be_assigned() checks the target's actual DB access,
        # not the caller's own (possibly fabricated-for-testing) scope.
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        updated = assign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assert updated.owner_id == _ENGINEER_USER_ID
        assert updated.owner  # legacy text synced

    def test_self_release_allowed_without_manager_role(self, db_session, risk, engineer_membership):
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        assign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        released = unassign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk)
        assert released.owner_id is None
        assert released.owner is None


class TestManagerAssignsOthers:
    def test_manager_can_assign_to_another_member(self, db_session, risk, engineer_membership):
        updated = assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assert updated.owner_id == _ENGINEER_USER_ID
        assert updated.assigned_by == _MANAGER_USER_ID

    def test_non_manager_cannot_assign_to_someone_else(self, db_session, risk, engineer_membership):
        # A site_engineer (non-manager) with project access tries to
        # assign the risk to a DIFFERENT user (not themselves).
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        assert exc_info.value.status_code == 403

    def test_non_manager_cannot_unassign_someone_else(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        with pytest.raises(HTTPException) as exc_info:
            unassign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk)
        assert exc_info.value.status_code == 403

    def test_project_manager_role_on_project_can_assign_someone_else(self, db_session, risk):
        """Manager authority via role_on_project (not the caller's global
        role, which is deliberately non-manager here), assigning to a
        DIFFERENT user — a real, globally-accessible one (admin), so no
        extra ProjectMembership row is needed for the target."""
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "project_manager"})
        updated = assign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        assert updated.owner_id == _MANAGER_USER_ID
        assert updated.assigned_by == _ENGINEER_USER_ID


class TestReassignment:
    def test_reassign_from_one_user_to_another(self, db_session, risk, engineer_membership):
        first = assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        assert first.owner_id == _MANAGER_USER_ID
        second = assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assert second.owner_id == _ENGINEER_USER_ID


class TestUnassignIdempotent:
    def test_unassigning_already_unassigned_is_a_noop(self, db_session, risk):
        result = unassign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk)
        assert result.owner_id is None  # no error


class TestInvalidUserValidation:
    def test_nonexistent_user_id_404(self, db_session, risk):
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, 999_999_999)
        assert exc_info.value.status_code == 404

    def test_cross_organization_user_404(self, db_session, risk, cross_org_user):
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, cross_org_user)
        assert exc_info.value.status_code == 404

    def test_inactive_user_rejected(self, db_session, risk, inactive_user):
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, inactive_user)
        assert exc_info.value.status_code == 409

    def test_user_without_project_membership_rejected(self, db_session, risk):
        # _ENGINEER_USER_ID has no membership on this project in this test
        # (no engineer_membership fixture used) and is not a global-read role.
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assert exc_info.value.status_code == 409

    def test_global_read_role_needs_no_explicit_membership(self, db_session, risk):
        # id=3 is the real seeded project_manager (global-read) — must be
        # assignable without any ProjectMembership row.
        updated = assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, 3)
        assert updated.owner_id == 3


class TestCrossTenantIsolation:
    def test_assign_on_entity_in_another_organization_is_404(self, db_session, risk):
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _cross_org_scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        assert exc_info.value.status_code == 404

    def test_restricted_role_without_access_gets_403(self, db_session, risk):
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _restricted_scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        assert exc_info.value.status_code == 403


class TestAssignmentHistory:
    def test_assign_reassign_unassign_recorded_in_order(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        unassign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk)

        history = (
            db_session.query(AssignmentHistory)
            .filter(AssignmentHistory.entity_type == "project_risk", AssignmentHistory.entity_id == risk)
            .order_by(AssignmentHistory.id.asc())
            .all()
        )
        assert len(history) == 3
        assert history[0].previous_owner_id is None
        assert history[0].new_owner_id == _MANAGER_USER_ID
        assert history[0].assigned_by == _MANAGER_USER_ID
        assert history[1].previous_owner_id == _MANAGER_USER_ID
        assert history[1].new_owner_id == _ENGINEER_USER_ID
        assert history[2].previous_owner_id == _ENGINEER_USER_ID
        assert history[2].new_owner_id is None
        for h in history:
            assert h.assigned_at is not None
            assert h.project_id == _REAL_PROJECT_ID


class TestOwnershipQueries:
    def test_assigned_to_me_filter(self, db_session, risk, issue, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID)
        scope = _scope()
        q = apply_ownership_filters(db_session.query(ProjectRisk).filter(ProjectRisk.project_id == _REAL_PROJECT_ID), ProjectRisk, scope, assigned_to_me=True)
        ids = [r.id for r in q.all()]
        assert risk in ids

    def test_assigned_to_specific_user_filter(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        q = apply_ownership_filters(db_session.query(ProjectRisk).filter(ProjectRisk.project_id == _REAL_PROJECT_ID), ProjectRisk, _scope(), assigned_to=_ENGINEER_USER_ID)
        ids = [r.id for r in q.all()]
        assert risk in ids

    def test_unassigned_filter(self, db_session, risk):
        q = apply_ownership_filters(db_session.query(ProjectRisk).filter(ProjectRisk.project_id == _REAL_PROJECT_ID), ProjectRisk, _scope(), unassigned=True)
        ids = [r.id for r in q.all()]
        assert risk in ids

    def test_unassigned_filter_excludes_assigned_rows(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        q = apply_ownership_filters(db_session.query(ProjectRisk).filter(ProjectRisk.project_id == _REAL_PROJECT_ID), ProjectRisk, _scope(), unassigned=True)
        ids = [r.id for r in q.all()]
        assert risk not in ids

    def test_overdue_filter_on_action_items(self, db_session, action_item):
        db_session.execute(sa_text("UPDATE meeting_action_items SET due_date = '2000-01-01' WHERE id = :id"), {"id": action_item})
        db_session.commit()
        q = apply_overdue_filter(db_session.query(MeetingActionItem).filter(MeetingActionItem.id == action_item), MeetingActionItem, overdue=True)
        ids = [r.id for r in q.all()]
        assert action_item in ids

    def test_overdue_filter_excludes_completed(self, db_session, action_item):
        db_session.execute(
            sa_text("UPDATE meeting_action_items SET due_date = '2000-01-01', status = 'Completed', completed_at = '2026-01-01' WHERE id = :id"),
            {"id": action_item},
        )
        db_session.commit()
        q = apply_overdue_filter(db_session.query(MeetingActionItem).filter(MeetingActionItem.id == action_item), MeetingActionItem, overdue=True)
        ids = [r.id for r in q.all()]
        assert action_item not in ids

    def test_overdue_filter_excludes_future_due_date(self, db_session, action_item):
        db_session.execute(sa_text("UPDATE meeting_action_items SET due_date = '2099-01-01' WHERE id = :id"), {"id": action_item})
        db_session.commit()
        q = apply_overdue_filter(db_session.query(MeetingActionItem).filter(MeetingActionItem.id == action_item), MeetingActionItem, overdue=True)
        ids = [r.id for r in q.all()]
        assert action_item not in ids


class TestConcurrency:
    def test_stale_expected_updated_at_is_409(self, db_session, risk):
        stale = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(HTTPException) as exc_info:
            assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID, expected_updated_at=stale)
        assert exc_info.value.status_code == 409

    def test_correct_expected_updated_at_succeeds(self, db_session, risk):
        current = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
        updated = assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _MANAGER_USER_ID, expected_updated_at=current.updated_at)
        assert updated.owner_id == _MANAGER_USER_ID


class TestAllEntitiesAssignable:
    """One smoke test per remaining entity — the shared _do_assign/
    _do_unassign core is already covered in depth via ProjectRisk above;
    this just proves each entity's thin wrapper wires it correctly."""

    def test_project_issue(self, db_session, issue):
        updated = assign_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, _MANAGER_USER_ID)
        assert updated.owner_id == _MANAGER_USER_ID
        released = unassign_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue)
        assert released.owner_id is None

    def test_action_item_legacy_owner_cleared_to_empty_string_not_null(self, db_session, action_item):
        assign_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item, _MANAGER_USER_ID)
        released = unassign_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item)
        assert released.owner_id is None
        assert released.owner == ""  # NOT NULL column — cleared to "", never None

    def test_safety_event(self, db_session, safety_event):
        updated = assign_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event, _MANAGER_USER_ID)
        assert updated.owner_id == _MANAGER_USER_ID
        released = unassign_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event)
        assert released.owner_id is None

    def test_ncr(self, db_session, ncr):
        updated = assign_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, _MANAGER_USER_ID)
        assert updated.owner_id == _MANAGER_USER_ID
        released = unassign_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr)
        assert released.owner_id is None

    def test_purchase_request_flat_route_pattern(self, db_session, purchase_request):
        updated = assign_purchase_request(db_session, _scope(), purchase_request, _MANAGER_USER_ID)
        assert updated.owner_id == _MANAGER_USER_ID
        released = unassign_purchase_request(db_session, _scope(), purchase_request)
        assert released.owner_id is None

    def test_purchase_request_cross_org_404(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            assign_purchase_request(db_session, _cross_org_scope(), purchase_request, _MANAGER_USER_ID)
        assert exc_info.value.status_code == 404


class TestHTTPRoutes:
    def test_assign_and_unassign_risk_via_http(self, client: TestClient, db_session, risk):
        resp = client.post(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}/assign", json={"user_id": _MANAGER_USER_ID})
        assert resp.status_code == 200
        assert resp.json()["owner_id"] == _MANAGER_USER_ID

        resp2 = client.post(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}/unassign", json={})
        assert resp2.status_code == 200
        assert resp2.json()["owner_id"] is None

    def test_assign_purchase_request_via_http_flat_route(self, client: TestClient, db_session, purchase_request):
        resp = client.post(f"/api/v1/procurement/purchase-requests/{purchase_request}/assign", json={"user_id": _MANAGER_USER_ID})
        assert resp.status_code == 200
        assert resp.json()["owner_id"] == _MANAGER_USER_ID

    def test_assign_extra_field_rejected(self, client: TestClient, db_session, risk):
        resp = client.post(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}/assign", json={"user_id": _MANAGER_USER_ID, "owner": "hacked"})
        assert resp.status_code == 422

    def test_list_risks_with_assigned_to_me_query_param(self, client: TestClient, db_session, risk):
        client.post(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}/assign", json={"user_id": _MANAGER_USER_ID})
        resp = client.get(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks", params={"assigned_to_me": True})
        assert resp.status_code == 200
        assert any(r["id"] == risk for r in resp.json())


class TestBackwardCompatibility:
    """Existing GET/POST endpoints for the six entities must keep behaving
    exactly as before — same spot-check approach as test_workflow_engine.py."""

    def test_existing_list_risks_route_still_works(self, client: TestClient, risk):
        resp = client.get(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks")
        assert resp.status_code == 200
        assert any(r["id"] == risk for r in resp.json())

    def test_existing_create_risk_route_unaffected(self, client: TestClient, db_session):
        resp = client.post(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks", json={"title": "HTTP Create Ownership Test"})
        assert resp.status_code == 201
        assert resp.json()["owner_id"] is None
        new_id = resp.json()["id"]
        db_session.query(ProjectRisk).filter(ProjectRisk.id == new_id).delete()
        db_session.commit()

    def test_existing_list_purchase_requests_route_unaffected(self, client: TestClient, purchase_request):
        resp = client.get("/api/v1/procurement/purchase-requests", params={"project_id": _REAL_PROJECT_ID, "limit": 100})
        assert resp.status_code == 200
        assert any(p["id"] == purchase_request for p in resp.json())

    def test_existing_seeded_ncr_readable_with_null_owner(self, db_session):
        existing = db_session.query(NCR).filter(NCR.owner_id.is_(None)).first()
        assert existing is not None  # confirms migration didn't force-populate unrelated rows
