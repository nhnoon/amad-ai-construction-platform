"""Site Report Intelligence — orchestration layer.

Two distinct outputs, matching the two existing API routes
(app/api/v1/site_reports.py) — endpoints and response shapes unchanged:

- `list_site_report_cards` / `build_site_report_intelligence`: deterministic,
  no LLM call, powers the report list and the detail page's raw data view
  (GET .../cards, GET .../intelligence). Fast, always available. Now built
  from report-scoped, date-windowed evidence (app/ai/site_report_evidence.py)
  instead of the old "3 most recent project-wide" pattern, so the raw data
  view itself no longer looks identical across different reports for the
  same project.

- `analyze_site_report`: the actual AI reasoning pipeline (POST
  .../analyze). Gathers the same report-scoped evidence, computes a
  transparent deterministic risk score, and makes exactly one Hermes call
  to reason over it — see app/ai/site_report_reasoning.py for what "reason"
  means here versus the old keyword-template approach it replaces.
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.ai.site_report_evidence import (
    ReportEvidence,
    _extract_project_staff,
    _in_window,
    _looks_blocked,
    _window_for_report,
    gather_report_evidence,
    parse_report_date,
)
from app.ai.site_report_reasoning import (
    _TIMED_OUT_MESSAGE_EN,
    _UNAVAILABLE_MESSAGE_EN,
    generate_report_reasoning,
)
from app.ai.site_report_risk_scoring import compute_report_risk_score
from app.models.documents import Correspondence, Document, GeneratedDocument
from app.models.projects import Project
from app.models.safety import NCR, SafetyEvent
from app.models.procurement import PurchaseOrder
from app.models.site import DailyActivity, SiteReport
from app.schemas.site import (
    AnalysisSectionSourceOut,
    AnalysisSourceOut,
    PriorityMatrixItemOut,
    RecommendedActionOut,
    RiskScoreBreakdownOut,
    RiskScoreComponentOut,
    SiteReportAnalysisOut,
    TrendAnalysisOut,
)

_SENTENCE_SPLIT_WORDS = (
    "delay", "delayed", "late", "behind", "slow", "hold", "stopp", "postpone",
)
_EQUIPMENT_WORDS = (
    "crane", "excavator", "loader", "pump", "generator", "truck", "scaffold",
    "welding", "compactor", "lift", "bulldozer",
)
_MATERIAL_WORDS = (
    "concrete", "cement", "rebar", "steel", "aggregate", "sand", "asphalt",
    "block", "brick", "cable", "pipe", "membrane", "insulation",
)
_COMPLETION_WORDS = ("complete", "completed", "finished", "installed", "closed", "executed", "poured")


def _short(text: str, limit: int = 180) -> str:
    txt = " ".join((text or "").split())
    return txt if len(txt) <= limit else f"{txt[: limit - 3]}..."


def _severity_label(score: int) -> str:
    if score >= 8:
        return "Critical"
    if score >= 5:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def _pick_by_keywords(lines, words, limit):
    found = []
    for line in lines:
        low = line.lower()
        if any(w in low for w in words):
            found.append(line)
        if len(found) >= limit:
            break
    return found


@dataclass
class IntelligenceResult:
    report: dict
    analysis: dict


def list_site_report_cards(db: Session, project_id: int, skip: int = 0, limit: int = 20) -> list[dict]:
    """Deterministic list view. Risk/safety/quality indicators are now
    computed per-report from that report's own evidence window (same
    windowing as the full evidence gatherer, but scoped to just the
    counts needed here to keep this list cheap) — previously these three
    indicators were project-wide counts applied identically to every card
    for a project, which was part of why the list itself looked
    uninformative before a report was even opened."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return []

    reports = (
        db.query(SiteReport)
        .filter(SiteReport.project_id == project_id)
        .order_by(SiteReport.report_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    if not reports:
        return []

    engineer, _ = _extract_project_staff(db, project_id)

    report_ids = [r.id for r in reports]
    activities = (
        db.query(DailyActivity)
        .filter(DailyActivity.project_id == project_id, DailyActivity.site_report_id.in_(report_ids))
        .all()
    )
    activities_by_report: dict[int, list[DailyActivity]] = defaultdict(list)
    for act in activities:
        activities_by_report[act.site_report_id].append(act)

    all_safety = db.query(SafetyEvent).filter(SafetyEvent.project_id == project_id).all()
    all_ncr = db.query(NCR).filter(NCR.project_id == project_id).all()
    all_pos = db.query(PurchaseOrder).filter(PurchaseOrder.project_id == project_id).all()

    cards: list[dict] = []
    for report in reports:
        w_start, w_end, _ = _window_for_report(db, project_id, report)
        report_activities = activities_by_report.get(report.id, [])

        windowed_safety = [
            s for s in all_safety if _in_window(parse_report_date(s.event_date), w_start, w_end)
        ]
        windowed_ncr = [
            n for n in all_ncr if _in_window(parse_report_date(n.issue_date), w_start, w_end)
            and (n.status or "").lower() not in ("closed", "resolved")
        ]
        windowed_late_po = [
            po for po in all_pos if po.is_late
            and _in_window(parse_report_date(po.promised_delivery), w_start, w_end)
        ]
        blocked = [a for a in report_activities if _looks_blocked(a.activity_description)]
        completed = [a for a in report_activities if any(w in (a.activity_description or "").lower() for w in _COMPLETION_WORDS)]

        progress_text = (
            f"{len(completed)} completed activities from {len(report_activities)} activity logs"
            if report_activities
            else "No daily activity records linked"
        )

        critical_safety = len([s for s in windowed_safety if (s.severity or "").lower() in ("high", "critical")])
        card_risk_score = len(windowed_ncr) + len(blocked) + len(windowed_late_po)
        card_safety_score = critical_safety + len(windowed_safety)
        card_quality_score = len(windowed_ncr)

        cards.append({
            "report_id": report.id,
            "project_id": project_id,
            "project_name": project.project_name,
            "report_date": report.report_date,
            "engineer": engineer.get("full_name") if engineer else None,
            "weather": report.weather,
            "work_progress": progress_text,
            "risk_indicator": _severity_label(card_risk_score),
            "safety_indicator": _severity_label(card_safety_score),
            "quality_indicator": _severity_label(card_quality_score),
        })

    return cards


def build_site_report_intelligence(db: Session, project_id: int, report_id: int) -> IntelligenceResult:
    """Deterministic detail/raw-data view (GET .../intelligence) — no LLM
    call. Built from the same report-scoped evidence window as the AI
    analysis, so different reports for the same project now show
    genuinely different equipment/delay/safety/quality signals here too,
    not just in the /analyze narrative."""
    ev = gather_report_evidence(db, project_id, report_id)
    report, project = ev.report, ev.project

    activity_lines = [a.activity_description for a in ev.activities if a.activity_description]
    summary_lines = [report.summary] if report.summary else []
    all_lines = summary_lines + activity_lines

    equipment_lines = _pick_by_keywords(all_lines, _EQUIPMENT_WORDS, 6)
    completed_work = _pick_by_keywords(all_lines, _COMPLETION_WORDS, 8)
    work_in_progress = [line for line in activity_lines if line not in completed_work][:8]
    delay_lines = _pick_by_keywords(all_lines, _SENTENCE_SPLIT_WORDS, 8)
    blocker_lines = [a.activity_description for a in ev.activities if _looks_blocked(a.activity_description)][:8]
    safety_lines = [f"[{s.event_date}] {s.severity} safety event: {s.description}" for s in ev.safety_events][:8]
    quality_lines = [f"[{n.issue_date}] NCR ({n.status}) {n.ncr_type}: {n.description}" for n in ev.ncrs][:8]
    materials_used = _pick_by_keywords(all_lines, _MATERIAL_WORDS, 8)

    if not equipment_lines and ev.activities:
        equipment_lines = ["No explicit equipment statement in report text; verify against activity logs and permits."]
    if not completed_work and ev.activities:
        completed_work = ["Daily activity records exist but completion statements are not explicit in text."]

    delays = delay_lines or ["No explicit schedule delay stated in this report's evidence window."]
    blockers = blocker_lines or ["No explicit blockers documented in this report's evidence window."]
    safety_observations = safety_lines or ["No safety events recorded in this report's evidence window."]
    quality_observations = quality_lines or ["No NCRs recorded in this report's evidence window."]
    site_issue_rows = [f"[{i.created_at or 'N/A'}] {i.title} ({i.severity}, {i.status})" for i in ev.open_project_issues]
    site_issues = site_issue_rows + blocker_lines
    if not site_issues:
        site_issues = ["No open site issues linked to this project."]
    if not work_in_progress:
        work_in_progress = ["No explicit in-progress statements found in activity logs."]
    if not materials_used:
        materials_used = ["No explicit materials were identified in report/activity text."]

    recommendations: list[str] = [
        "Run AI Analysis for evidence-based, prioritized recommendations with citations."
    ]

    attachments = (
        db.query(Document).filter(Document.project_id == project_id).order_by(Document.doc_date.desc()).limit(5).all()
    )
    generated_documents = (
        db.query(GeneratedDocument).filter(GeneratedDocument.project_id == project_id).order_by(GeneratedDocument.document_date.desc()).limit(5).all()
    )
    correspondence = (
        db.query(Correspondence).filter(Correspondence.project_id == project_id).order_by(Correspondence.sent_date.desc()).limit(5).all()
    )

    photo_attachments = [
        {"source_type": doc.doc_type, "source_id": doc.id, "title": doc.title, "date": doc.doc_date}
        for doc in attachments
        if any(key in (doc.doc_type or "").lower() or key in (doc.title or "").lower() for key in ("photo", "image", "snapshot", "site photo"))
    ]
    document_references = [
        {"source_type": doc.doc_type, "source_id": doc.id, "title": doc.title, "date": doc.doc_date}
        for doc in attachments
    ] + [
        {"source_type": f"generated_{doc.type}", "source_id": doc.id, "title": doc.file_name, "date": doc.document_date}
        for doc in generated_documents
    ] + [
        {"source_type": f"correspondence_{row.related_record_type}", "source_id": row.id, "title": row.subject, "date": row.sent_date}
        for row in correspondence
    ]

    report_payload = {
        "report_id": report.id,
        "project_id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "engineer": ev.engineer,
        "supervisor": ev.supervisor,
        "report_date": report.report_date,
        "weather": report.weather,
        "temperature": None,
        "manpower": {"total_workers": ev.total_workers, "subcontractor_breakdown": ev.manpower_breakdown},
        "equipment": equipment_lines,
        "completed_work": completed_work,
        "work_in_progress": work_in_progress,
        "materials_used": materials_used,
        "site_issues": site_issues,
        "delays": delays,
        "blockers": blockers,
        "recommendations": recommendations,
        "safety_observations": safety_observations,
        "quality_observations": quality_observations,
        "photos": photo_attachments,
        "attachments": [
            {"source_type": doc.doc_type, "source_id": doc.id, "title": doc.title, "date": doc.doc_date}
            for doc in attachments
        ],
        "document_references": document_references,
        "raw_summary": report.summary,
    }

    # analysis payload kept for internal callers/back-compat only — the real
    # AI analysis is analyze_site_report() below; GET .../intelligence never
    # calls Hermes.
    analysis = {
        "analysis_generated_from": "Deterministic evidence view — run AI Analysis for reasoned findings.",
        "executive_summary": "",
        "safety_findings": safety_observations,
        "quality_findings": quality_observations,
        "recommended_actions": [],
        "priority_level": "Low",
        "escalation_required": False,
        "confidence_score": 0,
        "section_sources": [],
        "source_attribution": [],
    }

    return IntelligenceResult(report=report_payload, analysis=analysis)


def _unavailable_analysis_out(reason: str) -> SiteReportAnalysisOut:
    """Structured fallback for a failure so unexpected it happened before
    evidence/risk could even be gathered — e.g. a DB error inside
    gather_report_evidence(). The route only ever raises ValueError (->404)
    or lets this function's own return value through; nothing else should
    ever reach the client as a bare, unlabeled 500 (see analyze_site_report
    below). This is the API contract "always return either completed
    intelligence or a structured error with explanation" for the one case
    where even the evidence/risk score aren't available."""
    return SiteReportAnalysisOut(
        analysis_generated_from="AI reasoning unavailable — an unexpected error occurred before evidence could be gathered.",
        reasoning_status="unavailable",
        reasoning_provider=None,
        reasoning_model=None,
        reasoning_error=reason,
        insufficient_evidence=False,
        insufficient_evidence_reason=None,
        ocr_quality_note=None,
        executive_summary="I don't have enough evidence to generate an AI analysis right now — an unexpected error occurred. Please try again or contact support if this persists.",
        major_findings=[], safety_findings=[], quality_findings=[], schedule_findings=[],
        procurement_findings=[], equipment_issues=[], weather_impact="", blocked_activities=[],
        critical_risks=[], recommended_actions=[], priority_matrix=[], next_site_visit_focus=[],
        questions_for_site_team=[], contradictions=[],
        trend_analysis=TrendAnalysisOut(available=False, summary=None, signals=[]),
        confidence_score=0,
        risk_score_breakdown=RiskScoreBreakdownOut(total=0, level="Unknown", components=[]),
        priority_level="Unknown",
        escalation_required=False,
        section_sources=[],
        source_attribution=[],
    )


# ---------------------------------------------------------------------------
# Deterministic mapping: compact Hermes output -> the broader
# SiteReportAnalysisOut shape the frontend already knows how to render.
# Hermes itself never generates this broader shape (see
# site_report_reasoning.py's module docstring) — every section below is
# derived in plain Python from the 7-field compact result, satisfying
# "generate secondary UI sections deterministically where possible."
# ---------------------------------------------------------------------------

def _format_finding_line(item) -> str:
    if item.evidence_codes:
        return f"{item.statement} [{', '.join(item.evidence_codes)}]"
    return item.statement


def _findings_by_category(findings: list, category: str) -> list[str]:
    return [_format_finding_line(f) for f in findings if f.category == category]


# ---------------------------------------------------------------------------
# In-memory, process-local cache: if the same report is re-analyzed and its
# evidence hasn't changed, return the last completed analysis instantly
# instead of re-running Hermes. Deliberately NOT a new DB table/migration —
# a fingerprint of the formatted evidence block is enough to detect "the
# underlying data changed" without persisting anything. Lost on server
# restart and not shared across multiple worker processes — see the final
# report's limitations section; upgrading to a persisted cache is a small,
# separate follow-up if this deployment ever runs multiple workers.
# ---------------------------------------------------------------------------
_ANALYSIS_CACHE: dict[tuple[int, int], tuple[str, SiteReportAnalysisOut]] = {}


def _evidence_fingerprint(ev: ReportEvidence, risk) -> str:
    from app.ai.site_report_reasoning import _format_evidence_block
    raw = _format_evidence_block(ev, risk)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record_site_report_memory(db: Session, scope, project_id: int, report_id: int, ev, risk, out) -> None:
    """Best-effort — a memory write must never fail the /analyze request
    that produced it. Only called for a completed (not insufficient-
    evidence, not unavailable) reasoning result, so memory never records a
    "no analysis" placeholder as if it were a real one."""
    if scope is None:
        return
    try:
        from app.ai.memory_records import record_memory
        keywords = (
            ["site report", f"SR-{report_id}", risk.level]
            + [f.statement[:40] for f in out.key_findings[:3]]
            + [f.statement[:40] for f in out.critical_risks[:2]]
        )
        record_memory(
            db, scope,
            source="site_report", category="risk_report",
            title=f"SR-{report_id} — {ev.project.project_code} ({risk.level} risk, {risk.total}/100)",
            summary=out.executive_summary,
            keywords=[k for k in keywords if k],
            citation=f"SR-{report_id}",
            confidence=risk.total,
            project_id=project_id,
        )
    except Exception as exc:
        logger.warning("site_report_memory_write_failed report_id=%s error=%s", report_id, exc)


def analyze_site_report(db: Session, project_id: int, report_id: int, scope=None) -> SiteReportAnalysisOut:
    """The actual AI reasoning pipeline (POST .../analyze). One evidence
    gather, one deterministic risk score, one Hermes call.

    Only ValueError (report/project not found) propagates to the caller —
    every other exception is caught here and converted into a structured
    "unavailable" SiteReportAnalysisOut so the frontend never has to handle
    a bare 500 for this endpoint, and never sits waiting on a request that
    can only ever end in an opaque server error.

    scope: optional AIAuthScope, used only to attribute an automatic
    memory write of a completed analysis (see app/ai/memory_records.py) —
    not used for retrieval/authorization, which this endpoint has never
    enforced (see app/api/v1/site_reports.py)."""
    try:
        ev = gather_report_evidence(db, project_id, report_id)
        risk = compute_report_risk_score(ev)
    except ValueError:
        raise
    except Exception as exc:
        logger.error("site_report_evidence_gather_failed project_id=%s report_id=%s error=%s", project_id, report_id, exc, exc_info=True)
        return _unavailable_analysis_out(f"Evidence/risk computation failed: {type(exc).__name__}")

    # Cache check: if this exact report's evidence hasn't changed since the
    # last COMPLETED analysis, return it instantly — no Hermes call, no
    # deterministic re-computation needed beyond the fingerprint itself.
    # Never caches a fallback/unavailable/timed_out result, so a transient
    # Hermes failure is always retried on the next click rather than stuck.
    fingerprint = _evidence_fingerprint(ev, risk)
    cache_key = (project_id, report_id)
    cached = _ANALYSIS_CACHE.get(cache_key)
    if cached is not None and cached[0] == fingerprint:
        logger.info(
            "site_report_analysis_cache_hit project_id=%s report_id=%s",
            project_id, report_id,
        )
        return cached[1]

    total_start = time.monotonic()
    try:
        result = generate_report_reasoning(ev, risk)
    except Exception as exc:
        # generate_report_reasoning() already catches provider/validation
        # errors internally and returns status="unavailable"/"timed_out" —
        # reaching this except means something outside that contract broke
        # (e.g. a bug in evidence formatting). Evidence/risk are already
        # computed, so still return them instead of discarding real data.
        logger.error("site_report_reasoning_unexpected_failure project_id=%s report_id=%s error=%s", project_id, report_id, exc, exc_info=True)
        from app.ai.site_report_reasoning import ReasoningResult
        result = ReasoningResult(
            status="unavailable", output=None, provider=None, model_name=None,
            error_message=f"Unexpected reasoning failure: {type(exc).__name__}",
        )
    total_duration_ms = (time.monotonic() - total_start) * 1000

    risk_out = RiskScoreBreakdownOut(
        total=risk.total,
        level=risk.level,
        components=[
            RiskScoreComponentOut(
                key=c.key, label=c.label, occurrences=c.occurrences, points=c.points,
                max_points=c.max_points, rationale=c.rationale, evidence_refs=c.evidence_refs,
            )
            for c in risk.components
        ],
    )

    source_attribution = [
        AnalysisSourceOut(source_type=item.category, source_id=item.code, label=item.code, excerpt=_short(item.text))
        for item in ev.evidence_items[:25]
    ]
    section_sources = [
        AnalysisSectionSourceOut(section="Risk Score", sources=[c.key for c in risk.components if c.points > 0]),
        AnalysisSectionSourceOut(section="Executive Summary", sources=[i.code for i in ev.evidence_items[:8]]),
    ]

    logger.info(
        "site_report_analyze_timing project_id=%s report_id=%s "
        "evidence_before_count=%d evidence_after_count=%d prompt_length=%d "
        "provider=%s model=%s hermes_duration_ms=%.0f total_duration_ms=%.0f "
        "reasoning_status=%s fallback_used=%s",
        project_id, report_id, ev.evidence_before_count, len(ev.evidence_items),
        result.prompt_length, result.provider, result.model_name,
        result.hermes_duration_ms, total_duration_ms, result.status,
        result.status != "completed",
    )

    if result.status == "completed" and result.output is not None:
        out = result.output
        if not out.insufficient_evidence:
            _record_site_report_memory(db, scope, project_id, report_id, ev, risk, out)
        analysis_out = SiteReportAnalysisOut(
            analysis_generated_from=f"Hermes reasoning over {len(ev.evidence_items)} report-scoped evidence item(s).",
            reasoning_status="completed",
            reasoning_provider=result.provider,
            reasoning_model=result.model_name,
            reasoning_error=None,
            insufficient_evidence=out.insufficient_evidence,
            insufficient_evidence_reason=out.insufficient_evidence_reason,
            ocr_quality_note=ev.ocr_quality_notes[0] if ev.ocr_quality_notes else None,
            executive_summary=out.executive_summary,
            major_findings=[_format_finding_line(f) for f in out.key_findings],
            safety_findings=_findings_by_category(out.key_findings, "safety"),
            quality_findings=_findings_by_category(out.key_findings, "quality"),
            schedule_findings=_findings_by_category(out.key_findings, "schedule"),
            procurement_findings=_findings_by_category(out.key_findings, "procurement"),
            equipment_issues=_findings_by_category(out.key_findings, "equipment"),
            weather_impact="",
            blocked_activities=[],
            critical_risks=[_format_finding_line(f) for f in out.critical_risks],
            recommended_actions=[
                RecommendedActionOut(
                    action=a.statement, priority=a.priority, reason="",
                    evidence_refs=a.evidence_codes, expected_benefit="",
                )
                for a in out.recommended_actions
            ],
            priority_matrix=[],
            next_site_visit_focus=[],
            questions_for_site_team=list(out.missing_information),
            contradictions=[],
            trend_analysis=TrendAnalysisOut(
                available=bool(out.trend_summary), summary=out.trend_summary or None, signals=[],
            ),
            missing_information=list(out.missing_information),
            confidence_score=risk.total,
            risk_score_breakdown=risk_out,
            priority_level=risk.level,
            escalation_required=risk.total >= 45,
            section_sources=section_sources,
            source_attribution=source_attribution,
        )
        _ANALYSIS_CACHE[cache_key] = (fingerprint, analysis_out)
        return analysis_out

    # Reasoning unavailable/timed out — honest failure state, never a
    # keyword-template narrative pretending to be the AI's answer. Evidence
    # and risk score (both independent of Hermes) are still returned.
    is_timeout = result.status == "timed_out"
    return SiteReportAnalysisOut(
        analysis_generated_from=f"AI reasoning {'timed out' if is_timeout else 'unavailable'} — {len(ev.evidence_items)} evidence item(s) were retrieved but not analyzed.",
        reasoning_status=result.status,
        reasoning_provider=result.provider,
        reasoning_model=result.model_name,
        reasoning_error=result.error_message,
        insufficient_evidence=False,
        insufficient_evidence_reason=None,
        ocr_quality_note=ev.ocr_quality_notes[0] if ev.ocr_quality_notes else None,
        executive_summary=_TIMED_OUT_MESSAGE_EN if is_timeout else _UNAVAILABLE_MESSAGE_EN,
        major_findings=[],
        safety_findings=[],
        quality_findings=[],
        schedule_findings=[],
        procurement_findings=[],
        equipment_issues=[],
        weather_impact="",
        blocked_activities=[],
        critical_risks=[],
        recommended_actions=[],
        priority_matrix=[],
        next_site_visit_focus=[],
        questions_for_site_team=[],
        contradictions=[],
        trend_analysis=TrendAnalysisOut(available=False, summary=None, signals=[]),
        missing_information=[],
        confidence_score=risk.total,
        risk_score_breakdown=risk_out,
        priority_level=risk.level,
        escalation_required=risk.total >= 45,
        section_sources=section_sources,
        source_attribution=source_attribution,
    )
