from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class MyWorkItemOut(BaseModel):
    entity_type: str
    entity_id: int
    # Optional (Sprint 5): the "approval" entity_type can target an
    # organization-scoped General Library document, which has no
    # project_id at all — every other entity_type still always
    # populates both fields.
    project_id: Optional[int] = None
    project_code: Optional[str] = None
    title: str
    status: str
    priority: Optional[str] = None
    due_date: Optional[str] = None
    is_overdue: bool
    is_due_soon: bool
    updated_at: datetime
    action_url: str
