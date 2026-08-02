from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class NotificationOut(BaseModel):
    id: int
    organization_id: int
    recipient_user_id: int
    actor_user_id: Optional[int] = None
    project_id: Optional[int] = None
    event_type: str
    entity_type: str
    entity_id: int
    title: str
    message: str
    severity: str
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    # deduplication_key is intentionally NOT exposed — internal
    # bookkeeping only (Sprint 4 Part A: "no internal storage keys ...
    # in messages").

    model_config = {"from_attributes": True}


class NotificationSummaryOut(BaseModel):
    unread_count: int
    total_count: int
    unread_by_severity: dict[str, int]


class MarkAllReadOut(BaseModel):
    updated_count: int
