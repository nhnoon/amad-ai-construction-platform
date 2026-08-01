from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...ai.workflow_engine import update_ncr, update_safety_event
from ...core.deps import CurrentScope, DbSession
from ...models.safety import SafetyEvent, NCR
from ...schemas.safety import SafetyEventOut, SafetyEventUpdate, NCROut, NCRUpdate

router = APIRouter(tags=["safety-quality"])


@router.get("/projects/{project_id}/safety-events", response_model=list[SafetyEventOut])
def list_safety_events(
    project_id: int,
    db: DbSession,
    scope: CurrentScope,
    severity: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    scope.enforce_project_access(project_id)
    q = db.query(SafetyEvent).filter(SafetyEvent.project_id == project_id)
    if severity:
        q = q.filter(SafetyEvent.severity == severity)
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/safety-events/{event_id}", response_model=SafetyEventOut)
def get_safety_event(project_id: int, event_id: int, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(project_id)
    event = (
        db.query(SafetyEvent)
        .filter(SafetyEvent.id == event_id, SafetyEvent.project_id == project_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Safety event not found")
    return event


@router.patch("/projects/{project_id}/safety-events/{event_id}", response_model=SafetyEventOut)
def update_safety_event_route(
    project_id: int, event_id: int, body: SafetyEventUpdate, db: DbSession, scope: CurrentScope,
):
    """Core Workflow Engine (Sprint 2) — see app/ai/workflow_engine.py.
    Only Open/Closed is supported; this model has no investigation/
    assignee field, so no such workflow is fabricated here."""
    return update_safety_event(db, scope, project_id, event_id, body)


@router.get("/projects/{project_id}/ncrs", response_model=list[NCROut])
def list_ncrs(
    project_id: int,
    db: DbSession,
    scope: CurrentScope,
    status: Optional[str] = None,
    ncr_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    scope.enforce_project_access(project_id)
    q = db.query(NCR).filter(NCR.project_id == project_id)
    if status:
        q = q.filter(NCR.status == status)
    if ncr_type:
        q = q.filter(NCR.ncr_type == ncr_type)
    return q.offset(skip).limit(limit).all()


@router.patch("/projects/{project_id}/ncrs/{ncr_id}", response_model=NCROut)
def update_ncr_route(project_id: int, ncr_id: int, body: NCRUpdate, db: DbSession, scope: CurrentScope):
    """Core Workflow Engine (Sprint 2) — see app/ai/workflow_engine.py for
    the status transition matrix and close-out rules."""
    return update_ncr(db, scope, project_id, ncr_id, body)
