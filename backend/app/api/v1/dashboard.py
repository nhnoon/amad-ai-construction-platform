from fastapi import APIRouter
from sqlalchemy import func, case, or_
from pydantic import BaseModel

from ...core.deps import CurrentScope, DbSession
from ...models.projects import Project
from ...models.procurement import Supplier, PurchaseOrder, PurchaseRequest
from ...models.safety import SafetyEvent, NCR
from ...models.site import SiteReport
from ...models.meetings import Meeting, ProjectDecision
from ...models.documents import Document, Correspondence

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardSummary(BaseModel):
    # Project health
    total_projects: int
    active_projects: int
    completed_projects: int
    delayed_projects: int      # status == "Delayed" only
    on_hold_projects: int      # status == "On Hold" only
    # Procurement
    total_suppliers: int
    active_suppliers: int
    total_purchase_requests: int
    open_purchase_requests: int
    total_purchase_orders: int
    late_purchase_orders: int
    # Safety & Quality
    total_safety_events: int
    high_severity_events: int
    total_ncrs: int
    open_ncrs: int
    # Activity
    total_site_reports: int
    total_meetings: int
    total_decisions: int
    # RFIs — the RFIs workspace has no dedicated record type; it's built
    # from documents/correspondence whose type/title/subject mentions
    # "RFI" (see isRfiLike() in pages/rfis.tsx). This counts the same way,
    # portfolio-wide, rather than inventing a different definition.
    total_rfis: int


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: DbSession, scope: CurrentScope):
    """Portfolio summary scoped to the caller's own organization (Phase 1
    production-hardening). ``scope.accessible_project_ids`` already reflects
    the caller's organization for global-read roles (admin/executive/
    project_manager) — see app/ai/scope.py — so every project-linked count
    below is filtered to that set. Suppliers remain a shared, portfolio-
    wide registry (no project/organization link exists on that table — see
    the same NOTE in procurement.py) and are intentionally NOT filtered."""
    ids = list(scope.accessible_project_ids)

    proj = db.query(
        func.count(Project.id).label("total"),
        func.sum(case((Project.status == "Active", 1), else_=0)).label("active"),
        func.sum(case((Project.status == "Completed", 1), else_=0)).label("completed"),
        func.sum(case((Project.status == "Delayed", 1), else_=0)).label("delayed"),
        func.sum(case((Project.status == "On Hold", 1), else_=0)).label("on_hold"),
    ).filter(Project.id.in_(ids)).one()

    # Suppliers — shared catalog, deliberately not organization-filtered.
    sup = db.query(
        func.count(Supplier.id).label("total"),
        func.sum(case((Supplier.status == "Active", 1), else_=0)).label("active"),
    ).one()

    pr = db.query(
        func.count(PurchaseRequest.id).label("total"),
        func.sum(case((PurchaseRequest.status.in_(["Pending Clarification", "Under Review", "Needs Rework", "Returned to Requester"]), 1), else_=0)).label("open"),
    ).filter(PurchaseRequest.project_id.in_(ids)).one()

    po = db.query(
        func.count(PurchaseOrder.id).label("total"),
        func.sum(case((PurchaseOrder.is_late == True, 1), else_=0)).label("late"),  # noqa: E712
    ).filter(PurchaseOrder.project_id.in_(ids)).one()

    safety = db.query(
        func.count(SafetyEvent.id).label("total"),
        func.sum(case((SafetyEvent.severity.in_(["High", "Critical"]), 1), else_=0)).label("high"),
    ).filter(SafetyEvent.project_id.in_(ids)).one()

    ncr = db.query(
        func.count(NCR.id).label("total"),
        func.sum(case((NCR.status != "Closed", 1), else_=0)).label("open"),
    ).filter(NCR.project_id.in_(ids)).one()

    total_site_reports = db.query(func.count(SiteReport.id)).filter(
        SiteReport.project_id.in_(ids)
    ).scalar()
    total_meetings = db.query(func.count(Meeting.id)).filter(
        Meeting.project_id.in_(ids)
    ).scalar()
    total_decisions = db.query(func.count(ProjectDecision.id)).filter(
        ProjectDecision.project_id.in_(ids)
    ).scalar()

    # RFI-like documents/correspondence: project-scoped ones filtered to
    # accessible projects; organization-scoped (General Library, no
    # project) ones filtered to the caller's own organization — same two
    # axes list_all_documents() (documents.py) already uses.
    doc_scope = or_(
        Document.project_id.in_(ids),
        (Document.project_id.is_(None) & (Document.organization_id == scope.organization_id)),
    )
    rfi_docs = db.query(func.count(Document.id)).filter(
        doc_scope, or_(Document.doc_type.ilike("%rfi%"), Document.title.ilike("%rfi%"))
    ).scalar() or 0
    rfi_correspondence = db.query(func.count(Correspondence.id)).filter(
        Correspondence.project_id.in_(ids),
        or_(Correspondence.related_record_type.ilike("%rfi%"), Correspondence.subject.ilike("%rfi%"))
    ).scalar() or 0

    return DashboardSummary(
        total_projects=proj.total or 0,
        active_projects=proj.active or 0,
        completed_projects=proj.completed or 0,
        delayed_projects=proj.delayed or 0,
        on_hold_projects=proj.on_hold or 0,
        total_suppliers=sup.total or 0,
        active_suppliers=sup.active or 0,
        total_purchase_requests=pr.total or 0,
        open_purchase_requests=pr.open or 0,
        total_purchase_orders=po.total or 0,
        late_purchase_orders=po.late or 0,
        total_safety_events=safety.total or 0,
        high_severity_events=safety.high or 0,
        total_ncrs=ncr.total or 0,
        open_ncrs=ncr.open or 0,
        total_site_reports=total_site_reports or 0,
        total_meetings=total_meetings or 0,
        total_decisions=total_decisions or 0,
        total_rfis=rfi_docs + rfi_correspondence,
    )
