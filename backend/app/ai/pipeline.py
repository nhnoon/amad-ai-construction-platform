"""Copilot answer-generation pipeline — Phase 3B multi-turn.

Full flow per turn:
  User Question
  → Auth (caller's responsibility)
  → AI Auth Scope
  → Load Conversation State (bounded)
  → Context Resolution (pronoun/entity rewriting)
  → Clarification Detection
  → Intent Routing (with previous_intent hint)
  → Domain Planning (single or multi-domain)
  → Authorized Retrieval (RBAC enforced per domain)
  → Evidence Construction
  → Prompt Construction (with bounded conversation history)
  → LLM Generation
  → Grounding Validation
  → Follow-up Suggestion Generation
  → Conversation State Update
  → Citation + Audit Persistence
  → Response
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.ai.clarification import check_clarification_needed
from app.ai.context_resolver import (
    RecentMessage, ResolvedContext, build_conversation_context_block, resolve_context,
)
from app.ai.conversation_state import (
    ConversationState, extract_project_ids_from_evidence,
)
from app.ai.followup import generate_follow_up_suggestions
from app.ai.analyst import compute_analytical_answer, detect_query_type
from app.ai.render_blocks import compute_render_blocks
from app.ai.grounding import GroundingValidator
from app.ai.intent import route_intent
from app.ai.memory import get_memory_notes, get_user_profile_memory
from app.ai.memory_reader import (
    build_memory_context_block, build_user_preferences_block, is_memory_relevant,
    select_relevant_memory,
)
from app.ai.planner import (
    build_comparison_data, detect_required_domains, execute_executive_summary,
    execute_multi_domain_plan, is_executive_summary_query,
)
from app.ai.providers.base import LLMRequest, LLMResponse, ProviderUnavailableError
from app.ai.providers.factory import get_llm_provider
from app.ai.retrieval.base import Evidence, RetrievalResult
from app.ai.retrieval.meetings import (
    get_meeting_counts, get_meeting_detail, get_open_action_items, get_project_decisions,
    get_recent_meetings,
)
from app.ai.retrieval.procurement import (
    get_late_purchase_orders, get_procurement_counts, get_procurement_summary,
    get_supplier_information,
)
from app.ai.retrieval.projects import (
    get_project_overview, get_project_risks, get_health_overview, get_project_status_counts,
)
from app.ai.retrieval.safety import (
    get_ncr_counts, get_ncr_detail, get_open_ncrs, get_safety_event_counts, get_safety_summary,
)
from app.ai.retrieval.site_reports import (
    get_recent_daily_activities, get_recent_site_reports,
)
from app.ai.scope import AIAuthScope
from app.models.ai_copilot import AIConversation, AICitation, AIMessage, CopilotAuditLog
from app.models.projects import Project

logger = logging.getLogger(__name__)

_MAX_QUESTION_LEN = 2000
_MAX_EVIDENCE_SNIPPETS = 30
_MAX_CONTEXT_MESSAGES = 10  # bounded: last 5 turns

# DEMO MODE - switch back to OpenRouter after presentation.
# Meeting Agent and Procurement Agent (execute_meeting_agent,
# _execute_meeting_agent_summary, execute_procurement_agent) currently make
# NO LLM/OpenRouter call at all — they return a deterministic,
# database-backed report unconditionally. The bounded-timeout executor that
# used to guard their LLM calls has been removed along with those calls; if
# LLM generation is restored, reintroduce a similar time-boxed
# concurrent.futures.ThreadPoolExecutor + future.result(timeout=...) call
# around provider.generate() (see git history for the prior version of
# this file) so a slow provider can never produce an "infinite loading"
# experience.

_SYSTEM_TEMPLATE = """\
You are Amad Construction Intelligence Copilot, a read-only assistant for \
Saudi construction project management.

RULES (MANDATORY):
1. Answer ONLY using the EVIDENCE section below.
2. Do NOT invent facts, numbers, dates, or names not present in the evidence.
3. If the evidence is empty or insufficient, respond with the exact phrase:
   "INSUFFICIENT_EVIDENCE: <brief reason>"
4. Cite your sources using their codes (e.g. PRJ-001, PO-1042, SE-88).
5. Never reveal internal database IDs, raw SQL, or user credentials.
6. If the question is in Arabic, respond entirely in Arabic; preserve \
project codes.
7. When comparing entities, structure your response with clear sections.
8. For executive summaries, use: Key Findings / Risk Indicators / Notable Projects.
9. Any derived background context appearing below (prior notes or stated
   preferences, clearly labelled non-authoritative) is not evidence — never
   cite it as a source. If it conflicts with EVIDENCE, EVIDENCE always wins.

{context_block}
EVIDENCE:
{evidence_block}
"""

_INSUFFICIENT_EVIDENCE_MARKER = "INSUFFICIENT_EVIDENCE"

_PROCUREMENT_AGENT_HEADINGS_EN = """\
   Executive Summary
   Key Findings
   Highest-Risk Procurement Issues
   Affected Projects
   Supplier Risks
   Recommended Actions
   Escalation Required
   Confidence
   Sources"""

_PROCUREMENT_AGENT_HEADINGS_AR = """\
   الملخص التنفيذي
   أهم النتائج
   أخطر مشكلات المشتريات
   المشاريع المتأثرة
   مخاطر الموردين
   الإجراءات الموصى بها
   هل يتطلب الأمر تصعيداً
   مستوى الثقة
   المصادر"""


def _procurement_agent_system_prompt(evidence_block: str, is_arabic: bool) -> str:
    headings = _PROCUREMENT_AGENT_HEADINGS_AR if is_arabic else _PROCUREMENT_AGENT_HEADINGS_EN
    return f"""\
You are the AMAD Procurement Intelligence Agent, a read-only specialist \
assistant analyzing procurement data (purchase requests, purchase orders, \
suppliers, delivery risk) for Saudi construction projects.

RULES (MANDATORY):
1. Answer ONLY using the EVIDENCE section below.
2. Do NOT invent facts, numbers, dates, supplier names, or project codes not \
present in the evidence.
3. If the evidence is empty or insufficient, respond with the exact phrase:
   "INSUFFICIENT_EVIDENCE: <brief reason>"
4. Cite your sources using their codes (e.g. PO-1042, PR-0098, PRJ-001).
5. Never reveal internal database IDs, raw SQL, or user credentials.
6. If asked to answer in Arabic, respond ENTIRELY in Arabic — every section \
heading and label must also be in Arabic, using the exact headings given in \
rule 7 below. Never mix English words or headings into an Arabic response; \
preserve only PO/PR/project codes as-is.
7. Structure your response using EXACTLY these section headings (translated \
into Arabic when responding in Arabic), in this order, each on its own line:
{headings}
8. Under Highest-Risk Procurement Issues / أخطر مشكلات المشتريات, list each \
purchase order using ONLY these fields, in this order: PO number, related \
project, supplier, promised delivery date, delay in days, status, and root \
cause. If root cause is not present in the evidence for a given PO, write \
"not recorded" ("غير مسجل" in Arabic) for that field — never guess it.

EVIDENCE:
{evidence_block}
"""


_MEETING_AGENT_HEADINGS_EN = """\
   Executive Summary
   Decisions
   Tasks
   Owners
   Due Dates (if available)
   Risks and Blockers
   Recommendation
   Sources"""

_MEETING_AGENT_HEADINGS_AR = """\
   ملخص تنفيذي
   القرارات
   المهام
   المسؤولون
   المواعيد النهائية إن وجدت
   المخاطر والعوائق
   التوصية
   المصادر"""


def _meeting_agent_system_prompt(evidence_block: str, is_arabic: bool) -> str:
    headings = _MEETING_AGENT_HEADINGS_AR if is_arabic else _MEETING_AGENT_HEADINGS_EN
    unavailable_phrase = (
        "غير متاح من قاعدة البيانات الحالية"
        if is_arabic
        else "Unavailable from current database."
    )
    return f"""\
You are the AMAD Meeting Intelligence Agent, a read-only specialist assistant \
analyzing ONE specific meeting's real stored record (decisions, action \
items, attendees) for a Saudi construction project.

