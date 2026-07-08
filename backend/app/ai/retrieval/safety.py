"""Safety event and NCR retrieval tools."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.models.safety import SafetyEvent, NCR
from .base import Evidence, RetrievalResult

_OPEN_NCR_STATUSES = ("Open", "Under Corrective Action")


def get_safety_summary(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    q = db.query(SafetyEvent)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(SafetyEvent.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={}, evidence=[])
        q = q.filter(SafetyEvent.project_id.in_(ids))

    events = q.order_by(SafetyEvent.id.desc()).limit(limit).all()
    if not events:
        return RetrievalResult(data={"safety_events": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for ev in events:
        rows.append({
            "id": ev.id,
            "project_id": ev.project_id,
            "event_date": ev.event_date,
            "severity": ev.severity,
            "description": ev.description,
            "corrective_action": ev.corrective_action,
        })
        evidence.append(Evidence(
            source_type="safety_event",
            source_id=str(ev.id),
            label=f"Safety Event SE-{ev.id}",
            snippet=(
                f"SE-{ev.id}: severity={ev.severity}, date={ev.event_date}, "
                f"description={ev.description[:120]}"
            ),
            project_id=ev.project_id,
            ui_metadata={"href": "/safety", "icon": "shield-alert"},
        ))

    return RetrievalResult(
        data={"safety_events": rows, "total": len(rows)}, evidence=evidence
    )


def get_open_ncrs(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    q = db.query(NCR).filter(NCR.status.in_(_OPEN_NCR_STATUSES))
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(NCR.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"ncrs": [], "total": 0}, evidence=[])
        q = q.filter(NCR.project_id.in_(ids))

    ncrs = q.order_by(NCR.id.desc()).limit(limit).all()
    if not ncrs:
        return RetrievalResult(data={"ncrs": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for n in ncrs:
        rows.append({
            "id": n.id,
            "project_id": n.project_id,
            "ncr_type": n.ncr_type,
            "description": n.description,
            "status": n.status,
            "issue_date": n.issue_date,
            "root_cause": n.root_cause,
        })
        evidence.append(Evidence(
            source_type="ncr",
            source_id=str(n.id),
            label=f"NCR NCR-{n.id}",
            snippet=(
                f"NCR-{n.id}: type={n.ncr_type}, status={n.status}, "
                f"date={n.issue_date}, description={n.description[:120]}"
            ),
            project_id=n.project_id,
            ui_metadata={"href": "/safety", "icon": "clipboard-x"},
        ))

    return RetrievalResult(data={"ncrs": rows, "total": len(rows)}, evidence=evidence)
