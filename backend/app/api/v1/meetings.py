from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...core.deps import DbSession
from ...models.meetings import Meeting, ProjectDecision, MeetingActionItem
from ...schemas.meetings import MeetingOut, ProjectDecisionOut, MeetingActionItemOut, MeetingActionItemCreate

router = APIRouter(tags=["meetings"])


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
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    q = db.query(MeetingActionItem).filter(MeetingActionItem.project_id == project_id)
    if status:
        q = q.filter(MeetingActionItem.status == status)
    return q.offset(skip).limit(limit).all()


@router.post("/projects/{project_id}/action-items", response_model=MeetingActionItemOut, status_code=201)
def create_action_item(project_id: int, body: MeetingActionItemCreate, db: DbSession):
    item = MeetingActionItem(project_id=project_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
