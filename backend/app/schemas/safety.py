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

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}
