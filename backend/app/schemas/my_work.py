from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class MyWorkItemOut(BaseModel):
    entity_type: str
    entity_id: int
    project_id: int
    project_code: str
    title: str
    status: str
    priority: Optional[str] = None
    due_date: Optional[str] = None
    is_overdue: bool
    is_due_soon: bool
    updated_at: datetime
    action_url: str
