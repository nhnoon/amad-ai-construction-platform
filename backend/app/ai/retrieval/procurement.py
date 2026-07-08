"""Procurement retrieval tools: purchase requests, purchase orders, suppliers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.models.procurement import PurchaseRequest, PurchaseOrder, Supplier
from .base import Evidence, RetrievalResult


def get_procurement_summary(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    q_pr = db.query(PurchaseRequest)
    q_po = db.query(PurchaseOrder)

    if project_id is not None:
        scope.enforce_project_access(project_id)
        q_pr = q_pr.filter(PurchaseRequest.project_id == project_id)
        q_po = q_po.filter(PurchaseOrder.project_id == project_id)
    else:
        if not scope.has_global_read:
            ids = list(scope.accessible_project_ids)
            if not ids:
                return RetrievalResult(data={}, evidence=[])
            q_pr = q_pr.filter(PurchaseRequest.project_id.in_(ids))
            q_po = q_po.filter(PurchaseOrder.project_id.in_(ids))

    prs = q_pr.order_by(PurchaseRequest.id.desc()).limit(limit).all()
    pos = q_po.order_by(PurchaseOrder.id.desc()).limit(limit).all()

    evidence = []
    pr_rows = []
    for pr in prs:
        pr_rows.append({
            "id": pr.id,
            "request_no": pr.request_no,
            "project_id": pr.project_id,
            "material_category": pr.material_category,
            "status": pr.status,
            "required_delivery_date": pr.required_delivery_date,
            "created_at": pr.created_at,
        })
        evidence.append(Evidence(
            source_type="purchase_request",
            source_id=pr.request_no,
            label=f"Purchase Request {pr.request_no}",
            snippet=(
                f"PR {pr.request_no}: category={pr.material_category}, "
                f"status={pr.status}, required_by={pr.required_delivery_date}"
            ),
            project_id=pr.project_id,
            ui_metadata={"href": "/procurement", "icon": "shopping-cart"},
        ))

    po_rows = []
    for po in pos:
        po_rows.append({
            "id": po.id,
            "po_number": po.po_number,
            "project_id": po.project_id,
            "supplier_id": po.supplier_id,
            "status": po.status,
            "promised_delivery": po.promised_delivery,
            "is_late": po.is_late,
            "delay_days": po.delay_days,
        })
        evidence.append(Evidence(
            source_type="purchase_order",
            source_id=po.po_number,
            label=f"Purchase Order {po.po_number}",
            snippet=(
                f"PO {po.po_number}: status={po.status}, "
                f"delivery={po.promised_delivery}, late={po.is_late}, delay={po.delay_days}d"
            ),
            project_id=po.project_id,
            ui_metadata={"href": "/procurement", "icon": "package"},
        ))

    return RetrievalResult(
        data={
            "purchase_requests": pr_rows,
            "purchase_orders": po_rows,
            "pr_count": len(pr_rows),
            "po_count": len(po_rows),
        },
        evidence=evidence,
    )


def get_late_purchase_orders(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    q = db.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["Overdue", "Delayed", "Late"]))

    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(PurchaseOrder.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"late_orders": [], "total": 0}, evidence=[])
        q = q.filter(PurchaseOrder.project_id.in_(ids))

    pos = q.order_by(PurchaseOrder.id.desc()).limit(limit).all()
    if not pos:
        return RetrievalResult(data={"late_orders": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for po in pos:
        rows.append({
            "po_number": po.po_number,
            "project_id": po.project_id,
            "status": po.status,
            "promised_delivery": po.promised_delivery,
            "delay_days": po.delay_days,
        })
        evidence.append(Evidence(
            source_type="purchase_order",
            source_id=po.po_number,
            label=f"Late PO {po.po_number}",
            snippet=(
                f"Late PO {po.po_number}: status={po.status}, "
                f"delivery={po.promised_delivery}, delay={po.delay_days}d"
            ),
            project_id=po.project_id,
            ui_metadata={"href": "/procurement", "icon": "alert-circle"},
        ))

    return RetrievalResult(data={"late_orders": rows, "total": len(rows)}, evidence=evidence)


def get_supplier_information(
    db: Session,
    scope: AIAuthScope,
    supplier_name: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
) -> RetrievalResult:
    q = db.query(Supplier)
    if supplier_name:
        q = q.filter(Supplier.supplier_name.ilike(f"%{supplier_name}%"))
    if category:
        q = q.filter(Supplier.category.ilike(f"%{category}%"))

    suppliers = q.order_by(Supplier.supplier_name).limit(limit).all()
    if not suppliers:
        return RetrievalResult(data={"suppliers": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for s in suppliers:
        rows.append({
            "id": s.id,
            "name": s.supplier_name,
            "category": s.category,
            "city": s.city,
            "status": s.status,
        })
        evidence.append(Evidence(
            source_type="supplier",
            source_id=str(s.id),
            label=f"Supplier {s.supplier_name}",
            snippet=(
                f"Supplier: {s.supplier_name}, category={s.category}, "
                f"city={s.city}, status={s.status}"
            ),
            ui_metadata={"href": "/suppliers", "icon": "users"},
        ))

    return RetrievalResult(data={"suppliers": rows, "total": len(rows)}, evidence=evidence)
