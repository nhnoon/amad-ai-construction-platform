"""
Smart Alerts Center — Phase 4B.

Deterministic alert generation from live PostgreSQL data.
No AI predictions. No mock data. Alerts are derived entirely from existing
project, safety, procurement, and quality records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.deps import DbSession
from ...models.projects import Project
from ...models.safety import SafetyEvent, NCR
from ...models.procurement import PurchaseOrder
from ...ai.health_score import get_all_projects_health

router = APIRouter(prefix="/alerts", tags=["alerts"])

# ── Schemas ────────────────────────────────────────────────────────────────────

AlertSeverity = Literal["critical", "high", "medium", "low"]
AlertCategory = Literal["health", "safety", "procurement", "quality", "schedule"]


class Alert(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    category: str
    project_id: Optional[int] = None
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    source_type: str
    source_id: str
    detected_at: str
    recommended_action: str


class AlertsResponse(BaseModel):
    alerts: list[Alert]
    total: int


class AlertsSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    by_category: dict[str, int]


# ── Thresholds ────────────────────────────────────────────────────────────────

_NCR_HIGH_THRESHOLD = 5       # >= 5 open NCRs per project → high severity
_NCR_MEDIUM_THRESHOLD = 2     # 2–4 open NCRs per project → medium severity
_LATE_PO_HIGH_DAYS = 30       # delay_days > 30 → high severity PO alert
_PROC_RISK_THRESHOLD = 3      # >= 3 late POs per project → procurement risk alert
_SAFETY_RISK_THRESHOLD = 3    # >= 3 high/critical events per project → safety risk alert

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate(s: str, n: int) -> str:
    return s[:n] + "…" if len(s) > n else s


# ── Alert generation ──────────────────────────────────────────────────────────

def _generate_alerts(db: Session) -> list[Alert]:
    alerts: list[Alert] = []
    now = _now()

    # Load project lookup (id → Project) once — used across all generators
    all_projects: dict[int, Project] = {
        p.id: p for p in db.query(Project).all()
    }

    # ── 1 & 2: Health score alerts (Critical and At Risk projects) ────────────
    health_scores = get_all_projects_health(db)
    for hs in health_scores:
        if hs.level not in ("Critical", "At Risk"):
            continue
        top_reasons = "; ".join(hs.reasons[:3]) if hs.reasons else "Multiple performance indicators below threshold"
        if hs.level == "Critical":
            alerts.append(Alert(
                id=f"health-critical-{hs.project_id}",
                title=f"Critical Health Score: {hs.project_code}",
                description=(
                    f"Project '{hs.project_name}' has a critical health score of "
                    f"{hs.score}/100. Immediate intervention required. "
                    f"Key issues: {top_reasons}."
                ),
                severity="critical",
                category="health",
                project_id=hs.project_id,
                project_code=hs.project_code,
                project_name=hs.project_name,
                source_type="project",
                source_id=f"project-{hs.project_id}",
                detected_at=now,
                recommended_action=(
                    "Convene emergency project review. "
                    "Address all critical issues immediately. "
                    "Escalate to executive leadership."
                ),
            ))
        else:  # At Risk
            alerts.append(Alert(
                id=f"health-atrisk-{hs.project_id}",
                title=f"At-Risk Project: {hs.project_code}",
                description=(
                    f"Project '{hs.project_name}' has an at-risk health score of "
                    f"{hs.score}/100. Performance is declining. "
                    f"Issues: {top_reasons}."
                ),
                severity="high",
                category="health",
                project_id=hs.project_id,
                project_code=hs.project_code,
                project_name=hs.project_name,
                source_type="project",
                source_id=f"project-{hs.project_id}",
                detected_at=now,
                recommended_action=(
                    "Schedule project performance review within 2 weeks. "
                    "Review and update the project risk register."
                ),
            ))

    # ── 3 & 4: High-severity safety events ───────────────────────────────────
    critical_safety_events = (
        db.query(SafetyEvent)
        .filter(SafetyEvent.severity.in_(["Critical", "High"]))
        .all()
    )
    for ev in critical_safety_events:
        proj = all_projects.get(ev.project_id)
        if not proj:
            continue
        sev = "critical" if ev.severity == "Critical" else "high"
        corrective = _truncate(ev.corrective_action or "Review required", 100)
        alerts.append(Alert(
            id=f"safety-event-{ev.id}",
            title=f"{ev.severity} Safety Event — {proj.project_code}",
            description=(
                f"A {ev.severity.lower()} severity safety incident was recorded "
                f"on {ev.event_date} for project '{proj.project_name}'. "
                f"Incident: {_truncate(ev.description, 120)}"
            ),
            severity=sev,
            category="safety",
            project_id=ev.project_id,
            project_code=proj.project_code,
            project_name=proj.project_name,
            source_type="safety_event",
            source_id=f"safety-{ev.id}",
            detected_at=now,
            recommended_action=(
                f"Halt related work and conduct immediate site investigation. "
                f"Corrective action: {corrective}"
                if ev.severity == "Critical"
                else f"Review and implement corrective action: {corrective}"
            ),
        ))

    # ── 10: Safety risk per project (≥3 high/critical events) ────────────────
    safety_by_project: dict[int, list[SafetyEvent]] = {}
    for ev in critical_safety_events:
        safety_by_project.setdefault(ev.project_id, []).append(ev)

    for proj_id, evs in safety_by_project.items():
        if len(evs) < _SAFETY_RISK_THRESHOLD:
            continue
        proj = all_projects.get(proj_id)
        if not proj:
            continue
        crit_cnt = sum(1 for e in evs if e.severity == "Critical")
        high_cnt = sum(1 for e in evs if e.severity == "High")
        alerts.append(Alert(
            id=f"safety-risk-{proj_id}",
            title=f"Safety Risk: {len(evs)} High-Severity Events — {proj.project_code}",
            description=(
                f"Project '{proj.project_name}' has accumulated {len(evs)} high/critical "
                f"severity safety events ({crit_cnt} Critical, {high_cnt} High). "
                "This pattern indicates elevated and systemic site safety risk."
            ),
            severity="critical" if crit_cnt >= 2 else "high",
            category="safety",
            project_id=proj_id,
            project_code=proj.project_code,
            project_name=proj.project_name,
            source_type="project_safety",
            source_id=f"safety-risk-{proj_id}",
            detected_at=now,
            recommended_action=(
                "Conduct a comprehensive safety audit immediately. "
                "Review and reinforce all site safety procedures. "
                "Consider a mandatory safety stand-down for all workers on site."
            ),
        ))

    # ── 4 & 9: Quality — open NCRs per project ───────────────────────────────
    open_ncrs = (
        db.query(NCR)
        .filter(NCR.status != "Closed")
        .all()
    )
    ncr_by_project: dict[int, list[NCR]] = {}
    for ncr in open_ncrs:
        ncr_by_project.setdefault(ncr.project_id, []).append(ncr)

    for proj_id, ncr_list in ncr_by_project.items():
        count = len(ncr_list)
        if count < _NCR_MEDIUM_THRESHOLD:
            continue
        proj = all_projects.get(proj_id)
        if not proj:
            continue
        sev = "high" if count >= _NCR_HIGH_THRESHOLD else "medium"
        alerts.append(Alert(
            id=f"quality-ncr-{proj_id}",
            title=f"{count} Open NCRs — {proj.project_code}",
            description=(
                f"Project '{proj.project_name}' has {count} open Non-Conformance Reports. "
                "Unresolved NCRs indicate quality control issues requiring immediate attention."
            ),
            severity=sev,
            category="quality",
            project_id=proj_id,
            project_code=proj.project_code,
            project_name=proj.project_name,
            source_type="project_ncrs",
            source_id=f"ncrs-{proj_id}",
            detected_at=now,
            recommended_action=(
                "Prioritize NCR closure. "
                "Review quality control processes. "
                "Assign responsible engineers to each open NCR."
            ),
        ))

    # ── 5: Late purchase orders (individual alerts) ───────────────────────────
    late_pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.is_late == True)  # noqa: E712
        .all()
    )
    for po in late_pos:
        proj = all_projects.get(po.project_id)
        if not proj:
            continue
        delay = po.delay_days or 0
        sev = "high" if delay > _LATE_PO_HIGH_DAYS else "medium"
        root_cause = _truncate(po.delay_root_cause or "Not specified", 80)
        alerts.append(Alert(
            id=f"procurement-late-po-{po.id}",
            title=f"Late PO {po.po_number} — {proj.project_code}",
            description=(
                f"Purchase Order {po.po_number} for project '{proj.project_name}' "
                f"is {delay} day{'s' if delay != 1 else ''} late. "
                f"Promised delivery: {po.promised_delivery}. "
                f"Root cause: {root_cause}."
            ),
            severity=sev,
            category="procurement",
            project_id=po.project_id,
            project_code=proj.project_code,
            project_name=proj.project_name,
            source_type="purchase_order",
            source_id=f"po-{po.id}",
            detected_at=now,
            recommended_action=(
                "Contact supplier for immediate delivery update. "
                "Identify critical-path impact on project schedule. "
                "Escalate to procurement manager if delivery not confirmed."
            ),
        ))

    # ── 8: Procurement risk per project (≥3 late POs) ────────────────────────
    late_by_project: dict[int, list[PurchaseOrder]] = {}
    for po in late_pos:
        late_by_project.setdefault(po.project_id, []).append(po)

    for proj_id, pos in late_by_project.items():
        if len(pos) < _PROC_RISK_THRESHOLD:
            continue
        proj = all_projects.get(proj_id)
        if not proj:
            continue
        avg_delay = round(sum(p.delay_days or 0 for p in pos) / len(pos))
        alerts.append(Alert(
            id=f"procurement-risk-{proj_id}",
            title=f"Procurement Risk: {len(pos)} Late POs — {proj.project_code}",
            description=(
                f"Project '{proj.project_name}' has {len(pos)} late purchase orders "
                f"with an average delay of {avg_delay} days. "
                "This indicates a systemic procurement performance issue."
            ),
            severity="high",
            category="procurement",
            project_id=proj_id,
            project_code=proj.project_code,
            project_name=proj.project_name,
            source_type="project_procurement",
            source_id=f"proc-risk-{proj_id}",
            detected_at=now,
            recommended_action=(
                "Conduct emergency procurement review. "
                "Evaluate supplier performance and consider alternative sourcing. "
                "Update project schedule for cumulative delay impact."
            ),
        ))

    # ── 6 & 7: Schedule — Delayed and On Hold projects ────────────────────────
    for proj in all_projects.values():
        if proj.status == "Delayed":
            alerts.append(Alert(
                id=f"schedule-delayed-{proj.id}",
                title=f"Delayed Project: {proj.project_code}",
                description=(
                    f"Project '{proj.project_name}' is behind schedule. "
                    f"Planned finish: {proj.planned_finish}. "
                    "Continued delay may impact client commitments and project economics."
                ),
                severity="high",
                category="schedule",
                project_id=proj.id,
                project_code=proj.project_code,
                project_name=proj.project_name,
                source_type="project",
                source_id=f"schedule-{proj.id}",
                detected_at=now,
                recommended_action=(
                    "Review and update the project schedule recovery plan. "
                    "Identify critical-path activities causing the delay. "
                    "Communicate updated timeline to client and stakeholders."
                ),
            ))
        elif proj.status == "On Hold":
            alerts.append(Alert(
                id=f"schedule-onhold-{proj.id}",
                title=f"Project On Hold: {proj.project_code}",
                description=(
                    f"Project '{proj.project_name}' is currently on hold. "
                    f"Planned finish: {proj.planned_finish}. "
                    "An undefined hold may lead to resource idling and schedule overrun."
                ),
                severity="medium",
                category="schedule",
                project_id=proj.id,
                project_code=proj.project_code,
                project_name=proj.project_name,
                source_type="project",
                source_id=f"schedule-{proj.id}",
                detected_at=now,
                recommended_action=(
                    "Confirm hold reason and expected duration with project owner. "
                    "Define clear resumption criteria. "
                    "Communicate hold status to all affected stakeholders."
                ),
            ))

    # Sort: critical → high → medium → low, then stable by id
    _SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: (_SEV_ORDER.get(a.severity, 9), a.id))

    return alerts


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=AlertsResponse)
def list_alerts(
    db: DbSession,
    severity: Optional[str] = Query(None, description="Filter: critical | high | medium | low"),
    category: Optional[str] = Query(None, description="Filter: health | safety | procurement | quality | schedule"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    alerts = _generate_alerts(db)

    if severity:
        alerts = [a for a in alerts if a.severity == severity.lower()]
    if category:
        alerts = [a for a in alerts if a.category == category.lower()]
    if project_id is not None:
        alerts = [a for a in alerts if a.project_id == project_id]

    total = len(alerts)
    paged = alerts[offset: offset + limit]
    return AlertsResponse(alerts=paged, total=total)


@router.get("/summary", response_model=AlertsSummary)
def get_alerts_summary(db: DbSession):
    alerts = _generate_alerts(db)

    by_sev: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_cat: dict[str, int] = {}

    for a in alerts:
        by_sev[a.severity] = by_sev.get(a.severity, 0) + 1
        by_cat[a.category] = by_cat.get(a.category, 0) + 1

    return AlertsSummary(
        total=len(alerts),
        critical=by_sev.get("critical", 0),
        high=by_sev.get("high", 0),
        medium=by_sev.get("medium", 0),
        low=by_sev.get("low", 0),
        by_category=by_cat,
    )
