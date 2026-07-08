from pydantic import BaseModel
from typing import Optional


class SubcontractorOut(BaseModel):
    id: int
    name: str
    trade: str
    contact_person: str
    phone: str
    email: str
    classification: str
    city: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class SubcontractorEvaluationOut(BaseModel):
    id: int
    subcontractor_id: int
    project_id: int
    evaluation_date: str
    quality_score: int
    safety_score: int
    schedule_score: int
    manpower_score: int
    overall_rating: float
    comments: str
    linked_safety_event_id: Optional[int] = None
    linked_ncr_id: Optional[int] = None
    linked_daily_activity_id: Optional[int] = None

    model_config = {"from_attributes": True}
