"""Ownership Engine (Sprint 3) — real user assignment for the six
workflow-shaped entities, replacing free-text ownership as the source of
truth while preserving it for backward compatibility.

Design mirrors app/ai/workflow_engine.py (Sprint 2) deliberately: one
small function per entity for fetch/authorize, delegating to two shared
internal implementations (_do_assign / _do_unassign) so the actual
assignment/history/authorization logic exists exactly once. Not a generic
"ownership framework" — six entities, one shared core, matching the
sprint brief's own "do not invent another user model" / keep-it-simple
instruction.

Authorization model:
  - Self-assign ("I'll take this") and self-release are always allowed to
    anyone with project access — no manager role required.
  - Assigning to, or unassigning, SOMEONE ELSE requires "manager"
    authority: either a global-read role (admin/executive/project_manager
    — the same role set AIAuthScope.has_global_read already uses) or that
    role as the caller's role_on_project for this specific project.
  - The target user must exist, belong to the caller's own organization,
    and be able to access the project (global-read role in that org, or
    an active ProjectMembership) — otherwise the assignment is rejected
    before anything is written.

Notifications: Sprint 4 (app/ai/notification_service.py) hooks into
emit_assignment_event() below — every assign/unassign/reassign call ends
by calling it exactly once, now with the db session and enough context
(organization_id, entity_label) to persist a notification, best-effort
(a notification failure can never affect the already-committed
assignment — see notification_service.py's own docstring).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Query, Session

from app.ai.entity_refs import entity_label as _entity_label
from app.ai.notification_service import notify_assignment
from app.ai.scope import AIAuthScope, get_project_or_404
from app.core.audit_log import AuditAction, AuditResult, record_audit_event
from app.models.auth import UserAccount
from app.models.meetings import MeetingActionItem
from app.models.organizations import ProjectMembership
from app.models.procurement import PurchaseRequest
from app.models.projects import Project, ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from app.models.assignment_history import AssignmentHistory

logger = logging.getLogger(__name__)

# Same role set as AIAuthScope.has_global_read (app/ai/scope.py) — not
# re-imported (that constant is module-private there) but intentionally
# identical: "manager" authority and "implicit org-wide project access"
# are the same underlying broad-authority concept in this app.
_MANAGER_ROLES = frozenset({"admin", "executive", "project_manager"})

ENTITY_PROJECT_RISK = "project_risk"
ENTITY_PROJECT_ISSUE = "project_issue"
ENTITY_ACTION_ITEM = "action_item"
ENTITY_SAFETY_EVENT = "safety_event"
ENTITY_NCR = "ncr"
ENTITY_PURCHASE_REQUEST = "purchase_request"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_concurrency(entity_label: str, current_updated_at, expected_updated_at) -> None:
    """Duplicated (not imported) from app/ai/workflow_engine.py's private
    helper of the same shape — deliberately, to avoid modifying a Sprint 2
    file for a cross-module import. Same semantics: omitted -> no check;
    provided and mismatched -> 409."""
    if expected_updated_at is None:
        return
    if current_updated_at != expected_updated_at:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"{entity_label} was modified since you last loaded it. Reload and try again.",
        )


def _can_manage_assignments(scope: AIAuthScope, project_id: int) -> bool:
    if scope.has_global_read:
        return True
    return scope.project_membership_roles.get(project_id) in _MANAGER_ROLES


def _user_can_be_assigned(db: Session, target_user: UserAccount, project: Project) -> bool:
    """Mirrors build_ai_scope()'s own notion of project access: a
    global-read role gets every project in their organization implicitly
    (no explicit membership row required, same as their own scope would
    show); every other role needs an active ProjectMembership."""
    if target_user.organization_id != project.organization_id:
        return False
    if target_user.role in _MANAGER_ROLES:
        return True
    membership = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.user_id == target_user.id,
            ProjectMembership.project_id == project.id,
            ProjectMembership.is_active.is_(True),
        )
        .first()
    )
    return membership is not None


def _resolve_target_user(db: Session, scope: AIAuthScope, project: Project, user_id: int) -> UserAccount:
    """404 (not 403) for both "doesn't exist" and "exists in another
    organization" — consistent with this app's existing hide-cross-tenant-
    existence policy (get_project_or_404, get_authorized_document)."""
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if user is None or user.organization_id != scope.organization_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Cannot assign to an inactive user.")
    if not _user_can_be_assigned(db, user, project):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"{user.email} does not have access to this project; add them as a project member before assigning.",
        )
    return user


# ─────────────────────────────────────────────────────────────────────────
# Notification integration point (Sprint 4 hooks in here — see module
# docstring). "Emit" means a structured log line only in this sprint; no
# notification is sent.
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AssignmentEvent:
    action: str  # "assigned" | "reassigned" | "unassigned"
    entity_type: str
    entity_id: int
    project_id: int
    organization_id: int
    entity_label: str
    previous_owner_id: Optional[int]
    new_owner_id: Optional[int]
    assigned_by: int
    assigned_at: datetime


def emit_assignment_event(db: Session, event: AssignmentEvent) -> None:
    logger.info(
        "assignment_event action=%s entity_type=%s entity_id=%s project_id=%s "
        "previous_owner_id=%s new_owner_id=%s assigned_by=%s assigned_at=%s",
        event.action, event.entity_type, event.entity_id, event.project_id,
        event.previous_owner_id, event.new_owner_id, event.assigned_by,
        event.assigned_at.isoformat(),
    )
    try:
        notify_assignment(db, event)
    except Exception:
        logger.exception(
            "emit_assignment_event_notification_failed action=%s entity_type=%s entity_id=%s",
            event.action, event.entity_type, event.entity_id,
        )


# ─────────────────────────────────────────────────────────────────────────
# Shared core — the only place that actually mutates a row's ownership.
# ─────────────────────────────────────────────────────────────────────────
def _do_assign(
    db: Session, scope: AIAuthScope, row, entity_type: str, project: Project,
    target_user_id: int, expected_updated_at, *, has_legacy_owner: bool,
) -> object:
    _check_concurrency(entity_type, row.updated_at, expected_updated_at)
    target_user = _resolve_target_user(db, scope, project, target_user_id)

    is_self_assign = target_user_id == scope.user_id
    if not is_self_assign and not _can_manage_assignments(scope, project.id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only managers can assign to other users.")

    previous_owner_id = row.owner_id
    now = _now()

    row.owner_id = target_user_id
    if has_legacy_owner:
        row.owner = target_user.full_name or target_user.email
    row.assigned_by = scope.user_id
    row.assigned_at = now
    row.updated_by = scope.user_id

    db.add(AssignmentHistory(
        entity_type=entity_type, entity_id=row.id, project_id=project.id,
        previous_owner_id=previous_owner_id, new_owner_id=target_user_id, assigned_by=scope.user_id,
    ))
    db.commit()
    db.refresh(row)

    emit_assignment_event(db, AssignmentEvent(
        action="reassigned" if previous_owner_id is not None else "assigned",
        entity_type=entity_type, entity_id=row.id, project_id=project.id,
        organization_id=project.organization_id, entity_label=_entity_label(entity_type, row),
        previous_owner_id=previous_owner_id, new_owner_id=target_user_id,
        assigned_by=scope.user_id, assigned_at=now,
    ))
    # RC1 Phase 1 Sprint 4 — Enterprise Audit Logging: one hook here
    # covers assign/reassign for all six workflow entities (see module
    # docstring — this shared core is the only place any of them mutate
    # ownership), instead of duplicating a call into each of the six
    # per-entity wrapper functions below.
    record_audit_event(
        entity_type=entity_type, entity_id=row.id, action=AuditAction.ASSIGN, result=AuditResult.SUCCESS,
        organization_id=project.organization_id, actor_user_id=scope.user_id, project_id=project.id,
        before_state={"owner_id": previous_owner_id}, after_state={"owner_id": target_user_id},
    )
    return row


def _do_unassign(
    db: Session, scope: AIAuthScope, row, entity_type: str, project: Project,
    expected_updated_at, *, has_legacy_owner: bool, legacy_owner_empty_value: Optional[str] = None,
) -> object:
    _check_concurrency(entity_type, row.updated_at, expected_updated_at)

    previous_owner_id = row.owner_id
    if previous_owner_id is None:
        return row  # idempotent no-op — already unassigned

    is_self_release = previous_owner_id == scope.user_id
    if not is_self_release and not _can_manage_assignments(scope, project.id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only managers can unassign another user's assignment.")

    now = _now()
    row.owner_id = None
    if has_legacy_owner:
        row.owner = legacy_owner_empty_value
    row.assigned_by = scope.user_id
    row.assigned_at = now
    row.updated_by = scope.user_id

    db.add(AssignmentHistory(
        entity_type=entity_type, entity_id=row.id, project_id=project.id,
        previous_owner_id=previous_owner_id, new_owner_id=None, assigned_by=scope.user_id,
    ))
    db.commit()
    db.refresh(row)

    emit_assignment_event(db, AssignmentEvent(
        action="unassigned", entity_type=entity_type, entity_id=row.id, project_id=project.id,
        organization_id=project.organization_id, entity_label=_entity_label(entity_type, row),
        previous_owner_id=previous_owner_id, new_owner_id=None,
        assigned_by=scope.user_id, assigned_at=now,
    ))
    record_audit_event(
        entity_type=entity_type, entity_id=row.id, action=AuditAction.UNASSIGN, result=AuditResult.SUCCESS,
        organization_id=project.organization_id, actor_user_id=scope.user_id, project_id=project.id,
        before_state={"owner_id": previous_owner_id}, after_state={"owner_id": None},
    )
    return row


# ─────────────────────────────────────────────────────────────────────────
# Per-entity fetch/authorize wrappers — same shape as Sprint 2's
# update_project_risk() etc.: resolve+authorize the parent project via the
# one canonical get_project_or_404 policy, fetch the row scoped by
# (id, project_id), then delegate to the shared core above.
# ─────────────────────────────────────────────────────────────────────────
def assign_project_risk(db, scope, project_id, risk_id, target_user_id, expected_updated_at=None) -> ProjectRisk:
    project = get_project_or_404(db, scope, project_id)
    risk = db.query(ProjectRisk).filter(ProjectRisk.id == risk_id, ProjectRisk.project_id == project_id).first()
    if risk is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Risk not found")
    return _do_assign(db, scope, risk, ENTITY_PROJECT_RISK, project, target_user_id, expected_updated_at, has_legacy_owner=True)


def unassign_project_risk(db, scope, project_id, risk_id, expected_updated_at=None) -> ProjectRisk:
    project = get_project_or_404(db, scope, project_id)
    risk = db.query(ProjectRisk).filter(ProjectRisk.id == risk_id, ProjectRisk.project_id == project_id).first()
    if risk is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Risk not found")
    return _do_unassign(db, scope, risk, ENTITY_PROJECT_RISK, project, expected_updated_at, has_legacy_owner=True, legacy_owner_empty_value=None)


def assign_project_issue(db, scope, project_id, issue_id, target_user_id, expected_updated_at=None) -> ProjectIssue:
    project = get_project_or_404(db, scope, project_id)
    issue = db.query(ProjectIssue).filter(ProjectIssue.id == issue_id, ProjectIssue.project_id == project_id).first()
    if issue is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return _do_assign(db, scope, issue, ENTITY_PROJECT_ISSUE, project, target_user_id, expected_updated_at, has_legacy_owner=True)


def unassign_project_issue(db, scope, project_id, issue_id, expected_updated_at=None) -> ProjectIssue:
    project = get_project_or_404(db, scope, project_id)
    issue = db.query(ProjectIssue).filter(ProjectIssue.id == issue_id, ProjectIssue.project_id == project_id).first()
    if issue is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return _do_unassign(db, scope, issue, ENTITY_PROJECT_ISSUE, project, expected_updated_at, has_legacy_owner=True, legacy_owner_empty_value=None)


def assign_action_item(db, scope, project_id, action_item_id, target_user_id, expected_updated_at=None) -> MeetingActionItem:
    project = get_project_or_404(db, scope, project_id)
    item = db.query(MeetingActionItem).filter(MeetingActionItem.id == action_item_id, MeetingActionItem.project_id == project_id).first()
    if item is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Action item not found")
    return _do_assign(db, scope, item, ENTITY_ACTION_ITEM, project, target_user_id, expected_updated_at, has_legacy_owner=True)


def unassign_action_item(db, scope, project_id, action_item_id, expected_updated_at=None) -> MeetingActionItem:
    project = get_project_or_404(db, scope, project_id)
    item = db.query(MeetingActionItem).filter(MeetingActionItem.id == action_item_id, MeetingActionItem.project_id == project_id).first()
    if item is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Action item not found")
    # owner is NOT NULL on this table (required at creation) — cleared to
    # "" rather than None, the only DB-safe "no owner" representation
    # without loosening a pre-existing constraint.
    return _do_unassign(db, scope, item, ENTITY_ACTION_ITEM, project, expected_updated_at, has_legacy_owner=True, legacy_owner_empty_value="")


def assign_safety_event(db, scope, project_id, event_id, target_user_id, expected_updated_at=None) -> SafetyEvent:
    project = get_project_or_404(db, scope, project_id)
    event = db.query(SafetyEvent).filter(SafetyEvent.id == event_id, SafetyEvent.project_id == project_id).first()
    if event is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Safety event not found")
    return _do_assign(db, scope, event, ENTITY_SAFETY_EVENT, project, target_user_id, expected_updated_at, has_legacy_owner=False)


def unassign_safety_event(db, scope, project_id, event_id, expected_updated_at=None) -> SafetyEvent:
    project = get_project_or_404(db, scope, project_id)
    event = db.query(SafetyEvent).filter(SafetyEvent.id == event_id, SafetyEvent.project_id == project_id).first()
    if event is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Safety event not found")
    return _do_unassign(db, scope, event, ENTITY_SAFETY_EVENT, project, expected_updated_at, has_legacy_owner=False)


def assign_ncr(db, scope, project_id, ncr_id, target_user_id, expected_updated_at=None) -> NCR:
    project = get_project_or_404(db, scope, project_id)
    ncr = db.query(NCR).filter(NCR.id == ncr_id, NCR.project_id == project_id).first()
    if ncr is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="NCR not found")
    return _do_assign(db, scope, ncr, ENTITY_NCR, project, target_user_id, expected_updated_at, has_legacy_owner=False)


def unassign_ncr(db, scope, project_id, ncr_id, expected_updated_at=None) -> NCR:
    project = get_project_or_404(db, scope, project_id)
    ncr = db.query(NCR).filter(NCR.id == ncr_id, NCR.project_id == project_id).first()
    if ncr is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="NCR not found")
    return _do_unassign(db, scope, ncr, ENTITY_NCR, project, expected_updated_at, has_legacy_owner=False)


def _get_purchase_request_and_project(db: Session, scope: AIAuthScope, request_id: int) -> tuple[PurchaseRequest, Project]:
    """PurchaseRequest's route isn't project-nested (see
    api/v1/procurement.py) — same pattern as
    workflow_engine.py::update_purchase_request: resolve the project from
    the row itself, but return the identical 404 whether the row truly
    doesn't exist or belongs to another organization's project, so
    existence is never distinguishable via status code or message."""
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    project = db.query(Project).filter(Project.id == pr.project_id).first() if pr is not None else None
    if pr is None or project is None or project.organization_id != scope.organization_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Purchase request not found")
    if not scope.can_access_project(pr.project_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied to this purchase request")
    return pr, project


def assign_purchase_request(db, scope, request_id, target_user_id, expected_updated_at=None) -> PurchaseRequest:
    pr, project = _get_purchase_request_and_project(db, scope, request_id)
    return _do_assign(db, scope, pr, ENTITY_PURCHASE_REQUEST, project, target_user_id, expected_updated_at, has_legacy_owner=False)


def unassign_purchase_request(db, scope, request_id, expected_updated_at=None) -> PurchaseRequest:
    pr, project = _get_purchase_request_and_project(db, scope, request_id)
    return _do_unassign(db, scope, pr, ENTITY_PURCHASE_REQUEST, project, expected_updated_at, has_legacy_owner=False)


# ─────────────────────────────────────────────────────────────────────────
# Query support — "assigned to me / assigned to user / unassigned /
# overdue / open", applied as filters on the SAME existing list endpoints
# (no new list routes), backed by the owner_id/status/due_date indexes
# added in migration 0017 so none of these ever need a sequential scan.
# ─────────────────────────────────────────────────────────────────────────
def apply_ownership_filters(
    query: Query, model, scope: AIAuthScope, *,
    assigned_to_me: bool = False, assigned_to: Optional[int] = None, unassigned: bool = False,
) -> Query:
    if assigned_to_me:
        query = query.filter(model.owner_id == scope.user_id)
    if assigned_to is not None:
        query = query.filter(model.owner_id == assigned_to)
    if unassigned:
        query = query.filter(model.owner_id.is_(None))
    return query


def apply_overdue_filter(query: Query, model, *, overdue: bool = False) -> Query:
    """Only meaningful for MeetingActionItem (the one entity among the six
    with a real due-date field) — due_date is a String(50) ISO date
    ("YYYY-MM-DD"), so lexicographic comparison is chronological."""
    if overdue:
        today = datetime.now(timezone.utc).date().isoformat()
        query = query.filter(model.due_date.isnot(None), model.due_date < today, model.status != "Completed")
    return query
