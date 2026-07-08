"""Site report and daily activity retrieval tools."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.models.site import SiteReport, DailyActivity
from .base import Evidence, RetrievalResult


def get_recent_site_reports(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 10,
) -> RetrievalResult:
    q = db.query(SiteReport)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(SiteReport.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"reports": [], "total": 0}, evidence=[])
        q = q.filter(SiteReport.project_id.in_(ids))

    reports = q.order_by(SiteReport.report_date.desc()).limit(limit).all()
    if not reports:
        return RetrievalResult(data={"reports": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for r in reports:
        rows.append({
            "id": r.id,
            "project_id": r.project_id,
            "report_date": r.report_date,
            "weather": r.weather,
            "summary": r.summary,
        })
        evidence.append(Evidence(
            source_type="site_report",
            source_id=str(r.id),
            label=f"Site Report SR-{r.id}",
            snippet=(
                f"SR-{r.id}: date={r.report_date}, weather={r.weather}, "
                f"summary={r.summary[:150]}"
            ),
            project_id=r.project_id,
            ui_metadata={"href": "/site-reports", "icon": "clipboard-check"},
        ))

    return RetrievalResult(data={"reports": rows, "total": len(rows)}, evidence=evidence)


def get_recent_daily_activities(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 10,
) -> RetrievalResult:
    q = db.query(DailyActivity)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(DailyActivity.project_id == project_id)
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return RetrievalResult(data={"activities": [], "total": 0}, evidence=[])
        q = q.filter(DailyActivity.project_id.in_(ids))

    acts = q.order_by(DailyActivity.activity_date.desc()).limit(limit).all()
    if not acts:
        return RetrievalResult(data={"activities": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for a in acts:
        rows.append({
            "id": a.id,
            "project_id": a.project_id,
            "activity_date": a.activity_date,
            "activity_description": a.activity_description,
            "manpower_count": a.manpower_count,
        })
        evidence.append(Evidence(
            source_type="daily_activity",
            source_id=str(a.id),
            label=f"Daily Activity DA-{a.id}",
            snippet=(
                f"DA-{a.id}: date={a.activity_date}, "
                f"manpower={a.manpower_count}, "
                f"description={a.activity_description[:120]}"
            ),
            project_id=a.project_id,
            ui_metadata={"href": "/site-reports", "icon": "hard-hat"},
        ))

    return RetrievalResult(data={"activities": rows, "total": len(rows)}, evidence=evidence)
