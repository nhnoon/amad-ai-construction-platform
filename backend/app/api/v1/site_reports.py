from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...ai.site_report_intelligence import (
    analyze_site_report,
    build_site_report_intelligence,
    list_site_report_cards,
)
from ...core.deps import DbSession
from ...models.site import SiteReport, DailyActivity
from ...schemas.site import (
    SiteReportOut,
    SiteReportCardOut,
    DailyActivityOut,
    SiteReportIntelligenceOut,
    SiteReportAnalysisOut,
)

router = APIRouter(tags=["site-reports"])


@router.get("/projects/{project_id}/site-reports", response_model=list[SiteReportOut])
def list_site_reports(
    project_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return (
        db.query(SiteReport)
        .filter(SiteReport.project_id == project_id)
        .order_by(SiteReport.report_date.desc())
        .offset(skip).limit(limit).all()
    )


@router.get("/projects/{project_id}/site-reports/cards", response_model=list[SiteReportCardOut])
def list_site_report_cards_route(
    project_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return list_site_report_cards(db=db, project_id=project_id, skip=skip, limit=limit)


@router.get("/projects/{project_id}/site-reports/{report_id}", response_model=SiteReportOut)
def get_site_report(project_id: int, report_id: int, db: DbSession):
    report = (
        db.query(SiteReport)
        .filter(SiteReport.id == report_id, SiteReport.project_id == project_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Site report not found")
    return report


@router.get("/projects/{project_id}/site-reports/{report_id}/activities", response_model=list[DailyActivityOut])
def list_report_activities(project_id: int, report_id: int, db: DbSession):
    return (
        db.query(DailyActivity)
        .filter(
            DailyActivity.site_report_id == report_id,
            DailyActivity.project_id == project_id,
        )
        .all()
    )


@router.get("/projects/{project_id}/daily-activities", response_model=list[DailyActivityOut])
def list_daily_activities(
    project_id: int,
    db: DbSession,
    subcontractor_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(DailyActivity).filter(DailyActivity.project_id == project_id)
    if subcontractor_id:
        q = q.filter(DailyActivity.subcontractor_id == subcontractor_id)
    return q.offset(skip).limit(limit).all()


@router.get(
    "/projects/{project_id}/site-reports/{report_id}/intelligence",
    response_model=SiteReportIntelligenceOut,
)
def get_site_report_intelligence(project_id: int, report_id: int, db: DbSession):
    try:
        result = build_site_report_intelligence(db=db, project_id=project_id, report_id=report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.report


@router.post(
    "/projects/{project_id}/site-reports/{report_id}/analyze",
    response_model=SiteReportAnalysisOut,
)
def analyze_site_report_route(project_id: int, report_id: int, db: DbSession):
    try:
        return analyze_site_report(db=db, project_id=project_id, report_id=report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
