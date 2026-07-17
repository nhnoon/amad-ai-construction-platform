"""Site Report Intelligence — deterministic, report-scoped evidence retrieval.

This is the fix for the root cause of "every report looks the same": the
previous implementation queried safety events / NCRs / procurement / risks
by project_id only, ordered by date and capped at 3-5 rows — so every
report for a given project saw the exact same handful of "most recent"
rows regardless of when that report was actually filed. Two reports filed
two months apart, or the newest and oldest report on file, got identical
evidence.

Here, every date-bearing evidence type is scoped to a WINDOW specific to
this one report: (previous report's date, this report's date]. The first
report for a project (no predecessor) falls back to a configurable
lookback (SITE_REPORT_DEFAULT_LOOKBACK_DAYS). Two different reports for
the same project now structurally cannot see the same safety/NCR/
procurement/meeting/document evidence unless their windows genuinely
overlap (e.g. two reports filed the same day).

No LLM call happens in this module — it is pure, deterministic retrieval,
by design (see site_report_reasoning.py for the one Hermes call this
feeds). RBAC is not enforced here directly; callers (the API routes) are
responsible for authorization, matching the existing convention in this
codebase's retrieval layer.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.documents import Document
from app.models.document_ocr import DocumentOCRResult
from app.models.meetings import Meeting
from app.models.procurement import PurchaseOrder, PurchaseRequest
from app.models.projects import Project, ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from app.models.site import DailyActivity, SiteReport
from app.models.subcontractors import Subcontractor


def parse_report_date(value: Optional[str]) -> Optional[date]:
    """Defensive multi-format parser — these are free-text String columns
    (see app/models/site.py), not real date columns, so format isn't
    guaranteed consistent across seed/import sources."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class EvidenceItem:
    """One citable fact. `code` is what Hermes and the response schema use
    to reference this item (e.g. "SE-42", "NCR-7") — every finding the
    reasoning layer produces must trace back to one or more of these codes."""

    code: str
    category: str  # safety | quality | procurement | meeting | document | activity | risk | issue
    item_date: Optional[str]
    text: str
    href: Optional[str] = None


@dataclass
class PriorReportSnapshot:
    """A lightweight, deterministic summary of ONE earlier report's own
    evidence window — used only for trend comparison, never re-runs Hermes
    for prior reports (that would multiply the number of LLM calls per
    analysis; see the performance note in site_report_reasoning.py)."""

    report_id: int
    report_date: Optional[str]
    safety_event_count: int
    critical_safety_count: int
    open_ncr_count: int
    late_po_count: int
    blocked_activity_count: int
    subcontractor_ids: set[int]
    ncr_descriptions: list[str]
    safety_descriptions: list[str]


@dataclass
class ReportEvidence:
    report: SiteReport
    project: Project
    activities: list[DailyActivity]
    manpower_breakdown: list[dict]
    total_workers: int
    engineer: Optional[dict]
    supervisor: Optional[dict]

    window_start: Optional[date]
    window_end: Optional[date]
    is_first_report_for_project: bool

    safety_events: list[SafetyEvent]
    ncrs: list[NCR]
    purchase_orders: list[PurchaseOrder]
    purchase_requests: list[PurchaseRequest]
    meetings: list[Meeting]
    documents_with_ocr: list[tuple[Document, Optional[DocumentOCRResult]]]

    # Project-wide "current state" registers — NOT report-window-scoped,
    # since these tables have no per-event date to window against. Kept
    # separate from the above so the reasoning prompt can tell Hermes
    # explicitly which evidence is "as of this report's date range" and
    # which is "current portfolio state" — conflating the two was part of
    # why report-specific reasoning previously looked identical.
    open_project_risks: list[ProjectRisk]
    open_project_issues: list[ProjectIssue]

    prior_reports: list[PriorReportSnapshot]

    evidence_items: list[EvidenceItem] = field(default_factory=list)
    ocr_quality_notes: list[str] = field(default_factory=list)
    # Instrumentation only (see PERFORMANCE IMPLEMENTATION §2) — the row
    # count actually retrieved from the DB in-window, before per-domain
    # ranking/capping. Compared against len(evidence_items) to measure how
    # much the compaction step is actually reducing prompt size by.
    evidence_before_count: int = 0

    @property
    def subcontractor_ids_on_site(self) -> set[int]:
        return {a.subcontractor_id for a in self.activities}


