from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AssignRequest(BaseModel):
    """Identical shape across all six entities — assignment is a generic
    operation (see app/ai/ownership_engine.py), so one schema is shared
    rather than six near-duplicates."""

    user_id: int
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class UnassignRequest(BaseModel):
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class AssignmentHistoryOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    project_id: int
    previous_owner_id: Optional[int] = None
    new_owner_id: Optional[int] = None
    assigned_by: Optional[int] = None
    assigned_at: datetime

    model_config = {"from_attributes": True}
