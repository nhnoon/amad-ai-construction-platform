"""Meeting and decision retrieval tools."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.models.meetings import Meeting, ProjectDecision
from .base import Evidence, RetrievalResult


def get_recent_meetings(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 10,
) -> RetrievalResult:
    q = db.query(Meeting)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(Meeting.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"meetings": [], "total": 0}, evidence=[])
        q = q.filter(Meeting.project_id.in_(ids))

    meetings = q.order_by(Meeting.meeting_date.desc()).limit(limit).all()
    if not meetings:
        return RetrievalResult(data={"meetings": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for m in meetings:
        rows.append({
            "id": m.id,
            "project_id": m.project_id,
            "meeting_date": m.meeting_date,
            "title": m.title,
            "meeting_type": m.meeting_type,
        })
        evidence.append(Evidence(
            source_type="meeting",
            source_id=str(m.id),
            label=f"Meeting MTG-{m.id}",
            snippet=(
                f"MTG-{m.id}: {m.title}, type={m.meeting_type}, date={m.meeting_date}"
            ),
            project_id=m.project_id,
            ui_metadata={"href": "/meetings", "icon": "calendar"},
        ))

    return RetrievalResult(data={"meetings": rows, "total": len(rows)}, evidence=evidence)


def get_project_decisions(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 10,
) -> RetrievalResult:
    q = db.query(ProjectDecision)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(ProjectDecision.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"decisions": [], "total": 0}, evidence=[])
        q = q.filter(ProjectDecision.project_id.in_(ids))

    decisions = q.order_by(ProjectDecision.id.desc()).limit(limit).all()
    if not decisions:
        return RetrievalResult(data={"decisions": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for d in decisions:
        rows.append({
            "id": d.id,
            "project_id": d.project_id,
            "decision_text": d.decision_text,
            "decision_date": d.decision_date,
            "owner": d.owner,
        })
        evidence.append(Evidence(
            source_type="project_decision",
            source_id=str(d.id),
            label=f"Decision DEC-{d.id}",
            snippet=(
                f"DEC-{d.id}: {d.decision_text[:120]}, "
                f"owner={d.owner}, date={d.decision_date}"
            ),
            project_id=d.project_id,
            ui_metadata={"href": "/meetings", "icon": "check-square"},
        ))

    return RetrievalResult(data={"decisions": rows, "total": len(rows)}, evidence=evidence)
