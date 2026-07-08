from fastapi import APIRouter
from sqlalchemy import func, case
from pydantic import BaseModel

from ...core.deps import DbSession
from ...models.projects import Project
from ...models.procurement import Supplier, PurchaseOrder, PurchaseRequest
from ...models.safety import SafetyEvent, NCR
from ...models.site import SiteReport
from ...models.meetings import Meeting, ProjectDecision

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


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: DbSession):
    proj = db.query(
        func.count(Project.id).label("total"),
        func.sum(case((Project.status == "Active", 1), else_=0)).label("active"),
        func.sum(case((Project.status == "Completed", 1), else_=0)).label("completed"),
        func.sum(case((Project.status == "Delayed", 1), else_=0)).label("delayed"),
        func.sum(case((Project.status == "On Hold", 1), else_=0)).label("on_hold"),
    ).one()

    sup = db.query(
        func.count(Supplier.id).label("total"),
        func.sum(case((Supplier.status == "Active", 1), else_=0)).label("active"),
    ).one()

    pr = db.query(
        func.count(PurchaseRequest.id).label("total"),
        func.sum(case((PurchaseRequest.status.in_(["Pending Clarification", "Under Review", "Needs Rework", "Returned to Requester"]), 1), else_=0)).label("open"),
    ).one()

    po = db.query(
        func.count(PurchaseOrder.id).label("total"),
        func.sum(case((PurchaseOrder.is_late == True, 1), else_=0)).label("late"),  # noqa: E712
    ).one()

    safety = db.query(
        func.count(SafetyEvent.id).label("total"),
        func.sum(case((SafetyEvent.severity.in_(["High", "Critical"]), 1), else_=0)).label("high"),
    ).one()

    ncr = db.query(
        func.count(NCR.id).label("total"),
        func.sum(case((NCR.status != "Closed", 1), else_=0)).label("open"),
    ).one()

    total_site_reports = db.query(func.count(SiteReport.id)).scalar()
    total_meetings = db.query(func.count(Meeting.id)).scalar()
    total_decisions = db.query(func.count(ProjectDecision.id)).scalar()

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
    )
