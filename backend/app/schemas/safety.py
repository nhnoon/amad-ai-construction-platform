from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class SafetyEventOut(BaseModel):
    id: int
    project_id: int
    subcontractor_id: int
    event_date: str
    severity: str
    description: str
    corrective_action: str
    # Core Workflow Engine (Sprint 2) — status is new; every pre-existing
    # row is backfilled to "Open" by the migration's server default.
    status: str = "Open"
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class SafetyEventUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    corrective_action: Optional[str] = None
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class NCROut(BaseModel):
    id: int
    project_id: int
    supplier_id: Optional[int] = None
    subcontractor_id: Optional[int] = None
    ncr_type: str
    description: str
    root_cause: str
    issue_date: str
    status: str
    # Core Workflow Engine (Sprint 2) — new, nullable; required (non-empty)
    # to transition an NCR to Closed.
    corrective_action: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class NCRUpdate(BaseModel):
    status: Optional[str] = None
    corrective_action: Optional[str] = None
    root_cause: Optional[str] = None
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}
