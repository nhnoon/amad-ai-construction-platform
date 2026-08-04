"""Notifications API (Sprint 4 Part D). Every query below filters by both
recipient_user_id == the caller AND organization_id == the caller's own
organization — a user may only ever read/modify their own notifications,
and cross-organization access is structurally impossible (not just a
policy check), matching this codebase's general defense-in-depth style.
No admin cross-user endpoint exists (none requested by the sprint brief).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func
from typing import Optional

from ...core.audit_log import AuditAction, AuditEntityType, AuditResult, record_audit_event
from ...core.deps import CurrentScope, DbSession
from ...models.notifications import Notification
from ...schemas.notifications import MarkAllReadOut, NotificationOut, NotificationSummaryOut

router = APIRouter(tags=["notifications"])


def _base_query(db, scope):
    return db.query(Notification).filter(
        Notification.recipient_user_id == scope.user_id,
        Notification.organization_id == scope.organization_id,
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    unread_only: bool = False,
    event_type: Optional[str] = None,
    project_id: Optional[int] = None,
    severity: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = _base_query(db, scope)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    if event_type:
        q = q.filter(Notification.event_type == event_type)
    if project_id is not None:
        q = q.filter(Notification.project_id == project_id)
    if severity:
        q = q.filter(Notification.severity == severity)
    if created_after:
        q = q.filter(Notification.created_at >= created_after)
    if created_before:
        q = q.filter(Notification.created_at <= created_before)

    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return q.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/notifications/summary", response_model=NotificationSummaryOut)
def notifications_summary(db: DbSession, scope: CurrentScope):
    base = _base_query(db, scope)
    total_count = base.count()
    unread_count = base.filter(Notification.is_read.is_(False)).count()
    rows = (
        _base_query(db, scope)
        .filter(Notification.is_read.is_(False))
        .with_entities(Notification.severity, func.count(Notification.id))
        .group_by(Notification.severity)
        .all()
    )
    return NotificationSummaryOut(
        unread_count=unread_count,
        total_count=total_count,
        unread_by_severity={severity: count for severity, count in rows},
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: int, db: DbSession, scope: CurrentScope):
    notification = _base_query(db, scope).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
        record_audit_event(
            entity_type=AuditEntityType.NOTIFICATION, entity_id=notification.id,
            action=AuditAction.NOTIFICATION_READ, result=AuditResult.SUCCESS,
            organization_id=scope.organization_id, actor_user_id=scope.user_id,
            project_id=notification.project_id,
        )
    return notification


@router.post("/notifications/read-all", response_model=MarkAllReadOut)
def mark_all_notifications_read(db: DbSession, scope: CurrentScope):
    now = datetime.now(timezone.utc)
    updated = (
        _base_query(db, scope)
        .filter(Notification.is_read.is_(False))
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db.commit()
    # Bulk update — no per-row entity_id available (see docstring on the
    # module survey this sprint), so this is deliberately one summary
    # audit row rather than `updated` individual ones.
    record_audit_event(
        entity_type=AuditEntityType.NOTIFICATION, action=AuditAction.NOTIFICATION_READ_ALL,
        result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
        after_state={"updated_count": updated},
    )
    return MarkAllReadOut(updated_count=updated)
