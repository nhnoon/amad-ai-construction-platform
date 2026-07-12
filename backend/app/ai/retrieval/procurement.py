"""Procurement retrieval tools: purchase requests, purchase orders, suppliers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.ai.scope import AIAuthScope
from app.models.procurement import PurchaseRequest, PurchaseOrder, Supplier
from .base import Evidence, RetrievalResult


def _po_snippet(po: PurchaseOrder) -> str:
    """Build a self-contained PO snippet: every field an LLM needs to answer
    a late-PO question (project, supplier, dates, root cause) must be in the
    snippet text itself — the LLM only ever sees Evidence.snippet, never the
    ORM object or Evidence.project_id, so anything omitted here is
    unanswerable (and any attempt to answer it would be an ungrounded guess).
    """
    project_code = po.project.project_code if po.project is not None else "unknown project"
    supplier_name = po.supplier.supplier_name if po.supplier is not None else "unknown supplier"
    root_cause = f", root_cause={po.delay_root_cause}" if po.delay_root_cause else ""
    return (
        f"PO {po.po_number}: project={project_code}, supplier={supplier_name}, "
        f"status={po.status}, promised_delivery={po.promised_delivery}, "
        f"late={po.is_late}, delay_days={po.delay_days}{root_cause}"
    )


def get_procurement_summary(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    q_pr = db.query(PurchaseRequest)
    q_po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.project), joinedload(PurchaseOrder.supplier)
    )

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
            "project_code": po.project.project_code if po.project is not None else None,
            "supplier_id": po.supplier_id,
            "supplier_name": po.supplier.supplier_name if po.supplier is not None else None,
            "status": po.status,
            "promised_delivery": po.promised_delivery,
            "is_late": po.is_late,
            "delay_days": po.delay_days,
            "delay_root_cause": po.delay_root_cause,
        })
        evidence.append(Evidence(
            source_type="purchase_order",
            source_id=po.po_number,
            label=f"Purchase Order {po.po_number}",
            snippet=_po_snippet(po),
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
    # NOTE: lateness is tracked via the is_late boolean (+ delay_days), not
    # via `status` — every PO in this dataset carries status="Delivered"
    # regardless of whether it arrived late, so a status-based filter (the
    # previous implementation) matched zero rows in practice. is_late is the
    # same field every other late-PO query in the codebase filters on
    # (dashboard.py, alerts.py, executive.py, reports.py, procurement.py).
    q = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.project), joinedload(PurchaseOrder.supplier))
        .filter(PurchaseOrder.is_late.is_(True))
    )

    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(PurchaseOrder.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"late_orders": [], "total": 0}, evidence=[])
        q = q.filter(PurchaseOrder.project_id.in_(ids))

    pos = q.order_by(PurchaseOrder.delay_days.desc()).limit(limit).all()
    if not pos:
        return RetrievalResult(data={"late_orders": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for po in pos:
        rows.append({
            "po_number": po.po_number,
            "project_id": po.project_id,
            "project_code": po.project.project_code if po.project is not None else None,
            "supplier_name": po.supplier.supplier_name if po.supplier is not None else None,
            "status": po.status,
            "promised_delivery": po.promised_delivery,
            "delay_days": po.delay_days,
            "delay_root_cause": po.delay_root_cause,
        })
        evidence.append(Evidence(
            source_type="purchase_order",
            source_id=po.po_number,
            label=f"Late PO {po.po_number}",
            snippet=_po_snippet(po),
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


def get_procurement_counts(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
) -> dict[str, int]:
    """True portfolio-wide (or project-scoped) COUNT(*) totals — unlike
    get_procurement_summary()/get_late_purchase_orders(), whose row lists are
    bounded by `limit` and are NOT a total count. Used by the Procurement
    Agent's deterministic fallback (see pipeline.py:_build_procurement_fallback)
    so "total POs" etc. are always a real number, never the sample size.
    """
    q_po = db.query(PurchaseOrder)
    q_pr = db.query(PurchaseRequest)

    if project_id is not None:
        scope.enforce_project_access(project_id)
        q_po = q_po.filter(PurchaseOrder.project_id == project_id)
        q_pr = q_pr.filter(PurchaseRequest.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return {"total_po": 0, "late_po": 0, "total_pr": 0, "open_pr": 0}
        q_po = q_po.filter(PurchaseOrder.project_id.in_(ids))
        q_pr = q_pr.filter(PurchaseRequest.project_id.in_(ids))

    total_po = q_po.count()
    late_po = q_po.filter(PurchaseOrder.is_late.is_(True)).count()
    total_pr = q_pr.count()
    # "Open/pending" = not yet converted to a PO and not returned/rejected —
    # i.e. still actively in-flight (Approved, Under Review, Pending
    # Clarification, Needs Rework).
    open_pr = q_pr.filter(
        ~PurchaseRequest.status.in_(["Converted to PO", "Returned to Requester"])
    ).count()
    # Suppliers are a global registry, not project-scoped — same convention
    # as get_supplier_information(). "High risk" is read directly off the
    # supplier's real name in the vendor registry (this dataset seeds
    # suppliers literally named "Risk Supplier N"); this is not a computed
    # judgment call, just a count of an existing, real data value.
    high_risk_suppliers = db.query(Supplier).filter(Supplier.supplier_name.ilike("%risk%")).count()

    return {
        "total_po": total_po, "late_po": late_po, "total_pr": total_pr, "open_pr": open_pr,
        "high_risk_suppliers": high_risk_suppliers,
    }