def _extract_project_staff(db: Session, project_id: int) -> tuple[Optional[dict], Optional[dict]]:
    from app.models.auth import UserAccount
    from app.models.organizations import ProjectMembership

    memberships = (
        db.query(ProjectMembership, UserAccount)
        .join(UserAccount, UserAccount.id == ProjectMembership.user_id)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.is_active.is_(True))
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


def _window_for_report(
    db: Session, project_id: int, report: SiteReport
) -> tuple[Optional[date], Optional[date], bool]:
    """(window_start, window_end, is_first_report). window_start is
    EXCLUSIVE (evidence dated on the previous report's own date belongs to
    THAT report, not this one); window_end is INCLUSIVE."""
    window_end = parse_report_date(report.report_date)

    prior_reports = (
        db.query(SiteReport)
        .filter(SiteReport.project_id == project_id, SiteReport.id != report.id)
        .all()
    )
    prior_with_dates = [
        (r, parse_report_date(r.report_date)) for r in prior_reports
    ]
    prior_with_dates = [(r, d) for r, d in prior_with_dates if d is not None]

    if window_end is not None:
        earlier = [(r, d) for r, d in prior_with_dates if d < window_end]
    else:
        # report_date itself didn't parse — fall back to id ordering so we
        # still get a deterministic, report-specific (not just
        # project-wide) predecessor rather than treating every unparsable
        # report as "first".
        earlier = [(r, d) for r, d in prior_with_dates if r.id < report.id]

    if not earlier:
        if window_end is not None:
            return window_end - timedelta(days=settings.SITE_REPORT_DEFAULT_LOOKBACK_DAYS), window_end, True
        return None, None, True

    prev_report, prev_date = max(earlier, key=lambda rd: rd[1])
    return prev_date, window_end, False


def _in_window(d: Optional[date], window_start: Optional[date], window_end: Optional[date]) -> bool:
    """Unparsable dates are excluded from window-scoped evidence rather
    than defaulting to "include" — silently including undated items would
    reintroduce exactly the kind of unscoped, always-present evidence this
    module exists to eliminate."""
    if d is None or window_end is None:
        return False
    if window_start is not None and not (window_start < d <= window_end):
        return False
    if window_start is None and d > window_end:
        return False
    return True


def _prior_report_snapshot(
    db: Session, project_id: int, report: SiteReport
) -> PriorReportSnapshot:
    w_start, w_end, _ = _window_for_report(db, project_id, report)

    safety = [
        ev for ev in db.query(SafetyEvent).filter(SafetyEvent.project_id == project_id).all()
        if _in_window(parse_report_date(ev.event_date), w_start, w_end)
    ]
    ncrs = [
        n for n in db.query(NCR).filter(NCR.project_id == project_id).all()
        if _in_window(parse_report_date(n.issue_date), w_start, w_end)
    ]
    pos = [
        po for po in db.query(PurchaseOrder).filter(PurchaseOrder.project_id == project_id).all()
        if _in_window(parse_report_date(po.promised_delivery), w_start, w_end)
    ]
    activities = (
        db.query(DailyActivity)
        .filter(DailyActivity.project_id == project_id, DailyActivity.site_report_id == report.id)
        .all()
    )
    blocked = [a for a in activities if _looks_blocked(a.activity_description)]

    return PriorReportSnapshot(
        report_id=report.id,
        report_date=report.report_date,
        safety_event_count=len(safety),
        critical_safety_count=len([s for s in safety if (s.severity or "").lower() in ("critical", "high")]),
        open_ncr_count=len([n for n in ncrs if (n.status or "").lower() not in ("closed", "resolved")]),
        late_po_count=len([po for po in pos if po.is_late]),
        blocked_activity_count=len(blocked),
        subcontractor_ids={a.subcontractor_id for a in activities},
        ncr_descriptions=[n.description for n in ncrs if n.description],
        safety_descriptions=[s.description for s in safety if s.description],
    )


