"""Ownership Engine (Sprint 3) — assignment history only, not a full audit
log. One row per assignment change (assign/reassign/unassign) across all
six ownership-upgraded entities.

Polymorphic by (entity_type, entity_id) rather than six separate history
tables or six nullable typed FKs — the same pattern this codebase already
uses for cross-entity references (see Correspondence.related_record_type/
related_record_id, GeneratedDocument.related_record_id in
app/models/documents.py).
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func
from .base import Base


class AssignmentHistory(Base):
    __tablename__ = "assignment_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # One of: "project_risk" | "project_issue" | "action_item" |
    # "safety_event" | "ncr" | "purchase_request" — see
    # app/ai/ownership_engine.py's ENTITY_TYPE_* constants.
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    # Denormalized for tenant-scoped queries without a join back through
    # six different tables — every entity here is already project-scoped.
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    previous_owner_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    new_owner_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    # Who performed the assignment/unassignment — always server-set from
    # scope.user_id, never client-supplied (same pattern as
    # Document.uploaded_by / *.updated_by from Sprints 1-2).
    assigned_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_assignment_history_entity", "entity_type", "entity_id"),
    )
