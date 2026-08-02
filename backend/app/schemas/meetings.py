from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class MeetingOut(BaseModel):
    id: int
    project_id: int
    meeting_date: str
    title: str
    meeting_type: str

    model_config = {"from_attributes": True}


class MeetingCreate(BaseModel):
    title: str
    meeting_date: str
    meeting_type: str
    # Attendee names only — MeetingAttendee's optional role/organization
    # fields aren't exposed on this fast-path create form.
    attendees: Optional[list[str]] = None


class ProjectDecisionOut(BaseModel):
    id: int
    project_id: int
    meeting_id: int
    decision_date: str
    decision_text: str
    owner: str

    model_config = {"from_attributes": True}


class MeetingActionItemBase(BaseModel):
    description: str
    owner: str
    due_date: Optional[str] = None
    status: str = "open"
    priority: str = "medium"
    source: str = "manual"


class MeetingActionItemCreate(MeetingActionItemBase):
    meeting_id: int
    project_id: int


class MeetingActionItemOut(MeetingActionItemBase):
    id: int
    meeting_id: int
    project_id: int
    # Core Workflow Engine (Sprint 2)
    completed_at: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    # Ownership Engine (Sprint 3)
    owner_id: Optional[int] = None
    assigned_by: Optional[int] = None
    assigned_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MeetingActionItemUpdate(BaseModel):
    """Reassignment (owner) and due-date changes are allowed independent
    of any status change — status is optional here too, so a PATCH that
    only reassigns or reschedules never needs to touch status at all."""

    status: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    completed_at: Optional[str] = None
    expected_updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}
