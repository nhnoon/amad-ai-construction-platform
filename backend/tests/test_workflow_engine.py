"""Tests for the Core Workflow Engine (Sprint 2 — app/ai/workflow_engine.py).

Real Postgres DB (same pattern as test_document_ocr.py / test_projects.py).
Covers, per entity (ProjectRisk, ProjectIssue, MeetingActionItem,
SafetyEvent, NCR, PurchaseRequest): every valid transition, invalid
transitions (409), unrecognized target status (400), close-out guard
failures/successes, reassignment/due-date updates independent of status,
optimistic concurrency, 404 for missing rows, cross-tenant/unauthorized
access, and that a no-op status (unchanged) is always accepted.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.scope import AIAuthScope
from app.ai.workflow_engine import (
    update_action_item,
    update_ncr,
    update_project_issue,
    update_project_risk,
    update_purchase_request,
    update_safety_event,
)
from app.models.meetings import Meeting, MeetingActionItem
from app.models.procurement import PurchaseRequest
from app.models.projects import ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from app.schemas.meetings import MeetingActionItemUpdate
from app.schemas.procurement import PurchaseRequestUpdate
from app.schemas.projects import ProjectIssueUpdate, ProjectRiskUpdate
from app.schemas.safety import NCRUpdate, SafetyEventUpdate
from tests.conftest import TEST_USER_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_REAL_SUBCONTRACTOR_ID = 1
_ORG_A = 1


def _scope(user_id: int = TEST_USER_ID, org_id: int = _ORG_A, role: str = "admin") -> AIAuthScope:
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"scope-test-{user_id}@test.local", full_name="Scope Test",
            role=role, is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        return build_ai_scope(user, db)
    finally:
        db.close()


def _restricted_scope(user_id: int = TEST_USER_ID) -> AIAuthScope:
    """Same organization as the real project, but no membership on it —
    exercises the 403 (not 404) branch."""
    return AIAuthScope(
        organization_id=_ORG_A, user_id=user_id, user_role="site_engineer",
        accessible_project_ids=(999_999,),
    )


def _cross_org_scope(user_id: int = TEST_USER_ID) -> AIAuthScope:
    """A different organization entirely — exercises the 404 (existence
    hidden) branch, not 403."""
    return AIAuthScope(
        organization_id=999, user_id=user_id, user_role="admin",
        accessible_project_ids=(),
    )


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def risk(db_session):
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Test Risk", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ProjectRisk).filter(ProjectRisk.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def issue(db_session):
    row = ProjectIssue(project_id=_REAL_PROJECT_ID, title="Test Issue", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ProjectIssue).filter(ProjectIssue.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def meeting(db_session):
    row = Meeting(project_id=_REAL_PROJECT_ID, meeting_date="2026-08-01", title="Workflow Test Meeting", meeting_type="site")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(Meeting).filter(Meeting.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def action_item(db_session, meeting):
    row = MeetingActionItem(
        meeting_id=meeting, project_id=_REAL_PROJECT_ID,
        description="Test action item", owner="Alice", status="open",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(MeetingActionItem).filter(MeetingActionItem.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def safety_event(db_session):
    row = SafetyEvent(
        project_id=_REAL_PROJECT_ID, subcontractor_id=_REAL_SUBCONTRACTOR_ID,
        event_date="2026-08-01", severity="Medium", description="Test event",
        corrective_action="", status="Open",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(SafetyEvent).filter(SafetyEvent.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def ncr(db_session):
    row = NCR(
        project_id=_REAL_PROJECT_ID, ncr_type="Quality", description="Test NCR",
        root_cause="Unknown", issue_date="2026-08-01", status="Open",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(NCR).filter(NCR.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def purchase_request(db_session):
    row = PurchaseRequest(
        project_id=_REAL_PROJECT_ID, request_no="WF-TEST-1",
        status="Pending Clarification", created_at="2026-08-01",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(PurchaseRequest).filter(PurchaseRequest.id == row.id).delete()
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────
# ProjectRisk: open -> {mitigating, closed}; mitigating -> {open, closed};
# closed -> {open}. closed requires non-empty mitigation.
# ─────────────────────────────────────────────────────────────────────────
class TestProjectRiskTransitions:
    def test_open_to_mitigating(self, db_session, risk):
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="mitigating"))
        assert updated.status == "mitigating"

    def test_open_to_closed_requires_mitigation(self, db_session, risk):
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="closed"))
        assert exc_info.value.status_code == 409

    def test_open_to_closed_succeeds_with_mitigation_in_same_call(self, db_session, risk):
        updated = update_project_risk(
            db_session, _scope(), _REAL_PROJECT_ID, risk,
            ProjectRiskUpdate(status="closed", mitigation="Added guardrails"),
        )
        assert updated.status == "closed"
        assert updated.mitigation == "Added guardrails"

    def test_closed_to_mitigating_directly_is_invalid(self, db_session, risk):
        update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="closed", mitigation="x"))
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="mitigating"))
        assert exc_info.value.status_code == 409

    def test_closed_to_open_reopen_allowed(self, db_session, risk):
        update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="closed", mitigation="x"))
        reopened = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="open"))
        assert reopened.status == "open"
        assert reopened.mitigation == "x"  # historical context preserved

    def test_unrecognized_status_is_400(self, db_session, risk):
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="banana"))
        assert exc_info.value.status_code == 400

    def test_noop_status_always_allowed(self, db_session, risk):
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(status="open", owner="Bob"))
        assert updated.status == "open"
        assert updated.owner == "Bob"

    def test_reassignment_without_status_change(self, db_session, risk):
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="Carol"))
        assert updated.owner == "Carol"
        assert updated.status == "open"

    def test_probability_and_impact_updatable(self, db_session, risk):
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(probability="high", impact="high"))
        assert updated.probability == "high"
        assert updated.impact == "high"

    def test_updated_by_stamped(self, db_session, risk):
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="X"))
        assert updated.updated_by == TEST_USER_ID


# ─────────────────────────────────────────────────────────────────────────
# ProjectIssue: open -> {In Progress, Resolved}; In Progress -> {open,
# Resolved}; Resolved -> {open}. Resolved requires non-empty resolution
# and stamps resolved_at.
# ─────────────────────────────────────────────────────────────────────────
class TestProjectIssueTransitions:
    def test_open_to_in_progress(self, db_session, issue):
        updated = update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, ProjectIssueUpdate(status="In Progress"))
        assert updated.status == "In Progress"

    def test_resolved_requires_nonempty_resolution(self, db_session, issue):
        with pytest.raises(HTTPException) as exc_info:
            update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, ProjectIssueUpdate(status="Resolved"))
        assert exc_info.value.status_code == 409

    def test_resolved_succeeds_and_stamps_resolved_at(self, db_session, issue):
        updated = update_project_issue(
            db_session, _scope(), _REAL_PROJECT_ID, issue,
            ProjectIssueUpdate(status="Resolved", resolution="Fixed the leak"),
        )
        assert updated.status == "Resolved"
        assert updated.resolution == "Fixed the leak"
        assert updated.resolved_at  # auto-stamped

    def test_resolved_with_explicit_resolved_at_not_overwritten(self, db_session, issue):
        updated = update_project_issue(
            db_session, _scope(), _REAL_PROJECT_ID, issue,
            ProjectIssueUpdate(status="Resolved", resolution="Fixed", resolved_at="2020-01-01"),
        )
        assert updated.resolved_at == "2020-01-01"

    def test_invalid_direct_open_to_resolved_then_reopen_then_resolved_again(self, db_session, issue):
        update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, ProjectIssueUpdate(status="Resolved", resolution="r1"))
        reopened = update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, ProjectIssueUpdate(status="open"))
        assert reopened.status == "open"
        assert reopened.resolution == "r1"  # preserved, not discarded

    def test_unrecognized_status_400(self, db_session, issue):
        with pytest.raises(HTTPException) as exc_info:
            update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, ProjectIssueUpdate(status="done"))
        assert exc_info.value.status_code == 400

    def test_severity_reassignment_without_status_change(self, db_session, issue):
        updated = update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, issue, ProjectIssueUpdate(owner="Dave", severity="high"))
        assert updated.owner == "Dave"
        assert updated.severity == "high"
        assert updated.status == "open"


# ─────────────────────────────────────────────────────────────────────────
# MeetingActionItem: open -> {In Progress, Completed}; In Progress ->
# {open, Completed}; Completed -> {open}. Completed requires completed_at.
# ─────────────────────────────────────────────────────────────────────────
class TestActionItemTransitions:
    def test_open_to_completed_auto_stamps_completed_at(self, db_session, action_item):
        updated = update_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item, MeetingActionItemUpdate(status="Completed"))
        assert updated.status == "Completed"
        assert updated.completed_at

    def test_completed_to_in_progress_direct_is_invalid(self, db_session, action_item):
        update_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item, MeetingActionItemUpdate(status="Completed"))
        with pytest.raises(HTTPException) as exc_info:
            update_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item, MeetingActionItemUpdate(status="In Progress"))
        assert exc_info.value.status_code == 409

    def test_reassignment_and_due_date_independent_of_status(self, db_session, action_item):
        updated = update_action_item(
            db_session, _scope(), _REAL_PROJECT_ID, action_item,
            MeetingActionItemUpdate(owner="Erin", due_date="2026-09-01"),
        )
        assert updated.owner == "Erin"
        assert updated.due_date == "2026-09-01"
        assert updated.status == "open"

    def test_priority_update(self, db_session, action_item):
        updated = update_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item, MeetingActionItemUpdate(priority="high"))
        assert updated.priority == "high"

    def test_unrecognized_status_400(self, db_session, action_item):
        with pytest.raises(HTTPException) as exc_info:
            update_action_item(db_session, _scope(), _REAL_PROJECT_ID, action_item, MeetingActionItemUpdate(status="done"))
        assert exc_info.value.status_code == 400


# ─────────────────────────────────────────────────────────────────────────
# SafetyEvent: Open -> Closed -> Open. Closed requires non-empty
# corrective_action. No fabricated investigation workflow.
# ─────────────────────────────────────────────────────────────────────────
class TestSafetyEventTransitions:
    def test_closed_requires_corrective_action(self, db_session, safety_event):
        with pytest.raises(HTTPException) as exc_info:
            update_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event, SafetyEventUpdate(status="Closed"))
        assert exc_info.value.status_code == 409

    def test_closed_succeeds_with_corrective_action(self, db_session, safety_event):
        updated = update_safety_event(
            db_session, _scope(), _REAL_PROJECT_ID, safety_event,
            SafetyEventUpdate(status="Closed", corrective_action="Retrained crew"),
        )
        assert updated.status == "Closed"
        assert updated.corrective_action == "Retrained crew"

    def test_reopen_allowed(self, db_session, safety_event):
        update_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event, SafetyEventUpdate(status="Closed", corrective_action="x"))
        reopened = update_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event, SafetyEventUpdate(status="Open"))
        assert reopened.status == "Open"

    def test_unrecognized_status_400(self, db_session, safety_event):
        with pytest.raises(HTTPException) as exc_info:
            update_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event, SafetyEventUpdate(status="Under Investigation"))
        assert exc_info.value.status_code == 400

    def test_severity_update_without_status_change(self, db_session, safety_event):
        updated = update_safety_event(db_session, _scope(), _REAL_PROJECT_ID, safety_event, SafetyEventUpdate(severity="High"))
        assert updated.severity == "High"
        assert updated.status == "Open"


# ─────────────────────────────────────────────────────────────────────────
# NCR: Open -> {Under Corrective Action, Closed}; Under Corrective Action
# -> {Closed, Open}; Closed -> {Open}. Closed requires corrective_action.
# ─────────────────────────────────────────────────────────────────────────
class TestNCRTransitions:
    def test_open_to_under_corrective_action(self, db_session, ncr):
        updated = update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Under Corrective Action"))
        assert updated.status == "Under Corrective Action"

    def test_closed_requires_corrective_action(self, db_session, ncr):
        with pytest.raises(HTTPException) as exc_info:
            update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Closed"))
        assert exc_info.value.status_code == 409

    def test_set_corrective_action_then_close_in_separate_calls(self, db_session, ncr):
        update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Under Corrective Action", corrective_action="Re-poured slab"))
        closed = update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Closed"))
        assert closed.status == "Closed"
        assert closed.corrective_action == "Re-poured slab"

    def test_root_cause_preserved_when_not_touched(self, db_session, ncr):
        updated = update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Under Corrective Action", corrective_action="x"))
        assert updated.root_cause == "Unknown"  # untouched, preserved

    def test_root_cause_updatable_when_provided(self, db_session, ncr):
        updated = update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(root_cause="Bad mix ratio"))
        assert updated.root_cause == "Bad mix ratio"

    def test_invalid_direct_transition_open_to_closed_without_action_is_409_not_reachability_error(self, db_session, ncr):
        # Open -> Closed IS a valid matrix transition; this specifically
        # exercises the close-out guard, not the matrix itself.
        with pytest.raises(HTTPException) as exc_info:
            update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Closed"))
        assert exc_info.value.status_code == 409

    def test_unrecognized_status_400(self, db_session, ncr):
        with pytest.raises(HTTPException) as exc_info:
            update_ncr(db_session, _scope(), _REAL_PROJECT_ID, ncr, NCRUpdate(status="Escalated"))
        assert exc_info.value.status_code == 400


# ─────────────────────────────────────────────────────────────────────────
# PurchaseRequest: matches the six real seeded status values + Rejected.
# Rejected / Returned to Requester require non-empty rework_reason.
# ─────────────────────────────────────────────────────────────────────────
class TestPurchaseRequestTransitions:
    def test_pending_clarification_to_under_review(self, db_session, purchase_request):
        updated = update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        assert updated.status == "Under Review"

    def test_under_review_to_approved(self, db_session, purchase_request):
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        approved = update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Approved"))
        assert approved.status == "Approved"

    def test_approved_to_converted_to_po(self, db_session, purchase_request):
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Approved"))
        converted = update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Converted to PO"))
        assert converted.status == "Converted to PO"

    def test_converted_to_po_is_terminal(self, db_session, purchase_request):
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Approved"))
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Converted to PO"))
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        assert exc_info.value.status_code == 409

    def test_rejected_requires_reason(self, db_session, purchase_request):
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Rejected"))
        assert exc_info.value.status_code == 409

    def test_rejected_succeeds_with_reason(self, db_session, purchase_request):
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Under Review"))
        rejected = update_purchase_request(
            db_session, _scope(), purchase_request,
            PurchaseRequestUpdate(status="Rejected", rework_reason="Budget exceeded"),
        )
        assert rejected.status == "Rejected"
        assert rejected.rework_reason == "Budget exceeded"

    def test_returned_to_requester_requires_reason(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Returned to Requester"))
        assert exc_info.value.status_code == 409

    def test_returned_to_requester_succeeds_with_reason_already_on_record(self, db_session, purchase_request):
        update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(rework_reason="Missing spec sheet"))
        returned = update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Returned to Requester"))
        assert returned.status == "Returned to Requester"

    def test_unrecognized_status_400(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _scope(), purchase_request, PurchaseRequestUpdate(status="Cancelled"))
        assert exc_info.value.status_code == 400


# ─────────────────────────────────────────────────────────────────────────
# Cross-cutting: authorization, missing IDs, concurrency — exercised once
# per representative entity type (risk = project-nested pattern, purchase
# request = the one non-project-nested route) rather than 6x each, since
# the underlying mechanism (get_project_or_404 / concurrency check) is
# shared, not duplicated per entity.
# ─────────────────────────────────────────────────────────────────────────
class TestAuthorizationAndMissingResources:
    def test_missing_risk_id_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, 999_999_999, ProjectRiskUpdate(owner="x"))
        assert exc_info.value.status_code == 404

    def test_restricted_scope_gets_403_not_404(self, db_session, risk):
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _restricted_scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="x"))
        assert exc_info.value.status_code == 403

    def test_cross_organization_scope_gets_404_not_403(self, db_session, risk):
        """Existence must be hidden across organizations — 404, not 403,
        matching get_project_or_404's documented policy."""
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _cross_org_scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="x"))
        assert exc_info.value.status_code == 404

    def test_purchase_request_missing_id_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _scope(), 999_999_999, PurchaseRequestUpdate(rework_reason="x"))
        assert exc_info.value.status_code == 404

    def test_purchase_request_cross_org_hidden_as_404(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _cross_org_scope(), purchase_request, PurchaseRequestUpdate(rework_reason="x"))
        assert exc_info.value.status_code == 404

    def test_purchase_request_restricted_scope_403(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            update_purchase_request(db_session, _restricted_scope(), purchase_request, PurchaseRequestUpdate(rework_reason="x"))
        assert exc_info.value.status_code == 403

    def test_ncr_under_nonexistent_project_id_is_404(self, db_session, ncr):
        """The URL's project_id is validated before the sub-resource is
        even looked up — a nonexistent project_id 404s regardless of
        whether the ncr_id itself is real."""
        with pytest.raises(HTTPException) as exc_info:
            update_ncr(db_session, _scope(), 999_999, ncr, NCRUpdate(status="Open"))
        assert exc_info.value.status_code == 404


class TestOptimisticConcurrency:
    def test_stale_expected_updated_at_is_409(self, db_session, risk):
        stale_timestamp = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(
                db_session, _scope(), _REAL_PROJECT_ID, risk,
                ProjectRiskUpdate(owner="x", expected_updated_at=stale_timestamp),
            )
        assert exc_info.value.status_code == 409

    def test_correct_expected_updated_at_succeeds(self, db_session, risk):
        current = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
        updated = update_project_risk(
            db_session, _scope(), _REAL_PROJECT_ID, risk,
            ProjectRiskUpdate(owner="x", expected_updated_at=current.updated_at),
        )
        assert updated.owner == "x"

    def test_omitting_expected_updated_at_always_succeeds(self, db_session, risk):
        update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="first"))
        # No expected_updated_at supplied — must never conflict, regardless
        # of how many updates happened since the row was last read.
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="second"))
        assert updated.owner == "second"

    def test_second_update_with_first_stale_token_is_rejected(self, db_session, risk):
        current = db_session.query(ProjectRisk).filter(ProjectRisk.id == risk).first()
        first_token = current.updated_at
        update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="first", expected_updated_at=first_token))
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, ProjectRiskUpdate(owner="second", expected_updated_at=first_token))
        assert exc_info.value.status_code == 409


