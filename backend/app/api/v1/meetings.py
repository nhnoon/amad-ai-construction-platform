import logging

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...ai.meeting_memory import write_meeting_memory
from ...ai.scope import build_ai_scope
from ...ai.workflow_engine import update_action_item
from ...ai.ownership_engine import apply_ownership_filters, apply_overdue_filter, assign_action_item, unassign_action_item
from ...core.deps import CurrentScope, CurrentUser, DbSession
from ...models.meetings import Meeting, ProjectDecision, MeetingActionItem, MeetingAttendee
from ...schemas.meetings import (
    MeetingOut, MeetingCreate, ProjectDecisionOut,
    MeetingActionItemOut, MeetingActionItemCreate, MeetingActionItemUpdate,
)
from ...schemas.ownership import AssignRequest, UnassignRequest

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
    scope: CurrentScope,
    meeting_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    scope.enforce_project_access(project_id)
    q = db.query(Meeting).filter(Meeting.project_id == project_id)
    if meeting_type:
        q = q.filter(Meeting.meeting_type == meeting_type)
    return q.offset(skip).limit(limit).all()


@router.post("/projects/{project_id}/meetings", response_model=MeetingOut, status_code=201)
def create_meeting(project_id: int, body: MeetingCreate, db: DbSession, current_user: CurrentUser, scope: CurrentScope):
    scope.enforce_project_access(project_id)
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
def get_meeting(project_id: int, meeting_id: int, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(project_id)
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
    scope: CurrentScope,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    scope.enforce_project_access(project_id)
    return (
        db.query(ProjectDecision)
        .filter(ProjectDecision.project_id == project_id)
        .offset(skip).limit(limit).all()
    )


@router.get("/projects/{project_id}/meetings/{meeting_id}/decisions", response_model=list[ProjectDecisionOut])
def list_meeting_decisions(project_id: int, meeting_id: int, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(project_id)
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
    scope: CurrentScope,
    meeting_id: Optional[int] = None,
    status: Optional[str] = None,
    assigned_to_me: bool = False,
    assigned_to: Optional[int] = None,
    unassigned: bool = False,
    overdue: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    scope.enforce_project_access(project_id)
    q = db.query(MeetingActionItem).filter(MeetingActionItem.project_id == project_id)
    if meeting_id is not None:
        q = q.filter(MeetingActionItem.meeting_id == meeting_id)
    if status:
        q = q.filter(MeetingActionItem.status == status)
    q = apply_ownership_filters(q, MeetingActionItem, scope, assigned_to_me=assigned_to_me, assigned_to=assigned_to, unassigned=unassigned)
    q = apply_overdue_filter(q, MeetingActionItem, overdue=overdue)
    return q.offset(skip).limit(limit).all()


@router.post("/projects/{project_id}/action-items", response_model=MeetingActionItemOut, status_code=201)
def create_action_item(project_id: int, body: MeetingActionItemCreate, db: DbSession, current_user: CurrentUser, scope: CurrentScope):
    scope.enforce_project_access(project_id)
    # body.project_id is intentionally discarded in favor of the URL's
    # project_id (already authorized above) — trusting a client-supplied
    # project_id here would let a caller attach the new action item to a
    # project it was never authorized for.
    item = MeetingActionItem(project_id=project_id, **body.model_dump(exclude={"project_id"}))
    db.add(item)
    db.commit()
    db.refresh(item)
    # Refresh this meeting's memory (upsert) so a later "what are the open
    # action items from MTG-N" question reflects this addition instead of
    # whatever was recorded at meeting-creation time.
    _write_meeting_memory_best_effort(db, current_user, item.meeting_id)
    return item


@router.patch("/projects/{project_id}/action-items/{action_item_id}", response_model=MeetingActionItemOut)
def update_action_item_route(
    project_id: int, action_item_id: int, body: MeetingActionItemUpdate,
    db: DbSession, scope: CurrentScope,
):
    """Core Workflow Engine (Sprint 2) — see app/ai/workflow_engine.py for
    the status transition matrix and close-out rules. Reassignment (owner)
    and due-date changes are allowed independent of any status change."""
    return update_action_item(db, scope, project_id, action_item_id, body)


@router.post("/projects/{project_id}/action-items/{action_item_id}/assign", response_model=MeetingActionItemOut)
def assign_action_item_route(project_id: int, action_item_id: int, body: AssignRequest, db: DbSession, scope: CurrentScope):
    """Ownership Engine (Sprint 3) — see app/ai/ownership_engine.py."""
    return assign_action_item(db, scope, project_id, action_item_id, body.user_id, body.expected_updated_at)


@router.post("/projects/{project_id}/action-items/{action_item_id}/unassign", response_model=MeetingActionItemOut)
def unassign_action_item_route(project_id: int, action_item_id: int, body: UnassignRequest, db: DbSession, scope: CurrentScope):
    return unassign_action_item(db, scope, project_id, action_item_id, body.expected_updated_at)
