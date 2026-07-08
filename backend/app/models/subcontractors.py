from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Subcontractor(Base):
    __tablename__ = "subcontractors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    trade = Column(String(100), nullable=False)
    contact_person = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    classification = Column(String(50), nullable=False)
    city = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(String(50), nullable=False)

    daily_activities = relationship("DailyActivity", back_populates="subcontractor")
    safety_events = relationship("SafetyEvent", back_populates="subcontractor")
    ncrs = relationship("NCR", back_populates="subcontractor")
    evaluations = relationship("SubcontractorEvaluation", back_populates="subcontractor")


class SubcontractorEvaluation(Base):
    __tablename__ = "subcontractor_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subcontractor_id = Column(Integer, ForeignKey("subcontractors.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    evaluation_date = Column(String(50), nullable=False)
    quality_score = Column(Integer, nullable=False)
    safety_score = Column(Integer, nullable=False)
    schedule_score = Column(Integer, nullable=False)
    manpower_score = Column(Integer, nullable=False)
    overall_rating = Column(Float, nullable=False)
    comments = Column(Text, nullable=False)
    linked_safety_event_id = Column(
        Integer, ForeignKey("safety_events.id"), nullable=True
    )
    linked_ncr_id = Column(Integer, ForeignKey("ncrs.id"), nullable=True)
    linked_daily_activity_id = Column(
        Integer, ForeignKey("daily_activities.id"), nullable=True
    )

    subcontractor = relationship("Subcontractor", back_populates="evaluations")
    project = relationship("Project", back_populates="subcontractor_evaluations")
    linked_safety_event = relationship(
        "SafetyEvent", back_populates="subcontractor_evaluations"
    )
    linked_ncr = relationship("NCR", back_populates="subcontractor_evaluations")
    linked_daily_activity = relationship(
        "DailyActivity", back_populates="subcontractor_evaluations"
    )
