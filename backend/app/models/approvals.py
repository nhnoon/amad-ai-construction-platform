"""Approval Engine (Sprint 5) — real, per-entity approve/reject/return
workflows for PurchaseRequest, ChangeOrder, Claim, and Document. Not an
AI concept (moved out of app/models/ai.py, where ApprovalRequest
previously sat unused and shaped for a different, never-built use case:
AI-agent action approval — action_type/action_description/payload/a
free-text requested_by defaulting to "ai_agent"). Those legacy columns
are kept, now nullable, untouched by Sprint 5's own code, in case that
original use case is ever built; Sprint 5 adds its own columns alongside
them rather than repurposing/renaming anything already shipped — see
alembic/versions/0019_approval_engine.py's docstring for the full
additive-migration rationale.

Design mirrors app/ai/ownership_engine.py / app/ai/workflow_engine.py
deliberately: one shared status vocabulary + transition matrix (see
app/ai/approval_engine.py), reviewer validation via real UserAccount /
ProjectMembership rows (never free text), and an append-only history
table (ApprovalHistory below) — the same polymorphic
(approval_request_id) pattern AssignmentHistory already uses for its own
append-only trail.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    # Sprint 5 columns — always populated by app/ai/approval_engine.py.
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    # One of "purchase_request" | "change_order" | "claim" | "document" —
    # see app/ai/approval_engine.py's ENTITY_* constants.
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    requested_by_user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    assigned_reviewer_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    # Document-specific: DocumentVersion.version_number this approval
    # applies to, snapshotted at request-creation time so a later
    # re-upload never silently inherits an earlier approval. NULL for
    # every other entity_type.
    target_version = Column(Integer, nullable=True)

    # Legacy AI-agent-approval columns (pre-Sprint-5) — kept, now
    # nullable, never populated by Sprint 5's own code.
    action_type = Column(String(100), nullable=True)
    action_description = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    requested_by = Column(String(100), nullable=False, default="ai_agent")
    reviewed_by = Column(String(255), nullable=True)

    risk_level = Column(String(20), nullable=False, default="medium")
    # "Pending" | "Under Review" | "Approved" | "Rejected" | "Returned" |
    # "Cancelled" — see app/ai/approval_engine.py::APPROVAL_TRANSITIONS.
    status = Column(String(50), nullable=False, default="pending", index=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_approval_requests_entity", "entity_type", "entity_id"),
        Index("ix_approval_requests_requested_by_user_id", "requested_by_user_id"),
        Index("ix_approval_requests_due_at", "due_at"),
    )


class ApprovalHistory(Base):
    """Append-only — one row per lifecycle transition (assign/reassign
    does NOT add a row here; it's not a status transition — see
    app/ai/approval_engine.py). Mirrors app/models/assignment_history.py
    exactly."""

    __tablename__ = "approval_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
