"""Approval Engine API (Sprint 5) — see app/ai/approval_engine.py for the
lifecycle logic. All mutating actions are thin wrappers around that
module; this file only handles request/response shaping and query
filtering.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional

from ...ai import approval_engine
from ...core.deps import CurrentScope, DbSession
from ...models.approvals import ApprovalRequest
from ...schemas.approvals import (
    ApprovalActionRequest,
    ApprovalAssignRequest,
    ApprovalHistoryOut,
    ApprovalReasonRequiredRequest,
    ApprovalRequestCreate,
    ApprovalRequestOut,
    ApprovalSummaryOut,
)

router = APIRouter(tags=["approvals"])


@router.post("/approvals", response_model=ApprovalRequestOut, status_code=201)
def create_approval(body: ApprovalRequestCreate, db: DbSession, scope: CurrentScope):
    return approval_engine.create_approval_request(
        db, scope, entity_type=body.entity_type, entity_id=body.entity_id,
        risk_level=body.risk_level, review_note=body.review_note,
        assigned_reviewer_id=body.assigned_reviewer_id, due_at=body.due_at,
    )


@router.get("/approvals", response_model=list[ApprovalRequestOut])
def list_approvals(
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    project_id: Optional[int] = None,
    assigned_to_me: bool = False,
    requested_by_me: bool = False,
    overdue: bool = False,
    due_soon: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = approval_engine.apply_approval_filters(
        db.query(ApprovalRequest), scope,
        status=status, entity_type=entity_type, project_id=project_id,
        assigned_to_me=assigned_to_me, requested_by_me=requested_by_me,
        overdue=overdue, due_soon=due_soon,
    )
    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return q.order_by(ApprovalRequest.created_at.desc()).offset(skip).limit(limit).all()


# Registered BEFORE /approvals/{approval_id} — a plain {approval_id} path
# parameter (no int converter in the path template) would otherwise
# match "summary" first and fail with a 422 trying to parse it as an int.
# Same precedent as app/api/v1/projects.py's health-score routes.
@router.get("/approvals/summary", response_model=ApprovalSummaryOut)
def approvals_summary(db: DbSession, scope: CurrentScope):
    mine = approval_engine.apply_approval_filters(db.query(ApprovalRequest), scope).filter(
        (ApprovalRequest.assigned_reviewer_id == scope.user_id) | (ApprovalRequest.requested_by_user_id == scope.user_id)
    )
    by_status: dict[str, int] = {}
    for row_status, count in mine.with_entities(ApprovalRequest.status, ApprovalRequest.id).all():
        by_status[row_status] = by_status.get(row_status, 0) + 1

    overdue_count = approval_engine.apply_approval_filters(
        db.query(ApprovalRequest), scope, overdue=True,
    ).filter(
        (ApprovalRequest.assigned_reviewer_id == scope.user_id) | (ApprovalRequest.requested_by_user_id == scope.user_id)
    ).count()
    due_soon_count = approval_engine.apply_approval_filters(
        db.query(ApprovalRequest), scope, due_soon=True,
    ).filter(
        (ApprovalRequest.assigned_reviewer_id == scope.user_id) | (ApprovalRequest.requested_by_user_id == scope.user_id)
    ).count()

    return ApprovalSummaryOut(by_status=by_status, overdue_count=overdue_count, due_soon_count=due_soon_count)


@router.get("/approvals/{approval_id}", response_model=ApprovalRequestOut)
def get_approval(approval_id: int, db: DbSession, scope: CurrentScope):
    return approval_engine.get_approval_or_404(db, scope, approval_id)


@router.get("/approvals/{approval_id}/history", response_model=list[ApprovalHistoryOut])
def get_approval_history(approval_id: int, db: DbSession, scope: CurrentScope):
    return approval_engine.get_history(db, scope, approval_id)


@router.patch("/approvals/{approval_id}/assign", response_model=ApprovalRequestOut)
def assign_reviewer(approval_id: int, body: ApprovalAssignRequest, db: DbSession, scope: CurrentScope):
    return approval_engine.assign_reviewer(db, scope, approval_id, body.reviewer_user_id, body.expected_updated_at)


@router.post("/approvals/{approval_id}/start-review", response_model=ApprovalRequestOut)
def start_review(approval_id: int, body: ApprovalActionRequest, db: DbSession, scope: CurrentScope):
    return approval_engine.start_review(db, scope, approval_id, body.expected_updated_at)


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestOut)
def approve(approval_id: int, body: ApprovalActionRequest, db: DbSession, scope: CurrentScope):
    return approval_engine.approve(db, scope, approval_id, body.review_note, body.expected_updated_at)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestOut)
def reject(approval_id: int, body: ApprovalReasonRequiredRequest, db: DbSession, scope: CurrentScope):
    return approval_engine.reject(db, scope, approval_id, body.review_note, body.expected_updated_at)


@router.post("/approvals/{approval_id}/return", response_model=ApprovalRequestOut)
def return_for_changes(approval_id: int, body: ApprovalReasonRequiredRequest, db: DbSession, scope: CurrentScope):
    return approval_engine.return_for_changes(db, scope, approval_id, body.review_note, body.expected_updated_at)


@router.post("/approvals/{approval_id}/cancel", response_model=ApprovalRequestOut)
def cancel(approval_id: int, body: ApprovalActionRequest, db: DbSession, scope: CurrentScope):
    return approval_engine.cancel(db, scope, approval_id, body.review_note, body.expected_updated_at)
