"""RC1 Phase 1 Sprint 4 — Enterprise Audit Logging.

record_audit_event() is the ONLY writer of app/models/audit.py::AuditLog
rows anywhere in this codebase — every instrumented call site (auth,
documents, workflow status/assignment, approvals, admin, notifications)
calls this one function; nothing constructs an AuditLog row directly.

Reliability contract — Sprint 4's explicit "Performance" requirement,
"audit logging must never block the business operation" / "if audit
persistence fails: business transaction succeeds, audit failure is
logged safely":

  - Runs in its OWN database session (a fresh SessionLocal(), see
    app/database.py), entirely independent of whatever session the
    calling route is using for its business logic. A failure here can
    never poison or roll back the caller's own transaction, and a
    failure in the caller's own transaction never prevents this from
    still recording what was attempted.
  - Catches every exception itself and logs it via the standard
    `logging` module — never re-raises, under any circumstance. A
    database outage, a constraint violation, anything: the calling
    route's response is completely unaffected.
  - Called synchronously (not deferred to a background task/queue): a
    background write that later fails has no coupling back to anything
    a developer or test would observe, which risks exactly the "audit
    event silently disappears" outcome Sprint 4 forbids. A synchronous
    write in an isolated session costs one small, already-pooled DB
    round-trip per mutating request but keeps failures visible (logged,
    and directly testable — see tests/test_audit_log.py's
    test_failed_audit_persistence_does_not_fail_business_operation).

Request metadata (IP / User-Agent / a correlation request_id) is read
from app/core/request_context.py's contextvar rather than requiring a
`Request` parameter — see that module's docstring for why: several call
sites (app/ai/workflow_engine.py, app/ai/ownership_engine.py,
app/ai/approval_engine.py) are layers below the route handler and don't
receive a Request object today.
"""
from __future__ import annotations

import logging
from typing import Any

from ..database import SessionLocal
from ..models.audit import AuditLog
from .request_context import get_request_context

logger = logging.getLogger(__name__)


# ── Vocabulary ──────────────────────────────────────────────────────
# Free-text at the DB layer (see AuditLog's own docstring for why — this
# codebase's consistent convention for *.status/workflow-style columns)
# but centralized here as the single source of truth for valid spellings,
# so every call site uses the same string instead of ad-hoc literals.

class AuditEntityType:
    USER_ACCOUNT = "user_account"
    SESSION = "session"
    DOCUMENT = "document"
    # Values for the six workflow entities deliberately match the
    # existing entity_type vocabulary already used elsewhere in this
    # codebase (app/ai/ownership_engine.py's ENTITY_* constants,
    # AssignmentHistory.entity_type, notification entity_type) rather
    # than inventing a parallel spelling — "action_item", not
    # "meeting_action_item".
    PROJECT_RISK = "project_risk"
    PROJECT_ISSUE = "project_issue"
    SAFETY_EVENT = "safety_event"
    NCR = "ncr"
    PURCHASE_REQUEST = "purchase_request"
    MEETING_ACTION_ITEM = "action_item"
    APPROVAL_REQUEST = "approval_request"
    ORGANIZATION = "organization"
    PROJECT_MEMBERSHIP = "project_membership"
    NOTIFICATION = "notification"


class AuditAction:
    LOGIN = "login"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    REFRESH = "refresh"
    PASSWORD_CHANGE = "password_change"

    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_NEW_VERSION = "document_new_version"
    DOCUMENT_ARCHIVE = "document_archive"
    DOCUMENT_RESTORE = "document_restore"
    DOCUMENT_DOWNLOAD = "document_download"

    STATUS_CHANGE = "status_change"
    ASSIGN = "assign"
    UNASSIGN = "unassign"

    APPROVE = "approve"
    REJECT = "reject"
    RETURN = "return"
    CANCEL = "cancel"
    REVIEWER_ASSIGN = "reviewer_assign"

    ORGANIZATION_UPDATE = "organization_update"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DISABLE = "user_disable"
    MEMBERSHIP_CREATE = "membership_create"
    MEMBERSHIP_REMOVE = "membership_remove"

    NOTIFICATION_READ = "notification_read"
    NOTIFICATION_READ_ALL = "notification_read_all"


class AuditResult:
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


def record_audit_event(
    *,
    entity_type: str,
    action: str,
    result: str,
    organization_id: int | None = None,
    actor_user_id: int | None = None,
    project_id: int | None = None,
    entity_id: int | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    context = get_request_context()

    # The entire body — including opening the session itself — is inside
    # this try/except, deliberately: SessionLocal() can itself raise (a
    # DB outage, an exhausted connection pool, ...), and that must be
    # caught exactly like a failed INSERT. A version of this function
    # that only wrapped the INSERT/commit and left SessionLocal() outside
    # the try block would still propagate a connection failure straight
    # into the caller's route handler — precisely the "audit logging must
    # never block/fail the business operation" guarantee this function
    # exists to uphold.
    db = None
    try:
        db = SessionLocal()
        db.add(AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            result=result,
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            request_id=context.request_id if context else None,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
        ))
        db.commit()
    except Exception:
        if db is not None:
            db.rollback()
        logger.exception(
            "audit_log_write_failed action=%s entity_type=%s entity_id=%s actor_user_id=%s",
            action, entity_type, entity_id, actor_user_id,
        )
    finally:
        if db is not None:
            db.close()
