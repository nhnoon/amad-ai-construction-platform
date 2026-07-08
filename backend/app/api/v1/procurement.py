from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from ...core.deps import DbSession
from ...models.procurement import PurchaseRequest, PurchaseOrder, Supplier
from ...schemas.procurement import (
    PurchaseRequestOut, PurchaseRequestCreate, PurchaseOrderOut, SupplierOut,
)

router = APIRouter(tags=["procurement"])


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
def get_procurement_summary(db: DbSession):
    """Returns aggregate counts for the procurement domain."""
    total_prs = db.query(func.count(PurchaseRequest.id)).scalar() or 0
    open_prs = db.query(func.count(PurchaseRequest.id)).filter(
        PurchaseRequest.status.in_(["Pending Clarification", "Under Review", "Needs Rework", "Returned to Requester"])
    ).scalar() or 0
    total_pos = db.query(func.count(PurchaseOrder.id)).scalar() or 0
    late_pos = db.query(func.count(PurchaseOrder.id)).filter(
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
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    material_category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    q = db.query(PurchaseRequest)
    if project_id:
        q = q.filter(PurchaseRequest.project_id == project_id)
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
def get_purchase_request(pr_id: int, db: DbSession):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    return pr


@router.post("/procurement/purchase-requests", response_model=PurchaseRequestOut, status_code=201)
def create_purchase_request(body: PurchaseRequestCreate, db: DbSession):
    pr = PurchaseRequest(**body.model_dump())
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


@router.get("/procurement/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    response: Response,
    db: DbSession,
    project_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    is_late: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    q = db.query(PurchaseOrder)
    if project_id:
        q = q.filter(PurchaseOrder.project_id == project_id)
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    q = db.query(PurchaseRequest).filter(PurchaseRequest.project_id == project_id)
    total = q.count()
    response.headers["X-Total-Count"] = str(total)
    return q.offset(skip).limit(limit).all()
