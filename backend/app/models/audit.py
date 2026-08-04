import uuid

from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from .base import Base


class AuditLog(Base):
    """RC1 Phase 1 Sprint 4 — Enterprise Audit Logging.

    Append-only, immutable record of every security-sensitive and
    mutating action this sprint covers (authentication, documents,
    workflow status/assignment, approvals, admin, notifications — see
    app/core/audit_log.py for the full action vocabulary and the single
    writer function, record_audit_event()).

    `id` (BigInteger — audit volume grows without bound over the life of
    a deployment, unlike this app's other tables) is the DB primary key,
    matching every other table's convention here; `event_id` is a
    separate stable UUID identifier for external reference (e.g. a
    support ticket citing "event abc-123", or a future export/webhook
    payload) that survives independently of internal row numbering.

    Immutability is enforced at TWO layers, deliberately:
      1. No service or route anywhere in the app ever UPDATEs or DELETEs
         a row here — app/core/audit_log.py::record_audit_event is an
         INSERT-only function and is the only writer; there is no
         update/delete function for this model at all, and GET /audit
         (app/api/v1/audit.py) is read-only.
      2. A database-level trigger (see migration 0021) rejects any
         UPDATE or DELETE on this table outright, at the Postgres level
         — so the guarantee holds even against a future application bug
         or an ad-hoc admin script bypassing the ORM entirely, not just
         against "normal" API usage.

    organization_id / actor_user_id / project_id all use
    ondelete="SET NULL" — deliberately, and unlike most FKs elsewhere in
    this codebase where that's about not blocking a delete: here it's
    specifically so an audit ROW IS NEVER LOST just because the actor,
    org, or project it referenced was later deleted. Losing the row
    would defeat the entire feature ("no audit event may silently
    disappear"); losing just the now-dangling reference is an acceptable,
    correctly-modeled trade-off.
    """

    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    # Nullable — many audited actions (login, admin/org-level actions)
    # have no project of their own; project-scoped entities (risks,
    # issues, safety events, NCRs, purchase requests, action items,
    # project documents) populate it for GET /audit's project filter.
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Free-text, validated at the call site via the AuditEntityType/
    # AuditAction/AuditResult constants in app/core/audit_log.py, not a
    # DB CHECK constraint — this codebase's consistent convention for
    # every *.status/workflow vocabulary column (see e.g. migration
    # 0019's docstring).
    entity_type = Column(String(50), nullable=False)
    # Nullable — a small number of audited actions (login, logout,
    # logout-all, notification-read-all) describe the actor's own
    # session/inbox rather than mutating one specific numbered row.
    entity_id = Column(Integer, nullable=True)

    action = Column(String(50), nullable=False)
    result = Column(String(20), nullable=False)

    # Request metadata (objective #5) — same extraction helpers already
    # established in Sprint 1/3 (client_ip_from_request,
    # request.headers["user-agent"]) and a new per-request correlation id
    # (see app/core/request_id.py) introduced this sprint specifically
    # for audit-log correlation, since none existed before.
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    request_id = Column(String(64), nullable=True)

    before_state = Column(JSONB, nullable=True)
    after_state = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_organization_id", "organization_id"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_project_id", "project_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
