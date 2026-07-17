import logging

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...ai.meeting_memory import write_meeting_memory
from ...ai.scope import build_ai_scope
from ...core.deps import CurrentUser, DbSession
from ...models.meetings import Meeting, ProjectDecision, MeetingActionItem, MeetingAttendee
from ...schemas.meetings import (
    MeetingOut, MeetingCreate, ProjectDecisionOut, MeetingActionItemOut, MeetingActionItemCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["meetings"])


def _write_meeting_memory_best_effort(db, current_user, meeting_id: int) -> None:
    """Memory is a supplement, never a blocker — a meeting/action-item
    write must succeed even if memory recording fails for any reason."""
    try:
        scope = build_ai_scope(current_user, db)
        write_meeting_memory(db, scope, meeting_id)
    except Exception as exc:
        logger.warning("meeting_memory_write_failed meeting_id=%s error=%s", meeting_id, exc)


@router.get("/projects/{project_id}/meetings", response_model=list[MeetingOut])
def list_meetings(
    project_id: int,
    db: DbSession,
    meeting_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Meeting).filter(Meeting.project_id == project_id)
    if meeting_type:
        q = q.filter(Meeting.meeting_type == meeting_type)
    return q.offset(skip).limit(limit).all()


@router.post("/projects/{project_id}/meetings", response_model=MeetingOut, status_code=201)
def create_meeting(project_id: int, body: MeetingCreate, db: DbSession, current_user: CurrentUser):
    meeting = Meeting(
        project_id=project_id,
        title=body.title,
        meeting_date=body.meeting_date,
        meeting_type=body.meeting_type,
    )
    db.add(meeting)
    db.flush()
    for name in body.attendees or []:
        name = name.strip()
        if name:
            db.add(MeetingAttendee(meeting_id=meeting.id, name=name))
    db.commit()
    db.refresh(meeting)
    _write_meeting_memory_best_effort(db, current_user, meeting.id)
    return meeting


@router.get("/projects/{project_id}/meetings/{meeting_id}", response_model=MeetingOut)
def get_meeting(project_id: int, meeting_id: int, db: DbSession):
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.project_id == project_id)
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/projects/{project_id}/decisions", response_model=list[ProjectDecisionOut])
def list_project_decisions(
    project_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return (
        db.query(ProjectDecision)
        .filter(ProjectDecision.project_id == project_id)
        .offset(skip).limit(limit).all()
    )


@router.get("/projects/{project_id}/meetings/{meeting_id}/decisions", response_model=list[ProjectDecisionOut])
def list_meeting_decisions(project_id: int, meeting_id: int, db: DbSession):
    return (
        db.query(ProjectDecision)
        .filter(
            ProjectDecision.meeting_id == meeting_id,
            ProjectDecision.project_id == project_id,
        )
        .all()
    )


@router.get("/projects/{project_id}/action-items", response_model=list[MeetingActionItemOut])
def list_action_items(
    project_id: int,
    db: DbSession,
    meeting_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    q = db.query(MeetingActionItem).filter(MeetingActionItem.project_id == project_id)
    if meeting_id is not None:
        q = q.filter(MeetingActionItem.meeting_id == meeting_id)
    if status:
        q = q.filter(MeetingActionItem.status == status)
    return q.offset(skip).limit(limit).all()


@router.post("/projects/{project_id}/action-items", response_model=MeetingActionItemOut, status_code=201)
def create_action_item(project_id: int, body: MeetingActionItemCreate, db: DbSession, current_user: CurrentUser):
    item = MeetingActionItem(project_id=project_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    # Refresh this meeting's memory (upsert) so a later "what are the open
    # action items from MTG-N" question reflects this addition instead of
    # whatever was recorded at meeting-creation time.
    _write_meeting_memory_best_effort(db, current_user, item.meeting_id)
    return item
