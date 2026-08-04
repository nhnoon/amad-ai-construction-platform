"""RC1 Phase 1 Sprint 4 — Enterprise Audit Logging: read-only query API.

Authorization (no cross-tenant visibility, ever):
  - Every result is clamped to the caller's own organization_id — there
    is deliberately no client-supplied "organization" filter parameter,
    since one could only ever be silently ignored or used to attempt
    cross-tenant access; the endpoint IS organization-scoped, just not
    client-controlled, matching this app's existing
    enforce_organization_access() precedent (app/ai/scope.py) of never
    letting a client pick a different tenant.
  - Non-manager roles (everyone except admin/executive/project_manager —
    the same "manager-like" role set already established independently
    in app/ai/scope.py, app/ai/ownership_engine.py, and
    app/ai/approval_engine.py) see only their OWN actions: actor_user_id
    is always forced to the caller, regardless of any actor_user_id
    filter supplied.
  - Managers see every action across their own organization, and may
    additionally filter by any actor within it.

Export readiness (Sprint 4: "prepare for, do not implement"): every
filter a bulk CSV/PDF export job would need (date range, actor, entity,
project, action, result) is already here and independently combinable;
the response is a flat list of typed fields with no export-hostile
nesting. No format=csv/pdf parameter exists yet — adding one with no
actual implementation behind it would be exactly the kind of
half-finished surface this project avoids; the day export is built, it
reuses this same filter set.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Response

from ...core.deps import CurrentScope, DbSession
from ...models.audit import AuditLog
from ...models.auth import UserAccount
from ...schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])

# Mirrors the identical, independently-defined set in app/ai/scope.py
# (_GLOBAL_READ_ROLES), app/ai/ownership_engine.py (_MANAGER_ROLES), and
# app/ai/approval_engine.py (_MANAGER_ROLES) — "manager-like" roles with
# organization-wide read access, established convention in this codebase
# rather than a new definition invented for audit logging.
_MANAGER_ROLES = frozenset({"admin", "executive", "project_manager"})

_SORT_COLUMNS = {
    "timestamp": AuditLog.created_at,
    "action": AuditLog.action,
    "result": AuditLog.result,
    "entity_type": AuditLog.entity_type,
}


@router.get("", response_model=list[AuditLogOut])
def list_audit_events(
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    actor_user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    project_id: Optional[int] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    sort_by: str = Query("timestamp", pattern="^(timestamp|action|result|entity_type)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    if scope.organization_id is None:
        # No organization to scope to — matches the established pattern
        # elsewhere in this codebase (e.g. POST /auth/register,
        # POST /admin/users) of refusing rather than guessing when an
        # account has no organization at all.
        response.headers["X-Total-Count"] = "0"
        return []

    q = db.query(AuditLog).filter(AuditLog.organization_id == scope.organization_id)

    is_manager = scope.user_role in _MANAGER_ROLES
    if not is_manager:
        q = q.filter(AuditLog.actor_user_id == scope.user_id)
    elif actor_user_id is not None:
        q = q.filter(AuditLog.actor_user_id == actor_user_id)

    if start_date is not None:
        q = q.filter(AuditLog.created_at >= start_date)
    if end_date is not None:
        q = q.filter(AuditLog.created_at <= end_date)
    if entity_type is not None:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)
    if project_id is not None:
        q = q.filter(AuditLog.project_id == project_id)
    if action is not None:
        q = q.filter(AuditLog.action == action)
    if result is not None:
        q = q.filter(AuditLog.result == result)

    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)

    sort_column = _SORT_COLUMNS[sort_by]
    order_clause = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    rows = q.order_by(order_clause, AuditLog.id.desc()).offset(skip).limit(limit).all()

    actor_ids = {row.actor_user_id for row in rows if row.actor_user_id is not None}
    actor_emails: dict[int, str] = {}
    if actor_ids:
        actor_emails = dict(
            db.query(UserAccount.id, UserAccount.email).filter(UserAccount.id.in_(actor_ids)).all()
        )

    return [
        AuditLogOut(
            id=row.id,
            event_id=row.event_id,
            timestamp=row.created_at,
            organization_id=row.organization_id,
            actor_user_id=row.actor_user_id,
            actor_email=actor_emails.get(row.actor_user_id) if row.actor_user_id else None,
            project_id=row.project_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            result=row.result,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            request_id=row.request_id,
            before_state=row.before_state,
            after_state=row.after_state,
            reason=row.reason,
        )
        for row in rows
    ]
