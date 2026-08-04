"""Core Workflow Engine (Sprint 2) — status transitions for the six
existing workflow-shaped entities that could previously be created but
never updated: ProjectRisk, ProjectIssue, MeetingActionItem, SafetyEvent,
NCR, PurchaseRequest.

Design intentionally stays a plain dict-based transition matrix + a
handful of small guard helpers — not a generic state-machine framework.
Six entities with 2-7 states each do not need one, and a heavier
abstraction would be exactly the kind of complexity the sprint brief
warns against.

Every `update_*` function below follows the same shape:
  1. Resolve and authorize the parent project — get_project_or_404()
     (404 hides cross-organization existence, 403 for same-org-no-access;
     the one canonical policy already used across the app, see
     app/ai/scope.py).
  2. Fetch the row scoped by (id, project_id) — 404 if not found under
     that project (also hides cross-project existence of another
     organization's or another project's row with the same numeric id).
  3. Optimistic concurrency check (§8) — if the caller supplied
     expected_updated_at and it doesn't match the row's current
     updated_at, 409 before anything else is validated or applied.
  4. Apply non-status fields first (owner/due_date/priority/mitigation/
     etc.) so status-transition close-out guards see the FINAL effective
     value of any field the same PATCH call also touched — e.g. sending
     {"corrective_action": "...", "status": "Closed"} in one request must
     see the just-set corrective_action, not the old one.
  5. If status is provided and differs from the current value, validate
     it against that entity's transition matrix (409 for a disallowed
     transition, 400 for a status string outside the vocabulary
     entirely), run any domain-specific close-out guard, then apply it.
  6. Stamp updated_by from the caller's scope (updated_at is handled by
     the column's own onupdate=func.now()), commit, return the row.

Ownership: every `owner`/`resolved_at`/`mitigation`/etc. field below is
still the free-text/string column that already existed — the full
owner_id (FK to a user) migration is explicitly deferred to a later
Ownership/Audit sprint, per this sprint's brief. `updated_by` is a
different, narrower concept: who last touched this row via the API,
always server-set from scope.user_id, never client-supplied — same
pattern already established by Document.uploaded_by /
DocumentOCRResult.requested_by.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.ai.notification_service import (
    notify_action_item_due_date_changed,
    notify_purchase_request_status,
    notify_status_change,
)
from app.ai.scope import AIAuthScope, get_project_or_404
from app.core.audit_log import AuditAction, AuditEntityType, AuditResult, record_audit_event
from app.models.meetings import MeetingActionItem
from app.models.procurement import PurchaseRequest
from app.models.projects import Project, ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from app.schemas.meetings import MeetingActionItemUpdate
from app.schemas.procurement import PurchaseRequestUpdate
from app.schemas.projects import ProjectIssueUpdate, ProjectRiskUpdate
from app.schemas.safety import NCRUpdate, SafetyEventUpdate


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _check_concurrency(entity_label: str, current_updated_at, expected_updated_at) -> None:
    """No-op if the caller didn't send expected_updated_at at all — every
    caller of these brand-new endpoints opts in or stays unaffected;
    there is no existing caller who could ever have supplied this field
    before this sprint, so this can never regress an existing integration."""
    if expected_updated_at is None:
        return
    if current_updated_at != expected_updated_at:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"{entity_label} was modified since you last loaded it. Reload and try again.",
        )


def validate_transition(entity_label: str, matrix: dict[str, set[str]], current_status: str, new_status: str) -> None:
    """A no-op status ("new" == current) is always allowed regardless of
    the matrix — a PATCH that redundantly repeats the current status
    alongside an unrelated field update (e.g. just reassigning owner)
    must not be rejected as an invalid transition."""
    if new_status == current_status:
        return
    if new_status not in matrix:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"'{new_status}' is not a recognized status for {entity_label}.",
        )
    allowed = matrix.get(current_status)
    if allowed is None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"{entity_label} is currently '{current_status}', which this workflow does not recognize; no transition can be validated.",
        )
    if new_status not in allowed:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot move {entity_label} from '{current_status}' to '{new_status}'. "
                f"Allowed next status(es): {', '.join(sorted(allowed)) if allowed else 'none (terminal state)'}."
            ),
        )


def _require_nonempty(value: Optional[str], field_label: str, entity_label: str, target_status: str) -> None:
    if not (value or "").strip():
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"{entity_label} cannot become '{target_status}' without a non-empty {field_label}.",
        )


def _reject_owner_text_conflict(row, entity_label: str) -> None:
    """Ownership Consistency Policy (Sprint 4 Part F). app/ai/ownership_engine.py
    already keeps the legacy free-text `owner` column in sync automatically
    on every real assign/unassign; the actual drift risk is the other
    direction — this plain PATCH silently overwriting `owner` text while
    `owner_id` still points at a real, different user. Policy chosen:
    reject the direct text edit once owner_id is set (rather than trying
    to auto-resolve the text back to a user, which would need fuzzy name
    matching and would let a plain PATCH bypass assign/unassign's
    self-vs-manager authorization). Rows where owner_id is still NULL
    (never assigned / pre-migration) keep accepting direct text edits
    exactly as before — old records are preserved untouched."""
    if row.owner_id is not None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"{entity_label} already has a real assigned owner; use the assign/unassign "
                f"endpoints instead of editing the legacy owner text directly."
            ),
        )


# ─────────────────────────────────────────────────────────────────────────
# ProjectRisk — "open" is the exact, unchanged existing POST-create default
# (see ProjectRiskBase.status); "mitigating"/"closed" are this sprint's own
# additions and free to pick a casing, kept lowercase to match "open".
# ─────────────────────────────────────────────────────────────────────────
PROJECT_RISK_TRANSITIONS: dict[str, set[str]] = {
    "open": {"mitigating", "closed"},
    "mitigating": {"open", "closed"},
    "closed": {"open"},
}


def update_project_risk(db: Session, scope: AIAuthScope, project_id: int, risk_id: int, patch: ProjectRiskUpdate) -> ProjectRisk:
    get_project_or_404(db, scope, project_id)
    risk = db.query(ProjectRisk).filter(ProjectRisk.id == risk_id, ProjectRisk.project_id == project_id).first()
    if risk is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Risk not found")

    _check_concurrency("Risk", risk.updated_at, patch.expected_updated_at)

    if patch.owner is not None:
        _reject_owner_text_conflict(risk, "Risk")
        risk.owner = patch.owner
    if patch.mitigation is not None:
        risk.mitigation = patch.mitigation
    if patch.probability is not None:
        risk.probability = patch.probability
    if patch.impact is not None:
        risk.impact = patch.impact

    old_status = risk.status
    status_changed = patch.status is not None and patch.status != old_status
    if status_changed:
        validate_transition("Risk", PROJECT_RISK_TRANSITIONS, risk.status, patch.status)
        if patch.status == "closed":
            # "Closure must preserve mitigation or closure rationale. Do
            # not silently discard historical context." — mitigation is
            # the one existing field that carries that rationale; no new
            # field is introduced to hold it.
            _require_nonempty(risk.mitigation, "mitigation", "Risk", "closed")
        risk.status = patch.status

    risk.updated_by = scope.user_id
    db.commit()
    db.refresh(risk)
    if status_changed:
        notify_status_change(
            db, scope=scope, row=risk, entity_type="project_risk", entity_label_text=risk.title,
            project_id=project_id, old_status=old_status, new_status=risk.status,
        )
        record_audit_event(
            entity_type=AuditEntityType.PROJECT_RISK, entity_id=risk.id, action=AuditAction.STATUS_CHANGE,
            result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=project_id, before_state={"status": old_status}, after_state={"status": risk.status},
        )
    return risk


# ─────────────────────────────────────────────────────────────────────────
# ProjectIssue — "open" is the exact existing default; "In Progress" /
# "Resolved" use this sprint's own wording (see the sprint brief's close-
# out rule text), since neither state existed in any row before this.
# ─────────────────────────────────────────────────────────────────────────
PROJECT_ISSUE_TRANSITIONS: dict[str, set[str]] = {
    "open": {"In Progress", "Resolved"},
    "In Progress": {"open", "Resolved"},
    "Resolved": {"open"},
}


def update_project_issue(db: Session, scope: AIAuthScope, project_id: int, issue_id: int, patch: ProjectIssueUpdate) -> ProjectIssue:
    get_project_or_404(db, scope, project_id)
    issue = db.query(ProjectIssue).filter(ProjectIssue.id == issue_id, ProjectIssue.project_id == project_id).first()
    if issue is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Issue not found")

    _check_concurrency("Issue", issue.updated_at, patch.expected_updated_at)

    if patch.owner is not None:
        _reject_owner_text_conflict(issue, "Issue")
        issue.owner = patch.owner
    if patch.resolution is not None:
        issue.resolution = patch.resolution
    if patch.resolved_at is not None:
        issue.resolved_at = patch.resolved_at
    if patch.severity is not None:
        issue.severity = patch.severity

    old_status = issue.status
    status_changed = patch.status is not None and patch.status != old_status
    if status_changed:
        validate_transition("Issue", PROJECT_ISSUE_TRANSITIONS, issue.status, patch.status)
        if patch.status == "Resolved":
            _require_nonempty(issue.resolution, "resolution", "Issue", "Resolved")
            # "resolved_at should be set consistently when resolved" —
            # stamp it every time this transition happens, unless the
            # caller already supplied a specific date in this same PATCH.
            if patch.resolved_at is None:
                issue.resolved_at = _today()
        issue.status = patch.status

    issue.updated_by = scope.user_id
    db.commit()
    db.refresh(issue)
    if status_changed:
        notify_status_change(
            db, scope=scope, row=issue, entity_type="project_issue", entity_label_text=issue.title,
            project_id=project_id, old_status=old_status, new_status=issue.status,
        )
        record_audit_event(
            entity_type=AuditEntityType.PROJECT_ISSUE, entity_id=issue.id, action=AuditAction.STATUS_CHANGE,
            result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=project_id, before_state={"status": old_status}, after_state={"status": issue.status},
        )
    return issue


# ─────────────────────────────────────────────────────────────────────────
# MeetingActionItem — "open" is the exact existing default; "In Progress" /
# "Completed" are new. Reassignment (owner) and due_date changes are
# always allowed and never require a status change in the same call.
# ─────────────────────────────────────────────────────────────────────────
ACTION_ITEM_TRANSITIONS: dict[str, set[str]] = {
    "open": {"In Progress", "Completed"},
    "In Progress": {"open", "Completed"},
    "Completed": {"open"},
}


def update_action_item(db: Session, scope: AIAuthScope, project_id: int, action_item_id: int, patch: MeetingActionItemUpdate) -> MeetingActionItem:
    get_project_or_404(db, scope, project_id)
    item = (
        db.query(MeetingActionItem)
        .filter(MeetingActionItem.id == action_item_id, MeetingActionItem.project_id == project_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Action item not found")

    _check_concurrency("Action item", item.updated_at, patch.expected_updated_at)

    if patch.owner is not None:
        _reject_owner_text_conflict(item, "Action item")
        item.owner = patch.owner
    old_due_date = item.due_date
    if patch.due_date is not None:
        item.due_date = patch.due_date
    if patch.priority is not None:
        item.priority = patch.priority
    if patch.completed_at is not None:
        item.completed_at = patch.completed_at

    old_status = item.status
    status_changed = patch.status is not None and patch.status != old_status
    if status_changed:
        validate_transition("Action item", ACTION_ITEM_TRANSITIONS, item.status, patch.status)
        if patch.status == "Completed":
            if patch.completed_at is None and not item.completed_at:
                item.completed_at = _today()
            _require_nonempty(item.completed_at, "completed_at", "Action item", "Completed")
        item.status = patch.status

    item.updated_by = scope.user_id
    db.commit()
    db.refresh(item)
    if status_changed:
        notify_status_change(
            db, scope=scope, row=item, entity_type="action_item", entity_label_text=(item.description or "Action item")[:80],
            project_id=project_id, old_status=old_status, new_status=item.status,
        )
        record_audit_event(
            entity_type=AuditEntityType.MEETING_ACTION_ITEM, entity_id=item.id, action=AuditAction.STATUS_CHANGE,
            result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=project_id, before_state={"status": old_status}, after_state={"status": item.status},
        )
    if patch.due_date is not None:
        notify_action_item_due_date_changed(
            db, scope=scope, item=item, project_id=project_id, old_due_date=old_due_date, new_due_date=item.due_date,
        )
    return item


# ─────────────────────────────────────────────────────────────────────────
# SafetyEvent — Open/Closed only. This model has no investigator/
# assignee/investigation-stage field, so no such workflow is fabricated;
# the only real close-out signal available is corrective_action.
# ─────────────────────────────────────────────────────────────────────────
SAFETY_EVENT_TRANSITIONS: dict[str, set[str]] = {
    "Open": {"Closed"},
    "Closed": {"Open"},
}


def update_safety_event(db: Session, scope: AIAuthScope, project_id: int, event_id: int, patch: SafetyEventUpdate) -> SafetyEvent:
    get_project_or_404(db, scope, project_id)
    event = db.query(SafetyEvent).filter(SafetyEvent.id == event_id, SafetyEvent.project_id == project_id).first()
    if event is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Safety event not found")

    _check_concurrency("Safety event", event.updated_at, patch.expected_updated_at)

    if patch.corrective_action is not None:
        event.corrective_action = patch.corrective_action
    if patch.severity is not None:
        event.severity = patch.severity

    old_status = event.status
    status_changed = patch.status is not None and patch.status != old_status
    if status_changed:
        validate_transition("Safety event", SAFETY_EVENT_TRANSITIONS, event.status, patch.status)
        if patch.status == "Closed":
            _require_nonempty(event.corrective_action, "corrective_action", "Safety event", "Closed")
        event.status = patch.status

    event.updated_by = scope.user_id
    db.commit()
    db.refresh(event)
    if status_changed:
        notify_status_change(
            db, scope=scope, row=event, entity_type="safety_event", entity_label_text=f"Safety event ({event.severity})",
            project_id=project_id, old_status=old_status, new_status=event.status,
        )
        record_audit_event(
            entity_type=AuditEntityType.SAFETY_EVENT, entity_id=event.id, action=AuditAction.STATUS_CHANGE,
            result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=project_id, before_state={"status": old_status}, after_state={"status": event.status},
        )
    return event


# ─────────────────────────────────────────────────────────────────────────
# NCR — matches the three status values already observed in real seeded
# data (Open, Under Corrective Action, Closed).
# ─────────────────────────────────────────────────────────────────────────
NCR_TRANSITIONS: dict[str, set[str]] = {
    "Open": {"Under Corrective Action", "Closed"},
    "Under Corrective Action": {"Closed", "Open"},
    "Closed": {"Open"},
}


def update_ncr(db: Session, scope: AIAuthScope, project_id: int, ncr_id: int, patch: NCRUpdate) -> NCR:
    get_project_or_404(db, scope, project_id)
    ncr = db.query(NCR).filter(NCR.id == ncr_id, NCR.project_id == project_id).first()
    if ncr is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="NCR not found")

    _check_concurrency("NCR", ncr.updated_at, patch.expected_updated_at)

    # "Preserve root-cause and corrective-action context" — both fields
    # are only ever touched when explicitly provided; omitted fields are
    # left exactly as they were.
    if patch.corrective_action is not None:
        ncr.corrective_action = patch.corrective_action
    if patch.root_cause is not None:
        ncr.root_cause = patch.root_cause

    old_status = ncr.status
    status_changed = patch.status is not None and patch.status != old_status
    if status_changed:
        validate_transition("NCR", NCR_TRANSITIONS, ncr.status, patch.status)
        if patch.status == "Closed":
            _require_nonempty(ncr.corrective_action, "corrective_action", "NCR", "Closed")
        ncr.status = patch.status

    ncr.updated_by = scope.user_id
    db.commit()
    db.refresh(ncr)
    if status_changed:
        notify_status_change(
            db, scope=scope, row=ncr, entity_type="ncr", entity_label_text=f"NCR ({ncr.ncr_type})",
            project_id=project_id, old_status=old_status, new_status=ncr.status,
        )
        record_audit_event(
            entity_type=AuditEntityType.NCR, entity_id=ncr.id, action=AuditAction.STATUS_CHANGE,
            result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=project_id, before_state={"status": old_status}, after_state={"status": ncr.status},
        )
    return ncr


# ─────────────────────────────────────────────────────────────────────────
# PurchaseRequest — matches the six status values already observed in
# real seeded data, plus "Rejected": a real decision Under Review can
# reach that simply had no seeded example. Approved -> "Converted to PO"
# only updates this row's own status; it does NOT create a PurchaseOrder
# row (no PO-create endpoint exists yet — a separate, already-documented
# gap, not something this sprint adds).
# ─────────────────────────────────────────────────────────────────────────
PURCHASE_REQUEST_TRANSITIONS: dict[str, set[str]] = {
    "Pending Clarification": {"Under Review", "Returned to Requester"},
    "Under Review": {"Approved", "Needs Rework", "Rejected", "Returned to Requester"},
    "Needs Rework": {"Under Review", "Pending Clarification"},
    "Returned to Requester": {"Pending Clarification", "Under Review"},
    "Approved": {"Converted to PO"},
    "Converted to PO": set(),
    "Rejected": set(),
}

_PURCHASE_REQUEST_REASON_REQUIRED = {"Rejected", "Returned to Requester"}


def update_purchase_request(db: Session, scope: AIAuthScope, request_id: int, patch: PurchaseRequestUpdate) -> PurchaseRequest:
    """PurchaseRequest's own route (unlike the other five) isn't nested
    under /projects/{project_id}/... (see api/v1/procurement.py's existing
    GET-by-id), so its project is resolved from the row itself rather than
    a path parameter. To still hide cross-organization existence behind a
    single 404 (matching get_project_or_404's policy) rather than leaking
    it via a distinguishable error message, both "doesn't exist" and
    "exists but its project belongs to another organization" return the
    exact same 404 detail string."""
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    project = db.query(Project).filter(Project.id == pr.project_id).first() if pr is not None else None
    if pr is None or project is None or project.organization_id != scope.organization_id:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Purchase request not found")
    if not scope.can_access_project(pr.project_id):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Access denied to this purchase request")

    _check_concurrency("Purchase request", pr.updated_at, patch.expected_updated_at)

    if patch.rework_reason is not None:
        pr.rework_reason = patch.rework_reason

    old_status = pr.status
    status_changed = patch.status is not None and patch.status != old_status
    if status_changed:
        validate_transition("Purchase request", PURCHASE_REQUEST_TRANSITIONS, pr.status, patch.status)
        if patch.status in _PURCHASE_REQUEST_REASON_REQUIRED:
            _require_nonempty(pr.rework_reason, "rework_reason", "Purchase request", patch.status)
        pr.status = patch.status

    pr.updated_by = scope.user_id
    db.commit()
    db.refresh(pr)
    if status_changed:
        notify_purchase_request_status(
            db, scope=scope, pr=pr, project_id=project.id, old_status=old_status, new_status=pr.status,
        )
        record_audit_event(
            entity_type=AuditEntityType.PURCHASE_REQUEST, entity_id=pr.id, action=AuditAction.STATUS_CHANGE,
            result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=project.id, before_state={"status": old_status}, after_state={"status": pr.status},
        )
    return pr
