from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.auth import UserAccount
from app.models.documents import Correspondence, Document, GeneratedDocument
from app.models.organizations import ProjectMembership
from app.models.projects import Project, ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from app.models.site import DailyActivity, SiteReport
from app.models.subcontractors import Subcontractor


_SENTENCE_SPLIT = re.compile(r"[\n\r]+|[.;]")
_DELAY_WORDS = (
    "delay",
    "delayed",
    "late",
    "behind",
    "slow",
    "hold",
    "stopp",
    "postpone",
)
_BLOCKER_WORDS = (
    "blocker",
    "blocked",
    "constraint",
    "permit",
    "approval",
    "material shortage",
    "access",
    "inspection pending",
    "awaiting",
)
_SAFETY_WORDS = (
    "safety",
    "incident",
    "near miss",
    "ppe",
    "hazard",
    "unsafe",
    "injury",
)
_QUALITY_WORDS = (
    "quality",
    "ncr",
    "defect",
    "rework",
    "snag",
    "nonconformance",
    "non-conformance",
)
_COMPLETION_WORDS = (
    "complete",
    "completed",
    "finished",
    "installed",
    "closed",
    "executed",
    "poured",
)
_EQUIPMENT_WORDS = (
    "crane",
    "excavator",
    "loader",
    "pump",
    "generator",
    "truck",
    "scaffold",
    "welding",
    "compactor",
    "lift",
    "bulldozer",
)
_MATERIAL_WORDS = (
    "concrete",
    "cement",
    "rebar",
    "steel",
    "aggregate",
    "sand",
    "asphalt",
    "block",
    "brick",
    "cable",
    "pipe",
    "membrane",
    "insulation",
)


@dataclass
class IntelligenceResult:
    report: dict
    analysis: dict


def _collect_sentences(texts: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    for text in texts:
        if not text:
            continue
        for chunk in _SENTENCE_SPLIT.split(text):
            cleaned = " ".join(chunk.split()).strip()
            if len(cleaned) >= 10:
                out.append(cleaned)
    return out


def _pick_by_keywords(lines: Iterable[str], words: tuple[str, ...], limit: int) -> list[str]:
    found: list[str] = []
    for line in lines:
        low = line.lower()
        if any(word in low for word in words):
            found.append(line)
        if len(found) >= limit:
            break
    return found


def _confidence_score(source_count: int, issue_count: int) -> int:
    score = 45 + min(source_count, 8) * 6 - min(issue_count, 4) * 3
    return max(35, min(95, score))


def _short(text: str, limit: int = 180) -> str:
    txt = " ".join(text.split())
    return txt if len(txt) <= limit else f"{txt[: limit - 3]}..."


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _severity_label(score: int) -> str:
    if score >= 8:
        return "Critical"
    if score >= 5:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def _extract_project_staff(db: Session, project_id: int) -> tuple[dict | None, dict | None]:
    memberships = (
        db.query(ProjectMembership, UserAccount)
        .join(UserAccount, UserAccount.id == ProjectMembership.user_id)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.is_active.is_(True),
        )
        .all()
    )

    engineer = None
    supervisor = None
    for membership, user in memberships:
        row = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role_on_project": membership.role_on_project,
        }
        role = (membership.role_on_project or "").lower()
        if engineer is None and role == "site_engineer":
            engineer = row
        if supervisor is None and role == "project_manager":
            supervisor = row

    if engineer is None:
        engineer = supervisor

    return engineer, supervisor


def list_site_report_cards(db: Session, project_id: int, skip: int = 0, limit: int = 20) -> list[dict]:
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
        .filter(
            DailyActivity.project_id == project_id,
            DailyActivity.site_report_id.in_(report_ids),
        )
        .all()
    )
    activities_by_report: dict[int, list[DailyActivity]] = defaultdict(list)
    for act in activities:
        activities_by_report[act.site_report_id].append(act)

    recent_safety = (
        db.query(SafetyEvent)
        .filter(SafetyEvent.project_id == project_id)
        .order_by(SafetyEvent.event_date.desc())
        .limit(5)
        .all()
    )
    open_ncr = (
        db.query(NCR)
        .filter(NCR.project_id == project_id, NCR.status != "Closed")
        .limit(10)
        .all()
    )
    open_issues = (
        db.query(ProjectIssue)
        .filter(ProjectIssue.project_id == project_id, ProjectIssue.status != "closed")
        .limit(20)
        .all()
    )

    safety_score = len([ev for ev in recent_safety if (ev.severity or "").lower() in ("high", "critical")])
    quality_score = len(open_ncr)
    risk_score = len(open_issues)

    cards: list[dict] = []
    for report in reports:
        report_activities = activities_by_report.get(report.id, [])
        lines = _collect_sentences([report.summary] + [a.activity_description for a in report_activities])
        completed = _pick_by_keywords(lines, _COMPLETION_WORDS, 20)
        delays = _pick_by_keywords(lines, _DELAY_WORDS, 20)
        blockers = _pick_by_keywords(lines, _BLOCKER_WORDS, 20)

        progress_text = (
            f"{len(completed)} completed activities from {len(report_activities)} activity logs"
            if report_activities
            else "No daily activity records linked"
        )

        card_risk_score = risk_score + len(delays) + len(blockers)
        card_safety_score = safety_score + len(_pick_by_keywords(lines, _SAFETY_WORDS, 10))
        card_quality_score = quality_score + len(_pick_by_keywords(lines, _QUALITY_WORDS, 10))

        cards.append(
            {
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
            }
        )

    return cards


