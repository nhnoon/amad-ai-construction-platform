from pydantic import BaseModel
from typing import Optional


class ChangeOrderOut(BaseModel):
    id: int
    project_id: int
    co_number: str
    description: str
    value: float
    status: str

    model_config = {"from_attributes": True}


class ClaimOut(BaseModel):
    id: int
    project_id: int
    claim_number: str
    claim_type: str
    amount: float
    status: str
    narrative: str

    model_config = {"from_attributes": True}


class ClaimEvidenceOut(BaseModel):
    id: int
    claim_id: int
    change_order_id: int
    decision_id: int
    document_id: int
    correspondence_id: int
    evidence_note: str

    model_config = {"from_attributes": True}
