from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...core.deps import DbSession
from ...models.safety import SafetyEvent, NCR
from ...schemas.safety import SafetyEventOut, NCROut

router = APIRouter(tags=["safety-quality"])


@router.get("/projects/{project_id}/safety-events", response_model=list[SafetyEventOut])
def list_safety_events(
    project_id: int,
    db: DbSession,
    severity: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(SafetyEvent).filter(SafetyEvent.project_id == project_id)
    if severity:
        q = q.filter(SafetyEvent.severity == severity)
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/safety-events/{event_id}", response_model=SafetyEventOut)
def get_safety_event(project_id: int, event_id: int, db: DbSession):
    event = (
        db.query(SafetyEvent)
        .filter(SafetyEvent.id == event_id, SafetyEvent.project_id == project_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Safety event not found")
    return event


@router.get("/projects/{project_id}/ncrs", response_model=list[NCROut])
def list_ncrs(
    project_id: int,
    db: DbSession,
    status: Optional[str] = None,
    ncr_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(NCR).filter(NCR.project_id == project_id)
    if status:
        q = q.filter(NCR.status == status)
    if ncr_type:
        q = q.filter(NCR.ncr_type == ncr_type)
    return q.offset(skip).limit(limit).all()
