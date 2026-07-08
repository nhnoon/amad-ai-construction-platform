from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class SiteReport(Base):
    __tablename__ = "site_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    report_date = Column(String(50), nullable=False)
    weather = Column(String(100), nullable=False)
    summary = Column(Text, nullable=False)

    project = relationship("Project", back_populates="site_reports")
    daily_activities = relationship("DailyActivity", back_populates="site_report")


class DailyActivity(Base):
    __tablename__ = "daily_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    subcontractor_id = Column(Integer, ForeignKey("subcontractors.id"), nullable=False)
    site_report_id = Column(Integer, ForeignKey("site_reports.id"), nullable=False)
    activity_date = Column(String(50), nullable=False)
    activity_description = Column(Text, nullable=False)
    manpower_count = Column(Integer, nullable=False)

    project = relationship("Project", back_populates="daily_activities")
    subcontractor = relationship("Subcontractor", back_populates="daily_activities")
    site_report = relationship("SiteReport", back_populates="daily_activities")
    subcontractor_evaluations = relationship(
        "SubcontractorEvaluation", back_populates="linked_daily_activity"
    )
