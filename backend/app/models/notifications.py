"""Notifications Engine (Sprint 4) — persistent, user-scoped, in-app-only
notifications. One row per notification, created by
app/ai/notification_service.py (never directly by routers — see that
module's docstring for the "one centralized service" rationale).

Organization- and recipient-scoped by design (Sprint 4 Part A/D): every
query in app/api/v1/notifications.py filters by both
recipient_user_id == caller AND organization_id == caller's own
organization, so cross-user and cross-tenant access are both structurally
impossible, not just policy.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func
from .base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Denormalized alongside recipient_user_id (rather than derived via a
    # join every query) — same reasoning as AssignmentHistory.project_id
    # (app/models/assignment_history.py): every notification is already
    # tenant-scoped at creation time, so this is a cheap, always-correct
    # column, not a join target.
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    # Who sees this notification. CASCADE — a notification has no meaning
    # once its recipient's account is gone.
    recipient_user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False)
    # Who performed the action that triggered this notification. Nullable
    # + SET NULL — same pattern as *.assigned_by / *.updated_by elsewhere
    # in this app: preserve the notification even if the actor's account
    # is later removed.
    actor_user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    # Nullable: not every future notification type needs to be tied to a
    # single project (none in this sprint, but the column shouldn't force
    # one). CASCADE — a notification about a deleted project is noise.
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    # e.g. "assigned" | "reassigned" | "unassigned" | "status_changed" |
    # "item_completed" | "item_reopened" | "due_date_changed" |
    # "purchase_request_approved" | "purchase_request_rejected" |
    # "purchase_request_returned" — see app/ai/notification_service.py.
    event_type = Column(String(50), nullable=False)
    # One of app/ai/ownership_engine.py's ENTITY_* values (or "purchase_request").
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    # "info" | "warning" | "critical" — free-text by convention (matches
    # this codebase's general avoidance of DB-level enums for workflow
    # vocabularies, e.g. *.status columns), validated at the service layer.
    severity = Column(String(20), nullable=False, server_default="info")
    # Frontend-agnostic relative path (e.g. "/projects/3/risks/12") — Part G:
    # no frontend work this sprint, this is only a forward-compatible seam.
    action_url = Column(String(500), nullable=True)

    is_read = Column(Boolean, nullable=False, server_default="false")
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Internal bookkeeping only — never serialized via the API (see
    # NotificationOut). NULL-able because Postgres unique indexes treat
    # every NULL as distinct, so notification types that never set one
    # (none currently) could never collide with each other.
    deduplication_key = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_notifications_recipient_user_id", "recipient_user_id"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_project_id", "project_id"),
        # Backs the hot "my unread, newest first" query (GET /notifications
        # default view) without a separate lookup + sort step.
        Index("ix_notifications_recipient_unread_created", "recipient_user_id", "is_read", "created_at"),
        Index("ix_notifications_dedup_key", "deduplication_key", unique=True),
    )