_BLOCKER_WORDS = (
    "blocked", "blocker", "pending inspection", "awaiting", "on hold",
    "cannot proceed", "stopped", "material shortage", "access denied",
)


def _looks_blocked(text: Optional[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(w in low for w in _BLOCKER_WORDS)


# ---------------------------------------------------------------------------
# Evidence compaction — per-domain caps, applied to the raw rows BEFORE they
# become EvidenceItems, so the prompt Hermes receives is bounded regardless
# of how large a report's window happens to be. Window-scoping (above) fixed
# "every report looks the same"; this fixes "a busy 2-week window sends 40
# rows to a 7B model and pushes generation time past several minutes."
# Ranking favors what a human reviewer would actually look at first:
# severity/unresolved status, then recency — never an arbitrary DB order.
# ---------------------------------------------------------------------------

_MAX_SAFETY_EVIDENCE = 3
_MAX_NCR_EVIDENCE = 3
_MAX_PROCUREMENT_EVIDENCE = 3
_MAX_MEETING_EVIDENCE = 2
_MAX_DOCUMENT_EVIDENCE = 3

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _severity_rank(value: Optional[str]) -> int:
    return _SEVERITY_RANK.get((value or "").lower(), 0)


def _date_sort_key(value: Optional[str]) -> date:
    parsed = parse_report_date(value)
    return parsed or date.min


def _rank_safety_events(events: list[SafetyEvent]) -> list[SafetyEvent]:
    return sorted(
        events,
        key=lambda e: (_severity_rank(e.severity), _date_sort_key(e.event_date)),
        reverse=True,
    )[:_MAX_SAFETY_EVIDENCE]


def _rank_ncrs(ncrs: list[NCR]) -> list[NCR]:
    def _key(n: NCR):
        unresolved = (n.status or "").lower() not in ("closed", "resolved")
        return (unresolved, _date_sort_key(n.issue_date))
    return sorted(ncrs, key=_key, reverse=True)[:_MAX_NCR_EVIDENCE]


def _rank_procurement(
    purchase_orders: list[PurchaseOrder], purchase_requests: list[PurchaseRequest]
) -> tuple[list[PurchaseOrder], list[PurchaseRequest]]:
    """Late POs and pending PRs are what a reviewer needs to see first —
    ranked together, then split back into their own lists, capped at a
    combined total of _MAX_PROCUREMENT_EVIDENCE."""
    po_scored = [(po, (1 if po.is_late else 0, po.delay_days or 0)) for po in purchase_orders]
    po_scored.sort(key=lambda t: t[1], reverse=True)
    pr_pending_statuses = {"pending clarification", "under review", "needs rework", "returned to requester"}
    pr_scored = [(pr, 1 if (pr.status or "").lower() in pr_pending_statuses else 0) for pr in purchase_requests]
    pr_scored.sort(key=lambda t: t[1], reverse=True)

    kept_pos: list[PurchaseOrder] = []
    kept_prs: list[PurchaseRequest] = []
    remaining = _MAX_PROCUREMENT_EVIDENCE
    for po, _ in po_scored:
        if remaining <= 0:
            break
        kept_pos.append(po)
        remaining -= 1
    for pr, _ in pr_scored:
        if remaining <= 0:
            break
        kept_prs.append(pr)
        remaining -= 1
    return kept_pos, kept_prs


def _rank_meetings(meetings: list[Meeting]) -> list[Meeting]:
    return sorted(meetings, key=lambda m: _date_sort_key(m.meeting_date), reverse=True)[:_MAX_MEETING_EVIDENCE]


def build_trend_snapshot(prior_reports: list[PriorReportSnapshot]) -> Optional[str]:
    """One compact trend line summarizing however many prior reports exist,
    replacing what used to be one full line PER prior report (up to
    SITE_REPORT_TREND_LOOKBACK_REPORTS separate lines) — same information
    density for trend reasoning, far fewer prompt characters. Returns None
    when there are no prior reports (first report for the project)."""
    if not prior_reports:
        return None
    # prior_reports is already ordered most-recent-first (see the query in
    # gather_report_evidence) — reverse to oldest-first so a reader sees
    # the trend running left-to-right in chronological order.
    ordered = list(reversed(prior_reports))
    safety = ",".join(str(p.safety_event_count) for p in ordered)
    ncr = ",".join(str(p.open_ncr_count) for p in ordered)
    late_po = ",".join(str(p.late_po_count) for p in ordered)
    blocked = ",".join(str(p.blocked_activity_count) for p in ordered)
    dates = ",".join(p.report_date or "undated" for p in ordered)
    return (
        f"Trend across last {len(ordered)} prior report(s) ({dates}, oldest first): "
        f"safety events [{safety}], open NCRs [{ncr}], late POs [{late_po}], "
        f"blocked activities [{blocked}]."
    )


def _rank_documents(
    documents_with_ocr: list[tuple[Document, Optional[DocumentOCRResult]]]
) -> list[tuple[Document, Optional[DocumentOCRResult]]]:
    """Documents with real, completed OCR text are more useful to reasoning
    than ones with only a stored summary or a failed extraction — ranked
    ahead, then by recency."""
    def _key(pair):
        doc, ocr = pair
        has_text = 1 if (ocr is not None and ocr.status == "completed" and ocr.extracted_text) else 0
        return (has_text, _date_sort_key(doc.doc_date))
    return sorted(documents_with_ocr, key=_key, reverse=True)[:_MAX_DOCUMENT_EVIDENCE]


def gather_report_evidence(db: Session, project_id: int, report_id: int) -> ReportEvidence:
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
        .filter(DailyActivity.project_id == project_id, DailyActivity.site_report_id == report_id)
        .all()
    )

    engineer, supervisor = _extract_project_staff(db, project_id)

    manpower_by_sub: dict[int, dict] = defaultdict(lambda: {"subcontractor_name": "Unknown", "workers": 0, "activity_count": 0})
    if activities:
        sub_ids = sorted({a.subcontractor_id for a in activities})
        subs = db.query(Subcontractor).filter(Subcontractor.id.in_(sub_ids)).all()
        sub_names = {s.id: s.name for s in subs}
        for a in activities:
            bucket = manpower_by_sub[a.subcontractor_id]
            bucket["subcontractor_name"] = sub_names.get(a.subcontractor_id, f"Subcontractor #{a.subcontractor_id}")
            bucket["workers"] += int(a.manpower_count or 0)
            bucket["activity_count"] += 1
    manpower_breakdown = [
        {"subcontractor_id": sid, **data}
        for sid, data in sorted(manpower_by_sub.items(), key=lambda kv: kv[1]["workers"], reverse=True)
    ]
    total_workers = sum(m["workers"] for m in manpower_breakdown)

    window_start, window_end, is_first = _window_for_report(db, project_id, report)

    safety_events = [
        ev for ev in db.query(SafetyEvent).filter(SafetyEvent.project_id == project_id).all()
        if _in_window(parse_report_date(ev.event_date), window_start, window_end)
    ]
    ncrs = [
        n for n in db.query(NCR).filter(NCR.project_id == project_id).all()
        if _in_window(parse_report_date(n.issue_date), window_start, window_end)
    ]
    purchase_orders = [
        po for po in db.query(PurchaseOrder).filter(PurchaseOrder.project_id == project_id).all()
        if _in_window(parse_report_date(po.promised_delivery), window_start, window_end)
        or _in_window(parse_report_date(po.actual_delivery), window_start, window_end)
    ]
    purchase_requests = [
        pr for pr in db.query(PurchaseRequest).filter(PurchaseRequest.project_id == project_id).all()
        if _in_window(parse_report_date(pr.required_delivery_date), window_start, window_end)
    ]
    meetings = [
        m for m in db.query(Meeting).filter(Meeting.project_id == project_id).all()
        if _in_window(parse_report_date(m.meeting_date), window_start, window_end)
    ]

    documents = [
        d for d in db.query(Document).filter(Document.project_id == project_id).all()
        if _in_window(parse_report_date(d.doc_date), window_start, window_end)
    ]
    ocr_by_doc: dict[int, DocumentOCRResult] = {}
    if documents:
        doc_ids = [d.id for d in documents]
        for ocr in db.query(DocumentOCRResult).filter(DocumentOCRResult.document_id.in_(doc_ids)).all():
            ocr_by_doc[ocr.document_id] = ocr
    documents_with_ocr = [(d, ocr_by_doc.get(d.id)) for d in documents]

    # Instrumentation: total in-window rows before per-domain ranking/caps.
    evidence_before_count = (
        len(safety_events) + len(ncrs) + len(purchase_orders) + len(purchase_requests)
        + len(meetings) + len(documents_with_ocr)
    )

    # Compaction: rank each domain and cap to a strict limit BEFORE building
    # EvidenceItems, so the prompt Hermes receives is bounded regardless of
    # how many rows a busy report's window contains — see the ranking
    # helpers above (_rank_safety_events etc.) for the per-domain criteria.
    safety_events = _rank_safety_events(safety_events)
    ncrs = _rank_ncrs(ncrs)
    purchase_orders, purchase_requests = _rank_procurement(purchase_orders, purchase_requests)
    meetings = _rank_meetings(meetings)
    documents_with_ocr = _rank_documents(documents_with_ocr)

    open_project_risks = (
        db.query(ProjectRisk).filter(ProjectRisk.project_id == project_id, ProjectRisk.status != "closed").limit(5).all()
    )
    open_project_issues = (
        db.query(ProjectIssue).filter(ProjectIssue.project_id == project_id, ProjectIssue.status != "closed").limit(5).all()
    )

    prior_report_rows = (
        db.query(SiteReport)
        .filter(SiteReport.project_id == project_id, SiteReport.id != report_id)
        .order_by(SiteReport.report_date.desc())
        .limit(settings.SITE_REPORT_TREND_LOOKBACK_REPORTS)
        .all()
    )
    prior_reports = [_prior_report_snapshot(db, project_id, r) for r in prior_report_rows]

    evidence = ReportEvidence(
        report=report,
        project=project,
        activities=activities,
        manpower_breakdown=manpower_breakdown,
        total_workers=total_workers,
        engineer=engineer,
        supervisor=supervisor,
        window_start=window_start,
        window_end=window_end,
        is_first_report_for_project=is_first,
        safety_events=safety_events,
        ncrs=ncrs,
        purchase_orders=purchase_orders,
        purchase_requests=purchase_requests,
        meetings=meetings,
        documents_with_ocr=documents_with_ocr,
        open_project_risks=open_project_risks,
        open_project_issues=open_project_issues,
        prior_reports=prior_reports,
        evidence_before_count=evidence_before_count,
    )
    _build_evidence_items(evidence)
    return evidence


def _build_evidence_items(ev: ReportEvidence) -> None:
    items = ev.evidence_items

    items.append(EvidenceItem(
        code=f"SR-{ev.report.id}",
        category="report",
        item_date=ev.report.report_date,
        text=f"Site report SR-{ev.report.id} for {ev.project.project_code}, weather: {ev.report.weather}. Summary: {ev.report.summary}",
        href="/site-reports",
    ))

    for a in ev.activities:
        items.append(EvidenceItem(
            code=f"DA-{a.id}",
            category="activity",
            item_date=a.activity_date,
            text=f"Daily activity DA-{a.id} (subcontractor #{a.subcontractor_id}, {a.manpower_count} workers): {a.activity_description}",
        ))

    for s in ev.safety_events:
        items.append(EvidenceItem(
            code=f"SE-{s.id}",
            category="safety",
            item_date=s.event_date,
            text=f"Safety event SE-{s.id} ({s.severity}): {s.description}. Corrective action: {s.corrective_action}",
            href="/safety",
        ))

    for n in ev.ncrs:
        items.append(EvidenceItem(
            code=f"NCR-{n.id}",
            category="quality",
            item_date=n.issue_date,
            text=f"NCR-{n.id} ({n.status}, type={n.ncr_type}): {n.description}. Root cause: {n.root_cause}",
            href="/safety",
        ))

    for po in ev.purchase_orders:
        late_note = f"LATE by {po.delay_days} day(s)" if po.is_late else "on schedule"
        items.append(EvidenceItem(
            code=f"PO-{po.id}",
            category="procurement",
            item_date=po.promised_delivery,
            text=f"Purchase order PO-{po.id} ({po.status}, {late_note}): promised {po.promised_delivery}, actual {po.actual_delivery or 'not delivered'}."
            + (f" Delay root cause: {po.delay_root_cause}" if po.delay_root_cause else ""),
            href="/procurement",
        ))

    for pr in ev.purchase_requests:
        items.append(EvidenceItem(
            code=f"PR-{pr.id}",
            category="procurement",
            item_date=pr.required_delivery_date,
            text=f"Purchase request PR-{pr.id} ({pr.status}) for {pr.material_category}: required by {pr.required_delivery_date}.",
            href="/procurement",
        ))

    for m in ev.meetings:
        items.append(EvidenceItem(
            code=f"MTG-{m.id}",
            category="meeting",
            item_date=m.meeting_date,
            text=f"Meeting MTG-{m.id} ({m.meeting_type}): {m.title}",
            href="/meetings",
        ))

    for doc, ocr in ev.documents_with_ocr:
        if ocr is not None and ocr.status == "completed" and ocr.extracted_text:
            excerpt = ocr.extracted_text[:300]
            items.append(EvidenceItem(
                code=f"DOC-{doc.id}",
                category="document",
                item_date=doc.doc_date,
                text=f"Document DOC-{doc.id} ({doc.title}, OCR text): {excerpt}",
                href="/documents",
            ))
            if (ocr.confidence is not None and ocr.confidence < 0.6) or len(ocr.extracted_text.strip()) < 40:
                ev.ocr_quality_notes.append(
                    f"OCR text for DOC-{doc.id} ({doc.title}) is short or low-confidence "
                    f"(confidence={ocr.confidence}); treat its content as uncertain."
                )
        elif ocr is not None and ocr.status == "failed":
            ev.ocr_quality_notes.append(f"OCR failed for DOC-{doc.id} ({doc.title}): {ocr.error_message or 'unknown error'}.")
            items.append(EvidenceItem(
                code=f"DOC-{doc.id}",
                category="document",
                item_date=doc.doc_date,
                text=f"Document DOC-{doc.id} ({doc.title}): OCR text unavailable (extraction failed). Summary on file: {doc.content_summary}",
            ))
        else:
            items.append(EvidenceItem(
                code=f"DOC-{doc.id}",
                category="document",
                item_date=doc.doc_date,
                text=f"Document DOC-{doc.id} ({doc.title}): {doc.content_summary}",
            ))

    for r in ev.open_project_risks:
        items.append(EvidenceItem(
            code=f"RISK-{r.id}",
            category="risk",
            item_date=None,
            text=f"Open project risk RISK-{r.id} ({r.status}, probability={r.probability}, impact={r.impact}): {r.title}. Mitigation: {r.mitigation}",
        ))

    for i in ev.open_project_issues:
        items.append(EvidenceItem(
            code=f"ISSUE-{i.id}",
            category="issue",
            item_date=None,
            text=f"Open project issue ISSUE-{i.id} ({i.severity}, {i.status}): {i.title}",
        ))
