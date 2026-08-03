"""Unified My Work Feed (Sprint 4 Part E, extended in Sprint 5) — one
read-only, bounded aggregation across the six ownership-upgraded
entities (app/ai/ownership_engine.py: ProjectRisk, ProjectIssue,
MeetingActionItem, SafetyEvent, NCR, PurchaseRequest) plus, since Sprint
5, a 7th "approval" branch. Always scoped to the caller's own
owner_id/assigned_reviewer_id — no "view another user's work" mode.

Built as a single SQL UNION ALL, not seven queries merged in Python:
every branch filters on its own owner column first (owner_id, indexed on
all six original tables since migration 0017; assigned_reviewer_id,
indexed on approval_requests since migration 0019), so the whole
aggregation stays bounded and index-backed without needing any new
indexes. If a caller filters by entity_type, only that one branch is
built at all — the other six are never even sent to the database.

Two fields are computed once per row, not fabricated per entity: which
statuses count as "done" (reused for both `open_only` filtering and
is_overdue/is_due_soon, so the two concepts can't disagree), and a
priority rank derived from whichever free-text priority/severity/impact/
risk_level column an entity actually has (risk/issue/action_item/
approval only — safety events, NCRs and purchase requests have no such
field on their models, so their rank is always 0, not an invented
value).

Sprint 5's "approval" branch is narrower than the other six: it only
covers approvals ASSIGNED TO the caller as reviewer (the same
single-owner-column contract every other branch already follows) — "my
approval requests" (requested_by_user_id == caller) is a different
ownership axis this feed intentionally does not distort itself to model;
see GET /approvals?requested_by_me=true instead
(app/api/v1/approvals.py). An approval's project_id can be NULL (a
General Library document approval has no project at all), so
project_id/project_code are the only two MyWorkItemOut fields that are
genuinely optional — every other entity_type still always populates
both.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.ai.entity_refs import build_action_url
from app.ai.scope import AIAuthScope
from app.models.approvals import ApprovalRequest
from app.models.meetings import MeetingActionItem
from app.models.procurement import PurchaseRequest
from app.models.projects import Project, ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent

# "Due soon" window — not specified by the sprint brief; 7 days is a
# reasonable, documented default for a construction-ops work feed.
DUE_SOON_WINDOW_DAYS = 7

ENTITY_TYPES = ("project_risk", "project_issue", "action_item", "safety_event", "ncr", "purchase_request", "approval")

_APPROVAL_TERMINAL_STATUSES = ("Approved", "Rejected", "Cancelled")

# One canonical "is this entity still open" status set per entity type —
# reused for open_only filtering AND is_overdue/is_due_soon computation.
# Matches the terminal-ish values already established in
# app/ai/workflow_engine.py's own transition matrices.
_ENTITY_CONFIG = {
    "project_risk": dict(
        model=ProjectRisk, title_expr=ProjectRisk.title, priority_col=ProjectRisk.impact,
        due_date_col=None, done_statuses=("closed",),
    ),
    "project_issue": dict(
        model=ProjectIssue, title_expr=ProjectIssue.title, priority_col=ProjectIssue.severity,
        due_date_col=None, done_statuses=("Resolved",),
    ),
    "action_item": dict(
        model=MeetingActionItem, title_expr=MeetingActionItem.description, priority_col=MeetingActionItem.priority,
        due_date_col=MeetingActionItem.due_date, done_statuses=("Completed",),
    ),
    "safety_event": dict(
        model=SafetyEvent, title_expr=sa.func.concat("Safety event (", SafetyEvent.severity, ")"), priority_col=None,
        due_date_col=None, done_statuses=("Closed",),
    ),
    "ncr": dict(
        model=NCR, title_expr=sa.func.concat("NCR (", NCR.ncr_type, ")"), priority_col=None,
        due_date_col=None, done_statuses=("Closed",),
    ),
    # required_delivery_date is the closest real date field a
    # PurchaseRequest has — not a fabricated "due_date" column.
    "purchase_request": dict(
        model=PurchaseRequest, title_expr=sa.func.concat("Purchase request ", PurchaseRequest.request_no), priority_col=None,
        due_date_col=PurchaseRequest.required_delivery_date, done_statuses=("Converted to PO", "Rejected"),
    ),
}


def _priority_rank(column) -> sa.ColumnElement:
    lowered = sa.func.lower(column)
    return sa.case(
        (lowered == "critical", 4),
        (lowered == "high", 3),
        (lowered == "medium", 2),
        (lowered == "low", 1),
        else_=0,
    )


def _build_subquery(
    *, entity_type: str, model, title_expr, priority_col, due_date_col, done_statuses,
    user_id: int, today: str, due_soon_cutoff: str,
    project_id_filter: Optional[int], status_filter: Optional[str], open_only: bool,
):
    status_col = model.status

    if due_date_col is not None:
        not_done = status_col.notin_(done_statuses) if done_statuses else sa.literal(True)
        is_overdue = sa.and_(due_date_col.isnot(None), due_date_col < today, not_done)
        is_due_soon = sa.and_(due_date_col.isnot(None), due_date_col >= today, due_date_col <= due_soon_cutoff, not_done)
        due_date_expr = due_date_col
    else:
        is_overdue = sa.literal(False)
        is_due_soon = sa.literal(False)
        due_date_expr = sa.cast(sa.null(), sa.String)

    if priority_col is not None:
        priority_expr = priority_col
        priority_rank_expr = _priority_rank(priority_col)
    else:
        priority_expr = sa.cast(sa.null(), sa.String)
        priority_rank_expr = sa.literal(0)

    q = (
        sa.select(
            sa.literal(entity_type).label("entity_type"),
            model.id.label("entity_id"),
            model.project_id.label("project_id"),
            Project.project_code.label("project_code"),
            title_expr.label("title"),
            status_col.label("status"),
            priority_expr.label("priority"),
            due_date_expr.label("due_date"),
            is_overdue.label("is_overdue"),
            is_due_soon.label("is_due_soon"),
            priority_rank_expr.label("priority_rank"),
            model.updated_at.label("updated_at"),
        )
        .join(Project, Project.id == model.project_id)
        .where(model.owner_id == user_id)
    )
    if project_id_filter is not None:
        q = q.where(model.project_id == project_id_filter)
    if status_filter is not None:
        q = q.where(status_col == status_filter)
    if open_only and done_statuses:
        q = q.where(status_col.notin_(done_statuses))
    return q


def _build_approval_subquery(
    *, user_id: int, today: str, due_soon_cutoff: str,
    project_id_filter: Optional[int], status_filter: Optional[str], open_only: bool,
):
    """Separate from _build_subquery (not one more entry in
    _ENTITY_CONFIG) because approval_requests genuinely differs on three
    axes the generic builder assumes are uniform across the six
    ownership entities: it's owned via assigned_reviewer_id (not
    owner_id), its project_id can be NULL (General Library document
    approvals — needs a LEFT join, not an inner join), and its due
    column (due_at) is a real DateTime, not the String(50) ISO-date
    columns every other branch compares lexicographically. Keeping this
    separate means the six already-shipped, already-tested branches are
    untouched by Sprint 5."""
    due_date_expr = sa.cast(sa.cast(ApprovalRequest.due_at, sa.Date), sa.String)
    not_done = ApprovalRequest.status.notin_(_APPROVAL_TERMINAL_STATUSES)
    is_overdue = sa.and_(ApprovalRequest.due_at.isnot(None), due_date_expr < today, not_done)
    is_due_soon = sa.and_(ApprovalRequest.due_at.isnot(None), due_date_expr >= today, due_date_expr <= due_soon_cutoff, not_done)
    title_expr = sa.func.concat(ApprovalRequest.entity_type, " #", sa.cast(ApprovalRequest.entity_id, sa.String))

    q = (
        sa.select(
            sa.literal("approval").label("entity_type"),
            ApprovalRequest.id.label("entity_id"),
            ApprovalRequest.project_id.label("project_id"),
            Project.project_code.label("project_code"),
            title_expr.label("title"),
            ApprovalRequest.status.label("status"),
            ApprovalRequest.risk_level.label("priority"),
            due_date_expr.label("due_date"),
            is_overdue.label("is_overdue"),
            is_due_soon.label("is_due_soon"),
            _priority_rank(ApprovalRequest.risk_level).label("priority_rank"),
            ApprovalRequest.updated_at.label("updated_at"),
        )
        .outerjoin(Project, Project.id == ApprovalRequest.project_id)
        .where(ApprovalRequest.assigned_reviewer_id == user_id)
    )
    if project_id_filter is not None:
        q = q.where(ApprovalRequest.project_id == project_id_filter)
    if status_filter is not None:
        q = q.where(ApprovalRequest.status == status_filter)
    if open_only:
        q = q.where(ApprovalRequest.status.notin_(_APPROVAL_TERMINAL_STATUSES))
    return q


def _build_any_subquery(
    entity_type: str, *, user_id: int, today: str, due_soon_cutoff: str,
    project_id_filter: Optional[int], status_filter: Optional[str], open_only: bool,
):
    if entity_type == "approval":
        return _build_approval_subquery(
            user_id=user_id, today=today, due_soon_cutoff=due_soon_cutoff,
            project_id_filter=project_id_filter, status_filter=status_filter, open_only=open_only,
        )
    return _build_subquery(
        entity_type=entity_type, user_id=user_id, today=today, due_soon_cutoff=due_soon_cutoff,
        project_id_filter=project_id_filter, status_filter=status_filter, open_only=open_only,
        **_ENTITY_CONFIG[entity_type],
    )


def get_my_work(
    db: Session, scope: AIAuthScope, *,
    entity_type: Optional[str] = None, project_id: Optional[int] = None, status: Optional[str] = None,
    open_only: bool = False, overdue: bool = False, due_soon: bool = False,
    skip: int = 0, limit: int = 20,
) -> tuple[list[dict], int]:
    today = datetime.now(timezone.utc).date().isoformat()
    due_soon_cutoff = (datetime.now(timezone.utc).date() + timedelta(days=DUE_SOON_WINDOW_DAYS)).isoformat()

    types = [entity_type] if entity_type else list(ENTITY_TYPES)
    subqueries = [
        _build_any_subquery(
            t, user_id=scope.user_id, today=today, due_soon_cutoff=due_soon_cutoff,
            project_id_filter=project_id, status_filter=status, open_only=open_only,
        )
        for t in types
    ]

    union_q = sa.union_all(*subqueries).subquery("my_work") if len(subqueries) > 1 else subqueries[0].subquery("my_work")

    base = sa.select(union_q)
    if overdue:
        base = base.where(union_q.c.is_overdue.is_(True))
    if due_soon:
        base = base.where(union_q.c.is_due_soon.is_(True))

    total = db.execute(sa.select(sa.func.count()).select_from(base.subquery())).scalar_one()

    ordered = base.order_by(
        union_q.c.is_overdue.desc(),
        union_q.c.is_due_soon.desc(),
        union_q.c.priority_rank.desc(),
        union_q.c.updated_at.desc(),
    ).offset(skip).limit(limit)

    rows = db.execute(ordered).mappings().all()
    items = [
        {
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "project_id": r["project_id"],
            "project_code": r["project_code"],
            "title": r["title"],
            "status": r["status"],
            "priority": r["priority"],
            "due_date": r["due_date"],
            "is_overdue": bool(r["is_overdue"]),
            "is_due_soon": bool(r["is_due_soon"]),
            "updated_at": r["updated_at"],
            "action_url": build_action_url(r["entity_type"], r["project_id"], r["entity_id"]),
        }
        for r in rows
    ]
    return items, total
