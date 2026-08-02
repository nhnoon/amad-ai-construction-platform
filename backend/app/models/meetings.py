from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    meeting_date = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    meeting_type = Column(String(100), nullable=False)

    project = relationship("Project", back_populates="meetings")
    project_decisions = relationship("ProjectDecision", back_populates="meeting")
    attendees = relationship("MeetingAttendee", back_populates="meeting")
    action_items = relationship("MeetingActionItem", back_populates="meeting")


class ProjectDecision(Base):
    __tablename__ = "project_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    decision_date = Column(String(50), nullable=False)
    decision_text = Column(Text, nullable=False)
    owner = Column(String(255), nullable=False)

    project = relationship("Project", back_populates="project_decisions")
    meeting = relationship("Meeting", back_populates="project_decisions")
    claim_evidence = relationship("ClaimEvidence", back_populates="decision")


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=True)
    organization = Column(String(255), nullable=True)

    meeting = relationship("Meeting", back_populates="attendees")


class MeetingActionItem(Base):
    __tablename__ = "meeting_action_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    owner = Column(String(255), nullable=False)
    due_date = Column(String(50), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="open", index=True)
    priority = Column(String(20), nullable=False, default="medium")
    source = Column(String(50), nullable=False, default="manual")
    # Core Workflow Engine (Sprint 2) — completed_at matches
    # ProjectIssue.resolved_at's existing type (a business-meaningful
    # close-out date), not the system-timestamp convention below.
    completed_at = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    # Ownership Engine (Sprint 3) — `owner` (free text, required at
    # creation) is kept unchanged for backward compatibility; `owner_id`
    # is the new real-user assignment, additive and nullable.
    owner_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)

    meeting = relationship("Meeting", back_populates="action_items")
