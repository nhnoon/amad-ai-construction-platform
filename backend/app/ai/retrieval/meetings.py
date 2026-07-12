"""Meeting and decision retrieval tools."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.models.meetings import Meeting, MeetingActionItem, MeetingAttendee, ProjectDecision
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


def get_open_action_items(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    """Open (status="open") action items across accessible projects — the
    portfolio-wide counterpart to get_meeting_detail()'s single-meeting
    action items. Used by the Meeting Agent's portfolio summary to surface
    real follow-up risk (overdue items, items missing an owner or due date)
    instead of the "not available at the portfolio level" placeholder.
    """
    q = db.query(MeetingActionItem).filter(MeetingActionItem.status == "open")
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(MeetingActionItem.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"action_items": [], "total": 0}, evidence=[])
        q = q.filter(MeetingActionItem.project_id.in_(ids))

    items = q.order_by(MeetingActionItem.id.desc()).limit(limit).all()
    if not items:
        return RetrievalResult(data={"action_items": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for a in items:
        rows.append({
            "id": a.id,
            "meeting_id": a.meeting_id,
            "project_id": a.project_id,
            "description": a.description,
            "owner": a.owner,
            "due_date": a.due_date,
            "status": a.status,
            "priority": a.priority,
        })
        evidence.append(Evidence(
            source_type="meeting_action_item",
            source_id=str(a.id),
            label=f"Action Item ACT-{a.id}",
            snippet=(
                f"ACT-{a.id}: {a.description[:200]}, owner={a.owner or 'not recorded'}, "
                f"due_date={a.due_date or 'not recorded'}, status={a.status}, priority={a.priority}"
            ),
            project_id=a.project_id,
            ui_metadata={"href": "/meetings", "icon": "list-checks"},
        ))

    return RetrievalResult(data={"action_items": rows, "total": len(rows)}, evidence=evidence)


def get_meeting_counts(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
) -> dict[str, int]:
    """True portfolio-wide (or project-scoped) COUNT(*) totals — unlike
    get_recent_meetings()/get_project_decisions(), whose row lists are
    bounded by `limit` and are NOT a total count. Used by the Meeting
    Agent's deterministic fallback so "total meetings"/"total decisions"
    are always a real number, never the sample size.
    """
    q_m = db.query(Meeting)
    q_d = db.query(ProjectDecision)
    q_a = db.query(MeetingActionItem).filter(MeetingActionItem.status == "open")

    if project_id is not None:
        scope.enforce_project_access(project_id)
        q_m = q_m.filter(Meeting.project_id == project_id)
        q_d = q_d.filter(ProjectDecision.project_id == project_id)
        q_a = q_a.filter(MeetingActionItem.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return {"total_meetings": 0, "total_decisions": 0, "total_open_action_items": 0}
        q_m = q_m.filter(Meeting.project_id.in_(ids))
        q_d = q_d.filter(ProjectDecision.project_id.in_(ids))
        q_a = q_a.filter(MeetingActionItem.project_id.in_(ids))

    return {
        "total_meetings": q_m.count(),
        "total_decisions": q_d.count(),
        "total_open_action_items": q_a.count(),
    }


def get_meeting_detail(
    db: Session,
    scope: AIAuthScope,
    meeting_id: int,
) -> RetrievalResult:
    """Full detail for ONE specific meeting: the meeting record itself plus
    its decisions, action items (with owner/due_date/status), and attendees.
    Raises 404 if the meeting doesn't exist, 403 via enforce_project_access
    if the caller can't see its project — same conventions used throughout
    this module and _get_or_create_conversation in pipeline.py.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    scope.enforce_project_access(meeting.project_id)

    evidence: list[Evidence] = [
        Evidence(
            source_type="meeting",
            source_id=str(meeting.id),
            label=f"Meeting MTG-{meeting.id}",
            snippet=(
                f"MTG-{meeting.id}: {meeting.title}, type={meeting.meeting_type}, "
                f"date={meeting.meeting_date}"
            ),
            project_id=meeting.project_id,
            ui_metadata={"href": "/meetings", "icon": "calendar"},
        )
    ]

    decisions = (
        db.query(ProjectDecision)
        .filter(ProjectDecision.meeting_id == meeting_id)
        .order_by(ProjectDecision.id.asc())
        .all()
    )
    for d in decisions:
        evidence.append(Evidence(
            source_type="project_decision",
            source_id=str(d.id),
            label=f"Decision DEC-{d.id}",
            snippet=(
                f"DEC-{d.id}: {d.decision_text[:300]}, owner={d.owner}, "
                f"date={d.decision_date}"
            ),
            project_id=d.project_id,
            ui_metadata={"href": "/meetings", "icon": "check-square"},
        ))

    action_items = (
        db.query(MeetingActionItem)
        .filter(MeetingActionItem.meeting_id == meeting_id)
        .order_by(MeetingActionItem.id.asc())
        .all()
    )
    for a in action_items:
        evidence.append(Evidence(
            source_type="meeting_action_item",
            source_id=str(a.id),
            label=f"Action Item ACT-{a.id}",
            snippet=(
                f"ACT-{a.id}: {a.description[:300]}, owner={a.owner}, "
                f"due_date={a.due_date or 'not recorded'}, status={a.status}, "
                f"priority={a.priority}"
            ),
            project_id=a.project_id,
            ui_metadata={"href": "/meetings", "icon": "list-checks"},
        ))

    attendees = (
        db.query(MeetingAttendee)
        .filter(MeetingAttendee.meeting_id == meeting_id)
        .order_by(MeetingAttendee.id.asc())
        .all()
    )
    for att in attendees:
        evidence.append(Evidence(
            source_type="meeting_attendee",
            source_id=str(att.id),
            label=f"Attendee {att.name}",
            snippet=(
                f"Attendee: {att.name}, role={att.role or 'not recorded'}, "
                f"organization={att.organization or 'not recorded'}"
            ),
            project_id=meeting.project_id,
            ui_metadata={"href": "/meetings", "icon": "users"},
        ))

    return RetrievalResult(
        data={
            "meeting_id": meeting.id,
            "project_id": meeting.project_id,
            "meeting_title": meeting.title,
            "meeting_date": meeting.meeting_date,
            "decision_count": len(decisions),
            "action_item_count": len(action_items),
            "attendee_count": len(attendees),
            # Structured rows (not just counts) so callers — e.g. the
            # deterministic no-LLM fallback in pipeline.py — can build a
            # real answer without re-parsing evidence snippet text.
            "decisions": [
                {
                    "id": d.id,
                    "decision_text": d.decision_text,
                    "owner": d.owner,
                    "decision_date": d.decision_date,
                }
                for d in decisions
            ],
            "action_items": [
                {
                    "id": a.id,
                    "description": a.description,
                    "owner": a.owner,
                    "due_date": a.due_date,
                    "status": a.status,
                    "priority": a.priority,
                }
                for a in action_items
            ],
        },
        evidence=evidence,
    )