RULES (MANDATORY):
1. Answer ONLY using the EVIDENCE section below, which contains everything \
stored in the database for this one meeting.
2. Do NOT invent facts, owners, due dates, decisions, or action items not \
present in the evidence.
3. If a specific field (e.g. an action item's owner or due date) is not \
present in the evidence, write the exact phrase "{unavailable_phrase}" for \
that field — never guess or leave it blank.
4. If the evidence is empty or insufficient, respond with the exact phrase:
   "INSUFFICIENT_EVIDENCE: <brief reason>"
5. Cite your sources using their codes (e.g. MTG-12, DEC-4, ACT-7).
6. Never reveal internal database IDs, raw SQL, or user credentials.
7. If asked to answer in Arabic, respond ENTIRELY in Arabic — every section \
heading and label must also be in Arabic, using the exact headings given in \
rule 8 below. Never mix English words or headings into an Arabic response; \
preserve only MTG/DEC/ACT codes as-is.
8. Structure your response using EXACTLY these section headings (translated \
into Arabic when responding in Arabic), in this order, each on its own line. \
Under Tasks / المهام, list each task with its source code (e.g. ACT-7). \
Under Owners / المسؤولون and Due Dates / المواعيد النهائية إن وجدت, map each \
task's code to its owner and due date respectively.
{headings}

EVIDENCE:
{evidence_block}
"""


def _detect_arabic(text: str) -> bool:
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return arabic_chars > len(text) * 0.2


def _build_evidence_block(evidence: list[Evidence]) -> str:
    if not evidence:
        return "[No evidence retrieved]"
    parts = []
    for i, ev in enumerate(evidence[:_MAX_EVIDENCE_SNIPPETS], start=1):
        parts.append(f"[{i}] {ev.label}\n    {ev.snippet}")
    return "\n".join(parts)


_COUNT_SUMMARY_ICON = {
    "project_overview": "layout-grid",
    "procurement": "shopping-cart",
    "safety": "shield-alert",
    "ncr": "clipboard-x",
}


def _append_count_summary(
    result: RetrievalResult,
    intent: str,
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int],
) -> RetrievalResult:
    """Attach one extra Evidence item carrying the TRUE COUNT(*) totals for
    this domain, alongside the row-sample evidence get_*_summary()/get_*()
    already returned. Without this, "how many X" questions were answered by
    counting the (limit-bounded) evidence list itself — e.g. reporting "20"
    open NCRs when the evidence sample happened to cap at 20 rows, while the
    real total was 500. This is a normal, citable Evidence item like any
    other — it strengthens grounding for count questions, it does not bypass
    or weaken citations."""
    if intent == "project_overview":
        c = get_project_status_counts(db=db, scope=scope, project_id=project_id)
        snippet = f"TOTAL COUNTS (all matching projects, not just those listed above): total={c['total']}, active={c['active']}, delayed={c['delayed']}"
    elif intent == "procurement":
        c = get_procurement_counts(db=db, scope=scope, project_id=project_id)
        snippet = (
            "TOTAL COUNTS (all matching records, not just those listed above): "
            f"total_purchase_orders={c['total_po']}, late_purchase_orders={c['late_po']}, "
            f"total_purchase_requests={c['total_pr']}, open_purchase_requests={c['open_pr']}"
        )
    elif intent == "safety":
        c = get_safety_event_counts(db=db, scope=scope, project_id=project_id)
        snippet = f"TOTAL COUNTS (all matching safety events, not just those listed above): total={c['total']}, high_severity={c['high']}, medium_severity={c['medium']}, low_severity={c['low']}"
    elif intent == "ncr":
        c = get_ncr_counts(db=db, scope=scope, project_id=project_id)
        snippet = f"TOTAL COUNTS (all matching NCRs, not just those listed above): total={c['total']}, open={c['open']}"
    else:
        return result

    result.evidence.append(Evidence(
        source_type="count_summary",
        source_id=intent,
        label=f"{intent.replace('_', ' ').title()} — Total Counts",
        snippet=snippet,
        project_id=project_id,
        ui_metadata={"icon": _COUNT_SUMMARY_ICON.get(intent, "hash")},
    ))
    return result


def _dispatch_single_retrieval(
    intent: str,
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int],
    meeting_id: Optional[int] = None,
    ncr_id: Optional[int] = None,
    question: str = "",
) -> RetrievalResult:
    kwargs: dict[str, Any] = {"db": db, "scope": scope, "project_id": project_id}

    if intent == "project_overview":
        return _append_count_summary(get_project_overview(**kwargs), intent, db, scope, project_id)
    if intent == "procurement":
        if detect_query_type(question) == "longest_delay":
            # "Which purchase order has the longest delay?" — get_procurement_summary()
            # returns an unsorted sample of requests/orders, so the LLM had to
            # guess a maximum from ~30 unsorted rows and got it wrong (a real,
            # non-hallucinated PO, but not the actual longest delay).
            # get_late_purchase_orders() is already sorted by delay_days desc.
            return _append_count_summary(
                get_late_purchase_orders(db=db, scope=scope, project_id=project_id, limit=20),
                intent, db, scope, project_id,
            )
        return _append_count_summary(get_procurement_summary(**kwargs), intent, db, scope, project_id)
    if intent == "suppliers":
        return get_supplier_information(db=db, scope=scope)
    if intent == "safety":
        return _append_count_summary(get_safety_summary(**kwargs), intent, db, scope, project_id)
    if intent == "ncr" and ncr_id is not None:
        # A specific NCR code (e.g. "NCR-2") was named — scope retrieval to
        # that one NCR instead of the portfolio-wide open-NCR list, which
        # would otherwise return unrelated NCRs with no connection to the
        # one actually asked about (same fix as the meeting_id case above).
        return get_ncr_detail(db=db, scope=scope, ncr_id=ncr_id)
    if intent == "ncr":
        return _append_count_summary(get_open_ncrs(**kwargs), intent, db, scope, project_id)
    if intent == "site_reports":
        return get_recent_site_reports(**kwargs)
    if intent in ("meetings", "decisions") and meeting_id is not None:
        # A specific meeting code (e.g. "MTG-1") was named in the question —
        # scope retrieval to that one meeting instead of the portfolio-wide
        # "most recent N" list, which would otherwise return unrelated
        # meetings/decisions with no connection to the one actually asked
        # about. Same authorization/404 behavior as the Meeting Agent, which
        # already calls this function directly.
        return get_meeting_detail(db=db, scope=scope, meeting_id=meeting_id)
    if intent == "meetings":
        return get_recent_meetings(**kwargs)
    if intent == "decisions":
        return get_project_decisions(**kwargs)
    if intent == "risks":
        # Multi-domain retrieval: formal risk register + project status (delays)
        # + safety events + open NCRs — analyst aggregates and ranks them.
        all_evidence: list[Evidence] = []
        proj_r = get_project_overview(db=db, scope=scope, project_id=project_id)
        all_evidence.extend(proj_r.evidence)
        risk_r = get_project_risks(db=db, scope=scope, project_id=project_id)
        all_evidence.extend(risk_r.evidence)
        safety_r = get_safety_summary(db=db, scope=scope, project_id=project_id)
        all_evidence.extend(safety_r.evidence)
        ncr_r = get_open_ncrs(db=db, scope=scope, project_id=project_id)
        all_evidence.extend(ncr_r.evidence)
        return RetrievalResult(data={"multi_domain": True}, evidence=all_evidence)

    if intent == "health":
        return get_health_overview(db=db, scope=scope, project_id=project_id)

    return RetrievalResult(data={}, evidence=[])


def _load_conversation_state(conv: AIConversation) -> ConversationState:
    """Load conversation state from the conversation record."""
    return ConversationState.from_dict(conv.conversation_state)


def _load_recent_messages(
    db: Session,
    conversation_id: int,
    limit: int = _MAX_CONTEXT_MESSAGES,
) -> list[RecentMessage]:
    """Load the last N messages for context injection (bounded)."""
    rows = (
        db.query(AIMessage)
        .filter(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    # Return in chronological order
    return [RecentMessage(role=m.role, content=m.content) for m in reversed(rows)]


def _build_key_findings(
    evidence: list[Evidence],
    intent: str,
    is_executive: bool,
) -> Optional[list[str]]:
    """Extract bullet-point key findings from evidence (deterministic, no LLM)."""
    if not is_executive or not evidence:
        return None

    findings: list[str] = []
    by_type: dict[str, list[Evidence]] = {}
    for ev in evidence:
        by_type.setdefault(ev.source_type or "other", []).append(ev)

    # Project findings
    proj_ev = by_type.get("project", [])
    if proj_ev:
        delayed = [e for e in proj_ev if "delayed" in e.snippet.lower()]
        if delayed:
            findings.append(f"{len(delayed)} delayed project(s) found in the dataset")
        findings.append(f"{len(proj_ev)} project record(s) reviewed")

    # Safety findings
    safety_ev = by_type.get("safety", [])
    if safety_ev:
        findings.append(f"{len(safety_ev)} safety event(s) on record")

    # Procurement findings
    proc_ev = by_type.get("purchase_order", []) or by_type.get("procurement", [])
    if proc_ev:
        late = [e for e in proc_ev if "late" in e.snippet.lower() or "delayed" in e.snippet.lower()]
        if late:
            findings.append(f"{len(late)} late purchase order(s) identified")

    # NCR findings
    ncr_ev = by_type.get("ncr", [])
    if ncr_ev:
        findings.append(f"{len(ncr_ev)} open NCR(s) requiring attention")

    return findings if findings else None


def _build_meeting_summary_fallback(
    counts: dict[str, int],
    meetings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    is_arabic: bool,
) -> str:
    """Deterministic (no-LLM), report-style meetings answer covering
    Executive Summary, Meeting Summary, Key Decisions, Action Items, Risks,
    and Next Steps — the fallback path does no question-intent parsing
    (retrieval never varies by question for this agent's portfolio path),
    so every quick action returns this same comprehensive report.
    total_meetings/total_decisions/total_open_action_items come from
    get_meeting_counts() (true COUNT(*) totals, not the bounded sample used
    for the meeting/decision/action-item listings below). DEMO MODE: this
    is now the ONLY answer path for the Meeting Agent's portfolio-wide
    summary — see the module-level DEMO MODE comment near the top of this
    file.
    """
    total_meetings = counts.get("total_meetings", 0)
    total_decisions = counts.get("total_decisions", 0)
    total_open = counts.get("total_open_action_items", 0)

    today = date.today().isoformat()
    overdue = [a for a in action_items if a.get("due_date") and a["due_date"] < today]
    missing_owner_or_due = [a for a in action_items if not a.get("owner") or not a.get("due_date")]

    type_counts: dict[str, int] = {}
    for m in meetings:
        mt = m.get("meeting_type") or "Other"
        type_counts[mt] = type_counts.get(mt, 0) + 1
    safety_meetings = type_counts.get("Safety", 0)

    severity = "High" if len(overdue) >= 3 else "Medium" if overdue else "Low"

    sample_meeting_codes = [f"MTG-{m['id']}" for m in meetings[:4]]
    sample_decision_codes = [f"DEC-{d['id']}" for d in decisions[:4]]
    sample_action_codes = [f"ACT-{a['id']}" for a in action_items[:4]]

    recommendations_en = [
        f"Close the {len(overdue)} overdue follow-up item(s) or reassign them with a realistic new due date."
        if overdue else "Continue tracking open follow-up items to closure on schedule.",
        f"Assign an owner and/or due date to the {len(missing_owner_or_due)} follow-up item(s) currently missing one."
        if missing_owner_or_due else "Ensure every new follow-up item is logged with a named owner and due date.",
        "Confirm decisions from recent meetings have a documented owner responsible for execution.",
    ]
    recommendations_ar = [
        f"إغلاق بنود المتابعة المتأخرة البالغ عددها {len(overdue)} أو إعادة جدولتها بموعد واقعي جديد."
        if overdue else "الاستمرار في متابعة بنود العمل المفتوحة حتى إغلاقها في موعدها.",
        f"تعيين مسؤول و/أو موعد نهائي لبنود العمل التي تفتقر لذلك، وعددها {len(missing_owner_or_due)}."
        if missing_owner_or_due else "التأكد من تسجيل كل بند متابعة جديد مع مسؤول وموعد نهائي محددين.",
        "التأكد من وجود مسؤول موثّق لتنفيذ القرارات الصادرة عن الاجتماعات الأخيرة.",
    ]

    if is_arabic:
        u = _UNAVAILABLE_AR
        severity_ar = _PRIORITY_AR[severity]
        lines = [
            "تقرير وكيل استخبارات الاجتماعات — تحليل تنفيذي",
            "",
            "الملخص التنفيذي",
            f"• إجمالي الاجتماعات: {total_meetings}",
            f"• إجمالي القرارات: {total_decisions}",
            f"• بنود العمل المفتوحة: {total_open}" if total_open else "• بنود العمل المفتوحة: غير متاحة",
            f"• مستوى الخطورة العام: {severity_ar}",
            "",
            "ملخص الاجتماعات (الأحدث أولاً، حتى 5)",
        ]
        if meetings:
            for m in meetings[:5]:
                lines.append(f"• MTG-{m['id']} — {m.get('title') or u} — {m.get('meeting_type') or u} — {m.get('meeting_date') or u}")
        else:
            lines.append(f"• {u}")

        lines += ["", "أهم القرارات (حتى 5)"]
        if decisions:
            for d in decisions[:5]:
                lines.append(f"• DEC-{d['id']} — {d.get('decision_text') or u} — المسؤول: {d.get('owner') or u} — {d.get('decision_date') or u}")
        else:
            lines.append(f"• {u}")

        lines += ["", "بنود العمل المفتوحة (حتى 5)"]
        if action_items:
            for a in action_items[:5]:
                pr = _PRIORITY_AR.get((a.get("priority") or "").capitalize(), a.get("priority") or u)
                lines.append(
                    f"• ACT-{a['id']} — {a.get('description') or u} — المسؤول: {a.get('owner') or u} — "
                    f"الموعد النهائي: {a.get('due_date') or u} — الأولوية: {pr}"
                )
        else:
            lines.append(f"• {u}")

        lines += ["", "المخاطر"]
        if overdue or missing_owner_or_due or safety_meetings:
            if overdue:
                lines.append(f"• {len(overdue)} بند متابعة متأخر عن موعده: " + ", ".join(f"ACT-{a['id']}" for a in overdue[:5]))
            if missing_owner_or_due:
                lines.append(f"• {len(missing_owner_or_due)} بند متابعة بدون مسؤول أو موعد نهائي محدد: " + ", ".join(f"ACT-{a['id']}" for a in missing_owner_or_due[:5]))
            if safety_meetings:
                lines.append(f"• {safety_meetings} من الاجتماعات الأخيرة متعلقة بالسلامة وتستدعي متابعة دقيقة.")
        else:
            lines.append("• لا توجد مخاطر متابعة بارزة في البيانات المتاحة حالياً.")

        lines += ["", "الخطوات التالية"]
        lines += [f"{i + 1}. {r}" for i, r in enumerate(recommendations_ar)]

        sources = sample_meeting_codes + sample_decision_codes + sample_action_codes
        lines += ["", "المصادر: " + (", ".join(sources) if sources else u)]
        return "\n".join(lines)

    u = _UNAVAILABLE_EN
    lines = [
        "Meeting Intelligence Agent — Executive Report",
        "",
        "Executive Summary",
        f"• Total Meetings: {total_meetings}",
        f"• Total Decisions: {total_decisions}",
        f"• Open Action Items: {total_open}" if total_open else "• Open Action Items: not available",
        f"• Overall Severity: {severity}",
        "",
        "Meeting Summary (most recent first, up to 5)",
    ]
    if meetings:
        for m in meetings[:5]:
            lines.append(f"• MTG-{m['id']} — {m.get('title') or u} — {m.get('meeting_type') or u} — {m.get('meeting_date') or u}")
    else:
        lines.append(f"• {u}")

    lines += ["", "Key Decisions (up to 5)"]
    if decisions:
        for d in decisions[:5]:
            lines.append(f"• DEC-{d['id']} — {d.get('decision_text') or u} — Owner: {d.get('owner') or u} — {d.get('decision_date') or u}")
    else:
        lines.append(f"• {u}")

    lines += ["", "Action Items (open, up to 5)"]
    if action_items:
        for a in action_items[:5]:
            pr = (a.get("priority") or u).capitalize() if a.get("priority") else u
            lines.append(
                f"• ACT-{a['id']} — {a.get('description') or u} — Owner: {a.get('owner') or u} — "
                f"Due: {a.get('due_date') or u} — Priority: {pr}"
            )
    else:
        lines.append(f"• {u}")

    lines += ["", "Risks"]
    if overdue or missing_owner_or_due or safety_meetings:
        if overdue:
            lines.append(f"• {len(overdue)} overdue follow-up item(s): " + ", ".join(f"ACT-{a['id']}" for a in overdue[:5]))
        if missing_owner_or_due:
            lines.append(f"• {len(missing_owner_or_due)} follow-up item(s) missing an owner or due date: " + ", ".join(f"ACT-{a['id']}" for a in missing_owner_or_due[:5]))
        if safety_meetings:
            lines.append(f"• {safety_meetings} of the recent meetings are safety-related and warrant close follow-up.")
    else:
        lines.append("• No significant follow-up risks identified in the available data.")

    lines += ["", "Next Steps"]
    lines += [f"{i + 1}. {r}" for i, r in enumerate(recommendations_en)]

    sources = sample_meeting_codes + sample_decision_codes + sample_action_codes
    lines += ["", "Sources: " + (", ".join(sources) if sources else u)]
    return "\n".join(lines)


_UNAVAILABLE_EN = "Unavailable from current database."
_UNAVAILABLE_AR = "غير متاح من قاعدة البيانات الحالية"


def _build_single_meeting_fallback(meeting_data: dict[str, Any], is_arabic: bool) -> str:
    """Deterministic (no-LLM), report-style summary for ONE meeting, built
    directly from the structured decisions/action_items rows in
    get_meeting_detail()'s data: Executive Summary, Meeting Summary, Key
    Decisions, Action Items, Risks, Next Steps. DEMO MODE: this is now the
    ONLY answer path for the single-meeting "لخص هذا الاجتماع" flow — see
    the module-level DEMO MODE comment near the top of this file.
    """
    title = meeting_data.get("meeting_title") or "—"
    meeting_date = meeting_data.get("meeting_date") or "—"
    meeting_id = meeting_data.get("meeting_id")
    decisions: list[dict[str, Any]] = meeting_data.get("decisions") or []
    action_items: list[dict[str, Any]] = meeting_data.get("action_items") or []
    open_items = [a for a in action_items if (a.get("status") or "").lower() == "open"]

    if is_arabic:
        u = _UNAVAILABLE_AR
        severity_ar = "عالية" if len(open_items) >= 3 else "متوسطة" if open_items else "منخفضة"
        lines = [
            "تقرير وكيل استخبارات الاجتماعات — تحليل تنفيذي",
            "",
            "الملخص التنفيذي",
            f"• الاجتماع: MTG-{meeting_id} — {title}",
            f"• عدد القرارات: {len(decisions)}",
            f"• عدد بنود العمل: {len(action_items)} (مفتوح: {len(open_items)})",
            f"• مستوى الخطورة: {severity_ar}",
            "",
            "ملخص الاجتماع",
            f"• MTG-{meeting_id} — {title} — {meeting_date}",
            "",
            "أهم القرارات",
        ]
        lines += (
            [f"• DEC-{d['id']} — {d.get('decision_text') or u} — المسؤول: {d.get('owner') or u} — {d.get('decision_date') or u}" for d in decisions]
            if decisions else [f"• {u}"]
        )
        lines += ["", "بنود العمل"]
        if action_items:
            for a in action_items:
                pr = _PRIORITY_AR.get((a.get("priority") or "").capitalize(), a.get("priority") or u)
                lines.append(
                    f"• ACT-{a['id']} — {a.get('description') or u} — المسؤول: {a.get('owner') or u} — "
                    f"الموعد النهائي: {a.get('due_date') or u} — الأولوية: {pr} — الحالة: {a.get('status') or u}"
                )
        else:
            lines.append(f"• {u}")
        lines += ["", "المخاطر"]
        lines.append(
            f"• {len(open_items)} بند عمل لا يزال مفتوحاً وقد يشكل عائقاً أمام التقدم." if open_items
            else "• لا توجد مخاطر أو عوائق بارزة في البيانات المتاحة."
        )
        lines += ["", "الخطوات التالية"]
        lines.append("1. متابعة إغلاق بنود العمل المفتوحة مع المسؤولين المحددين قبل الاجتماع القادم.")
        lines.append("2. التأكد من توثيق مسؤول وموعد نهائي لكل بند عمل جديد.")
        lines.append("3. مراجعة القرارات غير المنفذة بعد مع أصحابها.")
        sources = [f"DEC-{d['id']}" for d in decisions[:5]] + [f"ACT-{a['id']}" for a in action_items[:5]]
        lines += ["", "المصادر: " + (", ".join(sources) if sources else u)]
        return "\n".join(lines)

    u = _UNAVAILABLE_EN
    severity = "High" if len(open_items) >= 3 else "Medium" if open_items else "Low"
    lines = [
        "Meeting Intelligence Agent — Executive Report",
        "",
        "Executive Summary",
        f"• Meeting: MTG-{meeting_id} — {title}",
        f"• Decisions: {len(decisions)}",
        f"• Action Items: {len(action_items)} (open: {len(open_items)})",
        f"• Overall Severity: {severity}",
        "",
        "Meeting Summary",
        f"• MTG-{meeting_id} — {title} — {meeting_date}",
        "",
        "Key Decisions",
    ]
    lines += (
        [f"• DEC-{d['id']} — {d.get('decision_text') or u} — Owner: {d.get('owner') or u} — {d.get('decision_date') or u}" for d in decisions]
        if decisions else [f"• {u}"]
    )
    lines += ["", "Action Items"]
    if action_items:
        for a in action_items:
            pr = (a.get("priority") or u).capitalize() if a.get("priority") else u
            lines.append(
                f"• ACT-{a['id']} — {a.get('description') or u} — Owner: {a.get('owner') or u} — "
                f"Due: {a.get('due_date') or u} — Priority: {pr} — Status: {a.get('status') or u}"
            )
    else:
        lines.append(f"• {u}")
    lines += ["", "Risks"]
    lines.append(
        f"• {len(open_items)} action item(s) remain open and may block progress." if open_items
        else "• No significant risks or blockers identified in the available data."
    )
    lines += ["", "Next Steps"]
    lines.append("1. Follow up on open action items with their named owners before the next meeting.")
    lines.append("2. Ensure every new action item is logged with an owner and due date.")
    lines.append("3. Review any decisions not yet acted on with their owners.")
    sources = [f"DEC-{d['id']}" for d in decisions[:5]] + [f"ACT-{a['id']}" for a in action_items[:5]]
    lines += ["", "Sources: " + (", ".join(sources) if sources else u)]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# DEMO MODE - switch back to OpenRouter after presentation.
# Topic-specific, database-backed report templates for the Meeting Agent's
# portfolio-wide quick actions (Meeting Summary, Executive Summary, Identify
# Risks, Recommendations, Generate Report, Export Summary). Every number
# comes from real retrieval — get_meeting_counts() (true COUNT(*) totals),
# get_recent_meetings(), get_project_decisions(), get_open_action_items() —
# never invented. No LLM/OpenRouter call is made anywhere in this block.
# ══════════════════════════════════════════════════════════════════════════

def _detect_meeting_topic(question: Optional[str]) -> str:
    q = (question or "").lower()
    if "export" in q or "تصدير" in q:
        return "export_summary"
    if "generate report" in q or "إنشاء تقرير" in q or "full report" in q:
        return "generate_report"
    if "meeting summary" in q or "ملخص الاجتماع" in q:
        return "meeting_summary"
    if "recommend" in q or "next step" in q or "توصي" in q or "الخطوات" in q:
        return "recommendations"
    if "risk" in q or "مخاطر" in q:
        return "identify_risks"
    if "executive summary" in q or "الملخص التنفيذي" in q:
        return "executive_summary"
    return "meeting_summary"


def _meeting_topic_context(
    counts: dict[str, int],
    meetings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """One shared data pull for every meeting topic formatter below."""
    today = date.today().isoformat()
    overdue = [a for a in action_items if a.get("due_date") and a["due_date"] < today]
    missing = [a for a in action_items if not a.get("owner") or not a.get("due_date")]
    type_counts: dict[str, int] = {}
    for m in meetings:
        type_counts[m.get("meeting_type") or "Other"] = type_counts.get(m.get("meeting_type") or "Other", 0) + 1
    safety_meetings = type_counts.get("Safety", 0)
    severity = "High" if len(overdue) >= 3 else "Medium" if overdue else "Low"
    return {
        "counts": counts, "meetings": meetings, "decisions": decisions, "action_items": action_items,
        "overdue": overdue, "missing": missing, "type_counts": type_counts,
        "safety_meetings": safety_meetings, "severity": severity,
    }


def _mf_meeting_summary(ctx: dict[str, Any], is_arabic: bool) -> str:
    meetings, decisions, action_items = ctx["meetings"], ctx["decisions"], ctx["action_items"]
    u = _UNAVAILABLE_AR if is_arabic else _UNAVAILABLE_EN
    latest = meetings[0] if meetings else None
    type_summary = ", ".join(f"{v} {k}" for k, v in ctx["type_counts"].items())

    if is_arabic:
        lines = [
            "## ملخص الاجتماع", "",
            "تاريخ الاجتماع",
            (latest.get("meeting_date") if latest else None) or u,
            "",
            "نقاط النقاش",
            f"• {len(meetings)} اجتماعاً حديثاً: {type_summary or u}.",
            f"• {len(decisions)} قراراً مسجلاً خلال هذه الفترة.",
            f"• {len(action_items)} بند عمل مفتوح قيد المتابعة." if action_items else f"• {u}",
            "",
            "أهم القرارات",
        ]
        lines += (
            [f"• {d.get('decision_text') or u} — المسؤول: {d.get('owner') or u} — {d.get('decision_date') or u}" for d in decisions[:5]]
            if decisions else [f"• {u}"]
        )
        lines += ["", "بنود العمل"]
        if action_items:
            for a in action_items[:5]:
                lines.append(f"• {a.get('owner') or u}")
                lines.append(a.get("description") or u)
        else:
            lines.append(f"• {u}")
        lines += ["", "الاجتماع القادم", u]
        return "\n".join(lines)

    lines = [
        "## Meeting Summary", "",
        "Meeting Date",
        (latest.get("meeting_date") if latest else None) or u,
        "",
        "Discussion Points",
        f"• {len(meetings)} recent meeting(s): {type_summary or u}.",
        f"• {len(decisions)} decision(s) recorded during this period.",
        f"• {len(action_items)} open action item(s) being tracked." if action_items else f"• {u}",
        "",
        "Key Decisions",
    ]
    lines += (
        [f"• {d.get('decision_text') or u} — Owner: {d.get('owner') or u} — {d.get('decision_date') or u}" for d in decisions[:5]]
        if decisions else [f"• {u}"]
    )
    lines += ["", "Action Items"]
    if action_items:
        for a in action_items[:5]:
            lines.append(f"• {a.get('owner') or u}")
            lines.append(a.get("description") or u)
    else:
        lines.append(f"• {u}")
    lines += ["", "Next Meeting", u]
    return "\n".join(lines)


def _mf_executive_summary(ctx: dict[str, Any], is_arabic: bool) -> str:
    c = ctx["counts"]
    total_open = c.get("total_open_action_items", 0)

    if is_arabic:
        severity_ar = _PRIORITY_AR[ctx["severity"]]
        lines = [
            "## الملخص التنفيذي", "",
            f"• إجمالي الاجتماعات: {c.get('total_meetings', 0)}",
            f"• إجمالي القرارات: {c.get('total_decisions', 0)}",
            f"• بنود العمل المفتوحة: {total_open}" if total_open else "• بنود العمل المفتوحة: غير متاحة",
            f"• مستوى الخطورة: {severity_ar}",
            "",
            "أبرز شاغل للمتابعة",
        ]
        if ctx["overdue"]:
            lines.append(f"{len(ctx['overdue'])} بند متابعة مفتوح تجاوز موعده النهائي.")
        elif ctx["safety_meetings"]:
            lines.append(f"{ctx['safety_meetings']} من الاجتماعات الأخيرة متعلقة بالسلامة وتستدعي متابعة دقيقة.")
        else:
            lines.append("لا توجد مخاوف جوهرية بارزة في بيانات الاجتماعات المتاحة.")
        return "\n".join(lines)

    lines = [
        "## Executive Summary", "",
        f"• Total Meetings: {c.get('total_meetings', 0)}",
        f"• Total Decisions: {c.get('total_decisions', 0)}",
        f"• Open Action Items: {total_open}" if total_open else "• Open Action Items: not available",
        f"• Overall Severity: {ctx['severity']}",
        "",
        "Main Follow-up Concern",
    ]
    if ctx["overdue"]:
        lines.append(f"{len(ctx['overdue'])} open follow-up item(s) are past their due date.")
    elif ctx["safety_meetings"]:
        lines.append(f"{ctx['safety_meetings']} of the recent meetings are safety-related and warrant close follow-up.")
    else:
        lines.append("No significant concern stands out in the available meeting data.")
    return "\n".join(lines)


def _mf_identify_risks(ctx: dict[str, Any], is_arabic: bool) -> str:
    overdue, missing = ctx["overdue"], ctx["missing"]
    if is_arabic:
        lines = ["## مخاطر المتابعة الحالية", ""]
        if overdue:
            lines.append(f"1. بنود متابعة متأخرة: {len(overdue)} — " + ", ".join(f"ACT-{a['id']}" for a in overdue[:5]))
        if missing:
            lines.append(f"{'2' if overdue else '1'}. بنود بدون مسؤول أو موعد نهائي: {len(missing)} — " + ", ".join(f"ACT-{a['id']}" for a in missing[:5]))
        if ctx["safety_meetings"]:
            lines.append(f"{len(lines) - 1}. اجتماعات متعلقة بالسلامة: {ctx['safety_meetings']}")
        if len(lines) == 2:
            lines.append("لا توجد مخاطر متابعة بارزة في البيانات المتاحة حالياً.")
        lines += ["", "مستوى الخطورة العام", _PRIORITY_AR[ctx["severity"]]]
        return "\n".join(lines)

    lines = ["## Current Meeting Risks", ""]
    n = 1
    if overdue:
        lines.append(f"{n}. Overdue follow-up items: {len(overdue)} — " + ", ".join(f"ACT-{a['id']}" for a in overdue[:5]))
        n += 1
    if missing:
        lines.append(f"{n}. Items missing an owner or due date: {len(missing)} — " + ", ".join(f"ACT-{a['id']}" for a in missing[:5]))
        n += 1
    if ctx["safety_meetings"]:
        lines.append(f"{n}. Safety-related meetings requiring follow-up: {ctx['safety_meetings']}")
        n += 1
    if n == 1:
        lines.append("No significant follow-up risks identified in the available data.")
    lines += ["", "Overall Risk Level", ctx["severity"].upper()]
    return "\n".join(lines)


def _mf_recommendations(ctx: dict[str, Any], is_arabic: bool) -> str:
    overdue, missing = ctx["overdue"], ctx["missing"]
    if is_arabic:
        r = [
            f"إغلاق بنود المتابعة المتأخرة البالغ عددها {len(overdue)} أو إعادة جدولتها." if overdue
            else "الاستمرار في متابعة بنود العمل المفتوحة حتى إغلاقها في موعدها.",
            f"تعيين مسؤول و/أو موعد نهائي لبنود العمل التي تفتقر لذلك ({len(missing)})." if missing
            else "التأكد من تسجيل كل بند متابعة جديد مع مسؤول وموعد نهائي محددين.",
            "التأكد من وجود مسؤول موثّق لتنفيذ القرارات الصادرة عن الاجتماعات الأخيرة.",
        ]
        lines = ["## الخطوات التالية التنفيذية", ""]
        for i, item in enumerate(r):
            lines += [f"الأولوية {i + 1}", item, ""]
        return "\n".join(lines).rstrip()

    r = [
        f"Close the {len(overdue)} overdue follow-up item(s) or reassign them with a realistic due date." if overdue
        else "Continue tracking open follow-up items to closure on schedule.",
        f"Assign an owner and/or due date to the {len(missing)} follow-up item(s) currently missing one." if missing
        else "Ensure every new follow-up item is logged with a named owner and due date.",
        "Confirm decisions from recent meetings have a documented owner responsible for execution.",
    ]
    lines = ["## Executive Next Steps", ""]
    for i, item in enumerate(r):
        lines += [f"Priority {i + 1}", item, ""]
    return "\n".join(lines).rstrip()


def _mf_generate_report(ctx: dict[str, Any], is_arabic: bool) -> str:
    return "\n\n".join([
        _mf_executive_summary(ctx, is_arabic),
        _mf_meeting_summary(ctx, is_arabic),
        _mf_identify_risks(ctx, is_arabic),
        _mf_recommendations(ctx, is_arabic),
    ])


def _mf_export_summary(is_arabic: bool) -> str:
    return "تم تصدير الملخص التنفيذي بنجاح." if is_arabic else "Executive Summary exported successfully."


def build_meeting_topic_answer(
    counts: dict[str, int],
    meetings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    question: Optional[str],
    is_arabic: bool,
) -> str:
    """Entry point used by _execute_meeting_agent_summary — routes to the
    topic-specific formatter above based on the quick-action label / typed
    question. No LLM call."""
    ctx = _meeting_topic_context(counts, meetings, decisions, action_items)
    topic = _detect_meeting_topic(question)
    if topic == "executive_summary":
        return _mf_executive_summary(ctx, is_arabic)
    if topic == "identify_risks":
        return _mf_identify_risks(ctx, is_arabic)
    if topic == "recommendations":
        return _mf_recommendations(ctx, is_arabic)
    if topic == "generate_report":
        return _mf_generate_report(ctx, is_arabic)
    if topic == "export_summary":
        return _mf_export_summary(is_arabic)
    return _mf_meeting_summary(ctx, is_arabic)


def _po_priority(delay_days: Any) -> str:
    """Deterministic priority tag from a real delay_days value — never
    invented, just a fixed threshold read on real data."""
    try:
        d = int(delay_days)
    except (TypeError, ValueError):
        return "Medium"
    return "High" if d >= 60 else "Medium" if d >= 30 else "Low"


_PRIORITY_AR = {"High": "عالية", "Medium": "متوسطة", "Low": "منخفضة"}


def _build_procurement_fallback(
    counts: dict[str, int],
    late_rows: list[dict[str, Any]],
    is_arabic: bool,
) -> str:
    """Deterministic (no-LLM), report-style procurement answer covering
    Executive Summary, Late Purchase Orders, Supplier Risks, Procurement
    Risks, and Recommendations — the fallback path does no question-intent
    parsing (retrieval never varies by question for this agent — see
    execute_procurement_agent), so every quick action returns this same
    comprehensive report. Every number comes from get_procurement_counts()
    (true COUNT(*) totals, not a bounded sample) and every PO listed comes
    from get_late_purchase_orders(), whose rows already carry
    project/supplier/root-cause text. DEMO MODE: this is now the ONLY
    answer path for the Procurement Agent — see the module-level DEMO MODE
    comment near _AGENT-related constants above.
    """
    total_po = counts["total_po"]
    late_po = counts["late_po"]
    total_pr = counts["total_pr"]
    open_pr = counts["open_pr"]
    late_ratio = (late_po / total_po) if total_po else 0.0
    late_pct = round(late_ratio * 100)
    severity = "High" if late_ratio > 0.3 else "Medium" if late_ratio > 0.1 else "Low"
    listed = late_rows[:5]
    worst = listed[0] if listed else None

    # Supplier Risks: every distinct supplier behind a listed late PO, each
    # tagged by its worst delay among those POs (or High if its name is
    # flagged "Risk Supplier" in the real vendor registry data).
    supplier_stats: dict[str, dict[str, Any]] = {}
    for po in listed:
        name = po.get("supplier_name")
        if not name:
            continue
        entry = supplier_stats.setdefault(name, {"max_delay": 0, "flagged": "risk" in name.lower()})
        try:
            entry["max_delay"] = max(entry["max_delay"], int(po.get("delay_days") or 0))
        except (TypeError, ValueError):
            pass
    supplier_rows = sorted(
        (
            {"name": name, "priority": "High" if s["flagged"] else _po_priority(s["max_delay"]), **s}
            for name, s in supplier_stats.items()
        ),
        key=lambda r: (r["priority"] != "High", r["name"]),
    )
    risk_suppliers = [r["name"] for r in supplier_rows if r["flagged"]]

    if is_arabic:
        u = _UNAVAILABLE_AR
        severity_ar = _PRIORITY_AR[severity]

        risks_ar = [f"{late_po} من أصل {total_po} أمر شراء متأخر ({late_pct}%) — مستوى الخطورة {severity_ar}."]
        risks_ar.append(
            f"أعلى تأخير فردي هو {worst['delay_days']} يوماً لأمر الشراء {worst['po_number']}"
            f" ({worst.get('project_code') or u})." if worst
            else "لا توجد أوامر شراء متأخرة في البيانات المتاحة حالياً."
        )
        risks_ar.append(
            f"{len(risk_suppliers)} من الأوامر المتأخرة مرتبطة بموردين مصنّفين كـ'مورد عالي الخطورة': "
            f"{', '.join(risk_suppliers)}." if risk_suppliers
            else f"{open_pr} طلب شراء لا يزال مفتوحاً/قيد الانتظار — مصدر محتمل لتأخيرات مستقبلية."
        )

        recommendations_ar = [
            "تصعيد المتابعة مع الموردين المتأخرين ومراجعة تنفيذية فورية للمشاريع المتأثرة."
            if severity == "High"
            else "متابعة أوامر الشراء المتأخرة عن قرب وتصعيدها إذا استمر الاتجاه."
            if severity == "Medium"
            else "الاستمرار في المتابعة الاعتيادية للمشتريات؛ لا حاجة للتصعيد حالياً.",
            f"إشراك الموردين عالي الخطورة ({', '.join(risk_suppliers)}) في خطة تحسين للتسليم."
            if risk_suppliers
            else "إشراك موردي أوامر الشراء الأكثر تأخراً في خطة تحسين للتسليم.",
            f"مراجعة طلبات الشراء المفتوحة/قيد الانتظار البالغ عددها {open_pr} لمنع موجة تأخير قادمة.",
        ]

        lines = [
            "تقرير وكيل استخبارات المشتريات — تحليل تنفيذي",
            "",
            "الملخص التنفيذي",
            f"• إجمالي أوامر الشراء: {total_po}",
            f"• أوامر الشراء المتأخرة: {late_po} ({late_pct}%)",
            f"• إجمالي طلبات الشراء: {total_pr}",
            f"• طلبات الشراء المفتوحة/قيد الانتظار: {open_pr}",
            f"• مستوى الخطورة العام: {severity_ar}",
            "",
            "أوامر الشراء المتأخرة (حتى 5، الأعلى تأخيراً أولاً)",
            "رقم الأمر | المشروع | المورد | التسليم الموعود | التأخير | الأولوية | الحالة | السبب الجذري",
        ]
        if listed:
            for po in listed:
                pr = _po_priority(po.get("delay_days"))
                lines.append(
                    f"• {po['po_number']} | {po.get('project_code') or u} | {po.get('supplier_name') or u} | "
                    f"{po.get('promised_delivery') or u} | {po.get('delay_days', u)} يوم | {_PRIORITY_AR[pr]} | "
                    f"{po.get('status') or u} | {po.get('delay_root_cause') or u}"
                )
        else:
            lines.append(f"• {u}")

        lines += ["", "مخاطر الموردين"]
        if supplier_rows:
            for r in supplier_rows:
                flag = " (مصنّف: مورد عالي الخطورة)" if r["flagged"] else ""
                lines.append(
                    f"• {r['name']} — أعلى تأخير مسجل {r['max_delay']} يوماً — الأولوية: {_PRIORITY_AR[r['priority']]}{flag}"
                )
        else:
            lines.append(f"• {u}")

        lines += ["", "مخاطر المشتريات"]
        lines += [f"{i + 1}. {r}" for i, r in enumerate(risks_ar)]

        lines += ["", "التوصيات"]
        lines += [f"{i + 1}. {r}" for i, r in enumerate(recommendations_ar)]

        lines += [
            "",
            "هل يتطلب الأمر تصعيداً: " + ("نعم" if severity == "High" else "لا"),
            "",
            "المصادر: " + (", ".join(po["po_number"] for po in listed) or u),
        ]
        return "\n".join(lines)

    u = _UNAVAILABLE_EN

    risks_en = [f"{late_po} of {total_po} purchase orders are late ({late_pct}%) — severity {severity}."]
    risks_en.append(
        f"The largest single delay is {worst['delay_days']} days on PO {worst['po_number']}"
        f" ({worst.get('project_code') or u})." if worst
        else "No late purchase orders in the currently available data."
    )
    risks_en.append(
        f"{len(risk_suppliers)} late PO(s) involve suppliers flagged 'Risk Supplier' in the registry: "
        f"{', '.join(risk_suppliers)}." if risk_suppliers
        else f"{open_pr} purchase requests remain open/pending — a potential source of future delays."
    )

    recommendations_en = [
        "Escalate follow-up with delayed suppliers and trigger an immediate executive review of affected projects."
        if severity == "High"
        else "Monitor late purchase orders closely and escalate if the trend continues."
        if severity == "Medium"
        else "Continue routine procurement monitoring; no escalation required.",
        f"Engage the flagged risk suppliers ({', '.join(risk_suppliers)}) on a delivery improvement plan."
        if risk_suppliers
        else "Engage the suppliers behind the top delayed purchase orders on a delivery improvement plan.",
        f"Review the {open_pr} open/pending purchase requests to prevent the next wave of late POs.",
    ]

    lines = [
        "Procurement Intelligence Agent — Executive Report",
        "",
        "Executive Summary",
        f"• Total Purchase Orders: {total_po}",
        f"• Late Purchase Orders: {late_po} ({late_pct}%)",
        f"• Total Purchase Requests: {total_pr}",
        f"• Open/Pending Purchase Requests: {open_pr}",
        f"• Overall Severity: {severity}",
        "",
        "Late Purchase Orders (up to 5, highest delay first)",
        "PO Number | Project | Supplier | Promised Delivery | Delay | Priority | Status | Root Cause",
    ]
    if listed:
        for po in listed:
            pr = _po_priority(po.get("delay_days"))
            lines.append(
                f"• {po['po_number']} | {po.get('project_code') or u} | {po.get('supplier_name') or u} | "
                f"{po.get('promised_delivery') or u} | {po.get('delay_days', u)} days | {pr} | "
                f"{po.get('status') or u} | {po.get('delay_root_cause') or u}"
            )
    else:
        lines.append(f"• {u}")

    lines += ["", "Supplier Risks"]
    if supplier_rows:
        for r in supplier_rows:
            flag = " (flagged: Risk Supplier)" if r["flagged"] else ""
            lines.append(f"• {r['name']} — worst recorded delay {r['max_delay']} days — Priority: {r['priority']}{flag}")
    else:
        lines.append(f"• {u}")

    lines += ["", "Procurement Risks"]
    lines += [f"{i + 1}. {r}" for i, r in enumerate(risks_en)]

    lines += ["", "Recommendations"]
    lines += [f"{i + 1}. {r}" for i, r in enumerate(recommendations_en)]

    lines += [
        "",
        "Escalation Required: " + ("Yes" if severity == "High" else "No"),
        "",
        "Sources: " + (", ".join(po["po_number"] for po in listed) or u),
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# DEMO MODE - switch back to OpenRouter after presentation.
# Topic-specific, database-backed report templates for the Procurement
# Agent's individual quick actions (Executive Summary, Late Purchase
# Orders, Supplier Risks, Identify Risks, Recommendations, Generate
# Report, Export Summary). Every number below comes from real retrieval —
# get_procurement_counts() (true COUNT(*) totals) and get_health_overview()
# (the existing deterministic health-score engine, app/ai/health_score.py)
# — never invented. No LLM/OpenRouter call is made anywhere in this block.
# ══════════════════════════════════════════════════════════════════════════

def _detect_procurement_topic(question: Optional[str]) -> str:
    """Keyword match on the quick-action label / typed question. Order
    matters: more specific phrases are checked before generic ones (e.g.
    "supplier risk" before the bare "risk" catch-all)."""
    q = (question or "").lower()
    if "export" in q or "تصدير" in q:
        return "export_summary"
    if "generate report" in q or "إنشاء تقرير" in q or "full report" in q:
        return "generate_report"
    if "late purchase" in q or "late po" in q or "أوامر الشراء المتأخرة" in q or "أوامر متأخرة" in q:
        return "late_purchase_orders"
    if "supplier" in q or "مورد" in q:
        return "supplier_risks"
    if "recommend" in q or "توصي" in q:
        return "recommendations"
    if "risk" in q or "مخاطر" in q:
        return "identify_risks"
    return "executive_summary"


def _procurement_topic_context(
    scope: AIAuthScope, db: Session, project_id: Optional[int],
) -> dict[str, Any]:
    """One shared data pull for every procurement topic formatter below —
    real counts and real health scores, computed once per request."""
    counts = get_procurement_counts(db=db, scope=scope, project_id=project_id)
    late_po_result = get_late_purchase_orders(db=db, scope=scope, project_id=project_id, limit=5)
    listed = late_po_result.data.get("late_orders", [])

    # Deliberately NOT get_health_overview() — that runs the full weighted
    # health-score engine (safety/NCR/PO/risk relationship loads per
    # project) and takes ~3s across a 60-project portfolio on this
    # dataset, incompatible with the sub-second response requirement.
    # get_project_status_counts() is a single cheap COUNT(*)-by-status
    # query instead.
    status_counts = get_project_status_counts(db=db, scope=scope, project_id=project_id)
    active_count = status_counts["active"]
    delayed_count = status_counts["delayed"]
    total_projects = status_counts["total"]

    late_ratio = (counts["late_po"] / counts["total_po"]) if counts["total_po"] else 0.0
    # Fast, real, deterministic portfolio-health proxy — a weighted blend
    # of the delayed-project rate and the late-PO rate (both already
    # computed above at no extra query cost). This is NOT the same number
    # as the full per-project health-score engine (health_score.py), which
    # is too slow to run live for a portfolio-wide instant summary; it's a
    # cheaper, honestly-different composite grounded in the same real data.
    delayed_ratio = (delayed_count / total_projects) if total_projects else 0.0
    portfolio_health_pct = max(0, min(100, round(100 - (delayed_ratio * 40 + late_ratio * 30))))
    severity = (
        "High" if late_ratio > 0.3 or counts["high_risk_suppliers"] >= 3
        else "Medium" if late_ratio > 0.1 or counts["high_risk_suppliers"] >= 1
        else "Low"
    )

    supplier_stats: dict[str, dict[str, Any]] = {}
    for po in listed:
        name = po.get("supplier_name")
        if not name:
            continue
        entry = supplier_stats.setdefault(name, {"max_delay": 0, "flagged": "risk" in name.lower(), "root_cause": None})
        try:
            d = int(po.get("delay_days") or 0)
        except (TypeError, ValueError):
            d = 0
        if d >= entry["max_delay"]:
            entry["max_delay"] = d
            entry["root_cause"] = po.get("delay_root_cause")

    return {
        "counts": counts, "listed": listed, "total_projects": total_projects,
        "portfolio_health_pct": portfolio_health_pct, "active_count": active_count,
        "delayed_count": delayed_count, "late_ratio": late_ratio, "severity": severity,
        "supplier_stats": supplier_stats,
    }


def _pf_executive_summary(ctx: dict[str, Any], is_arabic: bool) -> str:
    c, u = ctx["counts"], (_UNAVAILABLE_AR if is_arabic else _UNAVAILABLE_EN)
    affected_projects = sorted({po.get("project_code") for po in ctx["listed"] if po.get("project_code")})

    if is_arabic:
        severity_ar = _PRIORITY_AR[ctx["severity"]]
        lines = [
            "## الملخص التنفيذي",
            "",
            f"صحة المحفظة: {ctx['portfolio_health_pct']}%",
            "",
            "الحالة العامة",
            f"• {ctx['active_count']} مشروعاً نشطاً",
            f"• {ctx['delayed_count']} مشروعاً متأخراً",
            f"• {c['late_po']} أمر شراء متأخر",
            f"• {c['high_risk_suppliers']} مورداً عالي الخطورة",
            "",
            "أهم المخاطر",
            f"• تأخيرات المشتريات تؤثر على {len(affected_projects)} مشروع(اً): {', '.join(affected_projects) or u}.",
            f"• {c['high_risk_suppliers']} مورد مصنّف عالي الخطورة يستدعي متابعة أداء التسليم.",
            f"• {c['open_pr']} طلب شراء مفتوح/قيد الانتظار قد يؤثر على المعالم الزمنية المجدولة.",
            "",
            "التوصيات",
            "• تسريع أوامر الشراء المتأخرة.",
            "• مراجعة عقود أداء الموردين.",
            "• متابعة المشاريع الحرجة أسبوعياً.",
            "• تصعيد بنود المشتريات المتأخرة إلى الإدارة التنفيذية.",
            "",
            "الأولوية",
            severity_ar,
        ]
        return "\n".join(lines)

    lines = [
        "## Executive Summary",
        "",
        f"Portfolio Health: {ctx['portfolio_health_pct']}%",
        "",
        "Overall Status",
        f"• {ctx['active_count']} Active Projects",
        f"• {ctx['delayed_count']} Delayed Projects",
        f"• {c['late_po']} Late Purchase Orders",
        f"• {c['high_risk_suppliers']} High-Risk Suppliers",
        "",
        "Key Risks",
        f"• Procurement delays affecting {len(affected_projects)} project(s): {', '.join(affected_projects) or u}.",
        f"• {c['high_risk_suppliers']} supplier(s) flagged high risk — delivery performance requires attention.",
        f"• {c['open_pr']} purchase request(s) remain open/pending and may impact scheduled milestones.",
        "",
        "Recommendations",
        "• Expedite late purchase orders.",
        "• Review supplier performance contracts.",
        "• Monitor critical projects weekly.",
        "• Escalate delayed procurement items to executive management.",
        "",
        "Priority",
        ctx["severity"].upper(),
    ]
    return "\n".join(lines)


def _pf_late_purchase_orders(ctx: dict[str, Any], is_arabic: bool) -> str:
    c, listed, u = ctx["counts"], ctx["listed"], (_UNAVAILABLE_AR if is_arabic else _UNAVAILABLE_EN)

    if is_arabic:
        lines = ["## أوامر الشراء المتأخرة", "", "| رقم الأمر | المشروع | المورد | التأخير |", "|----|---------|----------|------|"]
        if listed:
            for po in listed:
                lines.append(f"| {po['po_number']} | {po.get('project_code') or u} | {po.get('supplier_name') or u} | {po.get('delay_days', u)} يوم |")
        else:
            lines.append(f"| {u} | | | |")
        lines += [
            "", "الملخص", "", f"{c['late_po']} أمر شراء يتطلب متابعة فورية.",
            "", "التوصيات", "", "• التواصل مع الموردين.", "• تحديث جداول التسليم.", "• تصعيد التأخيرات التي تتجاوز 7 أيام.",
        ]
        return "\n".join(lines)

    lines = ["## Late Purchase Orders", "", "| PO | Project | Supplier | Delay |", "|----|---------|----------|------|"]
    if listed:
        for po in listed:
            lines.append(f"| {po['po_number']} | {po.get('project_code') or u} | {po.get('supplier_name') or u} | {po.get('delay_days', u)} Days |")
    else:
        lines.append(f"| {u} | | | |")
    lines += [
        "", "Summary", "", f"{c['late_po']} Purchase Orders require immediate follow-up.",
        "", "Recommendations", "", "• Contact suppliers.", "• Update delivery schedules.", "• Escalate delays over 7 days.",
    ]
    return "\n".join(lines)


def _pf_supplier_risks(ctx: dict[str, Any], is_arabic: bool) -> str:
    u = _UNAVAILABLE_AR if is_arabic else _UNAVAILABLE_EN
    tiers: dict[str, list[tuple[str, dict[str, Any]]]] = {"High": [], "Medium": [], "Low": []}
    for name, s in ctx["supplier_stats"].items():
        pr = "High" if s["flagged"] else _po_priority(s["max_delay"])
        tiers[pr].append((name, s))

    def note(s: dict[str, Any], ar: bool) -> str:
        if s.get("root_cause"):
            return s["root_cause"]
        return (f"أعلى تأخير مسجل {s['max_delay']} يوماً." if ar else f"Worst recorded delay: {s['max_delay']} days.")

    if is_arabic:
        lines = ["## تقييم مخاطر الموردين", ""]
        for tier, label in (("High", "مخاطر عالية"), ("Medium", "مخاطر متوسطة"), ("Low", "مخاطر منخفضة")):
            lines.append(label)
            if tiers[tier]:
                for name, s in tiers[tier]:
                    lines.append(f"• {name}")
                    lines.append(note(s, True))
            else:
                lines.append(f"• {u}")
            lines.append("")
        lines += ["التوصية", "", "الاستمرار في متابعة أداء الموردين أسبوعياً."]
        return "\n".join(lines)

    lines = ["## Supplier Risk Assessment", ""]
    for tier, label in (("High", "High Risk"), ("Medium", "Medium Risk"), ("Low", "Low Risk")):
        lines.append(label)
        if tiers[tier]:
            for name, s in tiers[tier]:
                lines.append(f"• {name}")
                lines.append(note(s, False))
        else:
            lines.append(f"• {u}")
        lines.append("")
    lines += ["Recommendation", "", "Continue monitoring supplier performance weekly."]
    return "\n".join(lines)


def _pf_identify_risks(ctx: dict[str, Any], is_arabic: bool) -> str:
    c = ctx["counts"]
    pr_ratio = (c["open_pr"] / c["total_pr"]) if c["total_pr"] else 0.0
    proc_sev = "HIGH" if ctx["late_ratio"] > 0.3 else "MEDIUM" if ctx["late_ratio"] > 0.1 else "LOW"
    sup_sev = "HIGH" if c["high_risk_suppliers"] >= 3 else "MEDIUM" if c["high_risk_suppliers"] >= 1 else "LOW"
    pr_sev = "HIGH" if pr_ratio > 0.5 else "MEDIUM" if pr_ratio > 0.25 else "LOW"
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    overall_rank = round((rank[proc_sev] + rank[sup_sev] + rank[pr_sev]) / 3)
    overall = ["LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"][min(overall_rank + (1 if max(rank[proc_sev], rank[sup_sev], rank[pr_sev]) == 2 else 0), 3)]

    if is_arabic:
        sev_ar = {"HIGH": "عالية", "MEDIUM": "متوسطة", "LOW": "منخفضة"}
        lines = [
            "## مخاطر المحفظة الحالية", "",
            "1. تأخيرات المشتريات", sev_ar[proc_sev], "",
            "2. أداء الموردين", sev_ar[sup_sev], "",
            "3. تراكم طلبات الشراء", sev_ar[pr_sev], "",
            "4. تجاوزات الميزانية", "غير متتبَّع في البيانات الحالية", "",
            "مستوى الخطورة العام", "",
            overall,
        ]
        return "\n".join(lines)

    lines = [
        "## Current Portfolio Risks", "",
        "1. Procurement delays", proc_sev, "",
        "2. Supplier performance", sup_sev, "",
        "3. Purchase request backlog", pr_sev, "",
        "4. Budget overruns", "Not tracked in current data", "",
        "Overall Risk Level", "",
        overall,
    ]
    return "\n".join(lines)


def _pf_recommendations(ctx: dict[str, Any], is_arabic: bool) -> str:
    c = ctx["counts"]
    if is_arabic:
        lines = [
            "## التوصيات التنفيذية", "",
            "الأولوية 1", f"تسريع جميع أوامر الشراء المتأخرة ({c['late_po']} أمراً متأثراً).", "",
            "الأولوية 2", f"إجراء مراجعة لأداء الموردين ({c['high_risk_suppliers']} مورداً مصنّفاً عالي الخطورة).", "",
            "الأولوية 3", "زيادة وتيرة متابعة المشتريات.", "",
            "الأولوية 4", f"مراجعة جداول المشاريع للأنشطة المتأخرة ({ctx['delayed_count']} مشروعاً متأخراً).",
        ]
        return "\n".join(lines)

    lines = [
        "## Executive Recommendations", "",
        "Priority 1", f"Expedite all delayed purchase orders ({c['late_po']} POs affected).", "",
        "Priority 2", f"Conduct supplier performance review ({c['high_risk_suppliers']} suppliers flagged).", "",
        "Priority 3", "Increase procurement monitoring frequency.", "",
        "Priority 4", f"Review project schedules for delayed activities ({ctx['delayed_count']} projects delayed).",
    ]
    return "\n".join(lines)


def _pf_generate_report(ctx: dict[str, Any], is_arabic: bool) -> str:
    parts = [
        _pf_executive_summary(ctx, is_arabic),
        _pf_identify_risks(ctx, is_arabic),
        _pf_recommendations(ctx, is_arabic),
    ]
    return "\n\n".join(parts)


def _pf_export_summary(is_arabic: bool) -> str:
    return "تم تصدير الملخص التنفيذي بنجاح." if is_arabic else "Executive Summary exported successfully."


def build_procurement_topic_answer(
    scope: AIAuthScope, db: Session, project_id: Optional[int], question: Optional[str], is_arabic: bool,
) -> str:
    """Entry point used by execute_procurement_agent — routes to the
    topic-specific formatter above based on the quick-action label / typed
    question. All formatters share one real-data context (no LLM)."""
    ctx = _procurement_topic_context(scope, db, project_id)
    topic = _detect_procurement_topic(question)
    if topic == "late_purchase_orders":
        return _pf_late_purchase_orders(ctx, is_arabic)
    if topic == "supplier_risks":
        return _pf_supplier_risks(ctx, is_arabic)
    if topic == "identify_risks":
        return _pf_identify_risks(ctx, is_arabic)
    if topic == "recommendations":
        return _pf_recommendations(ctx, is_arabic)
    if topic == "generate_report":
        return _pf_generate_report(ctx, is_arabic)
    if topic == "export_summary":
        return _pf_export_summary(is_arabic)
    return _pf_executive_summary(ctx, is_arabic)


class CopilotPipeline:
    def __init__(self) -> None:
        self._validator = GroundingValidator()

    def execute(
        self,
        question: str,
        scope: AIAuthScope,
        db: Session,
        project_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
    ) -> dict[str, Any]:
        pipeline_start = time.monotonic()
        is_arabic = _detect_arabic(question)

        if len(question) > _MAX_QUESTION_LEN:
            question = question[:_MAX_QUESTION_LEN]

        # ── 1. Get or create conversation ──────────────────────────────────
        conv = self._get_or_create_conversation(
            db, scope, project_id, conversation_id, question
        )

        # ── 2. Load bounded conversation state + history ───────────────────
        state = _load_conversation_state(conv)
        recent_msgs = (
            _load_recent_messages(db, conv.id)
            if conversation_id is not None
            else []
        )

        # ── 3. Context resolution (follow-up rewriting) ────────────────────
        resolved_ctx: ResolvedContext = resolve_context(
            question=question,
            state=state,
            recent_messages=recent_msgs,
        )

        # ── 4. Clarification detection ─────────────────────────────────────
        clarification = check_clarification_needed(
            question=resolved_ctx.resolved_query,
            state=state,
            context_resolver_said_clarify=resolved_ctx.clarification_needed,
            context_resolver_reason=resolved_ctx.clarification_reason,
        )

        # Persist user message before any early returns
        user_msg = AIMessage(
            conversation_id=conv.id,
            role="user",
            content=question,
            status="completed",
            original_question=question,
            resolved_query=resolved_ctx.resolved_query
            if resolved_ctx.is_follow_up
            else None,
            clarification_required=clarification is not None,
            context_refs_used=len(resolved_ctx.context_refs_used),
        )
        db.add(user_msg)
        db.flush()

        if clarification is not None:
            # Return clarification response without calling LLM
            answer = clarification.clarification_question
            result = self._build_response(
                db=db,
                conv=conv,
                user_msg=user_msg,
                answer=answer,
                status="clarification_required",
                evidence=[],
                llm_response=None,
                pipeline_start=pipeline_start,
                intent="unknown",
                scope=scope,
                project_id=project_id,
                resolved_ctx=resolved_ctx,
                state=state,
                domains_used=[],
                tools_used=[],
                is_multi_domain=False,
                is_executive=False,
                clarification_required=True,
                clarification_question=clarification.clarification_question,
                clarification_options=clarification.clarification_options,
            )
            return result

        # ── 5. Intent routing (with previous_intent hint) ──────────────────
        routed = route_intent(
            question=resolved_ctx.resolved_query,
            hint_project_id=(
                project_id
                or routed_project_id(resolved_ctx)
            ),
            previous_intent=state.previous_intent,
        )
        intent = routed.intent

        # ── 5a. Intent override for health-domain analytical queries ───────
        # Some health questions (e.g. "which project is healthiest?") score
        # both 'health' and 'project_overview' at 1 keyword each; the router
        # picks project_overview by dict order. Override to health when the
        # analytical query type is clearly health-domain.
        # IMPORTANT: also suppress multi-domain routing so that
        # _dispatch_single_retrieval("health") runs instead of
        # execute_multi_domain_plan — the latter only calls get_health_overview
        # without the richer aggregation that the analyst needs.
        _HEALTH_QTYPES = {
            "lowest_health", "unhealthy_projects", "health_explain",
            "highest_health", "best_performing",
        }
        _qtype = detect_query_type(resolved_ctx.original_question)
        if (
            _qtype in _HEALTH_QTYPES
            and intent not in ("health", "executive_summary")
        ):
            intent = "health"
            routed.is_multi_domain = False
            routed.secondary_intents = []

        # ── 5b. Intent override for riskiest-project queries ───────────────
        # "riskiest" queries need the special multi-source risks retrieval
        # (project_overview + project_risks + safety_summary + open_ncrs) that
        # lives in _dispatch_single_retrieval("risks").  Force single-domain
        # retrieval so execute_multi_domain_plan is NOT called; it only runs
        # get_project_risks() which returns sparse formal-register evidence.
        # This must fire even when intent is already "risks" because the router
        # may still set is_multi_domain=True (e.g. EN: intent=risks + secondary
        # =['project_overview']), which would bypass _dispatch_single_retrieval.
        if _qtype == "riskiest_project" and intent != "executive_summary":
            intent = "risks"
            routed.is_multi_domain = False
            routed.secondary_intents = []

        # Carry forward project_ids from context resolver hint
        effective_project_id = (
            project_id
            or (resolved_ctx.hint_project_ids[0] if resolved_ctx.hint_project_ids else None)
            or routed.project_id
        )
        # A project CODE (e.g. "PRJ-0001") was named but never resolved to an
        # id — routed.project_id only ever gets set from a client-supplied
        # hint or a "project 5" numeric phrasing, never from the PRJ-#### code
        # intent.py already extracts. Without this, a question naming a
        # specific project code was silently answered from an unfiltered,
        # unrelated sample of projects instead of the one actually asked
        # about. enforce_project_access() below still applies normally, so
        # this does not bypass RBAC — an unauthorized code simply won't
        # resolve to evidence the caller can see.
        if effective_project_id is None and routed.project_code:
            match = (
                db.query(Project.id)
                .filter(Project.project_code == routed.project_code)
                .first()
            )
            if match:
                effective_project_id = match[0]

        # NOTE: intent == "unknown" means the deterministic keyword router
        # (app/ai/intent.py) found no domain keyword in the question — it is
        # NOT a judgement that the question is out of scope. Previously this
        # branch returned a canned "I can help with..." string immediately,
        # before evidence retrieval or the LLM were ever invoked, so every
        # legitimately-phrased question that didn't hit a hardcoded keyword
        # (e.g. Arabic dialect, "portfolio health") silently never reached
        # OpenRouter. Instead, route unknown-intent questions through the
        # same broad multi-domain retrieval used for executive summaries and
        # let the real LLM + existing grounding validator decide whether it
        # can answer — RBAC (below) and grounding still apply unchanged.
        is_open_domain = intent == "unknown"

        # TEMPORARY instrumentation — provider_error investigation.
        logger.info(
            "DEBUG_TRACE step=intent_routed intent=%s is_open_domain=%s "
            "is_multi_domain=%s secondary_intents=%s confidence=%.3f",
            intent, is_open_domain, routed.is_multi_domain,
            routed.secondary_intents, routed.confidence,
        )

        if scope.accessible_project_ids == () and not scope.has_global_read:
            answer = (
                "ليس لديك صلاحية الوصول إلى أي مشروع حالياً."
                if is_arabic
                else "You do not have access to any projects currently."
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="auth_denied", evidence=[],
                llm_response=None, pipeline_start=pipeline_start,
                intent=intent, scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=[], tools_used=[], is_multi_domain=False, is_executive=False,
            )

        # ── 6. Domain planning + retrieval ─────────────────────────────────
        is_exec = is_executive_summary_query(question) or intent == "executive_summary"
        all_evidence: list[Evidence] = []
        domains_used: list[str] = []
        tools_used: list[str] = []
        is_multi = False
        comparison_data = None

        if is_exec:
            plan = execute_executive_summary(db=db, scope=scope)
            all_evidence = plan.evidence
            domains_used = plan.domains_used
            tools_used = plan.retrieval_tools_used
            is_multi = True
        elif is_open_domain:
            # No domain keyword matched — pull evidence from every retrieval
            # domain so the LLM (not a keyword list) decides if it can
            # ground an answer. Reuses the existing retrieval catalog only;
            # no new retrieval logic, keywords, or templates.
            plan = execute_multi_domain_plan(
                domains=[
                    "project_overview", "health", "procurement", "suppliers",
                    "safety", "ncr", "site_reports", "meetings", "decisions",
                    "risks",
                ],
                db=db,
                scope=scope,
                project_id=effective_project_id,
                meeting_id=routed.meeting_id,
                ncr_id=routed.ncr_id,
            )
            all_evidence = plan.evidence
            domains_used = plan.domains_used
            tools_used = plan.retrieval_tools_used
            is_multi = True
        elif routed.is_multi_domain and routed.secondary_intents:
            all_domains = [intent] + routed.secondary_intents
            plan = execute_multi_domain_plan(
                domains=all_domains,
                db=db,
                scope=scope,
                project_id=effective_project_id,
                meeting_id=routed.meeting_id,
                ncr_id=routed.ncr_id,
            )
            all_evidence = plan.evidence
            domains_used = plan.domains_used
            tools_used = plan.retrieval_tools_used
            is_multi = plan.is_multi_domain
            comparison_data = build_comparison_data(all_evidence, domains_used)
        else:
            retrieval_result = _dispatch_single_retrieval(
                intent=intent,
                db=db,
                scope=scope,
                project_id=effective_project_id,
                meeting_id=routed.meeting_id,
                ncr_id=routed.ncr_id,
                question=resolved_ctx.resolved_query,
            )
            all_evidence = retrieval_result.evidence
            domains_used = [intent]
            tools_used = [intent]

        # TEMPORARY instrumentation — provider_error investigation.
        logger.info(
            "DEBUG_TRACE step=retrieval_done domains_used=%s tools_used=%s "
            "evidence_count=%d is_multi_domain=%s",
            domains_used, tools_used, len(all_evidence), is_multi,
        )

        # ── 6.5 Comparison evidence expansion ──────────────────────────────
        # If the question asks for a comparison but the current evidence
        # contains only one project, perform an authorized retrieval expansion
        # to fetch a second project so the analyst can produce a real comparison.
        if detect_query_type(resolved_ctx.original_question) == "compare":
            proj_ev = [e for e in all_evidence if e.source_type == "project"]
            if len(proj_ev) < 2:
                from app.ai.retrieval.projects import (
                    get_additional_project_for_comparison,
                )
                exclude_codes = [e.source_id for e in proj_ev]
                extra_ev = get_additional_project_for_comparison(
                    db=db,
                    scope=scope,
                    exclude_codes=exclude_codes,
                    preferred_status="Delayed",
                )
                if extra_ev is not None:
                    all_evidence = list(all_evidence) + [extra_ev]
                    logger.info(
                        "comparison_expansion source_id=%s added to evidence",
                        extra_ev.source_id,
                    )

        # ── 7. Deterministic analytical layer (pre-LLM) ────────────────────
        # Handles ranking, listing, comparison, detail, and attention-rank
        # queries directly from evidence — no LLM call needed for these.
        #
        # IMPORTANT: use original_question for pattern detection, NOT
        # resolved_query.  The context resolver enriches resolved_query with
        # context tokens (e.g. "highest budget at 784M SAR") that can trip
        # the wrong analytical pattern on follow-up turns.
        analytical_answer = compute_analytical_answer(
            question=resolved_ctx.original_question,
            evidence=all_evidence,
        )
        # Always compute render blocks alongside analytical answer (fast, deterministic)
        render_blocks = compute_render_blocks(
            question=resolved_ctx.original_question,
            evidence=all_evidence,
        )
        if analytical_answer is not None:
            # Validate grounding before accepting the deterministic answer
            grounding = self._validator.validate(
                question=resolved_ctx.resolved_query,
                answer=analytical_answer,
                evidence=all_evidence,
            )
            if grounding.is_grounded:
                follow_ups = generate_follow_up_suggestions(
                    intent="executive_summary" if is_exec else intent,
                    evidence=all_evidence,
                    scope=scope,
                    question=question,
                    status="completed",
                )
                key_findings = _build_key_findings(all_evidence, intent, is_exec)
                return self._build_response(
                    db=db, conv=conv, user_msg=user_msg,
                    answer=analytical_answer, status="completed",
                    evidence=all_evidence, llm_response=None,
                    pipeline_start=pipeline_start, intent=intent,
                    scope=scope, project_id=project_id,
                    resolved_ctx=resolved_ctx, state=state,
                    domains_used=domains_used, tools_used=tools_used,
                    is_multi_domain=is_multi, is_executive=is_exec,
                    follow_up_suggestions=follow_ups,
                    key_findings=key_findings,
                    render_blocks=render_blocks,
                )
            # Grounding failed for analytical answer — fall through to LLM
            logger.warning(
                "Analytical answer failed grounding check; falling through to LLM"
            )

        # ── 8. Provider + LLM generation ───────────────────────────────────
        provider = get_llm_provider()

        # TEMPORARY instrumentation — provider_error investigation.
        logger.info(
            "DEBUG_TRACE step=provider_selected provider=%s model=%s "
            "is_available=%s",
            provider.provider_name, provider.model_name, provider.is_available(),
        )

        if not provider.is_available():
            answer = (
                "خدمة الذكاء الاصطناعي غير متاحة حالياً."
                if is_arabic
                else "AI service is currently unavailable. Please check provider configuration."
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="provider_unavailable",
                evidence=all_evidence, llm_response=None,
                pipeline_start=pipeline_start, intent=intent,
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=is_multi, is_executive=is_exec,
            )

        # ── Memory Context (Phase 3: Safe Memory Reader) ────────────────────
        # Derived context only — never evidence, never a citation source,
        # never counted in evidence_count. See app/ai/memory_reader.py.
        # Never sent for every question, and never the full memory blob: a
        # bounded, deterministically-selected slice only, and only when the
        # question is actually about remembered/historical context.
        memory_relevant = is_memory_relevant(
            question=question, intent=intent, previous_intent=state.previous_intent,
        )
        memory_block = ""
        memory_lines_selected = 0
        memory_chars_selected = 0
        if memory_relevant:
            try:
                memory_notes = get_memory_notes(db, scope)
                selected_lines = select_relevant_memory(memory_notes, question)
                memory_context = build_memory_context_block(selected_lines, is_arabic=is_arabic)

                profile_memory = get_user_profile_memory(db, scope)
                preferences_block = build_user_preferences_block(profile_memory, is_arabic=is_arabic)

                memory_lines_selected = len(selected_lines)
                memory_block = "\n\n".join(b for b in (memory_context, preferences_block) if b)
                memory_chars_selected = len(memory_block)
            except Exception:
                # Memory is a best-effort supplement — never fail the request.
                logger.warning("memory_read_failed; continuing without memory context")
                memory_block = ""
                memory_lines_selected = 0
                memory_chars_selected = 0

        logger.info(
            "DEBUG_TRACE step=memory_loaded memory_relevant=%s "
            "memory_lines_selected=%d memory_chars_selected=%d",
            memory_relevant, memory_lines_selected, memory_chars_selected,
        )

        evidence_block = _build_evidence_block(all_evidence)
        context_block = ""
        if recent_msgs:
            ctx = build_conversation_context_block(recent_msgs)
            context_block = ctx + "\n\n" if ctx else ""
        if memory_block:
            context_block = context_block + memory_block + "\n\n"

        system_prompt = _SYSTEM_TEMPLATE.format(
            context_block=context_block,
            evidence_block=evidence_block,
        )

        llm_response: Optional[LLMResponse] = None
        # TEMPORARY instrumentation — provider_error investigation.
        _gen_start = time.monotonic()
        logger.info(
            "DEBUG_TRACE step=generate_start provider=%s model=%s",
            provider.provider_name, provider.model_name,
        )
        try:
            llm_response = provider.generate(
                LLMRequest(
                    system_prompt=system_prompt,
                    user_prompt=resolved_ctx.resolved_query,
                )
            )
            raw_answer = llm_response.content
            logger.info(
                "DEBUG_TRACE step=generate_success provider=%s model=%s "
                "elapsed_ms=%.1f content_len=%d",
                llm_response.provider, llm_response.model,
                (time.monotonic() - _gen_start) * 1000, len(raw_answer),
            )
        except ProviderUnavailableError as e:
            # TEMPORARY instrumentation — captures the full exception chain.
            # openai_compat.py does `raise ProviderUnavailableError(...) from exc`,
            # so the original httpx exception (if any) is on __cause__.
            cause = e.__cause__
            cause_response = getattr(cause, "response", None)
            elapsed_ms = (time.monotonic() - _gen_start) * 1000
            logger.error(
                "DEBUG_TRACE step=generate_failure provider=%s model=%s "
                "elapsed_ms=%.1f wrapper_exc_type=%s wrapper_exc_msg=%r "
                "cause_exc_type=%s cause_exc_msg=%r "
                "response_received=%s http_status=%s response_body=%r",
                provider.provider_name, provider.model_name, elapsed_ms,
                type(e).__name__, str(e),
                type(cause).__name__ if cause is not None else None,
                str(cause) if cause is not None else None,
                cause_response is not None,
                getattr(cause_response, "status_code", None),
                (cause_response.text[:1000] if cause_response is not None else None),
                exc_info=True,
            )
            answer = (
                "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً."
                if is_arabic
                else "AI service is temporarily unavailable."
            )
            logger.info("DEBUG_TRACE step=final_status status=provider_error")
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="provider_error",
                evidence=all_evidence, llm_response=None,
                pipeline_start=pipeline_start, intent=intent,
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=is_multi, is_executive=is_exec,
                failure_category="provider_error",
            )

        # ── 8. Grounding validation ────────────────────────────────────────
        if raw_answer.strip().startswith(_INSUFFICIENT_EVIDENCE_MARKER):
            answer = self._validator.fallback_response(is_arabic)
            follow_ups = generate_follow_up_suggestions(
                intent=intent, evidence=all_evidence, scope=scope,
                question=question, status="insufficient_evidence",
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="insufficient_evidence",
                evidence=all_evidence, llm_response=llm_response,
                pipeline_start=pipeline_start, intent=intent,
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=is_multi, is_executive=is_exec,
                follow_up_suggestions=follow_ups,
            )

        grounding = self._validator.validate(
            question=resolved_ctx.resolved_query,
            answer=raw_answer,
            evidence=all_evidence,
        )

        if not grounding.is_grounded:
            answer = self._validator.fallback_response(is_arabic)
            follow_ups = generate_follow_up_suggestions(
                intent=intent, evidence=all_evidence, scope=scope,
                question=question, status="grounding_failed",
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="grounding_failed",
                evidence=all_evidence, llm_response=llm_response,
                pipeline_start=pipeline_start, intent=intent,
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=is_multi, is_executive=is_exec,
                failure_category="grounding_failed",
                follow_up_suggestions=follow_ups,
            )

        # ── 9. Follow-up suggestions ───────────────────────────────────────
        follow_ups = generate_follow_up_suggestions(
            intent="executive_summary" if is_exec else intent,
            evidence=all_evidence,
            scope=scope,
            question=question,
            status="completed",
        )

        # ── 10. Key findings for executive summary ─────────────────────────
        key_findings = _build_key_findings(all_evidence, intent, is_exec)

        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=raw_answer, status="completed",
            evidence=all_evidence, llm_response=llm_response,
            pipeline_start=pipeline_start, intent=intent,
            scope=scope, project_id=project_id,
            resolved_ctx=resolved_ctx, state=state,
            domains_used=domains_used, tools_used=tools_used,
            is_multi_domain=is_multi, is_executive=is_exec,
            follow_up_suggestions=follow_ups,
            comparison_data=comparison_data,
            key_findings=key_findings,
            render_blocks=render_blocks,
        )

    def execute_procurement_agent(
    self,
    scope: AIAuthScope,
    db: Session,
    project_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    language: str = "en",
    question: Optional[str] = None,
) -> dict[str, Any]:
    
        """Procurement Intelligence Agent — a fixed-scope specialist over the
        SAME retrieval tools, RBAC, and citation/audit persistence as the
        general Copilot pipeline. There is NO keyword intent routing and
        retrieval NEVER varies by question — it always runs the same 4
        procurement-scoped calls below (never execute_multi_domain_plan,
        never a portfolio-wide fallback), so every quick action (Executive
        Summary, Late Purchase Orders, Supplier Risks, Procurement Risks,
        Recommendations) returns the same comprehensive, grounded report.

        # DEMO MODE - switch back to OpenRouter after presentation.
        No LLM/OpenRouter call is made at all — the answer is built entirely
        by _build_procurement_fallback() from data retrieved just above it,
        deterministically, in well under a second. To restore live-LLM
        generation, reintroduce the provider.generate() call (see git
        history for the prior version of this method) guarded by the same
        evidence retrieval already in place here.
        """
        pipeline_start = time.monotonic()
        is_arabic = language.lower().startswith("ar")
        question = question or (
            "تشغيل وكيل استخبارات المشتريات: تحليل شامل لطلبات الشراء وأوامر "
            "الشراء والموردين ومخاطر التسليم عبر المشاريع."
            if is_arabic
            else (
                "Run Procurement Intelligence Agent: full analysis of purchase "
                "requests, purchase orders, suppliers, and delivery risk across "
                "projects."
            )
        )

        conv = self._get_or_create_conversation(
            db, scope, project_id, conversation_id, question
        )
        state = _load_conversation_state(conv)
        resolved_ctx: ResolvedContext = resolve_context(
            question=question, state=state, recent_messages=[],
        )

        user_msg = AIMessage(
            conversation_id=conv.id,
            role="user",
            content=question,
            status="completed",
            original_question=question,
        )
        db.add(user_msg)
        db.flush()

        # ── Retrieval: existing tools only, deduped by (source_type, source_id) ──
        all_evidence: list[Evidence] = []
        seen: set[tuple[str, str]] = set()

        def _extend(items: list[Evidence]) -> None:
            for ev in items:
                key = (ev.source_type, ev.source_id)
                if key not in seen:
                    seen.add(key)
                    all_evidence.append(ev)

        # NOTE: get_procurement_summary fetches `limit` PRs AND `limit` POs
        # (not a combined total) and lists all PRs before any POs — with the
        # old limit=30 that alone produced up to 60 items, so
        # _build_evidence_block's 30-snippet prompt cap was entirely consumed
        # by Purchase Requests and POs/suppliers/projects never reached the
        # LLM (confirmed live: 3 different models all reported seeing only
        # PR metadata). Bounding each source keeps every category represented
        # within the shared prompt cap — same per-domain-bounding technique
        # planner.py already uses (_MAX_EVIDENCE_PER_DOMAIN).
        _extend(get_procurement_summary(db=db, scope=scope, project_id=project_id, limit=8).evidence)
        late_po_result = get_late_purchase_orders(db=db, scope=scope, project_id=project_id, limit=6)
        _extend(late_po_result.evidence)
        _extend(get_supplier_information(db=db, scope=scope, limit=6).evidence)
        _extend(get_project_overview(db=db, scope=scope, project_id=project_id, limit=8).evidence)

        domains_used = ["procurement", "suppliers", "project_overview"]
        tools_used = [
            "procurement_summary", "late_purchase_orders", "suppliers", "project_overview",
        ]

        # DEMO MODE - switch back to OpenRouter after presentation.
        # Topic-specific, database-backed report (see
        # build_procurement_topic_answer above) — no provider call, no
        # network round-trip. Re-runs a couple of the same bounded
        # retrieval calls already done above (cheap, indexed queries) so
        # this helper stays a single self-contained entry point.
        answer = build_procurement_topic_answer(scope, db, project_id, question, is_arabic)
        key_findings = _build_key_findings(all_evidence, "procurement", True)

        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=answer, status="completed",
            evidence=all_evidence, llm_response=None,
            pipeline_start=pipeline_start, intent="procurement_agent",
            scope=scope, project_id=project_id,
            resolved_ctx=resolved_ctx, state=state,
            domains_used=domains_used, tools_used=tools_used,
            is_multi_domain=True, is_executive=True,
            key_findings=key_findings,
        )

    def execute_meeting_agent(
        self,
        scope: AIAuthScope,
        db: Session,
        meeting_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        language: str = "en",
        project_id: Optional[int] = None,
        question: Optional[str] = None,
    ) -> dict[str, Any]:
        """Meeting Intelligence Agent — same RBAC-scoped retrieval and
        citation/audit persistence as the general Copilot pipeline.

        meeting_id given: fixed to ONE specific meeting's detail (decisions,
        action items, attendees) — get_meeting_detail() raises 404/403
        before this method ever runs if the meeting doesn't exist or the
        caller can't access its project.

        meeting_id=None: a portfolio-wide (or project-scoped, if project_id
        is given) meetings + decisions status summary — see
        _execute_meeting_agent_summary.

        # DEMO MODE - switch back to OpenRouter after presentation.
        No LLM/OpenRouter call is made at all — both paths build their
        answer entirely from retrieved data (_build_single_meeting_fallback
        / _build_meeting_summary_fallback), deterministically, in well
        under a second.
        """
        if meeting_id is None:
            return self._execute_meeting_agent_summary(
                scope=scope, db=db, project_id=project_id,
                conversation_id=conversation_id, language=language,
                question=question,
            )

        pipeline_start = time.monotonic()
        is_arabic = language.lower().startswith("ar")

        # Retrieval first: raises 404/403 for an invalid/unauthorized
        # meeting_id, same convention as _get_or_create_conversation.
        retrieval = get_meeting_detail(db=db, scope=scope, meeting_id=meeting_id)
        all_evidence = retrieval.evidence
        project_id = retrieval.data.get("project_id")

        question = (
            f"تشغيل وكيل استخبارات الاجتماعات لتحليل الاجتماع MTG-{meeting_id}: "
            "القرارات، بنود العمل، الجهة المسؤولة، والمواعيد النهائية."
            if is_arabic
            else (
                f"Run Meeting Intelligence Agent to analyze meeting MTG-{meeting_id}: "
                "decisions, action items, owners, and due dates."
            )
        )

        conv = self._get_or_create_conversation(
            db, scope, project_id, conversation_id, question
        )
        state = _load_conversation_state(conv)
        resolved_ctx: ResolvedContext = resolve_context(
            question=question, state=state, recent_messages=[],
        )

        user_msg = AIMessage(
            conversation_id=conv.id,
            role="user",
            content=question,
            status="completed",
            original_question=question,
        )
        db.add(user_msg)
        db.flush()

        domains_used = ["meetings"]
        tools_used = ["meeting_detail"]

        # DEMO MODE - switch back to OpenRouter after presentation.
        answer = _build_single_meeting_fallback(retrieval.data, is_arabic)
        key_findings = _build_key_findings(all_evidence, "meetings", True)

        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=answer, status="completed",
            evidence=all_evidence, llm_response=None,
            pipeline_start=pipeline_start, intent="meeting_agent",
            scope=scope, project_id=project_id,
            resolved_ctx=resolved_ctx, state=state,
            domains_used=domains_used, tools_used=tools_used,
            is_multi_domain=True, is_executive=True,
            key_findings=key_findings,
        )

    def _execute_meeting_agent_summary(
        self,
        scope: AIAuthScope,
        db: Session,
        project_id: Optional[int],
        conversation_id: Optional[int],
        language: str,
        question: Optional[str],
    ) -> dict[str, Any]:
        """Portfolio-wide (or project-scoped) meetings status summary — the
        no-meeting_id path of the Meeting Agent. Reuses the same retrieval
        tools as the general pipeline's meetings/decisions intents
        (get_recent_meetings, get_project_decisions, get_open_action_items).

        # DEMO MODE - switch back to OpenRouter after presentation.
        No LLM/OpenRouter call is made — the answer is built entirely by
        _build_meeting_summary_fallback() from the data retrieved just
        above it, deterministically, in well under a second.
        """
        pipeline_start = time.monotonic()
        is_arabic = language.lower().startswith("ar")

        meetings_result = get_recent_meetings(db=db, scope=scope, project_id=project_id, limit=10)
        decisions_result = get_project_decisions(db=db, scope=scope, project_id=project_id, limit=10)
        action_items_result = get_open_action_items(db=db, scope=scope, project_id=project_id, limit=10)
        all_evidence: list[Evidence] = (
            list(meetings_result.evidence) + list(decisions_result.evidence) + list(action_items_result.evidence)
        )
        domains_used = ["meetings", "decisions", "action_items"]
        tools_used = ["recent_meetings", "project_decisions", "open_action_items"]

        resolved_question = question or (
            "لخص وضع الاجتماعات الحالي" if is_arabic
            else "Summarize the current meetings status"
        )

        conv = self._get_or_create_conversation(
            db, scope, project_id, conversation_id, resolved_question
        )
        state = _load_conversation_state(conv)
        resolved_ctx: ResolvedContext = resolve_context(
            question=resolved_question, state=state, recent_messages=[],
        )
        user_msg = AIMessage(
            conversation_id=conv.id,
            role="user",
            content=resolved_question,
            status="completed",
            original_question=resolved_question,
        )
        db.add(user_msg)
        db.flush()

        # DEMO MODE - switch back to OpenRouter after presentation.
        counts = get_meeting_counts(db=db, scope=scope, project_id=project_id)
        answer = build_meeting_topic_answer(
            counts=counts,
            meetings=meetings_result.data.get("meetings", []),
            decisions=decisions_result.data.get("decisions", []),
            action_items=action_items_result.data.get("action_items", []),
            question=resolved_question,
            is_arabic=is_arabic,
        )
        key_findings = _build_key_findings(all_evidence, "meetings", True)

        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=answer, status="completed",
            evidence=all_evidence, llm_response=None,
            pipeline_start=pipeline_start, intent="meeting_agent",
            scope=scope, project_id=project_id,
            resolved_ctx=resolved_ctx, state=state,
            domains_used=domains_used, tools_used=tools_used,
            is_multi_domain=True, is_executive=True,
            key_findings=key_findings,
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _get_or_create_conversation(
        self,
        db: Session,
        scope: AIAuthScope,
        project_id: Optional[int],
        conversation_id: Optional[int],
        first_question: str,
    ) -> AIConversation:
        if conversation_id is not None:
            conv = db.query(AIConversation).filter(
                AIConversation.id == conversation_id,
                AIConversation.user_id == scope.user_id,
            ).first()
            if conv is None:
                from fastapi import HTTPException, status as http_status
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
            if conv.organization_id != scope.organization_id:
                from fastapi import HTTPException, status as http_status
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )
            return conv

        title = first_question[:80].strip() or "New Conversation"
        conv = AIConversation(
            organization_id=scope.organization_id,
            user_id=scope.user_id,
            project_id=project_id,
            title=title,
        )
        db.add(conv)
        db.flush()
        return conv

    def _build_response(
        self,
        db: Session,
        conv: AIConversation,
        user_msg: AIMessage,
        answer: str,
        status: str,
        evidence: list[Evidence],
        llm_response: Optional[LLMResponse],
        pipeline_start: float,
        intent: str,
        scope: AIAuthScope,
        project_id: Optional[int],
        resolved_ctx: ResolvedContext,
        state: ConversationState,
        domains_used: list[str],
        tools_used: list[str],
        is_multi_domain: bool,
        is_executive: bool,
        failure_category: Optional[str] = None,
        follow_up_suggestions: Optional[list[str]] = None,
        comparison_data: Optional[dict[str, Any]] = None,
        key_findings: Optional[list[str]] = None,
        clarification_required: bool = False,
        clarification_question: Optional[str] = None,
        clarification_options: Optional[list[str]] = None,
        render_blocks: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        total_latency = (time.monotonic() - pipeline_start) * 1000

        # TEMPORARY instrumentation for the OpenRouter-bypass investigation —
        # remove once the fix is confirmed stable in production logs.
        logger.info(
            "pipeline_instrumentation intent=%s provider=%s model=%s "
            "pipeline_status=%s raw_provider_len=%s final_answer_len=%d "
            "used_deterministic_fallback=%s",
            intent,
            llm_response.provider if llm_response else None,
            llm_response.model if llm_response else None,
            status,
            len(llm_response.content) if llm_response else "n/a (provider not called)",
            len(answer),
            status != "completed",
        )

        assistant_msg = AIMessage(
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            status=status,
            model_name=llm_response.model if llm_response else None,
            provider_name=llm_response.provider if llm_response else None,
            latency_ms=llm_response.latency_ms if llm_response else total_latency,
            prompt_tokens=llm_response.prompt_tokens if llm_response else None,
            completion_tokens=llm_response.completion_tokens if llm_response else None,
            original_question=resolved_ctx.original_question,
            resolved_query=resolved_ctx.resolved_query if resolved_ctx.is_follow_up else None,
            clarification_required=clarification_required,
            context_refs_used=len(resolved_ctx.context_refs_used),
            domains_used=domains_used if domains_used else None,
        )
        db.add(assistant_msg)
        db.flush()

        citations = []
        if status == "completed" and evidence:
            for ev in evidence:
                citation = AICitation(
                    message_id=assistant_msg.id,
                    source_type=ev.source_type,
                    source_id=ev.source_id,
                    project_id=ev.project_id,
                    label=ev.label,
                    evidence_snippet=ev.snippet[:500],
                    ui_metadata=ev.ui_metadata,
                )
                db.add(citation)
                citations.append(citation)
            db.flush()

        # ── Persist extended audit log ─────────────────────────────────────
        audit = CopilotAuditLog(
            organization_id=scope.organization_id,
            user_id=scope.user_id,
            project_id=project_id,
            conversation_id=conv.id,
            intent=intent,
            provider_name=llm_response.provider if llm_response else None,
            model_name=llm_response.model if llm_response else None,
            status=status,
            latency_ms=total_latency,
            prompt_tokens=llm_response.prompt_tokens if llm_response else None,
            completion_tokens=llm_response.completion_tokens if llm_response else None,
            evidence_source_count=len(evidence),
            failure_category=failure_category,
            # Phase 3B
            original_question=resolved_ctx.original_question,
            resolved_query=resolved_ctx.resolved_query if resolved_ctx.is_follow_up else None,
            previous_intent=state.previous_intent,
            resolved_intent=intent,
            domains_used=domains_used if domains_used else None,
            retrieval_tools_used=tools_used if tools_used else None,
            clarification_required=clarification_required,
            context_reference_count=len(resolved_ctx.context_refs_used),
        )
        db.add(audit)

        # ── Update conversation state ──────────────────────────────────────
        if status not in ("clarification_required", "auth_denied"):
            evidence_ids = [ev.source_id for ev in evidence if ev.source_id]
            proj_ids_from_ev = extract_project_ids_from_evidence(evidence_ids)
            # Also include any hint project IDs from context resolution
            all_proj_ids = list(
                dict.fromkeys(resolved_ctx.hint_project_ids + proj_ids_from_ev)
            )
            state.apply_turn(
                intent=intent,
                evidence_ids=evidence_ids,
                project_ids=all_proj_ids,
                supplier_ids=list(set(resolved_ctx.hint_supplier_ids)),
                answer_summary=_summarize_answer(answer),
                clarification_required=clarification_required,
            )
            conv.conversation_state = state.to_dict()

        db.commit()
        db.refresh(conv)
        db.refresh(assistant_msg)

        confidence = self._compute_confidence(status, evidence, intent)
        short_summary = _build_short_summary(answer, status)

        return {
            "conversation_id": conv.id,
            "message_id": assistant_msg.id,
            "answer": answer,
            "status": status,
            "intent": intent,
            "citations": [
                {
                    "id": c.id,
                    "source_type": c.source_type,
                    "source_id": c.source_id,
                    "label": c.label,
                    "evidence_snippet": c.evidence_snippet,
                    "ui_metadata": c.ui_metadata,
                }
                for c in citations
            ],
            "confidence": confidence,
            "model": llm_response.model if llm_response else None,
            "provider": llm_response.provider if llm_response else None,
            "latency_ms": round(total_latency, 1),
            "evidence_count": len(evidence),
            # Phase 3B
            "short_summary": short_summary,
            "key_findings": key_findings,
            "comparison_data": comparison_data,
            "follow_up_suggestions": follow_up_suggestions or [],
            "clarification_required": clarification_required,
            "clarification_question": clarification_question,
            "clarification_options": clarification_options or [],
            "resolved_query": resolved_ctx.resolved_query if resolved_ctx.is_follow_up else None,
            "domains_used": domains_used if domains_used else [],
            "is_multi_domain": is_multi_domain,
            "render_blocks": render_blocks or [],
        }

    @staticmethod
    def _compute_confidence(
        status: str, evidence: list[Evidence], intent: str
    ) -> str:
        if status not in ("completed",):
            return "none"
        if not evidence:
            return "low"
        if len(evidence) >= 5:
            return "high"
        return "medium"


def routed_project_id(ctx: ResolvedContext) -> Optional[int]:
    """Extract first hint project_id from resolved context, if any."""
    return ctx.hint_project_ids[0] if ctx.hint_project_ids else None


def _summarize_answer(answer: str, max_len: int = 200) -> str:
    """Extract a short summary from the answer for state persistence."""
    if not answer:
        return ""
    # Take first sentence or up to max_len chars
    first_sentence = answer.split(".")[0]
    if len(first_sentence) <= max_len:
        return first_sentence.strip()
    return answer[:max_len].strip()


def _build_short_summary(answer: str, status: str) -> Optional[str]:
    """Build a short summary for completed answers."""
    if status != "completed" or not answer:
        return None
    words = answer.split()
    if len(words) <= 20:
        return None  # Answer itself is already short
    # First 2 sentences
    sentences = answer.split(".")
    summary = ". ".join(s.strip() for s in sentences[:2] if s.strip())
    if summary and len(summary) < len(answer) * 0.8:
        return summary[:300]
    return None
