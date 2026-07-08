"""
Executive Intelligence Engine — Phase 4C.

Deterministic portfolio intelligence from live PostgreSQL data.
No AI, no LLM, no predictions. All metrics derived from operational records.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func

from ...core.deps import DbSession
from ...models.projects import Project
from ...models.safety import SafetyEvent, NCR
from ...models.procurement import PurchaseOrder
from ...ai.health_score import get_all_projects_health, HealthScoreResult

router = APIRouter(prefix="/executive", tags=["executive"])

# ── Pydantic schemas ───────────────────────────────────────────────────────────

class ProjectBrief(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    status: str
    score: int
    level: str
    primary_reason: str


class RiskCategory(BaseModel):
    category: str
    label: str
    severity: str          # critical | high | medium | low
    count: int
    detail: str


class ExecutiveIntelligence(BaseModel):
    portfolio_status: str  # Excellent | Good | At Risk | Critical
    portfolio_score: int   # 0–100 portfolio average
    executive_summary: str
    total_projects: int
    critical_count: int
    at_risk_count: int
    good_count: int
    excellent_count: int
    top_priorities: list[ProjectBrief]   # worst active projects, worst first
    biggest_risks: list[RiskCategory]    # ranked risk categories
    best_projects: list[ProjectBrief]    # highest-scoring projects
    attention_required: list[ProjectBrief]  # critical + at-risk, worst first


# ── Helpers ───────────────────────────────────────────────────────────────────

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _score_to_level(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "At Risk"
    return "Critical"


def _count_to_severity(count: int, high_thresh: int, medium_thresh: int) -> str:
    if count >= high_thresh:
        return "critical"
    if count >= medium_thresh:
        return "high"
    if count > 0:
        return "medium"
    return "low"


def _brief(hs: HealthScoreResult) -> ProjectBrief:
    reason = (
        hs.reasons[0]
        if hs.reasons
        else "Multiple performance indicators below threshold"
    )
    return ProjectBrief(
        project_id=hs.project_id,
        project_code=hs.project_code,
        project_name=hs.project_name,
        status=hs.status or "",
        score=hs.score,
        level=hs.level,
        primary_reason=reason,
    )


# ── Intelligence computation ───────────────────────────────────────────────────

def _compute_executive_intelligence(db) -> ExecutiveIntelligence:  # type: ignore[type-arg]
    # ── 1. Health scores (sorted worst-first by get_all_projects_health) ──────
    health_scores = get_all_projects_health(db)

    if not health_scores:
        return ExecutiveIntelligence(
            portfolio_status="Unknown",
            portfolio_score=0,
            executive_summary="No project data is currently available.",
            total_projects=0,
            critical_count=0,
            at_risk_count=0,
            good_count=0,
            excellent_count=0,
            top_priorities=[],
            biggest_risks=[],
            best_projects=[],
            attention_required=[],
        )

    total = len(health_scores)
    critical_hs  = [h for h in health_scores if h.level == "Critical"]
    at_risk_hs   = [h for h in health_scores if h.level == "At Risk"]
    good_hs      = [h for h in health_scores if h.level == "Good"]
    excellent_hs = [h for h in health_scores if h.level == "Excellent"]

    avg_score      = round(sum(h.score for h in health_scores) / total)
    portfolio_level = _score_to_level(avg_score)

    # ── 2. Operational counts from live DB ────────────────────────────────────
    critical_safety: int = (
        db.query(func.count(SafetyEvent.id))
        .filter(SafetyEvent.severity.in_(["Critical", "High"]))
        .scalar()
        or 0
    )
    open_ncrs: int = (
        db.query(func.count(NCR.id))
        .filter(NCR.status != "Closed")
        .scalar()
        or 0
    )
    late_pos: int = (
        db.query(func.count(PurchaseOrder.id))
        .filter(PurchaseOrder.is_late.is_(True))
        .scalar()
        or 0
    )
    delayed_projects: int = (
        db.query(func.count(Project.id))
        .filter(Project.status.in_(["Delayed", "On Hold", "Suspended"]))
        .scalar()
        or 0
    )

    # ── 3. Risk categories ────────────────────────────────────────────────────
    health_risk_count = len(critical_hs) + len(at_risk_hs)
    risks: list[RiskCategory] = [
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
                f"{late_pos} late purchase orders affecting "
                "project delivery timelines and supply chains"
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
                "or suspended status impacting portfolio delivery"
            ),
        ),
        RiskCategory(
            category="health",
            label="Project Health",
            severity=_count_to_severity(health_risk_count, 10, 3),
            count=health_risk_count,
            detail=(
                f"{len(critical_hs)} critical and {len(at_risk_hs)} at-risk projects "
                "pulling down overall portfolio performance"
            ),
        ),
    ]
    # Sort: severity order first, then count descending
    risks.sort(key=lambda r: (_SEV_ORDER.get(r.severity, 4), -r.count))

    # ── 4. Top priorities (worst active/non-completed projects) ───────────────
    active_worst = [
        h for h in health_scores
        if (h.status or "").strip().lower() not in ("completed",)
    ]
    top_priorities = [_brief(h) for h in active_worst[:5]]

    # ── 5. Best projects (highest score, Excellent/Good, non-completed) ───────
    best_candidates = sorted(
        [
            h for h in health_scores
            if h.level in ("Excellent", "Good")
            and (h.status or "").strip().lower() not in ("completed",)
        ],
        key=lambda h: -h.score,
    )
    best_projects = [_brief(h) for h in best_candidates[:5]]

    # ── 6. Attention required (critical + at-risk, worst first) ──────────────
    # critical_hs and at_risk_hs are already ordered worst-first
    attention_required = [_brief(h) for h in (critical_hs + at_risk_hs)[:6]]

    # ── 7. Executive summary (deterministic, rule-based) ─────────────────────
    status_phrase = {
        "Excellent": "performing excellently",
        "Good":      "in good standing",
        "At Risk":   "at risk",
        "Critical":  "in a critical state",
    }.get(portfolio_level, "under review")

    parts: list[str] = [
        f"The portfolio is {status_phrase} "
        f"with an average health score of {avg_score}/100."
    ]

    if len(critical_hs) > 0:
        s = "s" if len(critical_hs) > 1 else ""
        parts.append(
            f"{len(critical_hs)} project{s} require immediate executive intervention."
        )
    elif len(at_risk_hs) > 0:
        s = "s" if len(at_risk_hs) > 1 else ""
        parts.append(
            f"{len(at_risk_hs)} project{s} are performing below acceptable thresholds."
        )

    top_risk = risks[0] if risks else None
    if top_risk and top_risk.severity in ("critical", "high"):
        driver_map = {
            "procurement": (
                f"Procurement delays ({late_pos} late POs) "
                "are the primary portfolio risk driver."
            ),
            "safety": (
                f"Safety performance ({critical_safety} critical/high events) "
                "demands priority attention."
            ),
            "quality": (
                f"Quality control ({open_ncrs} open NCRs) "
                "requires systematic remediation."
            ),
            "schedule": (
                f"Schedule adherence ({delayed_projects} delayed/on-hold projects) "
                "is impacting portfolio delivery."
            ),
            "health": (
                f"Overall project health ({health_risk_count} projects below threshold) "
                "is the primary concern."
            ),
        }
        if top_risk.category in driver_map:
            parts.append(driver_map[top_risk.category])

    executive_summary = " ".join(parts)

    return ExecutiveIntelligence(
        portfolio_status=portfolio_level,
        portfolio_score=avg_score,
        executive_summary=executive_summary,
        total_projects=total,
        critical_count=len(critical_hs),
        at_risk_count=len(at_risk_hs),
        good_count=len(good_hs),
        excellent_count=len(excellent_hs),
        top_priorities=top_priorities,
        biggest_risks=risks,
        best_projects=best_projects,
        attention_required=attention_required,
    )


# ── Route ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=ExecutiveIntelligence)
def get_executive_intelligence(db: DbSession) -> ExecutiveIntelligence:
    """
    Return deterministic executive portfolio intelligence.
    Derived entirely from live project, safety, procurement, and quality data.
    """
    return _compute_executive_intelligence(db)
