"""
Executive Weekly Report — Phase 4D.

Deterministic report generated from live PostgreSQL data.
No AI, no LLM, no mock data. All metrics derived from operational records.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, distinct

from ...core.deps import DbSession
from ...models.projects import Project
from ...models.safety import SafetyEvent, NCR
from ...models.procurement import PurchaseOrder, PurchaseRequest
from ...models.meetings import Meeting, MeetingActionItem
from ...ai.health_score import get_all_projects_health, HealthScoreResult
from .executive import (
    ProjectBrief, RiskCategory,
    _compute_executive_intelligence,
    _SEV_ORDER, _count_to_severity, _brief,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# ── Pydantic schemas ───────────────────────────────────────────────────────────

class ReportPeriod(BaseModel):
    start_date: str   # ISO date YYYY-MM-DD
    end_date: str     # ISO date YYYY-MM-DD
    week_number: int
    year: int
    label: str        # e.g. "Week 28, 2026 · 7–13 Jul 2026"


class HealthDistribution(BaseModel):
    excellent: int
    good: int
    at_risk: int
    critical: int
    total: int
    average_score: int


class ReportAlert(BaseModel):
    severity: str
    category: str
    title: str
    description: str
    project_code: Optional[str] = None


class ProcurementBlocker(BaseModel):
    label: str
    count: int
    detail: str
    severity: str


class SafetyHighlight(BaseModel):
    label: str
    count: int
    detail: str
    severity: str


class QualityHighlight(BaseModel):
    label: str
    count: int
    detail: str
    severity: str


class RecommendedAction(BaseModel):
    priority: int
    area: str
    action: str
    rationale: str


class SourceReference(BaseModel):
    source: str
    record_count: int
    description: str


class ExecutiveWeeklyReport(BaseModel):
    report_period: ReportPeriod
    generated_at: str
    portfolio_summary: str
    portfolio_status: str
    portfolio_score: int
    health_distribution: HealthDistribution
    top_priorities: list[ProjectBrief]
    biggest_risks: list[RiskCategory]
    critical_alerts: list[ReportAlert]
    procurement_blockers: list[ProcurementBlocker]
    safety_highlights: list[SafetyHighlight]
    quality_highlights: list[QualityHighlight]
    recommended_actions: list[RecommendedAction]
    sources: list[SourceReference]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _current_report_period() -> ReportPeriod:
    today = datetime.now(tz=timezone.utc).date()
    # ISO week: Monday = weekday 0
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    iso_year, iso_week, _ = today.isocalendar()

    def fmt(d) -> str:  # type: ignore[no-untyped-def]
        if hasattr(d, "strftime"):
            # Cross-platform date formatting (avoid %-d which doesn't work on Windows)
            formatted = d.strftime("%d %b %Y")
            # Remove leading zero from day
            return formatted.lstrip("0").lstrip() or formatted
        return str(d)

    label = f"Week {iso_week}, {iso_year} · {fmt(monday)}–{fmt(sunday)}"
    return ReportPeriod(
        start_date=monday.isoformat(),
        end_date=sunday.isoformat(),
        week_number=iso_week,
        year=iso_year,
        label=label,
    )


def _severity_badge(sev: str) -> str:
    return {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}.get(
        sev.lower(), "medium"
    )


# ── Report computation ────────────────────────────────────────────────────────

def _compute_executive_weekly_report(db) -> ExecutiveWeeklyReport:  # type: ignore[type-arg]
    now_str = datetime.now(tz=timezone.utc).isoformat()
    period = _current_report_period()

    # ── Health scores ─────────────────────────────────────────────────────────
    health_scores = get_all_projects_health(db)

    if not health_scores:
        return _empty_report(period, now_str)

    total = len(health_scores)
    critical_hs  = [h for h in health_scores if h.level == "Critical"]
    at_risk_hs   = [h for h in health_scores if h.level == "At Risk"]
    good_hs      = [h for h in health_scores if h.level == "Good"]
    excellent_hs = [h for h in health_scores if h.level == "Excellent"]
    avg_score    = round(sum(h.score for h in health_scores) / total)

    portfolio_level = (
        "Excellent" if avg_score >= 80
        else "Good" if avg_score >= 60
        else "At Risk" if avg_score >= 40
        else "Critical"
    )

    health_dist = HealthDistribution(
        excellent=len(excellent_hs),
        good=len(good_hs),
        at_risk=len(at_risk_hs),
        critical=len(critical_hs),
        total=total,
        average_score=avg_score,
    )

    # ── Operational DB counts ─────────────────────────────────────────────────
    critical_safety: int = (
        db.query(func.count(SafetyEvent.id))
        .filter(SafetyEvent.severity.in_(["Critical", "High"]))
        .scalar() or 0
    )
    high_safety: int = (
        db.query(func.count(SafetyEvent.id))
        .filter(SafetyEvent.severity == "High")
        .scalar() or 0
    )
    medium_safety: int = (
        db.query(func.count(SafetyEvent.id))
        .filter(SafetyEvent.severity.in_(["Medium", "Low"]))
        .scalar() or 0
    )
    open_ncrs: int = (
        db.query(func.count(NCR.id))
        .filter(NCR.status != "Closed")
        .scalar() or 0
    )
    closed_ncrs: int = (
        db.query(func.count(NCR.id))
        .filter(NCR.status == "Closed")
        .scalar() or 0
    )
    corrective_ncrs: int = (
        db.query(func.count(NCR.id))
        .filter(NCR.status == "Under Corrective Action")
        .scalar() or 0
    )
    late_pos: int = (
        db.query(func.count(PurchaseOrder.id))
        .filter(PurchaseOrder.is_late.is_(True))
        .scalar() or 0
    )
    total_pos: int = (
        db.query(func.count(PurchaseOrder.id)).scalar() or 0
    )
    open_prs: int = (
        db.query(func.count(PurchaseRequest.id))
        .filter(PurchaseRequest.status.in_(["Under Review", "Pending Clarification"]))
        .scalar() or 0
    )
    rework_prs: int = (
        db.query(func.count(PurchaseRequest.id))
        .filter(PurchaseRequest.status.in_(["Needs Rework", "Returned to Requester"]))
        .scalar() or 0
    )
    delayed_projects: int = (
        db.query(func.count(Project.id))
        .filter(Project.status.in_(["Delayed", "On Hold", "Suspended"]))
        .scalar() or 0
    )
    open_actions: int = (
        db.query(func.count(MeetingActionItem.id))
        .filter(MeetingActionItem.status == "open")
        .scalar() or 0
    )
    overdue_actions: int = (
        db.query(func.count(MeetingActionItem.id))
        .filter(
            MeetingActionItem.status == "open",
            MeetingActionItem.priority == "high",
        )
        .scalar() or 0
    )

    # ── Top priorities (worst active projects, worst first) ───────────────────
    active_worst = [
        h for h in health_scores
        if (h.status or "").strip().lower() not in ("completed",)
    ]
    top_priorities = [_brief(h) for h in active_worst[:5]]

    # ── Biggest risks (reuse executive engine logic) ──────────────────────────
    health_risk_count = len(critical_hs) + len(at_risk_hs)
    biggest_risks: list[RiskCategory] = [
        RiskCategory(
            category="safety",
            label="Safety Events",
            severity=_count_to_severity(critical_safety, 10, 3),
            count=critical_safety,
            detail=(
                f"{critical_safety} critical/high severity safety events "
                "requiring investigation and corrective action"
            ),
        ),
        RiskCategory(
            category="procurement",
            label="Procurement",
            severity=_count_to_severity(late_pos, 50, 10),
            count=late_pos,
            detail=(
                f"{late_pos} late purchase orders out of {total_pos} total, "
                "affecting project delivery timelines"
            ),
        ),
        RiskCategory(
            category="quality",
            label="Quality (NCRs)",
            severity=_count_to_severity(open_ncrs, 20, 5),
            count=open_ncrs,
            detail=(
                f"{open_ncrs} open non-conformance reports "
                "pending resolution across the portfolio"
            ),
        ),
        RiskCategory(
            category="schedule",
            label="Schedule",
            severity=_count_to_severity(delayed_projects, 5, 2),
            count=delayed_projects,
            detail=(
                f"{delayed_projects} projects with delayed, on-hold, "
                "or suspended status"
            ),
        ),
        RiskCategory(
            category="health",
            label="Project Health",
            severity=_count_to_severity(health_risk_count, 10, 3),
            count=health_risk_count,
            detail=(
                f"{len(critical_hs)} critical and {len(at_risk_hs)} at-risk "
                "projects below performance thresholds"
            ),
        ),
    ]
    biggest_risks.sort(key=lambda r: (_SEV_ORDER.get(r.severity, 4), -r.count))

    # ── Critical alerts (top items from worst projects & operational counts) ──
    critical_alerts: list[ReportAlert] = []
    # Critical projects
    for h in critical_hs[:4]:
        reason = h.reasons[0] if h.reasons else "Multiple performance indicators below threshold"
        critical_alerts.append(ReportAlert(
            severity="critical",
            category="health",
            title=f"Critical Project: {h.project_code}",
            description=f"Score {h.score}/100 — {reason}",
            project_code=h.project_code,
        ))
    # Procurement
    if late_pos > 0:
        sev = "critical" if late_pos >= 50 else "high"
        critical_alerts.append(ReportAlert(
            severity=sev,
            category="procurement",
            title=f"{late_pos} Late Purchase Orders",
            description=f"{late_pos} POs past promised delivery date across the portfolio",
        ))
    if rework_prs > 0:
        critical_alerts.append(ReportAlert(
            severity="high",
            category="procurement",
            title=f"{rework_prs} Purchase Requests Need Rework",
            description=f"{rework_prs} PRs returned for rework or clarification",
        ))
    # Safety
    if critical_safety > 0:
        sev = "critical" if critical_safety >= 10 else "high"
        critical_alerts.append(ReportAlert(
            severity=sev,
            category="safety",
            title=f"{critical_safety} Critical/High Safety Events",
            description=f"{critical_safety} safety events requiring immediate corrective action",
        ))
    # Quality
    if open_ncrs > 0:
        sev = "critical" if open_ncrs >= 20 else "high"
        critical_alerts.append(ReportAlert(
            severity=sev,
            category="quality",
            title=f"{open_ncrs} Open Non-Conformance Reports",
            description=f"{open_ncrs} NCRs pending resolution; {corrective_ncrs} under corrective action",
        ))
    # Sort by severity
    sev_ord = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    critical_alerts.sort(key=lambda a: sev_ord.get(a.severity, 4))
    critical_alerts = critical_alerts[:10]

    # ── Procurement blockers ──────────────────────────────────────────────────
    procurement_blockers: list[ProcurementBlocker] = []
    if late_pos > 0:
        procurement_blockers.append(ProcurementBlocker(
            label="Late Purchase Orders",
            count=late_pos,
            detail=(
                f"{late_pos} of {total_pos} purchase orders ({round(late_pos/total_pos*100) if total_pos else 0}%) "
                "are past promised delivery, risking project material supply"
            ),
            severity=_count_to_severity(late_pos, 50, 10),
        ))
    if open_prs > 0:
        procurement_blockers.append(ProcurementBlocker(
            label="Purchase Requests Under Review",
            count=open_prs,
            detail=f"{open_prs} PRs awaiting approval or pending clarification",
            severity=_count_to_severity(open_prs, 20, 5),
        ))
    if rework_prs > 0:
        procurement_blockers.append(ProcurementBlocker(
            label="Purchase Requests Requiring Rework",
            count=rework_prs,
            detail=f"{rework_prs} PRs returned for rework or sent back to requester",
            severity=_count_to_severity(rework_prs, 10, 3),
        ))

    # ── Safety highlights ─────────────────────────────────────────────────────
    safety_highlights: list[SafetyHighlight] = []
    if critical_safety > 0:
        safety_highlights.append(SafetyHighlight(
            label="Critical / High Severity Events",
            count=critical_safety,
            detail=(
                f"{critical_safety} safety events classified as critical or high severity "
                "require mandatory investigation and corrective action"
            ),
            severity=_count_to_severity(critical_safety, 10, 3),
        ))
    if medium_safety > 0:
        safety_highlights.append(SafetyHighlight(
            label="Medium / Low Severity Events",
            count=medium_safety,
            detail=f"{medium_safety} lower-severity safety events on record requiring monitoring",
            severity="low",
        ))
    if open_actions > 0:
        safety_highlights.append(SafetyHighlight(
            label="Open Meeting Action Items",
            count=open_actions,
            detail=f"{open_actions} open action items from project meetings; {overdue_actions} high priority",
            severity=_count_to_severity(overdue_actions, 10, 3),
        ))

    # ── Quality / NCR highlights ──────────────────────────────────────────────
    quality_highlights: list[QualityHighlight] = []
    total_ncrs = open_ncrs + closed_ncrs
    if open_ncrs > 0:
        quality_highlights.append(QualityHighlight(
            label="Open Non-Conformance Reports",
            count=open_ncrs,
            detail=(
                f"{open_ncrs} NCRs are open; {corrective_ncrs} are under corrective action. "
                f"Closure rate: {round(closed_ncrs / total_ncrs * 100) if total_ncrs else 0}%"
            ),
            severity=_count_to_severity(open_ncrs, 20, 5),
        ))
    if closed_ncrs > 0:
        quality_highlights.append(QualityHighlight(
            label="Resolved Non-Conformance Reports",
            count=closed_ncrs,
            detail=f"{closed_ncrs} NCRs successfully closed and resolved",
            severity="low",
        ))

    # ── Recommended executive actions (deterministic rules) ──────────────────
    actions: list[RecommendedAction] = []
    priority = 1

    if len(critical_hs) > 0:
        actions.append(RecommendedAction(
            priority=priority,
            area="Project Health",
            action=f"Schedule emergency executive review for {len(critical_hs)} critical project(s)",
            rationale=(
                f"{len(critical_hs)} projects scored below 40/100. "
                f"Immediate intervention required: {', '.join(h.project_code for h in critical_hs[:3])}"
                + (f" and {len(critical_hs)-3} more" if len(critical_hs) > 3 else "")
            ),
        ))
        priority += 1

    if late_pos >= 50:
        actions.append(RecommendedAction(
            priority=priority,
            area="Procurement",
            action=f"Convene procurement crisis meeting to address {late_pos} late purchase orders",
            rationale=(
                f"{late_pos} POs are past delivery date ({round(late_pos/total_pos*100) if total_pos else 0}% of all POs). "
                "Supply chain disruption is the leading portfolio risk."
            ),
        ))
        priority += 1
    elif late_pos >= 10:
        actions.append(RecommendedAction(
            priority=priority,
            area="Procurement",
            action=f"Expedite delivery for {late_pos} overdue purchase orders",
            rationale=f"{late_pos} POs are past promised delivery date, risking project material supply.",
        ))
        priority += 1

    if critical_safety >= 10:
        actions.append(RecommendedAction(
            priority=priority,
            area="Safety",
            action="Commission portfolio-wide safety audit",
            rationale=(
                f"{critical_safety} critical/high severity safety events indicate systemic issues. "
                "Immediate safety review of all active sites is required."
            ),
        ))
        priority += 1
    elif critical_safety >= 3:
        actions.append(RecommendedAction(
            priority=priority,
            area="Safety",
            action=f"Review corrective actions for {critical_safety} critical/high safety events",
            rationale=f"{critical_safety} high-severity safety events require verified corrective action closure.",
        ))
        priority += 1

    if open_ncrs >= 20:
        actions.append(RecommendedAction(
            priority=priority,
            area="Quality",
            action=f"Initiate quality improvement program to close {open_ncrs} open NCRs",
            rationale=(
                f"{open_ncrs} open non-conformance reports indicate quality control gaps. "
                "Systematic NCR resolution program should be implemented."
            ),
        ))
        priority += 1
    elif open_ncrs >= 5:
        actions.append(RecommendedAction(
            priority=priority,
            area="Quality",
            action=f"Assign NCR closure owners for {open_ncrs} open non-conformance reports",
            rationale=f"{open_ncrs} NCRs without closure plan risk compounding quality issues.",
        ))
        priority += 1

    if len(at_risk_hs) >= 5:
        actions.append(RecommendedAction(
            priority=priority,
            area="Portfolio Recovery",
            action=f"Implement recovery plans for {len(at_risk_hs)} at-risk projects",
            rationale=(
                f"{len(at_risk_hs)} projects are at risk (score 40–59). "
                "Early intervention can prevent deterioration to critical status."
            ),
        ))
        priority += 1

    if open_actions >= 10:
        actions.append(RecommendedAction(
            priority=priority,
            area="Governance",
            action=f"Review and close {open_actions} overdue meeting action items",
            rationale=(
                f"{open_actions} action items from project meetings remain open, "
                f"including {overdue_actions} high-priority items requiring attention."
            ),
        ))
        priority += 1

    # ── Sources ───────────────────────────────────────────────────────────────
    total_safety = (
        db.query(func.count(SafetyEvent.id)).scalar() or 0
    )
    total_ncrs_all = (
        db.query(func.count(NCR.id)).scalar() or 0
    )
    total_prs = (
        db.query(func.count(PurchaseRequest.id)).scalar() or 0
    )
    sources = [
        SourceReference(
            source="Project Health Scores",
            record_count=total,
            description=f"Health scores computed for all {total} active/tracked projects",
        ),
        SourceReference(
            source="Purchase Orders",
            record_count=total_pos,
            description=f"{total_pos} purchase orders evaluated for delivery status",
        ),
        SourceReference(
            source="Purchase Requests",
            record_count=total_prs,
            description=f"{total_prs} purchase requests reviewed for status and blockers",
        ),
        SourceReference(
            source="Safety Events",
            record_count=total_safety,
            description=f"{total_safety} safety events assessed for severity and corrective action",
        ),
        SourceReference(
            source="Non-Conformance Reports",
            record_count=total_ncrs_all,
            description=f"{total_ncrs_all} NCRs reviewed; {open_ncrs} open, {closed_ncrs} closed",
        ),
        SourceReference(
            source="Meeting Action Items",
            record_count=open_actions + (
                db.query(func.count(MeetingActionItem.id)).filter(MeetingActionItem.status != "open").scalar() or 0
            ),
            description=f"Action items from project meetings tracked for completion",
        ),
    ]

    # ── Portfolio summary (deterministic prose) ───────────────────────────────
    status_phrase = {
        "Excellent": "performing excellently",
        "Good":      "in good standing",
        "At Risk":   "at risk",
        "Critical":  "in a critical state",
    }.get(portfolio_level, "under review")

    parts = [
        f"Executive Weekly Report for {period.label}. "
        f"The portfolio of {total} projects is {status_phrase} "
        f"with an average health score of {avg_score}/100."
    ]
    if len(critical_hs) > 0:
        s = "s" if len(critical_hs) > 1 else ""
        parts.append(f"{len(critical_hs)} project{s} require immediate executive intervention.")
    if late_pos > 0:
        parts.append(f"Procurement delays ({late_pos} late POs) remain the leading operational risk.")
    if open_ncrs > 0:
        parts.append(f"Quality control requires attention with {open_ncrs} open NCRs.")
    portfolio_summary = " ".join(parts)

    return ExecutiveWeeklyReport(
        report_period=period,
        generated_at=now_str,
        portfolio_summary=portfolio_summary,
        portfolio_status=portfolio_level,
        portfolio_score=avg_score,
        health_distribution=health_dist,
        top_priorities=top_priorities,
        biggest_risks=biggest_risks,
        critical_alerts=critical_alerts,
        procurement_blockers=procurement_blockers,
        safety_highlights=safety_highlights,
        quality_highlights=quality_highlights,
        recommended_actions=actions,
        sources=sources,
    )


def _empty_report(period: ReportPeriod, now_str: str) -> ExecutiveWeeklyReport:
    return ExecutiveWeeklyReport(
        report_period=period,
        generated_at=now_str,
        portfolio_summary="No project data is currently available for this report.",
        portfolio_status="Unknown",
        portfolio_score=0,
        health_distribution=HealthDistribution(
            excellent=0, good=0, at_risk=0, critical=0, total=0, average_score=0
        ),
        top_priorities=[],
        biggest_risks=[],
        critical_alerts=[],
        procurement_blockers=[],
        safety_highlights=[],
        quality_highlights=[],
        recommended_actions=[],
        sources=[],
    )


# ── Route ──────────────────────────────────────────────────────────────────────

@router.get("/executive-weekly", response_model=ExecutiveWeeklyReport)
def get_executive_weekly_report(db: DbSession) -> ExecutiveWeeklyReport:
    """
    Generate a deterministic Executive Weekly Report from live portfolio data.
    Covers health, procurement, safety, quality, and recommended actions.
    """
    return _compute_executive_weekly_report(db)