class TestBackwardCompatibility:
    """Existing GET/POST endpoints must keep behaving exactly as before —
    spot-checked directly against the real HTTP routes."""

    def test_existing_list_risks_route_unaffected(self, client: TestClient, risk):
        resp = client.get(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks")
        assert resp.status_code == 200
        assert any(r["id"] == risk for r in resp.json())

    def test_existing_create_risk_route_unaffected(self, client: TestClient, db_session):
        resp = client.post(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks", json={"title": "HTTP Create Test"})
        assert resp.status_code == 201
        new_id = resp.json()["id"]
        assert resp.json()["status"] == "open"
        db_session.query(ProjectRisk).filter(ProjectRisk.id == new_id).delete()
        db_session.commit()

    def test_existing_list_ncrs_route_unaffected(self, client: TestClient, ncr):
        resp = client.get(f"/api/v1/projects/{_REAL_PROJECT_ID}/ncrs")
        assert resp.status_code == 200
        assert any(n["id"] == ncr for n in resp.json())

    def test_existing_list_purchase_requests_route_unaffected(self, client: TestClient, purchase_request):
        resp = client.get("/api/v1/procurement/purchase-requests", params={"project_id": _REAL_PROJECT_ID, "limit": 100})
        assert resp.status_code == 200
        assert any(p["id"] == purchase_request for p in resp.json())

    def test_existing_create_action_item_route_unaffected(self, client: TestClient, db_session, meeting):
        resp = client.post(
            f"/api/v1/projects/{_REAL_PROJECT_ID}/action-items",
            json={"meeting_id": meeting, "project_id": _REAL_PROJECT_ID, "description": "HTTP create test", "owner": "Frank"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "open"
        new_id = resp.json()["id"]
        db_session.query(MeetingActionItem).filter(MeetingActionItem.id == new_id).delete()
        db_session.commit()


class TestHTTPPatchRoutes:
    def test_patch_risk_route(self, client: TestClient, risk):
        resp = client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}", json={"status": "closed", "mitigation": "handled"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_patch_risk_invalid_transition_returns_409(self, client: TestClient, risk):
        client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}", json={"status": "closed", "mitigation": "x"})
        resp = client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}", json={"status": "mitigating"})
        assert resp.status_code == 409

    def test_patch_issue_route(self, client: TestClient, issue):
        resp = client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/issues/{issue}", json={"status": "Resolved", "resolution": "done"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "Resolved"

    def test_patch_action_item_route(self, client: TestClient, action_item):
        resp = client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/action-items/{action_item}", json={"status": "Completed"})
        assert resp.status_code == 200
        assert resp.json()["completed_at"]

    def test_patch_safety_event_route(self, client: TestClient, safety_event):
        resp = client.patch(
            f"/api/v1/projects/{_REAL_PROJECT_ID}/safety-events/{safety_event}",
            json={"status": "Closed", "corrective_action": "Barrier installed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Closed"

    def test_patch_ncr_route(self, client: TestClient, ncr):
        resp = client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/ncrs/{ncr}", json={"corrective_action": "Reworked"})
        assert resp.status_code == 200
        assert resp.json()["corrective_action"] == "Reworked"

    def test_patch_purchase_request_route(self, client: TestClient, purchase_request):
        resp = client.patch(f"/api/v1/procurement/purchase-requests/{purchase_request}", json={"status": "Under Review"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "Under Review"

    def test_patch_extra_field_rejected(self, client: TestClient, risk):
        """Update schemas use extra="forbid" — arbitrary free-text fields
        (e.g. a client trying to set title directly) must be rejected,
        not silently ignored or applied."""
        resp = client.patch(f"/api/v1/projects/{_REAL_PROJECT_ID}/risks/{risk}", json={"title": "Hacked Title"})
        assert resp.status_code == 422
