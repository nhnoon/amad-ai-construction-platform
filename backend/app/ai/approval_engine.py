"""Approval Engine (Sprint 5) — real, per-entity approve/reject/return
workflows for PurchaseRequest, ChangeOrder, Claim, and Document. Design
mirrors app/ai/ownership_engine.py (Sprint 3) and app/ai/workflow_engine.py
(Sprint 2) deliberately: small guard helpers + one explicit transition
matrix, reusing app/ai/workflow_engine.py::validate_transition directly
(it is already fully generic — 400 for an unrecognized target status, 409
for a disallowed transition, no-op-to-self always allowed) rather than
duplicating it. `_MANAGER_ROLES` / `_check_concurrency` are duplicated
(not imported) from the equivalent private helpers in ownership_engine.py
/ workflow_engine.py — the same documented precedent those two files
already established for each other: avoid modifying a prior sprint's
file for a cross-module import of a private name.

Business rules per entity (see the Sprint 5 report for the full
rationale):
  - PurchaseRequest: approve/reject/return call directly into the
    *existing* app/ai/workflow_engine.py::update_purchase_request, so its
    own transition matrix, its own reason-required guard, and its own
    Sprint 4 notification hook all still apply — zero duplicated logic.
    That call happens BEFORE this module's own ApprovalRequest status is
    committed, so if the underlying PurchaseRequest can't accept the
    transition (e.g. it isn't "Under Review"), the whole approval action
    fails atomically with that same error — nothing here is left
    half-applied.
  - ChangeOrder / Claim: intentionally NO entity mutation. Neither table
    has an updated_at/concurrency column or any prior workflow engine;
    inventing one now to silently start mutating status/value would be
    exactly the "fabricating behavior" the sprint brief warns against.
    The ApprovalRequest row (+ its history) is the sole, fully-auditable
    record of the decision.
  - Document: approval is pinned to `target_version`
    (DocumentVersion.version_number), snapshotted at request-creation
    time. No `is_approved` flag is added to Document itself — "is the
    CURRENT version approved" is answered by comparing
    Document.version_number to the latest Approved ApprovalRequest's
    target_version, so a later re-upload never silently inherits an
    earlier approval.

Notifications: every lifecycle action ends by calling the relevant
app/ai/notification_service.py::notify_approval_* helper exactly once,
best-effort (see that module's own docstring) — a notification failure
can never affect an already-committed approval decision.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Query, Session

from app.ai.document_access import get_authorized_document
from app.ai.notification_service import (
    notify_approval_assigned,
    notify_approval_cancelled,
    notify_approval_decided,
    notify_approval_requested,
    notify_approval_review_started,
)
from app.ai.scope import AIAuthScope, get_project_or_404
from app.ai.workflow_engine import update_purchase_request, validate_transition
from app.core.audit_log import AuditAction, AuditEntityType, AuditResult, record_audit_event
from app.models.approvals import ApprovalHistory, ApprovalRequest
from app.models.auth import UserAccount
from app.models.claims import ChangeOrder, Claim
from app.models.documents import Document
from app.models.procurement import PurchaseRequest
from app.models.projects import Project
from app.schemas.procurement import PurchaseRequestUpdate

ENTITY_PURCHASE_REQUEST = "purchase_request"
ENTITY_CHANGE_ORDER = "change_order"
ENTITY_CLAIM = "claim"
ENTITY_DOCUMENT = "document"
SUPPORTED_ENTITY_TYPES = frozenset({ENTITY_PURCHASE_REQUEST, ENTITY_CHANGE_ORDER, ENTITY_CLAIM, ENTITY_DOCUMENT})

# Same role set as ownership_engine.py's _MANAGER_ROLES / scope.py's
# _GLOBAL_READ_ROLES — duplicated deliberately, see module docstring.
_MANAGER_ROLES = frozenset({"admin", "executive", "project_manager"})

STATUS_PENDING = "Pending"
STATUS_UNDER_REVIEW = "Under Review"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"
STATUS_RETURNED = "Returned"
STATUS_CANCELLED = "Cancelled"

APPROVAL_TRANSITIONS: dict[str, set[str]] = {
    STATUS_PENDING: {STATUS_UNDER_REVIEW, STATUS_APPROVED, STATUS_REJECTED, STATUS_RETURNED, STATUS_CANCELLED},
    STATUS_UNDER_REVIEW: {STATUS_APPROVED, STATUS_REJECTED, STATUS_RETURNED, STATUS_CANCELLED},
    STATUS_RETURNED: {STATUS_UNDER_REVIEW, STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED},
    STATUS_APPROVED: set(),
    STATUS_REJECTED: set(),
    STATUS_CANCELLED: set(),
}
_TERMINAL_STATUSES = {STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_concurrency(current_updated_at, expected_updated_at) -> None:
    """Duplicated (not imported) from workflow_engine.py's private helper
    of the same shape — see module docstring."""
    if expected_updated_at is None:
        return
    if current_updated_at != expected_updated_at:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Approval request was modified since you last loaded it. Reload and try again.",
        )


def _validate_approval_transition(old_status: str, new_status: str) -> None:
    """workflow_engine.py::validate_transition treats new_status ==
    current_status as an always-allowed no-op — correct for its own
    PATCH-with-optional-fields use case (e.g. reassigning owner while
    redundantly repeating the current status), but WRONG here: every
    approval action is a single-purpose verb with no other field being
    updated alongside it, so a repeated call (double form-submit, a
    stale client retry, a genuine double-approval race) must surface as
    a 409 "already decided" conflict, not silently succeed a second
    time. This is the one deliberate divergence from the reused matrix
    validator — everything else about it (unknown-status 400, matrix-
    disallowed 409) is identical."""
    if new_status == old_status:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Approval request is already '{old_status}'.",
        )
    validate_transition("Approval request", APPROVAL_TRANSITIONS, old_status, new_status)


def _require_nonempty(value: Optional[str], action_label: str) -> None:
    if not (value or "").strip():
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"A non-empty review_note is required to {action_label}.",
        )


def _can_manage(scope: AIAuthScope, project_id: Optional[int]) -> bool:
    if scope.has_global_read:
        return True
    if project_id is None:
        return False
    return scope.project_membership_roles.get(project_id) in _MANAGER_ROLES


def _is_reviewer_or_manager(scope: AIAuthScope, approval: ApprovalRequest) -> bool:
    if approval.assigned_reviewer_id == scope.user_id:
        return True
    return _can_manage(scope, approval.project_id)


# ─────────────────────────────────────────────────────────────────────────
# Entity resolution — one function per supported entity_type, reusing the
# existing canonical fetch/authorize helper for each rather than
# reinventing tenant rules. Returns (row, project_id_or_None). The
# approval's own organization_id is always scope.organization_id — by the
# time any of these returns, access has already been confirmed to be
# within the caller's own organization, so no separate per-entity
# organization_id resolution is needed.
# ─────────────────────────────────────────────────────────────────────────
def _resolve_purchase_request(db: Session, scope: AIAuthScope, entity_id: int) -> tuple[PurchaseRequest, int]:
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == entity_id).first()
    project = db.query(Project).filter(Project.id == pr.project_id).first() if pr is not None else None
    if pr is None or project is None or project.organization_id != scope.organization_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Purchase request not found")
    if not scope.can_access_project(pr.project_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied to this purchase request")
    return pr, project.id


def _resolve_change_order(db: Session, scope: AIAuthScope, entity_id: int) -> tuple[ChangeOrder, int]:
    row = db.query(ChangeOrder).filter(ChangeOrder.id == entity_id).first()
    if row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Change order not found")
    get_project_or_404(db, scope, row.project_id)
    return row, row.project_id


def _resolve_claim(db: Session, scope: AIAuthScope, entity_id: int) -> tuple[Claim, int]:
    row = db.query(Claim).filter(Claim.id == entity_id).first()
    if row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Claim not found")
    get_project_or_404(db, scope, row.project_id)
    return row, row.project_id


def _resolve_document(db: Session, scope: AIAuthScope, entity_id: int) -> tuple[Document, Optional[int]]:
    document = get_authorized_document(db, scope, entity_id)
    return document, document.project_id


def resolve_entity(db: Session, scope: AIAuthScope, entity_type: str, entity_id: int) -> tuple[object, Optional[int]]:
    if entity_type == ENTITY_PURCHASE_REQUEST:
        return _resolve_purchase_request(db, scope, entity_id)
    if entity_type == ENTITY_CHANGE_ORDER:
        return _resolve_change_order(db, scope, entity_id)
    if entity_type == ENTITY_CLAIM:
        return _resolve_claim(db, scope, entity_id)
    if entity_type == ENTITY_DOCUMENT:
        return _resolve_document(db, scope, entity_id)
    raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Unsupported entity_type '{entity_type}'.")


# ─────────────────────────────────────────────────────────────────────────
# Reviewer validation — real UserAccount rows only, never free text.
# Project access is implied by the role check itself: _MANAGER_ROLES is
# exactly scope.py's _GLOBAL_READ_ROLES set, and a global-read role
# already has implicit access to every project in its own organization
# (see build_ai_scope) — so no separate ProjectMembership query is
# needed once role membership is confirmed.
# ─────────────────────────────────────────────────────────────────────────
def validate_reviewer(db: Session, scope: AIAuthScope, reviewer_user_id: int) -> UserAccount:
    reviewer = db.query(UserAccount).filter(UserAccount.id == reviewer_user_id).first()
    if reviewer is None or reviewer.organization_id != scope.organization_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Reviewer not found")
    if not reviewer.is_active:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Cannot assign an inactive reviewer.")
    if reviewer.role not in _MANAGER_ROLES:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"{reviewer.email} does not have an allowed reviewer role ({', '.join(sorted(_MANAGER_ROLES))}).",
        )
    return reviewer


# ─────────────────────────────────────────────────────────────────────────
# Access to an existing ApprovalRequest row.
# ─────────────────────────────────────────────────────────────────────────
def get_approval_or_404(db: Session, scope: AIAuthScope, approval_id: int) -> ApprovalRequest:
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if approval is None or approval.organization_id != scope.organization_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Approval request not found")
    if approval.project_id is not None:
        scope.enforce_project_access(approval.project_id)
    return approval


def _write_history(db: Session, approval: ApprovalRequest, *, previous_status: Optional[str], new_status: str, actor_user_id: int, note: Optional[str]) -> None:
    db.add(ApprovalHistory(
        approval_request_id=approval.id, previous_status=previous_status, new_status=new_status,
        actor_user_id=actor_user_id, note=note,
    ))


def _entity_label(entity_type: str, entity_id: int) -> str:
    return f"{entity_type.replace('_', ' ')} #{entity_id}"


# ─────────────────────────────────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────────────────────────────────
def create_approval_request(
    db: Session, scope: AIAuthScope, *, entity_type: str, entity_id: int,
    risk_level: str = "medium", review_note: Optional[str] = None,
    assigned_reviewer_id: Optional[int] = None, due_at: Optional[datetime] = None,
) -> ApprovalRequest:
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity_type '{entity_type}'. Supported: {', '.join(sorted(SUPPORTED_ENTITY_TYPES))}.",
        )
    entity, project_id = resolve_entity(db, scope, entity_type, entity_id)

    if assigned_reviewer_id is not None:
        validate_reviewer(db, scope, assigned_reviewer_id)

    target_version = entity.version_number if entity_type == ENTITY_DOCUMENT else None

    approval = ApprovalRequest(
        organization_id=scope.organization_id, project_id=project_id,
        entity_type=entity_type, entity_id=entity_id,
        requested_by_user_id=scope.user_id, assigned_reviewer_id=assigned_reviewer_id,
        risk_level=risk_level, status=STATUS_PENDING, review_note=review_note,
        due_at=due_at, target_version=target_version,
    )
    db.add(approval)
    db.flush()
    _write_history(db, approval, previous_status=None, new_status=STATUS_PENDING, actor_user_id=scope.user_id, note=review_note)
    db.commit()
    db.refresh(approval)

    notify_approval_requested(db, approval=approval, actor_user_id=scope.user_id, entity_label=_entity_label(entity_type, entity_id))
    return approval


def assign_reviewer(db: Session, scope: AIAuthScope, approval_id: int, reviewer_user_id: int, expected_updated_at: Optional[datetime] = None) -> ApprovalRequest:
    approval = get_approval_or_404(db, scope, approval_id)
    if approval.status in _TERMINAL_STATUSES:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=f"Approval request is already '{approval.status}'; cannot (re)assign a reviewer.")
    if not _can_manage(scope, approval.project_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only managers can assign/reassign the reviewer.")
    _check_concurrency(approval.updated_at, expected_updated_at)
    validate_reviewer(db, scope, reviewer_user_id)

    previous_reviewer_id = approval.assigned_reviewer_id
    approval.assigned_reviewer_id = reviewer_user_id
    db.commit()
    db.refresh(approval)

    notify_approval_assigned(
        db, approval=approval, actor_user_id=scope.user_id,
        previous_reviewer_id=previous_reviewer_id, entity_label=_entity_label(approval.entity_type, approval.entity_id),
    )
    record_audit_event(
        entity_type=AuditEntityType.APPROVAL_REQUEST, entity_id=approval.id, action=AuditAction.REVIEWER_ASSIGN,
        result=AuditResult.SUCCESS, organization_id=approval.organization_id, actor_user_id=scope.user_id,
        project_id=approval.project_id,
        before_state={"assigned_reviewer_id": previous_reviewer_id},
        after_state={"assigned_reviewer_id": reviewer_user_id},
    )
    return approval


def start_review(db: Session, scope: AIAuthScope, approval_id: int, expected_updated_at: Optional[datetime] = None) -> ApprovalRequest:
    approval = get_approval_or_404(db, scope, approval_id)
    if not _is_reviewer_or_manager(scope, approval):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only the assigned reviewer or a manager can start review.")
    _check_concurrency(approval.updated_at, expected_updated_at)

    old_status = approval.status
    _validate_approval_transition(old_status, STATUS_UNDER_REVIEW)
    approval.status = STATUS_UNDER_REVIEW
    _write_history(db, approval, previous_status=old_status, new_status=STATUS_UNDER_REVIEW, actor_user_id=scope.user_id, note=None)
    db.commit()
    db.refresh(approval)

    notify_approval_review_started(db, approval=approval, actor_user_id=scope.user_id, entity_label=_entity_label(approval.entity_type, approval.entity_id))
    return approval


def _apply_entity_decision(db: Session, scope: AIAuthScope, approval: ApprovalRequest, target_status: str, review_note: Optional[str]) -> None:
    """PurchaseRequest is the one entity whose approval decision also
    mutates the source row — via the *existing* Sprint 2 workflow engine,
    not duplicated logic. Runs BEFORE the ApprovalRequest's own status is
    changed, so a rejected-by-the-underlying-workflow transition (e.g.
    the PR isn't in a state that can move) fails the whole action
    atomically instead of leaving the approval and the PR out of sync."""
    if approval.entity_type != ENTITY_PURCHASE_REQUEST:
        return

    pr_status_map = {
        STATUS_APPROVED: "Approved",
        STATUS_REJECTED: "Rejected",
        STATUS_RETURNED: "Returned to Requester",
    }
    pr_status = pr_status_map.get(target_status)
    if pr_status is None:
        return
    patch_kwargs = {"status": pr_status}
    if pr_status in ("Rejected", "Returned to Requester"):
        patch_kwargs["rework_reason"] = review_note
    update_purchase_request(db, scope, approval.entity_id, PurchaseRequestUpdate(**patch_kwargs))


def approve(db: Session, scope: AIAuthScope, approval_id: int, review_note: Optional[str] = None, expected_updated_at: Optional[datetime] = None) -> ApprovalRequest:
    approval = get_approval_or_404(db, scope, approval_id)
    if not _is_reviewer_or_manager(scope, approval):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only the assigned reviewer or a manager can approve.")
    _check_concurrency(approval.updated_at, expected_updated_at)
    old_status = approval.status
    _validate_approval_transition(old_status, STATUS_APPROVED)

    _apply_entity_decision(db, scope, approval, STATUS_APPROVED, review_note)

    if review_note is not None:
        approval.review_note = review_note
    approval.status = STATUS_APPROVED
    approval.reviewed_by_user_id = scope.user_id
    approval.reviewed_at = _now()
    _write_history(db, approval, previous_status=old_status, new_status=STATUS_APPROVED, actor_user_id=scope.user_id, note=review_note)
    db.commit()
    db.refresh(approval)

    notify_approval_decided(db, approval=approval, actor_user_id=scope.user_id, entity_label=_entity_label(approval.entity_type, approval.entity_id))
    record_audit_event(
        entity_type=AuditEntityType.APPROVAL_REQUEST, entity_id=approval.id, action=AuditAction.APPROVE,
        result=AuditResult.SUCCESS, organization_id=approval.organization_id, actor_user_id=scope.user_id,
        project_id=approval.project_id, before_state={"status": old_status}, after_state={"status": approval.status},
        reason=review_note,
    )
    return approval


def reject(db: Session, scope: AIAuthScope, approval_id: int, review_note: str, expected_updated_at: Optional[datetime] = None) -> ApprovalRequest:
    _require_nonempty(review_note, "reject an approval request")
    approval = get_approval_or_404(db, scope, approval_id)
    if not _is_reviewer_or_manager(scope, approval):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only the assigned reviewer or a manager can reject.")
    _check_concurrency(approval.updated_at, expected_updated_at)
    old_status = approval.status
    _validate_approval_transition(old_status, STATUS_REJECTED)

    _apply_entity_decision(db, scope, approval, STATUS_REJECTED, review_note)

    approval.review_note = review_note
    approval.status = STATUS_REJECTED
    approval.reviewed_by_user_id = scope.user_id
    approval.reviewed_at = _now()
    _write_history(db, approval, previous_status=old_status, new_status=STATUS_REJECTED, actor_user_id=scope.user_id, note=review_note)
    db.commit()
    db.refresh(approval)

    notify_approval_decided(db, approval=approval, actor_user_id=scope.user_id, entity_label=_entity_label(approval.entity_type, approval.entity_id))
    record_audit_event(
        entity_type=AuditEntityType.APPROVAL_REQUEST, entity_id=approval.id, action=AuditAction.REJECT,
        result=AuditResult.SUCCESS, organization_id=approval.organization_id, actor_user_id=scope.user_id,
        project_id=approval.project_id, before_state={"status": old_status}, after_state={"status": approval.status},
        reason=review_note,
    )
    return approval


def return_for_changes(db: Session, scope: AIAuthScope, approval_id: int, review_note: str, expected_updated_at: Optional[datetime] = None) -> ApprovalRequest:
    _require_nonempty(review_note, "return an approval request for changes")
    approval = get_approval_or_404(db, scope, approval_id)
    if not _is_reviewer_or_manager(scope, approval):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only the assigned reviewer or a manager can return an approval request.")
    _check_concurrency(approval.updated_at, expected_updated_at)
    old_status = approval.status
    _validate_approval_transition(old_status, STATUS_RETURNED)

    _apply_entity_decision(db, scope, approval, STATUS_RETURNED, review_note)

    approval.review_note = review_note
    approval.status = STATUS_RETURNED
    _write_history(db, approval, previous_status=old_status, new_status=STATUS_RETURNED, actor_user_id=scope.user_id, note=review_note)
    db.commit()
    db.refresh(approval)

    notify_approval_decided(db, approval=approval, actor_user_id=scope.user_id, entity_label=_entity_label(approval.entity_type, approval.entity_id))
    record_audit_event(
        entity_type=AuditEntityType.APPROVAL_REQUEST, entity_id=approval.id, action=AuditAction.RETURN,
        result=AuditResult.SUCCESS, organization_id=approval.organization_id, actor_user_id=scope.user_id,
        project_id=approval.project_id, before_state={"status": old_status}, after_state={"status": approval.status},
        reason=review_note,
    )
    return approval


def cancel(db: Session, scope: AIAuthScope, approval_id: int, review_note: Optional[str] = None, expected_updated_at: Optional[datetime] = None) -> ApprovalRequest:
    approval = get_approval_or_404(db, scope, approval_id)
    is_requester = approval.requested_by_user_id == scope.user_id
    if not is_requester and not _can_manage(scope, approval.project_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only the requester or a manager can cancel an approval request.")
    _check_concurrency(approval.updated_at, expected_updated_at)
    old_status = approval.status
    _validate_approval_transition(old_status, STATUS_CANCELLED)

    if review_note is not None:
        approval.review_note = review_note
    approval.status = STATUS_CANCELLED
    _write_history(db, approval, previous_status=old_status, new_status=STATUS_CANCELLED, actor_user_id=scope.user_id, note=review_note)
    db.commit()
    db.refresh(approval)

    notify_approval_cancelled(db, approval=approval, actor_user_id=scope.user_id, entity_label=_entity_label(approval.entity_type, approval.entity_id))
    record_audit_event(
        entity_type=AuditEntityType.APPROVAL_REQUEST, entity_id=approval.id, action=AuditAction.CANCEL,
        result=AuditResult.SUCCESS, organization_id=approval.organization_id, actor_user_id=scope.user_id,
        project_id=approval.project_id, before_state={"status": old_status}, after_state={"status": approval.status},
        reason=review_note,
    )
    return approval


def get_history(db: Session, scope: AIAuthScope, approval_id: int) -> list[ApprovalHistory]:
    get_approval_or_404(db, scope, approval_id)
    return (
        db.query(ApprovalHistory)
        .filter(ApprovalHistory.approval_request_id == approval_id)
        .order_by(ApprovalHistory.id.asc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────
# Query support
# ─────────────────────────────────────────────────────────────────────────
def apply_approval_filters(
    query: Query, scope: AIAuthScope, *,
    status: Optional[str] = None, entity_type: Optional[str] = None, project_id: Optional[int] = None,
    assigned_to_me: bool = False, requested_by_me: bool = False,
    overdue: bool = False, due_soon: bool = False, due_soon_days: int = 7,
) -> Query:
    query = query.filter(ApprovalRequest.organization_id == scope.organization_id)
    if status is not None:
        query = query.filter(ApprovalRequest.status == status)
    if entity_type is not None:
        query = query.filter(ApprovalRequest.entity_type == entity_type)
    if project_id is not None:
        query = query.filter(ApprovalRequest.project_id == project_id)
    if assigned_to_me:
        query = query.filter(ApprovalRequest.assigned_reviewer_id == scope.user_id)
    if requested_by_me:
        query = query.filter(ApprovalRequest.requested_by_user_id == scope.user_id)
    if overdue:
        now = _now()
        query = query.filter(ApprovalRequest.due_at.isnot(None), ApprovalRequest.due_at < now, ApprovalRequest.status.notin_(_TERMINAL_STATUSES))
    if due_soon:
        now = _now()
        cutoff = now + timedelta(days=due_soon_days)
        query = query.filter(ApprovalRequest.due_at.isnot(None), ApprovalRequest.due_at >= now, ApprovalRequest.due_at <= cutoff, ApprovalRequest.status.notin_(_TERMINAL_STATUSES))
    return query