def build_site_report_intelligence(db: Session, project_id: int, report_id: int) -> IntelligenceResult:
    report = (
        db.query(SiteReport)
        .filter(SiteReport.id == report_id, SiteReport.project_id == project_id)
        .first()
    )
    if not report:
        raise ValueError("Site report not found")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Project not found")

    activities = (
        db.query(DailyActivity)
        .filter(
            DailyActivity.project_id == project_id,
            DailyActivity.site_report_id == report_id,
        )
        .all()
    )

    engineer, supervisor = _extract_project_staff(db, project_id)

    manpower_by_subcontractor: dict[int, dict] = defaultdict(
        lambda: {"subcontractor_name": "Unknown", "workers": 0, "activity_count": 0}
    )

    if activities:
        subcontractor_ids = sorted({a.subcontractor_id for a in activities})
        subcontractors = (
            db.query(Subcontractor)
            .filter(Subcontractor.id.in_(subcontractor_ids))
            .all()
        )
        subcontractor_names = {s.id: s.name for s in subcontractors}

        for activity in activities:
            bucket = manpower_by_subcontractor[activity.subcontractor_id]
            bucket["subcontractor_name"] = subcontractor_names.get(
                activity.subcontractor_id,
                f"Subcontractor #{activity.subcontractor_id}",
            )
            bucket["workers"] += int(activity.manpower_count or 0)
            bucket["activity_count"] += 1

    manpower_breakdown = [
        {
            "subcontractor_id": sid,
            "subcontractor_name": data["subcontractor_name"],
            "workers": data["workers"],
            "activity_count": data["activity_count"],
        }
        for sid, data in sorted(
            manpower_by_subcontractor.items(),
            key=lambda kv: kv[1]["workers"],
            reverse=True,
        )
    ]

    total_workers = sum(item["workers"] for item in manpower_breakdown)

    activity_lines = _collect_sentences(a.activity_description for a in activities)
    summary_lines = _collect_sentences([report.summary])
    all_lines = summary_lines + activity_lines

    equipment_lines = _pick_by_keywords(all_lines, _EQUIPMENT_WORDS, 6)
    completed_work = _pick_by_keywords(all_lines, _COMPLETION_WORDS, 8)
    work_in_progress = [line for line in activity_lines if line not in completed_work][:8]
    delay_lines = _pick_by_keywords(all_lines, _DELAY_WORDS, 8)
    blocker_lines = _pick_by_keywords(all_lines, _BLOCKER_WORDS, 8)
    safety_lines = _pick_by_keywords(all_lines, _SAFETY_WORDS, 8)
    quality_lines = _pick_by_keywords(all_lines, _QUALITY_WORDS, 8)
    materials_used = _pick_by_keywords(all_lines, _MATERIAL_WORDS, 8)

    recent_safety = (
        db.query(SafetyEvent)
        .filter(SafetyEvent.project_id == project_id)
        .order_by(SafetyEvent.event_date.desc())
        .limit(3)
        .all()
    )
    recent_ncr = (
        db.query(NCR)
        .filter(NCR.project_id == project_id)
        .order_by(NCR.issue_date.desc())
        .limit(3)
        .all()
    )

    open_risks = (
        db.query(ProjectRisk)
        .filter(ProjectRisk.project_id == project_id, ProjectRisk.status != "closed")
        .limit(3)
        .all()
    )
    open_issues = (
        db.query(ProjectIssue)
        .filter(ProjectIssue.project_id == project_id, ProjectIssue.status != "closed")
        .limit(3)
        .all()
    )

    attachments = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.doc_date.desc())
        .limit(5)
        .all()
    )
    generated_documents = (
        db.query(GeneratedDocument)
        .filter(GeneratedDocument.project_id == project_id)
        .order_by(GeneratedDocument.document_date.desc())
        .limit(5)
        .all()
    )
    correspondence = (
        db.query(Correspondence)
        .filter(Correspondence.project_id == project_id)
        .order_by(Correspondence.sent_date.desc())
        .limit(5)
        .all()
    )

    for ev in recent_safety:
        safety_lines.append(f"[{ev.event_date}] {ev.severity} safety event: {ev.description}")
    for ncr in recent_ncr:
        quality_lines.append(
            f"[{ncr.issue_date}] NCR ({ncr.status}) {ncr.ncr_type}: {ncr.description}"
        )

    if not equipment_lines and activities:
        equipment_lines = [
            "No explicit equipment statement in report text; verify against activity logs and permits."
        ]
    if not completed_work and activities:
        completed_work = [
            "Daily activity records exist but completion statements are not explicit in text."
        ]

    delays = delay_lines or ["No explicit schedule delay stated in this report."]
    blockers = blocker_lines or ["No explicit blockers documented in this report."]
    safety_observations = safety_lines or ["No safety observations were explicitly logged."]
    quality_observations = quality_lines or ["No quality deviations were explicitly logged."]
    site_issue_rows = [f"[{i.created_at or 'N/A'}] {i.title} ({i.severity}, {i.status})" for i in open_issues]
    site_issues = _dedupe_keep_order(site_issue_rows + blocker_lines)
    if not site_issues:
        site_issues = ["No open site issues linked to this project report."]

    if not work_in_progress:
        work_in_progress = ["No explicit in-progress statements found in activity logs."]
    if not materials_used:
        materials_used = ["No explicit materials were identified in report/activity text."]

    source_attribution: list[dict] = [
        {
            "source_type": "site_report",
            "source_id": str(report.id),
            "label": f"Site Report SR-{report.id}",
            "excerpt": _short(report.summary),
        }
    ]

    for activity in activities[:5]:
        source_attribution.append(
            {
                "source_type": "daily_activity",
                "source_id": str(activity.id),
                "label": f"Daily Activity DA-{activity.id}",
                "excerpt": _short(activity.activity_description),
            }
        )

    for ev in recent_safety:
        source_attribution.append(
            {
                "source_type": "safety_event",
                "source_id": str(ev.id),
                "label": f"Safety Event SE-{ev.id}",
                "excerpt": _short(ev.description),
            }
        )

    for ncr in recent_ncr:
        source_attribution.append(
            {
                "source_type": "ncr",
                "source_id": str(ncr.id),
                "label": f"NCR-{ncr.id}",
                "excerpt": _short(ncr.description),
            }
        )

    issues_count = len(delay_lines) + len(blocker_lines) + len(recent_safety) + len(recent_ncr)
    confidence = _confidence_score(len(source_attribution), issues_count)

    escalation_required = (
        len(delay_lines) >= 2
        or any(ev.severity.lower() in ("high", "critical") for ev in recent_safety)
        or any((n.status or "").lower() not in ("closed", "resolved") for n in recent_ncr)
    )

    progress_assessment = (
        f"{len(activities)} activity records logged with total manpower of {total_workers}. "
        f"{len(completed_work)} completion indicators were identified from report text."
    )

    delay_analysis = (
        f"{len(delay_lines)} delay signal(s) and {len(blocker_lines)} blocker signal(s) were detected "
        "from report and activity narratives."
    )
    schedule_impact = (
        "Potential schedule slippage detected from delay/blocker notes. Recovery planning is recommended."
        if delay_lines or blocker_lines
        else "No direct schedule slippage indicators were found in this report data."
    )

    risk_terms = [r.title for r in open_risks if r.title] + [i.title for i in open_issues if i.title]
    risk_focus = ", ".join(risk_terms[:3]) if risk_terms else "No explicit open risk-register items tied to this report."
    risk_analysis = (
        f"Project-level open risks/issues reviewed: {risk_focus}. "
        f"Recent safety events: {len(recent_safety)}; recent NCRs: {len(recent_ncr)}."
    )

    recommended_actions: list[str] = []
    if delay_lines:
        recommended_actions.append("Issue a 72-hour recovery plan with revised crew and equipment allocation.")
    if blocker_lines:
        recommended_actions.append("Assign owners for each blocker and track closure in the next coordination meeting.")
    if recent_safety:
        recommended_actions.append("Close all open corrective actions from recent safety events before next major activity.")
    if recent_ncr:
        recommended_actions.append("Perform targeted quality inspection and close open NCR root causes.")
    if not recommended_actions:
        recommended_actions.append("Maintain current execution controls and continue daily verification checks.")

    priority_score = len(delay_lines) + len(blocker_lines) + len(recent_safety) * 2 + len(recent_ncr)
    priority_level = _severity_label(priority_score)

    executive_summary = (
        f"{project.project_code} {project.project_name}: report {report.report_date} indicates "
        f"{len(activities)} active workstreams under {report.weather.lower()} conditions. "
        f"Primary concerns: {len(delay_lines)} schedule-related and {len(recent_safety) + len(recent_ncr)} "
        "safety/quality signals."
    )

    analysis = {
        "analysis_generated_from": "Analysis generated from report data.",
        "executive_summary": executive_summary,
        "progress_assessment": progress_assessment,
        "delay_analysis": delay_analysis,
        "risk_analysis": risk_analysis,
        "safety_findings": safety_observations,
        "quality_findings": quality_observations,
        "schedule_impact": schedule_impact,
        "recommended_actions": recommended_actions,
        "priority_level": priority_level,
        "escalation_required": escalation_required,
        "confidence_score": confidence,
        "section_sources": [
            {
                "section": "Executive Summary",
                "sources": ["SiteReport.summary", "SiteReport.report_date", "DailyActivity.activity_description"],
            },
            {
                "section": "Progress Assessment",
                "sources": ["DailyActivity.manpower_count", "DailyActivity.activity_description"],
            },
            {
                "section": "Delay Analysis",
                "sources": ["SiteReport.summary", "DailyActivity.activity_description", "ProjectIssue"],
            },
            {
                "section": "Risk Analysis",
                "sources": ["ProjectRisk", "ProjectIssue", "SafetyEvent", "NCR"],
            },
            {
                "section": "Safety Findings",
                "sources": ["SiteReport.summary", "DailyActivity.activity_description", "SafetyEvent"],
            },
            {
                "section": "Quality Findings",
                "sources": ["SiteReport.summary", "DailyActivity.activity_description", "NCR"],
            },
            {
                "section": "Schedule Impact",
                "sources": ["SiteReport.summary", "DailyActivity.activity_description", "ProjectIssue"],
            },
            {
                "section": "Recommended Actions",
                "sources": ["Delay Analysis", "Risk Analysis", "Safety Findings", "Quality Findings"],
            },
            {
                "section": "Priority Level",
                "sources": ["Delay Analysis", "Safety Findings", "Quality Findings", "NCR.status"],
            },
            {
                "section": "Escalation Required",
                "sources": ["SafetyEvent.severity", "NCR.status", "Delay Analysis"],
            },
        ],
        "source_attribution": source_attribution,
    }

    photo_attachments = [
        {
            "source_type": doc.doc_type,
            "source_id": doc.id,
            "title": doc.title,
            "date": doc.doc_date,
        }
        for doc in attachments
        if any(key in (doc.doc_type or "").lower() or key in (doc.title or "").lower() for key in ("photo", "image", "snapshot", "site photo"))
    ]

    document_references = [
        {
            "source_type": doc.doc_type,
            "source_id": doc.id,
            "title": doc.title,
            "date": doc.doc_date,
        }
        for doc in attachments
    ] + [
        {
            "source_type": f"generated_{doc.type}",
            "source_id": doc.id,
            "title": doc.file_name,
            "date": doc.document_date,
        }
        for doc in generated_documents
    ] + [
        {
            "source_type": f"correspondence_{row.related_record_type}",
            "source_id": row.id,
            "title": row.subject,
            "date": row.sent_date,
        }
        for row in correspondence
    ]

    report_payload = {
        "report_id": report.id,
        "project_id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "engineer": engineer,
        "supervisor": supervisor,
        "report_date": report.report_date,
        "weather": report.weather,
        "temperature": None,
        "manpower": {
            "total_workers": total_workers,
            "subcontractor_breakdown": manpower_breakdown,
        },
        "equipment": equipment_lines,
        "completed_work": completed_work,
        "work_in_progress": work_in_progress,
        "materials_used": materials_used,
        "site_issues": site_issues,
        "delays": delays,
        "blockers": blockers,
        "recommendations": recommended_actions,
        "safety_observations": safety_observations,
        "quality_observations": quality_observations,
        "photos": photo_attachments,
        "attachments": [
            {
                "source_type": doc.doc_type,
                "source_id": doc.id,
                "title": doc.title,
                "date": doc.doc_date,
            }
            for doc in attachments
        ],
        "document_references": document_references,
        "raw_summary": report.summary,
    }

    return IntelligenceResult(report=report_payload, analysis=analysis)
