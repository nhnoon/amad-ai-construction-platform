from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ApprovalRequestCreate(BaseModel):
    entity_type: str
    entity_id: int
    risk_level: str = "medium"
    review_note: Optional[str] = None
    assigned_reviewer_id: Optional[int] = None
    due_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class ApprovalAssignRequest(BaseModel):
    reviewer_user_id: int
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class ApprovalActionRequest(BaseModel):
    """Shared body shape for start-review/approve/cancel — review_note is
    optional here. reject/return use ApprovalReasonRequiredRequest
    instead, where it's required."""
    review_note: Optional[str] = None
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class ApprovalReasonRequiredRequest(BaseModel):
    review_note: str
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class ApprovalRequestOut(BaseModel):
    id: int
    organization_id: int
    project_id: Optional[int] = None
    entity_type: str
    entity_id: int
    requested_by_user_id: Optional[int] = None
    assigned_reviewer_id: Optional[int] = None
    status: str
    risk_level: str
    review_note: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    target_version: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalHistoryOut(BaseModel):
    id: int
    approval_request_id: int
    previous_status: Optional[str] = None
    new_status: str
    actor_user_id: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalSummaryOut(BaseModel):
    by_status: dict[str, int]
    overdue_count: int
    due_soon_count: int
