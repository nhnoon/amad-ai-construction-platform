"""Tests for the Approval Engine (Sprint 5 — app/ai/approval_engine.py,
app/api/v1/approvals.py). Real Postgres DB (same pattern as
test_ownership_engine.py / test_notifications_engine.py). Covers: create,
reviewer validation, assign/reassign authorization, every valid/invalid
transition, unknown-status 400, required-note enforcement, PurchaseRequest
entity-mutation side effect, ChangeOrder/Claim/Document recorded-but-not-
mutated, Document target_version snapshot, requester/reviewer/manager
permission matrix, cross-tenant isolation, stale-concurrency/double-submit
protection, notifications (including dedup + transaction safety), approval
history, and .gitignore test-trackability.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from app.ai import approval_engine
from app.ai.notification_service import notify
from app.ai.scope import AIAuthScope
from app.ai.workflow_engine import validate_transition
from app.models.approvals import ApprovalHistory, ApprovalRequest
from app.models.claims import ChangeOrder, Claim
from app.models.documents import Document
from app.models.notifications import Notification
from app.models.procurement import PurchaseRequest
from tests.conftest import TEST_USER_ID, TEST_USER_ORGANIZATION_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_ORG_A = TEST_USER_ORGANIZATION_ID
_MANAGER_USER_ID = TEST_USER_ID  # real seeded admin — global read, manager authority
_ENGINEER_USER_ID = 4  # real seeded site_engineer — non-manager role
_PM_USER_ID = 3  # real seeded project_manager (global read, manager authority)


def _scope(user_id: int = _MANAGER_USER_ID, org_id: int = _ORG_A, role: str = "admin", membership_roles=None) -> AIAuthScope:
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"approval-scope-{user_id}@test.local", full_name="Approval Scope Test",
            role=role, is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
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


def _cross_org_scope(user_id: int = _MANAGER_USER_ID) -> AIAuthScope:
    return AIAuthScope(organization_id=999, user_id=user_id, user_role="admin", accessible_project_ids=())


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _cleanup_approval(db_session, approval_id: int) -> None:
    db_session.query(Notification).filter(Notification.entity_type == "approval", Notification.entity_id == approval_id).delete()
    db_session.query(ApprovalHistory).filter(ApprovalHistory.approval_request_id == approval_id).delete()
    db_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).delete()
    db_session.commit()


@pytest.fixture
def purchase_request(db_session):
    row = PurchaseRequest(project_id=_REAL_PROJECT_ID, request_no="APR-TEST-1", status="Under Review", created_at="2026-08-02")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(PurchaseRequest).filter(PurchaseRequest.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def change_order(db_session):
    row = ChangeOrder(project_id=_REAL_PROJECT_ID, co_number="APR-CO-1", description="Approval test CO", value=1000.0, status="Pending")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ChangeOrder).filter(ChangeOrder.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def claim(db_session):
    row = Claim(project_id=_REAL_PROJECT_ID, claim_number="APR-CLM-1", claim_type="Delay", amount=5000.0, status="Open", narrative="Approval test claim")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(Claim).filter(Claim.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def document(db_session):
    row = Document(
        project_id=_REAL_PROJECT_ID, doc_type="drawing", title="Approval Test Doc",
        doc_date="2026-08-02", content_summary="Test", version_number=1,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(Document).filter(Document.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def engineer_membership(db_session):
    from app.models.organizations import ProjectMembership
    row = ProjectMembership(user_id=_ENGINEER_USER_ID, project_id=_REAL_PROJECT_ID, role_on_project="site_engineer", is_active=True)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ProjectMembership).filter(ProjectMembership.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def inactive_user(db_session):
    from app.models.auth import UserAccount
    user = UserAccount(
        email="approval-inactive@test.local", hashed_password="x", full_name="Inactive Reviewer",
        role="project_manager", is_active=False, organization_id=_ORG_A,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user.id
    db_session.query(UserAccount).filter(UserAccount.id == user.id).delete()
    db_session.commit()


@pytest.fixture
def cross_org_user(db_session):
    from app.models.auth import UserAccount
    from app.models.organizations import Organization
    org = Organization(name="Approval Cross Org", slug=f"approval-cross-org-{datetime.now(timezone.utc).timestamp()}")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    user = UserAccount(
        email="approval-cross-org-user@test.local", hashed_password="x", full_name="Cross Org User",
        role="project_manager", is_active=True, organization_id=org.id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user.id
    db_session.query(UserAccount).filter(UserAccount.id == user.id).delete()
    db_session.query(Organization).filter(Organization.id == org.id).delete()
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────
# Create + reviewer validation
# ─────────────────────────────────────────────────────────────────────────
class TestCreateApproval:
    def test_create_for_purchase_request(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(
            db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request,
        )
        try:
            assert approval.status == "Pending"
            assert approval.requested_by_user_id == _MANAGER_USER_ID
            assert approval.organization_id == _ORG_A
            assert approval.project_id == _REAL_PROJECT_ID
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_create_for_change_order(self, db_session, change_order):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="change_order", entity_id=change_order)
        try:
            assert approval.entity_type == "change_order"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_create_for_claim(self, db_session, claim):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="claim", entity_id=claim)
        try:
            assert approval.entity_type == "claim"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_create_for_document_snapshots_target_version(self, db_session, document):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="document", entity_id=document)
        try:
            assert approval.target_version == 1
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_unsupported_entity_type_is_400(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            approval_engine.create_approval_request(db_session, _scope(), entity_type="ncr", entity_id=purchase_request)
        assert exc_info.value.status_code == 400

    def test_creates_history_row(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            history = db_session.query(ApprovalHistory).filter(ApprovalHistory.approval_request_id == approval.id).all()
            assert len(history) == 1
            assert history[0].previous_status is None
            assert history[0].new_status == "Pending"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_entity_in_another_organization_is_404(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            approval_engine.create_approval_request(db_session, _cross_org_scope(), entity_type="purchase_request", entity_id=purchase_request)
        assert exc_info.value.status_code == 404


class TestReviewerValidation:
    def test_nonexistent_reviewer_404(self, db_session, purchase_request):
        with pytest.raises(HTTPException) as exc_info:
            approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=999_999_999)
        assert exc_info.value.status_code == 404

    def test_cross_org_reviewer_404(self, db_session, purchase_request, cross_org_user):
        with pytest.raises(HTTPException) as exc_info:
            approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=cross_org_user)
        assert exc_info.value.status_code == 404

    def test_inactive_reviewer_409(self, db_session, purchase_request, inactive_user):
        with pytest.raises(HTTPException) as exc_info:
            approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=inactive_user)
        assert exc_info.value.status_code == 409

    def test_wrong_role_reviewer_409(self, db_session, purchase_request):
        # engineer (site_engineer) is not in _MANAGER_ROLES
        with pytest.raises(HTTPException) as exc_info:
            approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=_ENGINEER_USER_ID)
        assert exc_info.value.status_code == 409

    def test_valid_manager_reviewer_accepted(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=_PM_USER_ID)
        try:
            assert approval.assigned_reviewer_id == _PM_USER_ID
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# Assign / reassign
# ─────────────────────────────────────────────────────────────────────────
class TestAssignReviewer:
    def test_manager_can_assign(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            updated = approval_engine.assign_reviewer(db_session, _scope(), approval.id, _PM_USER_ID)
            assert updated.assigned_reviewer_id == _PM_USER_ID
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_non_manager_cannot_assign(self, db_session, purchase_request, engineer_membership):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.assign_reviewer(db_session, scope, approval.id, _PM_USER_ID)
            assert exc_info.value.status_code == 403
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_reassign_after_initial_assignment(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=_PM_USER_ID)
        try:
            updated = approval_engine.assign_reviewer(db_session, _scope(), approval.id, _MANAGER_USER_ID)
            assert updated.assigned_reviewer_id == _MANAGER_USER_ID
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_cannot_assign_after_terminal(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.assign_reviewer(db_session, _scope(), approval.id, _PM_USER_ID)
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# Transitions
# ─────────────────────────────────────────────────────────────────────────
class TestValidTransitions:
    def test_full_happy_path_pending_to_approved(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=_PM_USER_ID)
        try:
            reviewer_scope = _scope(user_id=_PM_USER_ID, role="project_manager")
            started = approval_engine.start_review(db_session, reviewer_scope, approval.id)
            assert started.status == "Under Review"
            approved = approval_engine.approve(db_session, reviewer_scope, approval.id, review_note="Looks good")
            assert approved.status == "Approved"
            assert approved.reviewed_by_user_id == _PM_USER_ID
            assert approved.reviewed_at is not None
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_pending_directly_to_approved(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approved = approval_engine.approve(db_session, _scope(), approval.id)
            assert approved.status == "Approved"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_reject_requires_and_records_reason(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            rejected = approval_engine.reject(db_session, _scope(), approval.id, "Budget exceeded")
            assert rejected.status == "Rejected"
            assert rejected.review_note == "Budget exceeded"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_return_then_resume_review(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            returned = approval_engine.return_for_changes(db_session, _scope(), approval.id, "Need more detail")
            assert returned.status == "Returned"
            resumed = approval_engine.start_review(db_session, _scope(), approval.id)
            assert resumed.status == "Under Review"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_cancel_by_requester(self, db_session, change_order):
        requester_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        approval = approval_engine.create_approval_request(db_session, requester_scope, entity_type="change_order", entity_id=change_order)
        try:
            cancelled = approval_engine.cancel(db_session, requester_scope, approval.id)
            assert cancelled.status == "Cancelled"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_cancel_by_manager_who_is_not_requester(self, db_session, change_order):
        requester_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        approval = approval_engine.create_approval_request(db_session, requester_scope, entity_type="change_order", entity_id=change_order)
        try:
            cancelled = approval_engine.cancel(db_session, _scope(), approval.id)
            assert cancelled.status == "Cancelled"
        finally:
            _cleanup_approval(db_session, approval.id)


class TestInvalidTransitions:
    def test_cannot_transition_from_terminal_approved(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.reject(db_session, _scope(), approval.id, "too late")
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_cannot_transition_from_terminal_rejected(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.reject(db_session, _scope(), approval.id, "no")
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.approve(db_session, _scope(), approval.id)
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_double_approve_is_409_not_double_applied(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.approve(db_session, _scope(), approval.id)
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_unknown_status_is_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("Approval request", approval_engine.APPROVAL_TRANSITIONS, "Pending", "NotARealStatus")
        assert exc_info.value.status_code == 400

    def test_reject_without_reason_is_409(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.reject(db_session, _scope(), approval.id, "   ")
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_return_without_reason_is_409(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.return_for_changes(db_session, _scope(), approval.id, "")
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# Business rules per entity
# ─────────────────────────────────────────────────────────────────────────
class TestEntityMutationRules:
    def test_purchase_request_status_moves_on_approve(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            db_session.expire_all()
            pr = db_session.query(PurchaseRequest).filter(PurchaseRequest.id == purchase_request).first()
            assert pr.status == "Approved"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_purchase_request_reject_requires_and_forwards_reason(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.reject(db_session, _scope(), approval.id, "Over budget")
            db_session.expire_all()
            pr = db_session.query(PurchaseRequest).filter(PurchaseRequest.id == purchase_request).first()
            assert pr.status == "Rejected"
            assert pr.rework_reason == "Over budget"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_purchase_request_underlying_workflow_conflict_fails_atomically(self, db_session, purchase_request):
        """The PR itself is "Under Review"; force it into a state that
        cannot reach Approved (e.g. Needs Rework has its own valid
        forward path, but jumping Pending Clarification -> Approved is
        not allowed) and confirm the approval action fails without
        silently marking the ApprovalRequest itself Approved."""
        db_session.execute(sa_text("UPDATE purchase_requests SET status = 'Pending Clarification' WHERE id = :id"), {"id": purchase_request})
        db_session.commit()
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            with pytest.raises(HTTPException):
                approval_engine.approve(db_session, _scope(), approval.id)
            db_session.expire_all()
            reloaded = db_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).first()
            assert reloaded.status == "Pending"  # never flipped
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_change_order_not_mutated_on_approve(self, db_session, change_order):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="change_order", entity_id=change_order)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            db_session.expire_all()
            co = db_session.query(ChangeOrder).filter(ChangeOrder.id == change_order).first()
            assert co.status == "Pending"  # untouched
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_claim_not_mutated_on_reject(self, db_session, claim):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="claim", entity_id=claim)
        try:
            approval_engine.reject(db_session, _scope(), approval.id, "Insufficient evidence")
            db_session.expire_all()
            row = db_session.query(Claim).filter(Claim.id == claim).first()
            assert row.status == "Open"  # untouched
            reloaded = db_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).first()
            assert reloaded.review_note == "Insufficient evidence"  # decision + note preserved
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_document_new_version_does_not_inherit_approval(self, db_session, document):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="document", entity_id=document)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            db_session.expire_all()
            doc = db_session.query(Document).filter(Document.id == document).first()
            assert doc.version_number == 1  # untouched by approval
            # simulate a new version being uploaded
            doc.version_number = 2
            db_session.commit()
            reloaded_approval = db_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).first()
            assert reloaded_approval.target_version == 1  # still pinned to the version that was actually approved
            assert reloaded_approval.target_version != doc.version_number
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# Authorization matrix
# ─────────────────────────────────────────────────────────────────────────
class TestAuthorizationMatrix:
    def test_requester_alone_cannot_approve(self, db_session, change_order):
        requester_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        approval = approval_engine.create_approval_request(db_session, requester_scope, entity_type="change_order", entity_id=change_order)
        try:
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.approve(db_session, requester_scope, approval.id)
            assert exc_info.value.status_code == 403
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_assigned_reviewer_can_approve_a_request_they_did_not_create(self, db_session, change_order):
        # Reviewers are structurally constrained to _MANAGER_ROLES by
        # validate_reviewer(), so the meaningful check here isn't "can a
        # non-manager reviewer approve" (impossible by construction) but
        # that the SPECIFIC assigned reviewer — not just any manager —
        # is the one whose approval actually applies.
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="change_order", entity_id=change_order, assigned_reviewer_id=_PM_USER_ID)
        try:
            reviewer_scope = _scope(user_id=_PM_USER_ID, role="project_manager")
            approved = approval_engine.approve(db_session, reviewer_scope, approval.id)
            assert approved.status == "Approved"
            assert approved.reviewed_by_user_id == _PM_USER_ID
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_random_user_cannot_cancel(self, db_session, change_order):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="change_order", entity_id=change_order)
        try:
            other_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.cancel(db_session, other_scope, approval.id)
            assert exc_info.value.status_code == 403
        finally:
            _cleanup_approval(db_session, approval.id)


class TestCrossTenantIsolation:
    def test_approval_from_another_org_is_404(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.get_approval_or_404(db_session, _cross_org_scope(), approval.id)
            assert exc_info.value.status_code == 404
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# Concurrency
# ─────────────────────────────────────────────────────────────────────────
class TestConcurrency:
    def test_stale_expected_updated_at_is_409(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            stale = datetime(2000, 1, 1, tzinfo=timezone.utc)
            with pytest.raises(HTTPException) as exc_info:
                approval_engine.approve(db_session, _scope(), approval.id, expected_updated_at=stale)
            assert exc_info.value.status_code == 409
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_correct_expected_updated_at_succeeds(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approved = approval_engine.approve(db_session, _scope(), approval.id, expected_updated_at=approval.updated_at)
            assert approved.status == "Approved"
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────
class TestApprovalNotifications:
    def test_create_with_reviewer_notifies_reviewer(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request, assigned_reviewer_id=_PM_USER_ID)
        try:
            n = db_session.query(Notification).filter(Notification.entity_type == "approval", Notification.entity_id == approval.id, Notification.recipient_user_id == _PM_USER_ID).first()
            assert n is not None
            assert n.event_type == "approval_requested"
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_decision_notifies_requester(self, db_session, change_order):
        requester_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        approval = approval_engine.create_approval_request(db_session, requester_scope, entity_type="change_order", entity_id=change_order)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            n = db_session.query(Notification).filter(
                Notification.entity_type == "approval", Notification.entity_id == approval.id,
                Notification.recipient_user_id == _ENGINEER_USER_ID, Notification.event_type == "approval_approved",
            ).first()
            assert n is not None
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_actor_never_notifies_self(self, db_session, purchase_request):
        # manager both requests and approves their own request — requester
        # notification would be a self-notification and must not exist.
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.approve(db_session, _scope(), approval.id)
            count = db_session.query(Notification).filter(Notification.entity_type == "approval", Notification.entity_id == approval.id).count()
            assert count == 0
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_identical_notify_calls_dedup_to_one_row(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            kwargs = dict(
                organization_id=_ORG_A, recipient_user_id=_PM_USER_ID, actor_user_id=_MANAGER_USER_ID,
                project_id=_REAL_PROJECT_ID, event_type="approval_requested", entity_type="approval", entity_id=approval.id,
                title="Approval requested", message="test", severity="info", action_url="/x",
                deduplication_key=f"approval:{approval.id}:{_PM_USER_ID}:approval_requested",
            )
            notify(db_session, **kwargs)
            notify(db_session, **kwargs)
            rows = db_session.query(Notification).filter(Notification.entity_type == "approval", Notification.entity_id == approval.id, Notification.recipient_user_id == _PM_USER_ID).all()
            assert len(rows) == 1
        finally:
            _cleanup_approval(db_session, approval.id)

    def test_notification_failure_does_not_break_approval(self, db_session, change_order, monkeypatch):
        requester_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        approval = approval_engine.create_approval_request(db_session, requester_scope, entity_type="change_order", entity_id=change_order)
        try:
            monkeypatch.setattr("app.ai.notification_service.notify", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
            approved = approval_engine.approve(db_session, _scope(), approval.id)
            assert approved.status == "Approved"  # the real decision still succeeded
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# History
# ─────────────────────────────────────────────────────────────────────────
class TestApprovalHistory:
    def test_history_recorded_in_order(self, db_session, purchase_request):
        approval = approval_engine.create_approval_request(db_session, _scope(), entity_type="purchase_request", entity_id=purchase_request)
        try:
            approval_engine.start_review(db_session, _scope(), approval.id)
            approval_engine.reject(db_session, _scope(), approval.id, "no good")
            history = approval_engine.get_history(db_session, _scope(), approval.id)
            assert [h.new_status for h in history] == ["Pending", "Under Review", "Rejected"]
            assert history[-1].note == "no good"
        finally:
            _cleanup_approval(db_session, approval.id)


# ─────────────────────────────────────────────────────────────────────────
# HTTP-level
# ─────────────────────────────────────────────────────────────────────────
class TestHTTPRoutes:
    def test_full_lifecycle_via_http(self, client: TestClient, db_session, purchase_request):
        resp = client.post("/api/v1/approvals", json={"entity_type": "purchase_request", "entity_id": purchase_request})
        assert resp.status_code == 201
        approval_id = resp.json()["id"]
        try:
            resp2 = client.post(f"/api/v1/approvals/{approval_id}/approve", json={})
            assert resp2.status_code == 200
            assert resp2.json()["status"] == "Approved"

            resp3 = client.get(f"/api/v1/approvals/{approval_id}")
            assert resp3.status_code == 200

            resp4 = client.get(f"/api/v1/approvals/{approval_id}/history")
            assert resp4.status_code == 200
            assert len(resp4.json()) == 2
        finally:
            _cleanup_approval(db_session, approval_id)

    def test_summary_route_not_shadowed_by_id_route(self, client: TestClient):
        resp = client.get("/api/v1/approvals/summary")
        assert resp.status_code == 200
        assert "by_status" in resp.json()

    def test_reject_without_reason_via_http_is_409(self, client: TestClient, db_session, purchase_request):
        resp = client.post("/api/v1/approvals", json={"entity_type": "purchase_request", "entity_id": purchase_request})
        approval_id = resp.json()["id"]
        try:
            resp2 = client.post(f"/api/v1/approvals/{approval_id}/reject", json={"review_note": ""})
            assert resp2.status_code == 409
        finally:
            _cleanup_approval(db_session, approval_id)

    def test_extra_field_rejected(self, client: TestClient, db_session, purchase_request):
        resp = client.post("/api/v1/approvals", json={"entity_type": "purchase_request", "entity_id": purchase_request, "hacked": True})
        assert resp.status_code == 422

    def test_list_filters_by_assigned_to_me(self, client: TestClient, db_session, purchase_request):
        resp = client.post("/api/v1/approvals", json={"entity_type": "purchase_request", "entity_id": purchase_request, "assigned_reviewer_id": _MANAGER_USER_ID})
        approval_id = resp.json()["id"]
        try:
            resp2 = client.get("/api/v1/approvals", params={"assigned_to_me": True, "limit": 100})
            assert resp2.status_code == 200
            assert any(a["id"] == approval_id for a in resp2.json())
        finally:
            _cleanup_approval(db_session, approval_id)


# ─────────────────────────────────────────────────────────────────────────
# .gitignore / test trackability (Sprint 5 pre-check items 3-4)
# ─────────────────────────────────────────────────────────────────────────
class TestGitignoreHygiene:
    def test_backend_tests_directory_is_not_gitignored(self):
        repo_root = Path(__file__).resolve().parents[2]
        try:
            result = subprocess.run(
                ["git", "check-ignore", "backend/tests/test_approval_engine.py"],
                cwd=repo_root, capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("git not available in this environment")
            return
        # git check-ignore exits 1 (not ignored) — 0 would mean still ignored.
        assert result.returncode == 1, f"backend/tests/test_*.py is still gitignored: {result.stdout}"

    def test_backend_root_debug_scripts_still_ignored(self):
        repo_root = Path(__file__).resolve().parents[2]
        try:
            result = subprocess.run(
                ["git", "check-ignore", "backend/test_api.py"],
                cwd=repo_root, capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("git not available in this environment")
            return
        assert result.returncode == 0  # still correctly ignored
