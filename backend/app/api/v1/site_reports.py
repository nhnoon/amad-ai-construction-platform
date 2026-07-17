import logging

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...ai.scope import build_ai_scope
from ...ai.site_report_intelligence import (
    analyze_site_report,
    build_site_report_intelligence,
    list_site_report_cards,
)
from ...core.deps import CurrentUser, DbSession
from ...models.site import SiteReport, DailyActivity
from ...schemas.site import (
    SiteReportOut,
    SiteReportCardOut,
    DailyActivityOut,
    SiteReportIntelligenceOut,
    SiteReportAnalysisOut,
)

logger = logging.getLogger(__name__)

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
def analyze_site_report_route(project_id: int, report_id: int, db: DbSession, current_user: CurrentUser):
    try:
        scope = build_ai_scope(current_user, db)
        return analyze_site_report(db=db, project_id=project_id, report_id=report_id, scope=scope)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        # analyze_site_report() already converts everything except
        # ValueError into a structured "unavailable" result — reaching
        # this except means something broke outside that contract (e.g. in
        # response serialization itself). Still never let a bare, unlabeled
        # 500 reach the frontend for this endpoint: the client-side
        # AbortController timeout (site-report-detail.tsx) is generous
        # enough to tolerate a real Hermes call, so an unhandled exception
        # here would otherwise look identical to "endless loading" for as
        # long as that timeout takes to fire.
        logger.error("analyze_site_report_route_unhandled project_id=%s report_id=%s error=%s", project_id, report_id, exc, exc_info=True)
        from ...ai.site_report_intelligence import _unavailable_analysis_out
        return _unavailable_analysis_out(f"Unexpected server error: {type(exc).__name__}")
