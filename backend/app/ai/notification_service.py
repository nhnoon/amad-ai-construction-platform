"""Notification Engine (Sprint 4) — the one centralized service that
creates persistent, user-scoped Notification rows (app/models/notifications.py).
Both integration seams the sprint brief asks for call in here:
  - Part B: app/ai/ownership_engine.py::emit_assignment_event() ->
    notify_assignment() below.
  - Part C: app/ai/workflow_engine.py's update_* functions ->
    notify_status_change() / notify_action_item_due_date_changed() /
    notify_purchase_request_status() below.
No router or engine function builds a Notification row directly — this
is deliberate, matching the sprint brief's "one centralized notification
service rather than notification logic duplicated inside routers."

Best-effort by design: every public function here catches its own
exceptions, logs, and returns — never raises. Same pattern already
established by app/api/v1/meetings.py::_write_meeting_memory_best_effort
("a meeting/action-item write must succeed even if memory recording
fails for any reason"). A notification failing to write must never turn
an otherwise-successful assignment or workflow update into an error
response, and since every call site here runs AFTER the caller's own
db.commit() has already succeeded, there is nothing left to roll back —
a notification failure only rolls back its own attempted insert.

Deduplication: every deduplication_key is built WITHOUT a timestamp, from
only the resulting state of a transition (old/new status, old/new owner,
event type). Two calls describing the identical transition — e.g. a
genuine concurrent race (two near-simultaneous requests both computing
the same before/after state), or the same event object handed to this
service twice by a bug/retry one level up — collapse into exactly one
notification via a single atomic
INSERT ... ON CONFLICT (deduplication_key) DO NOTHING. Note this does
NOT dedupe two independent, sequential end-to-end calls to e.g.
assign_project_risk() with the same target: the second such call
legitimately observes a different previous_owner_id (the first call's
result) and is correctly recorded as a distinct "reassigned" event with
its own key — that is real, new information, not a duplicate. The
underlying AssignmentHistory/audit trail is never affected either way —
dedup only ever collapses the notification, never the workflow write
itself. See tests/test_notifications_engine.py.

Part G (delivery scope): notify() below, right after the row commits, is
the one seam a future delivery adapter (email/SMS/push/Slack/Teams) would
hook into. None of that is implemented this sprint — in-app rows only.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ai.entity_refs import build_action_url, entity_label
from app.models.notifications import Notification

logger = logging.getLogger(__name__)

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

EVENT_ASSIGNED = "assigned"
EVENT_REASSIGNED = "reassigned"
EVENT_UNASSIGNED = "unassigned"
EVENT_STATUS_CHANGED = "status_changed"
EVENT_ITEM_COMPLETED = "item_completed"
EVENT_ITEM_REOPENED = "item_reopened"
EVENT_DUE_DATE_CHANGED = "due_date_changed"
EVENT_PR_APPROVED = "purchase_request_approved"
EVENT_PR_REJECTED = "purchase_request_rejected"
EVENT_PR_RETURNED = "purchase_request_returned"


def notify(
    db: Session, *, organization_id: int, recipient_user_id: Optional[int],
    actor_user_id: Optional[int], project_id: Optional[int], event_type: str,
    entity_type: str, entity_id: int, title: str, message: str, severity: str,
    action_url: Optional[str], deduplication_key: Optional[str],
) -> None:
    """Low-level create — never notifies the actor about their own action
    (applied once, here, so every caller gets this rule for free rather
    than re-checking it themselves), never raises."""
    if recipient_user_id is None or recipient_user_id == actor_user_id:
        return
    try:
        stmt = pg_insert(Notification.__table__).values(
            organization_id=organization_id,
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            project_id=project_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            message=message,
            severity=severity,
            action_url=action_url,
            deduplication_key=deduplication_key,
        )
        if deduplication_key is not None:
            stmt = stmt.on_conflict_do_nothing(index_elements=["deduplication_key"])
        db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "notification_creation_failed event_type=%s entity_type=%s entity_id=%s recipient_user_id=%s",
            event_type, entity_type, entity_id, recipient_user_id,
        )


# ─────────────────────────────────────────────────────────────────────────
# Part B — Assignment Event Integration
# ─────────────────────────────────────────────────────────────────────────
def notify_assignment(db: Session, event) -> None:
    """event: app/ai/ownership_engine.py::AssignmentEvent. Called from
    emit_assignment_event() after the assignment's own transaction has
    already committed."""
    try:
        action_url = build_action_url(event.entity_type, event.project_id, event.entity_id)

        if event.action in (EVENT_ASSIGNED, EVENT_REASSIGNED):
            notify(
                db, organization_id=event.organization_id, recipient_user_id=event.new_owner_id,
                actor_user_id=event.assigned_by, project_id=event.project_id,
                event_type=event.action, entity_type=event.entity_type, entity_id=event.entity_id,
                title=f"Assigned: {event.entity_label}",
                message=f"You were assigned to {event.entity_label}.",
                severity=SEVERITY_INFO, action_url=action_url,
                deduplication_key=(
                    f"assign:{event.entity_type}:{event.entity_id}:{event.new_owner_id}:"
                    f"{event.action}:{event.new_owner_id}:{event.previous_owner_id}"
                ),
            )

        if event.action == EVENT_REASSIGNED and event.previous_owner_id is not None and event.previous_owner_id != event.new_owner_id:
            notify(
                db, organization_id=event.organization_id, recipient_user_id=event.previous_owner_id,
                actor_user_id=event.assigned_by, project_id=event.project_id,
                event_type=EVENT_REASSIGNED, entity_type=event.entity_type, entity_id=event.entity_id,
                title=f"Reassigned: {event.entity_label}",
                message=f"{event.entity_label} was reassigned to someone else.",
                severity=SEVERITY_INFO, action_url=action_url,
                deduplication_key=(
                    f"assign:{event.entity_type}:{event.entity_id}:{event.previous_owner_id}:"
                    f"reassigned_away:{event.new_owner_id}:{event.previous_owner_id}"
                ),
            )

        if event.action == EVENT_UNASSIGNED and event.previous_owner_id is not None:
            notify(
                db, organization_id=event.organization_id, recipient_user_id=event.previous_owner_id,
                actor_user_id=event.assigned_by, project_id=event.project_id,
                event_type=EVENT_UNASSIGNED, entity_type=event.entity_type, entity_id=event.entity_id,
                title=f"Unassigned: {event.entity_label}",
                message=f"You were unassigned from {event.entity_label}.",
                severity=SEVERITY_INFO, action_url=action_url,
                deduplication_key=(
                    f"assign:{event.entity_type}:{event.entity_id}:{event.previous_owner_id}:"
                    f"unassigned:None:{event.previous_owner_id}"
                ),
            )
    except Exception:
        logger.exception(
            "notify_assignment_failed action=%s entity_type=%s entity_id=%s",
            event.action, event.entity_type, event.entity_id,
        )


# ─────────────────────────────────────────────────────────────────────────
# Part C — Workflow Notifications
# ─────────────────────────────────────────────────────────────────────────
# The status value each entity reaches when "done" — used to distinguish
# item_completed (reaching it) from item_reopened (leaving it) from a
# plain status_changed (neither). Matches the terminal-ish values already
# established by app/ai/workflow_engine.py's own transition matrices.
_TERMINAL_STATUS = {
    "project_risk": "closed",
    "project_issue": "Resolved",
    "action_item": "Completed",
    "safety_event": "Closed",
    "ncr": "Closed",
}

_PR_STATUS_EVENTS = {
    "Approved": (EVENT_PR_APPROVED, SEVERITY_INFO),
    "Rejected": (EVENT_PR_REJECTED, SEVERITY_WARNING),
    "Returned to Requester": (EVENT_PR_RETURNED, SEVERITY_WARNING),
}


def notify_status_change(
    db: Session, *, scope, row, entity_type: str, entity_label_text: str,
    project_id: int, old_status: str, new_status: str,
) -> None:
    """Generic status-change notification for risk/issue/action_item/
    safety_event/ncr. Recipient is always the entity's real owner
    (owner_id) — never notifies an unassigned entity's non-existent
    owner, and never notifies the actor about their own change."""
    try:
        if row.owner_id is None or row.owner_id == scope.user_id:
            return
        terminal = _TERMINAL_STATUS.get(entity_type)
        if terminal is not None and new_status == terminal:
            event_type, title_prefix, severity = EVENT_ITEM_COMPLETED, "Completed", SEVERITY_INFO
        elif terminal is not None and old_status == terminal and new_status != terminal:
            event_type, title_prefix, severity = EVENT_ITEM_REOPENED, "Reopened", SEVERITY_WARNING
        else:
            event_type, title_prefix, severity = EVENT_STATUS_CHANGED, "Status changed", SEVERITY_INFO

        action_url = build_action_url(entity_type, project_id, row.id)
        notify(
            db, organization_id=scope.organization_id, recipient_user_id=row.owner_id,
            actor_user_id=scope.user_id, project_id=project_id,
            event_type=event_type, entity_type=entity_type, entity_id=row.id,
            title=f"{title_prefix}: {entity_label_text}",
            message=f"{entity_label_text} status changed from '{old_status}' to '{new_status}'.",
            severity=severity, action_url=action_url,
            deduplication_key=f"workflow:{entity_type}:{row.id}:{row.owner_id}:{event_type}:{old_status}:{new_status}",
        )
    except Exception:
        logger.exception("notify_status_change_failed entity_type=%s entity_id=%s", entity_type, getattr(row, "id", None))


def notify_action_item_due_date_changed(
    db: Session, *, scope, item, project_id: int, old_due_date: Optional[str], new_due_date: Optional[str],
) -> None:
    try:
        if item.owner_id is None or item.owner_id == scope.user_id:
            return
        if new_due_date is None or new_due_date == old_due_date:
            return
        label = entity_label("action_item", item)
        action_url = build_action_url("action_item", project_id, item.id)
        notify(
            db, organization_id=scope.organization_id, recipient_user_id=item.owner_id,
            actor_user_id=scope.user_id, project_id=project_id,
            event_type=EVENT_DUE_DATE_CHANGED, entity_type="action_item", entity_id=item.id,
            title=f"Due date changed: {label}",
            message=f"{label} is now due {new_due_date}.",
            severity=SEVERITY_INFO, action_url=action_url,
            deduplication_key=f"workflow:action_item:{item.id}:{item.owner_id}:due_date_changed:{old_due_date}:{new_due_date}",
        )
    except Exception:
        logger.exception("notify_action_item_due_date_changed_failed entity_id=%s", getattr(item, "id", None))


def notify_purchase_request_status(
    db: Session, *, scope, pr, project_id: int, old_status: str, new_status: str,
) -> None:
    """PR-specific: only the three most valuable decision states
    (approved/rejected/returned) — per the sprint brief, not every status
    hop (e.g. Under Review -> Needs Rework is not notified)."""
    try:
        if pr.owner_id is None or pr.owner_id == scope.user_id:
            return
        mapped = _PR_STATUS_EVENTS.get(new_status)
        if mapped is None:
            return
        event_type, severity = mapped
        label = entity_label("purchase_request", pr)
        action_url = build_action_url("purchase_request", project_id, pr.id)
        notify(
            db, organization_id=scope.organization_id, recipient_user_id=pr.owner_id,
            actor_user_id=scope.user_id, project_id=project_id,
            event_type=event_type, entity_type="purchase_request", entity_id=pr.id,
            title=f"{new_status}: {label}",
            message=f"{label} was {new_status.lower()}.",
            severity=severity, action_url=action_url,
            deduplication_key=f"workflow:purchase_request:{pr.id}:{pr.owner_id}:{event_type}:{old_status}:{new_status}",
        )
    except Exception:
        logger.exception("notify_purchase_request_status_failed entity_id=%s", getattr(pr, "id", None))
