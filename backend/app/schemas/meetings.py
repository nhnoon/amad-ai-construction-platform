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

    model_config = {"from_attributes": True}
