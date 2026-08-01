from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from ...ai.workflow_engine import update_purchase_request
from ...core.deps import CurrentScope, DbSession
from ...models.procurement import PurchaseRequest, PurchaseOrder, Supplier
from ...schemas.procurement import (
    PurchaseRequestOut, PurchaseRequestCreate, PurchaseRequestUpdate,
    PurchaseOrderOut, SupplierOut,
)

router = APIRouter(tags=["procurement"])

# NOTE (Phase 1 production-hardening): Supplier is a shared, portfolio-wide
# vendor registry — the model carries no project_id or organization_id (see
# app/models/procurement.py), and nothing in the schema ties a supplier to
# one tenant. Supplier list/detail/performance below are therefore left
# unscoped by organization in this phase, same as the AI retrieval layer's
# own get_supplier_information() (app/ai/retrieval/procurement.py). If
# suppliers ever need to become organization-specific, that requires an
# actual schema decision (its own organization_id + backfill), not an
# API-layer filter — see the Phase 1 report's "remaining limitations".


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    response: Response,
    db: DbSession,
    category: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    q = db.query(Supplier)
    if category:
        q = q.filter(Supplier.category == category)
    if status:
        q = q.filter(Supplier.status == status)
    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return q.offset(skip).limit(limit).all()


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: DbSession):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.get("/suppliers/{supplier_id}/performance")
def get_supplier_performance(supplier_id: int, db: DbSession):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    total_pos = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.supplier_id == supplier_id
    ).scalar() or 0

    late_pos = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.supplier_id == supplier_id,
        PurchaseOrder.is_late == True,  # noqa: E712
    ).scalar() or 0

    avg_delay = db.query(func.avg(PurchaseOrder.delay_days)).filter(
        PurchaseOrder.supplier_id == supplier_id,
    ).scalar() or 0.0

    on_time_rate = round((total_pos - late_pos) / total_pos * 100, 1) if total_pos > 0 else 0.0

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.supplier_name,
        "category": supplier.category,
        "total_purchase_orders": total_pos,
        "late_orders": late_pos,
        "on_time_rate_pct": on_time_rate,
        "avg_delay_days": round(float(avg_delay), 1),
    }


@router.get("/procurement/summary")
def get_procurement_summary(db: DbSession, scope: CurrentScope):
    """Returns aggregate counts for the procurement domain, scoped to the
    caller's accessible projects (Phase 1 production-hardening) — supplier
    totals remain global, see the module-level NOTE above."""
    ids = list(scope.accessible_project_ids)
    if not ids:
        return {
            "total_purchase_requests": 0, "open_purchase_requests": 0,
            "total_purchase_orders": 0, "late_purchase_orders": 0,
            "total_suppliers": db.query(func.count(Supplier.id)).scalar() or 0,
        }

    total_prs = db.query(func.count(PurchaseRequest.id)).filter(
        PurchaseRequest.project_id.in_(ids)
    ).scalar() or 0
    open_prs = db.query(func.count(PurchaseRequest.id)).filter(
        PurchaseRequest.project_id.in_(ids),
        PurchaseRequest.status.in_(["Pending Clarification", "Under Review", "Needs Rework", "Returned to Requester"])
    ).scalar() or 0
    total_pos = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.project_id.in_(ids)
    ).scalar() or 0
    late_pos = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.project_id.in_(ids),
        PurchaseOrder.is_late == True  # noqa: E712
    ).scalar() or 0
    total_suppliers = db.query(func.count(Supplier.id)).scalar() or 0

    return {
        "total_purchase_requests": total_prs,
        "open_purchase_requests": open_prs,
        "total_purchase_orders": total_pos,
        "late_purchase_orders": late_pos,
        "total_suppliers": total_suppliers,
    }


@router.get("/procurement/purchase-requests", response_model=list[PurchaseRequestOut])
def list_purchase_requests(
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    material_category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = db.query(PurchaseRequest).filter(PurchaseRequest.project_id == project_id)
    else:
        ids = list(scope.accessible_project_ids)
        if not ids:
            response.headers["X-Total-Count"] = "0"
            return []
        q = db.query(PurchaseRequest).filter(PurchaseRequest.project_id.in_(ids))
    if status:
        q = q.filter(PurchaseRequest.status == status)
    if material_category:
        q = q.filter(PurchaseRequest.material_category == material_category)
    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return q.offset(skip).limit(limit).all()


@router.get("/procurement/purchase-requests/{pr_id}", response_model=PurchaseRequestOut)
def get_purchase_request(pr_id: int, db: DbSession, scope: CurrentScope):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    scope.enforce_project_access(pr.project_id)
    return pr


@router.patch("/procurement/purchase-requests/{request_id}", response_model=PurchaseRequestOut)
def update_purchase_request_route(request_id: int, body: PurchaseRequestUpdate, db: DbSession, scope: CurrentScope):
    """Core Workflow Engine (Sprint 2) — see app/ai/workflow_engine.py for
    the status transition matrix and close-out rules (Rejected/Returned to
    Requester require a non-empty rework_reason)."""
    return update_purchase_request(db, scope, request_id, body)


@router.post("/procurement/purchase-requests", response_model=PurchaseRequestOut, status_code=201)
def create_purchase_request(body: PurchaseRequestCreate, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(body.project_id)
    pr = PurchaseRequest(**body.model_dump())
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


@router.get("/procurement/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    project_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    is_late: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = db.query(PurchaseOrder).filter(PurchaseOrder.project_id == project_id)
    else:
        ids = list(scope.accessible_project_ids)
        if not ids:
            response.headers["X-Total-Count"] = "0"
            return []
        q = db.query(PurchaseOrder).filter(PurchaseOrder.project_id.in_(ids))
    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    if is_late is not None:
        q = q.filter(PurchaseOrder.is_late == is_late)
    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/purchase-requests", response_model=list[PurchaseRequestOut])
def list_project_purchase_requests(
    project_id: int,
    response: Response,
    db: DbSession,
    scope: CurrentScope,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    scope.enforce_project_access(project_id)
    q = db.query(PurchaseRequest).filter(PurchaseRequest.project_id == project_id)
    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    return q.offset(skip).limit(limit).all()
