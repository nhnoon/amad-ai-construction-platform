"""Unified My Work Feed API (Sprint 4 Part E) — see app/ai/my_work.py for
the aggregation itself."""
from fastapi import APIRouter, Query, Response
from typing import Literal, Optional

from ...ai.my_work import get_my_work
from ...core.deps import CurrentScope, DbSession
from ...schemas.my_work import MyWorkItemOut

router = APIRouter(tags=["my-work"])

# Kept as an explicit literal (not derived from app.ai.my_work.ENTITY_TYPES)
# so FastAPI/Pydantic can build static OpenAPI enum documentation from it.
_EntityTypeFilter = Literal[
    "project_risk", "project_issue", "action_item", "safety_event", "ncr", "purchase_request",
]


@router.get("/my-work", response_model=list[MyWorkItemOut])
def list_my_work(
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    entity_type: Optional[_EntityTypeFilter] = None,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    open_only: bool = False,
    overdue: bool = False,
    due_soon: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    items, total = get_my_work(
        db, scope,
        entity_type=entity_type, project_id=project_id, status=status,
        open_only=open_only, overdue=overdue, due_soon=due_soon,
        skip=skip, limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return items
