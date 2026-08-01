from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    subcontractor_id = Column(Integer, ForeignKey("subcontractors.id"), nullable=False)
    event_date = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    corrective_action = Column(Text, nullable=False)
    # Core Workflow Engine (Sprint 2) — this table had no status concept at
    # all before; every existing row is backfilled to 'Open' (see migration
    # 0016). Only Open/Closed are supported — no investigation/assignee
    # workflow is fabricated since no such fields exist on this model.
    status = Column(String(50), nullable=False, server_default="Open")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)

    project = relationship("Project", back_populates="safety_events")
    subcontractor = relationship("Subcontractor", back_populates="safety_events")
    subcontractor_evaluations = relationship(
        "SubcontractorEvaluation", back_populates="linked_safety_event"
    )


class NCR(Base):
    __tablename__ = "ncrs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    subcontractor_id = Column(Integer, ForeignKey("subcontractors.id"), nullable=True)
    ncr_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=False)
    issue_date = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    # Core Workflow Engine (Sprint 2) — required to reach Closed; NULL for
    # every existing row until explicitly set via PATCH.
    corrective_action = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)

    project = relationship("Project", back_populates="ncrs")
    supplier = relationship("Supplier", back_populates="ncrs")
    subcontractor = relationship("Subcontractor", back_populates="ncrs")
    subcontractor_evaluations = relationship(
        "SubcontractorEvaluation", back_populates="linked_ncr"
    )
