"""
Deterministic Project Health Score Engine — Phase 4A.

Scoring model: start at 100, subtract weighted penalties per domain.
Score 0–100 → Level: Excellent (80-100) | Good (60-79) | At Risk (40-59) | Critical (0-39)

All computation is pure Python over ORM objects — no AI, no external calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.projects import Project, ProjectRisk
from app.models.safety import SafetyEvent, NCR
from app.models.procurement import PurchaseOrder

# ── Weight constants ──────────────────────────────────────────────────────────

# Safety events: penalty per event by severity, sub-cap per tier, total cap
_SAFETY_PENALTY: dict[str, float] = {
    "Critical": 5.0, "High": 3.0, "Medium": 1.5, "Low": 0.5
}
_SAFETY_SUB_CAP: dict[str, float] = {
    "Critical": 15.0, "High": 15.0, "Medium": 8.0, "Low": 5.0
}
_SAFETY_TOTAL_CAP = 25.0

# NCRs: per open NCR (not Closed)
_NCR_PENALTY_PER = 1.5
_NCR_CAP = 20.0

# Late purchase orders
_PO_PENALTY_PER = 0.8
_PO_CAP = 15.0

# Project risks: by impact level
_RISK_PENALTY: dict[str, float] = {"high": 3.0, "medium": 1.5, "low": 0.5}
_RISK_CAP: dict[str, float] = {"high": 6.0, "medium": 4.0, "low": 2.0}
_RISK_TOTAL_CAP = 10.0

# Schedule: by status and overdue days
_STATUS_FIXED_PENALTY: dict[str, float] = {
    "Suspended": 30.0,
    "On Hold": 15.0,
}


# ── Date parsing ──────────────────────────────────────────────────────────────

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ── Factor calculators ────────────────────────────────────────────────────────

def _schedule_penalty(project: Project, today: date) -> tuple[float, list[str]]:
    status = (project.status or "").strip()
    planned = _parse_date(project.planned_finish)
    reasons: list[str] = []

    if status == "Completed":
        return 0.0, []

    if status in _STATUS_FIXED_PENALTY:
        reasons.append(f"Project is {status.lower()}")
        return _STATUS_FIXED_PENALTY[status], reasons

    if status == "Delayed":
        delay_days = max(0, (today - planned).days) if planned else 0
        extra = min(0.3 * delay_days, 10.0)
        penalty = 25.0 + extra
        if delay_days > 0:
            reasons.append(f"{delay_days}-day delay past planned finish")
        else:
            reasons.append("Project is behind schedule (Delayed status)")
        return penalty, reasons

    # Active / Planning — check if past planned finish
    if planned and today > planned:
        delay_days = (today - planned).days
        penalty = min(1.0 * delay_days, 20.0)
        reasons.append(f"{delay_days}-day overdue (planned finish: {planned})")
        return penalty, reasons

    return 0.0, []


def _safety_penalty(safety_events: list) -> tuple[float, list[str]]:
    by_sev: dict[str, int] = {}
    for e in safety_events:
        sev = (getattr(e, "severity", None) or "Low").strip()
        by_sev[sev] = by_sev.get(sev, 0) + 1

    total_penalty = 0.0
    reasons: list[str] = []
    for sev in ("Critical", "High", "Medium", "Low"):
        count = by_sev.get(sev, 0)
        if count == 0:
            continue
        per = _SAFETY_PENALTY.get(sev, 0.5)
        cap = _SAFETY_SUB_CAP.get(sev, 5.0)
        total_penalty += min(per * count, cap)
        if sev in ("Critical", "High"):
            reasons.append(f"{count} {sev} Severity Safety Event{'s' if count > 1 else ''}")
        elif sev == "Medium" and count >= 5:
            reasons.append(f"{count} Medium Severity Safety Events")

    return min(total_penalty, _SAFETY_TOTAL_CAP), reasons


def _ncr_penalty(ncrs: list) -> tuple[float, list[str]]:
    open_ncrs = [n for n in ncrs if (getattr(n, "status", "") or "").strip().lower() != "closed"]
    if not open_ncrs:
        return 0.0, []
    count = len(open_ncrs)
    penalty = min(_NCR_PENALTY_PER * count, _NCR_CAP)
    return penalty, [f"{count} Open NCR{'s' if count > 1 else ''}"]


def _procurement_penalty(purchase_orders: list) -> tuple[float, list[str]]:
    late = [po for po in purchase_orders if getattr(po, "is_late", False)]
    if not late:
        return 0.0, []
    count = len(late)
    penalty = min(_PO_PENALTY_PER * count, _PO_CAP)
    return penalty, [f"{count} Late Purchase Order{'s' if count > 1 else ''}"]


def _risk_penalty(risks: list) -> tuple[float, list[str]]:
    open_risks = [r for r in risks if (getattr(r, "status", "") or "").strip().lower() == "open"]
    if not open_risks:
        return 0.0, []

    by_impact: dict[str, int] = {}
    for r in open_risks:
        imp = (getattr(r, "impact", None) or "medium").strip().lower()
        by_impact[imp] = by_impact.get(imp, 0) + 1

    total_penalty = 0.0
    for imp, count in by_impact.items():
        per = _RISK_PENALTY.get(imp, 1.0)
        cap = _RISK_CAP.get(imp, 2.0)
        total_penalty += min(per * count, cap)

    total_penalty = min(total_penalty, _RISK_TOTAL_CAP)
    total_open = len(open_risks)
    reason = f"{total_open} Open Project Risk{'s' if total_open > 1 else ''}"
    return total_penalty, [reason]


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class HealthScoreResult:
    project_id: int
    project_code: str
    project_name: str
    status: str
    score: int                        # 0–100
    level: str                        # Excellent | Good | At Risk | Critical
    reasons: list[str] = field(default_factory=list)
    # Penalty breakdown (for transparency)
    schedule_penalty: float = 0.0
    safety_penalty: float = 0.0
    ncr_penalty: float = 0.0
    procurement_penalty: float = 0.0
    risk_penalty: float = 0.0


def _score_to_level(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "At Risk"
    return "Critical"


# ── Public API ────────────────────────────────────────────────────────────────

def compute_health_score(
    project: Project,
    today: Optional[date] = None,
) -> HealthScoreResult:
    """Compute a deterministic health score from a project with loaded relationships.

    The project object must have the following relationships loaded:
    safety_events, ncrs, purchase_orders, risks.
    Pass ``today`` to override the reference date (useful for tests).
    """
    today = today or date.today()

    sp, sr = _schedule_penalty(project, today)
    sfp, sfr = _safety_penalty(getattr(project, "safety_events", []) or [])
    np_, nr = _ncr_penalty(getattr(project, "ncrs", []) or [])
    pp, pr = _procurement_penalty(getattr(project, "purchase_orders", []) or [])
    rp, rr = _risk_penalty(getattr(project, "risks", []) or [])

    total_penalty = sp + sfp + np_ + pp + rp
    score = max(0, min(100, round(100.0 - total_penalty)))
    level = _score_to_level(score)

    return HealthScoreResult(
        project_id=project.id,
        project_code=project.project_code,
        project_name=project.project_name,
        status=project.status,
        score=score,
        level=level,
        reasons=sr + sfr + nr + pr + rr,
        schedule_penalty=round(sp, 2),
        safety_penalty=round(sfp, 2),
        ncr_penalty=round(np_, 2),
        procurement_penalty=round(pp, 2),
        risk_penalty=round(rp, 2),
    )


def _load_project_full(project_id: int, db: Session) -> Optional[Project]:
    """Load a project with all relationships needed for health scoring."""
    return (
        db.query(Project)
        .options(
            joinedload(Project.safety_events),
            joinedload(Project.ncrs),
            joinedload(Project.purchase_orders),
            joinedload(Project.risks),
        )
        .filter(Project.id == project_id)
        .first()
    )


def get_project_health(project_id: int, db: Session) -> Optional[HealthScoreResult]:
    """Return health score for one project, or None if not found."""
    project = _load_project_full(project_id, db)
    if not project:
        return None
    return compute_health_score(project)


def get_all_projects_health(db: Session) -> list[HealthScoreResult]:
    """Return health scores for all projects, sorted by score ascending (worst first)."""
    projects = (
        db.query(Project)
        .options(
            joinedload(Project.safety_events),
            joinedload(Project.ncrs),
            joinedload(Project.purchase_orders),
            joinedload(Project.risks),
        )
        .all()
    )
    today = date.today()
    results = [compute_health_score(p, today) for p in projects]
    results.sort(key=lambda r: r.score)
    return results
