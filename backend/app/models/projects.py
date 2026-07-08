from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_code = Column(String(50), nullable=False, unique=True)
    project_name = Column(String(255), nullable=False)
    project_type = Column(String(100), nullable=False)
    client_name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    start_date = Column(String(50), nullable=False)
    planned_finish = Column(String(50), nullable=False)
    actual_finish = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, index=True)
    budget = Column(Float, nullable=False)

    purchase_requests = relationship("PurchaseRequest", back_populates="project")
    purchase_orders = relationship("PurchaseOrder", back_populates="project")
    site_reports = relationship("SiteReport", back_populates="project")
    daily_activities = relationship("DailyActivity", back_populates="project")
    meetings = relationship("Meeting", back_populates="project")
    project_decisions = relationship("ProjectDecision", back_populates="project")
    documents = relationship("Document", back_populates="project")
    generated_documents = relationship("GeneratedDocument", back_populates="project")
    correspondence = relationship("Correspondence", back_populates="project")
    claims = relationship("Claim", back_populates="project")
    change_orders = relationship("ChangeOrder", back_populates="project")
    phases = relationship("ProjectPhase", back_populates="project")
    milestones = relationship("ProjectMilestone", back_populates="project")
    risks = relationship("ProjectRisk", back_populates="project")
    issues = relationship("ProjectIssue", back_populates="project")
    safety_events = relationship("SafetyEvent", back_populates="project")
    ncrs = relationship("NCR", back_populates="project")
    subcontractor_evaluations = relationship("SubcontractorEvaluation", back_populates="project")
    memberships = relationship("ProjectMembership", back_populates="project")


class ProjectPhase(Base):
    __tablename__ = "project_phases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    sequence = Column(Integer, nullable=False, server_default="1")
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, server_default="planned")

    project = relationship("Project", back_populates="phases")
    milestones = relationship("ProjectMilestone", back_populates="phase")


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    phase_id = Column(Integer, ForeignKey("project_phases.id"), nullable=True)
    name = Column(String(255), nullable=False)
    planned_date = Column(String(50), nullable=False)
    actual_date = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, server_default="pending")

    project = relationship("Project", back_populates="milestones")
    phase = relationship("ProjectPhase", back_populates="milestones")


class ProjectRisk(Base):
    __tablename__ = "project_risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    probability = Column(String(20), nullable=False, server_default="medium")
    impact = Column(String(20), nullable=False, server_default="medium")
    status = Column(String(50), nullable=False, server_default="open")
    owner = Column(String(255), nullable=True)
    mitigation = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=True)

    project = relationship("Project", back_populates="risks")


class ProjectIssue(Base):
    __tablename__ = "project_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, server_default="medium")
    status = Column(String(50), nullable=False, server_default="open")
    owner = Column(String(255), nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=True)
    resolved_at = Column(String(50), nullable=True)

    project = relationship("Project", back_populates="issues")
