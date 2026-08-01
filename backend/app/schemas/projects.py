from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class ProjectBase(BaseModel):
    project_code: str
    project_name: str
    project_type: str
    client_name: str
    city: str
    start_date: str
    planned_finish: str
    actual_finish: Optional[str] = None
    status: str
    budget: float


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    client_name: Optional[str] = None
    city: Optional[str] = None
    start_date: Optional[str] = None
    planned_finish: Optional[str] = None
    actual_finish: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None


class ProjectOut(ProjectBase):
    id: int

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    id: int
    project_code: str
    project_name: str
    project_type: str
    client_name: str
    city: str
    status: str
    budget: float
    start_date: str
    planned_finish: str

    model_config = {"from_attributes": True}


class ProjectRiskBase(BaseModel):
    title: str
    description: Optional[str] = None
    probability: str = "medium"
    impact: str = "medium"
    status: str = "open"
    owner: Optional[str] = None
    mitigation: Optional[str] = None


class ProjectRiskCreate(ProjectRiskBase):
    pass


class ProjectRiskOut(ProjectRiskBase):
    id: int
    project_id: int
    # Core Workflow Engine (Sprint 2)
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class ProjectRiskUpdate(BaseModel):
    """Partial update — every field optional; only relevant, pre-existing
    workflow fields are updatable (see app/ai/workflow_engine.py for the
    status transition matrix and close-out rules). `title`/`description`
    are content fields, not workflow fields, and are intentionally not
    included here."""

    status: Optional[str] = None
    owner: Optional[str] = None
    mitigation: Optional[str] = None
    probability: Optional[str] = None
    impact: Optional[str] = None
    # Optimistic concurrency (Sprint 2 §8) — omit to skip the check
    # entirely (fully backward compatible, since no existing caller could
    # ever have known this field). If provided and it does not match the
    # row's current updated_at, the update is rejected with 409.
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class ProjectIssueBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str = "medium"
    status: str = "open"
    owner: Optional[str] = None
    resolution: Optional[str] = None


class ProjectIssueCreate(ProjectIssueBase):
    pass


class ProjectIssueOut(ProjectIssueBase):
    id: int
    project_id: int
    resolved_at: Optional[str] = None
    # Core Workflow Engine (Sprint 2)
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class ProjectIssueUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[str] = None
    severity: Optional[str] = None
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


# ── Health Score ──────────────────────────────────────────────────────────────

class HealthScoreOut(BaseModel):
    """Full health score result for a single project."""
    project_id: int
    project_code: str
    project_name: str
    status: str
    score: int                    # 0–100
    level: str                    # Excellent | Good | At Risk | Critical
    reasons: List[str]
    schedule_penalty: float
    safety_penalty: float
    ncr_penalty: float
    procurement_penalty: float
    risk_penalty: float

    model_config = {"from_attributes": True}


class ProjectHealthSummary(BaseModel):
    """Lightweight health counts for dashboard use."""
    excellent: int
    good: int
    at_risk: int
    critical: int
    avg_score: float
