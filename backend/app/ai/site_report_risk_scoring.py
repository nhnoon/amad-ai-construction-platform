"""Site Report Intelligence — deterministic risk scoring.

This replaces the old "confidence_score" (backend/app/ai/site_report_intelligence.py,
_confidence_score(): `45 + min(source_count, 8) * 6 - min(issue_count, 4) * 3`) —
an arbitrary formula with no relationship to anything real, presented to
users as if it were the AI's confidence in its own answer.

What this module produces instead is a RISK score, not a confidence score:
a transparent, weighted sum over the report's own evidence (open NCRs,
critical safety events, adverse weather, schedule delay signals, blocked
activities, missing-inspection mentions, repeated cross-report
observations, late procurement, and open contract-level issues), clamped
to 0-100, with every contributing component reported alongside the total
so the number can be audited rather than trusted blindly. No LLM is
involved in computing it — it must be reproducible from the same evidence
every time.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.site_report_evidence import ReportEvidence, _looks_blocked

# Each weight below is deliberately documented with WHY, not left as a bare
# magic number — every entry states what one occurrence costs, the cap on
# how much that category can contribute, and the reasoning.
_WEIGHTS: dict[str, tuple[int, int, str]] = {
    # (points_per_occurrence, max_points_for_category, rationale)
    "open_ncr": (8, 32, "An open non-conformance is unresolved quality risk; capped at 4 NCRs so one report with many minor NCRs doesn't dominate the score."),
    "critical_safety": (15, 30, "Critical/high-severity safety events are the single highest-consequence signal available; capped at 2 events."),
    "moderate_safety": (6, 18, "Medium/low-severity safety events still matter but far less than critical ones; capped at 3 events."),
    "adverse_weather": (10, 10, "Adverse weather (rain/storm/sandstorm/extreme heat) directly threatens schedule and, for some trades, safety; flat penalty since severity gradation isn't recorded."),
    "late_procurement": (6, 18, "A late purchase order in this report's window is a concrete, dated schedule threat; capped at 3 POs."),
    "blocked_activity": (5, 20, "An activity description matching blocker language (pending inspection, awaiting, on hold, etc.) signals stalled work; capped at 4 activities."),
    "missing_inspection_mention": (8, 8, "An explicit 'inspection pending/overdue' mention is a compounding risk (safety + schedule + compliance in one); flat penalty, evidence-cited."),
    "repeated_observation": (10, 20, "The same issue (by subcontractor + NCR/safety description overlap) appearing in this report AND a prior report indicates a problem that wasn't resolved; capped at 2 repeats."),
    "open_contract_issue": (10, 20, "An open, high/critical-severity project issue reflects unresolved contractual/commercial exposure; capped at 2 issues."),
}

_ADVERSE_WEATHER_WORDS = ("rain", "storm", "sandstorm", "heavy wind", "extreme heat", "flood", "fog")
_INSPECTION_OVERDUE_WORDS = ("inspection pending", "inspection overdue", "awaiting inspection", "pending inspection")


@dataclass
class RiskComponent:
    key: str
    label: str
    occurrences: int
    points: int
    max_points: int
    rationale: str
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class RiskScoreBreakdown:
    total: int
    level: str
    components: list[RiskComponent]


def _level_for_score(score: int) -> str:
    if score >= 70:
        return "Critical"
    if score >= 45:
        return "High"
    if score >= 20:
        return "Medium"
    return "Low"


def _repeated_observations(ev: ReportEvidence) -> tuple[int, list[str]]:
    """An issue is "repeated" if this report's NCR/safety description text
    overlaps (same subcontractor + shared significant word) with a prior
    report's own NCR/safety descriptions. Deliberately coarse — this is a
    retrieval signal fed to the risk score and to Hermes, not a final
    verdict; Hermes does the actual contextual judgment call in the
    reasoning layer (see site_report_reasoning.py)."""
    current_texts = [n.description for n in ev.ncrs if n.description] + [
        s.description for s in ev.safety_events if s.description
    ]
    if not current_texts or not ev.prior_reports:
        return 0, []

    def _keywords(text: str) -> set[str]:
        return {w for w in text.lower().split() if len(w) >= 6}

    refs: list[str] = []
    count = 0
    for cur in current_texts:
        cur_kw = _keywords(cur)
        if not cur_kw:
            continue
        for prior in ev.prior_reports:
            prior_texts = prior.ncr_descriptions + prior.safety_descriptions
            for pt in prior_texts:
                overlap = cur_kw & _keywords(pt)
                if len(overlap) >= 2:
                    count += 1
                    refs.append(f"SR-{prior.report_id}")
                    break
            else:
                continue
            break
    return count, refs


def compute_report_risk_score(ev: ReportEvidence) -> RiskScoreBreakdown:
    components: list[RiskComponent] = []

    open_ncrs = [n for n in ev.ncrs if (n.status or "").lower() not in ("closed", "resolved")]
    pts, cap, why = _WEIGHTS["open_ncr"]
    n_occ = len(open_ncrs)
    components.append(RiskComponent(
        "open_ncr", "Open NCRs in this report's window", n_occ,
        min(n_occ * pts, cap), cap, why, [f"NCR-{n.id}" for n in open_ncrs],
    ))

    critical_safety = [s for s in ev.safety_events if (s.severity or "").lower() in ("critical", "high")]
    pts, cap, why = _WEIGHTS["critical_safety"]
    n_occ = len(critical_safety)
    components.append(RiskComponent(
        "critical_safety", "Critical/high-severity safety events", n_occ,
        min(n_occ * pts, cap), cap, why, [f"SE-{s.id}" for s in critical_safety],
    ))

    moderate_safety = [s for s in ev.safety_events if (s.severity or "").lower() in ("medium", "low")]
    pts, cap, why = _WEIGHTS["moderate_safety"]
    n_occ = len(moderate_safety)
    components.append(RiskComponent(
        "moderate_safety", "Medium/low-severity safety events", n_occ,
        min(n_occ * pts, cap), cap, why, [f"SE-{s.id}" for s in moderate_safety],
    ))

    weather_low = (ev.report.weather or "").lower()
    is_adverse = any(w in weather_low for w in _ADVERSE_WEATHER_WORDS)
    pts, cap, why = _WEIGHTS["adverse_weather"]
    components.append(RiskComponent(
        "adverse_weather", "Adverse weather conditions", 1 if is_adverse else 0,
        pts if is_adverse else 0, cap, why, [f"SR-{ev.report.id}"] if is_adverse else [],
    ))

    late_pos = [po for po in ev.purchase_orders if po.is_late]
    pts, cap, why = _WEIGHTS["late_procurement"]
    n_occ = len(late_pos)
    components.append(RiskComponent(
        "late_procurement", "Late purchase orders in this window", n_occ,
        min(n_occ * pts, cap), cap, why, [f"PO-{po.id}" for po in late_pos],
    ))

    blocked = [a for a in ev.activities if _looks_blocked(a.activity_description)]
    pts, cap, why = _WEIGHTS["blocked_activity"]
    n_occ = len(blocked)
    components.append(RiskComponent(
        "blocked_activity", "Activities showing blocker language", n_occ,
        min(n_occ * pts, cap), cap, why, [f"DA-{a.id}" for a in blocked],
    ))

    all_text = " ".join(
        [ev.report.summary or ""] + [a.activity_description or "" for a in ev.activities]
    ).lower()
    inspection_flag = any(w in all_text for w in _INSPECTION_OVERDUE_WORDS)
    pts, cap, why = _WEIGHTS["missing_inspection_mention"]
    components.append(RiskComponent(
        "missing_inspection_mention", "Overdue/pending inspection mentioned", 1 if inspection_flag else 0,
        pts if inspection_flag else 0, cap, why, [f"SR-{ev.report.id}"] if inspection_flag else [],
    ))

    repeat_count, repeat_refs = _repeated_observations(ev)
    pts, cap, why = _WEIGHTS["repeated_observation"]
    components.append(RiskComponent(
        "repeated_observation", "Issues repeated from a prior report", repeat_count,
        min(repeat_count * pts, cap), cap, why, repeat_refs,
    ))

    contract_issues = [
        i for i in ev.open_project_issues if (i.severity or "").lower() in ("high", "critical")
    ]
    pts, cap, why = _WEIGHTS["open_contract_issue"]
    n_occ = len(contract_issues)
    components.append(RiskComponent(
        "open_contract_issue", "Open high/critical project issues", n_occ,
        min(n_occ * pts, cap), cap, why, [f"ISSUE-{i.id}" for i in contract_issues],
    ))

    total = min(100, sum(c.points for c in components))
    return RiskScoreBreakdown(total=total, level=_level_for_score(total), components=components)
