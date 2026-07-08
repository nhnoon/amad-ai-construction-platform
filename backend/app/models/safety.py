from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
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

    project = relationship("Project", back_populates="ncrs")
    supplier = relationship("Supplier", back_populates="ncrs")
    subcontractor = relationship("Subcontractor", back_populates="ncrs")
    subcontractor_evaluations = relationship(
        "SubcontractorEvaluation", back_populates="linked_ncr"
    )
