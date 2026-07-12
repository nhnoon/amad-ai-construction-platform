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

import concurrent.futures
import logging
import time
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
from app.ai.planner import (
    build_comparison_data, detect_required_domains, execute_executive_summary,
    execute_multi_domain_plan, is_executive_summary_query,
)
from app.ai.providers.base import LLMRequest, LLMResponse, ProviderUnavailableError
from app.ai.providers.factory import get_llm_provider
from app.ai.retrieval.base import Evidence, RetrievalResult
from app.ai.retrieval.meetings import get_meeting_detail, get_project_decisions, get_recent_meetings
from app.ai.retrieval.procurement import (
    get_late_purchase_orders, get_procurement_summary, get_supplier_information,
)
from app.ai.retrieval.projects import get_project_overview, get_project_risks, get_health_overview
from app.ai.retrieval.safety import get_open_ncrs, get_safety_summary
from app.ai.retrieval.site_reports import (
    get_recent_daily_activities, get_recent_site_reports,
)
from app.ai.scope import AIAuthScope
from app.models.ai_copilot import AIConversation, AICitation, AIMessage, CopilotAuditLog

logger = logging.getLogger(__name__)

_MAX_QUESTION_LEN = 2000
_MAX_EVIDENCE_SNIPPETS = 30
_MAX_CONTEXT_MESSAGES = 10  # bounded: last 5 turns

# Meeting Agent portfolio-wide summary: the LLM call is time-boxed to this
# many seconds (independent of the provider's own retry/timeout settings in
# openai_compat.py, which are shared by every other caller and not touched
# here) so a slow or unreachable provider can never produce the "infinite
# loading" experience — on timeout the deterministic summary below is
# returned instead. Runs on its own executor so a hung request doesn't
# consume worker threads used elsewhere.
_MEETING_AGENT_LLM_TIMEOUT_S = 4.0
_meeting_agent_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="meeting-agent-llm"
)

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
   Action Items
   Risks and Blockers
   Follow-up Items
   Escalation Required
   Confidence
   Sources"""

_MEETING_AGENT_HEADINGS_AR = """\
   الملخص التنفيذي
   القرارات
   بنود العمل
   المخاطر والمعوقات
   بنود المتابعة
   هل يتطلب الأمر تصعيداً
   مستوى الثقة
   المصادر"""


def _meeting_agent_system_prompt(evidence_block: str, is_arabic: bool) -> str:
    headings = _MEETING_AGENT_HEADINGS_AR if is_arabic else _MEETING_AGENT_HEADINGS_EN
    unavailable_phrase = (
        "غير متاح في قاعدة البيانات الحالية."
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
Under Action Items / بنود العمل, list each item with its Owner and Due Date \
inline (translated into Arabic when responding in Arabic).
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


def _dispatch_single_retrieval(
    intent: str,
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int],
) -> RetrievalResult:
    kwargs: dict[str, Any] = {"db": db, "scope": scope, "project_id": project_id}

    if intent == "project_overview":
        return get_project_overview(**kwargs)
    if intent == "procurement":
        return get_procurement_summary(**kwargs)
    if intent == "suppliers":
        return get_supplier_information(db=db, scope=scope)
    if intent == "safety":
        return get_safety_summary(**kwargs)
    if intent == "ncr":
        return get_open_ncrs(**kwargs)
    if intent == "site_reports":
        return get_recent_site_reports(**kwargs)
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
    meetings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    is_arabic: bool,
) -> str:
    """Deterministic (no-LLM) meetings status summary, built only from the
    same evidence rows the LLM would have seen. Used whenever the Meeting
    Agent's portfolio-wide summary call times out, hits a rate limit, or
    comes back ungrounded — never a raw provider error, always a real
    answer grounded in the retrieved meetings/decisions.
    """
    total_meetings = len(meetings)
    total_decisions = len(decisions)

    type_counts: dict[str, int] = {}
    for m in meetings:
        mt = m.get("meeting_type") or "Other"
        type_counts[mt] = type_counts.get(mt, 0) + 1
    safety_meetings = type_counts.get("Safety", 0)

    sample_meeting_codes = [f"MTG-{m['id']}" for m in meetings[:5]]
    sample_decision_codes = [f"DEC-{d['id']}" for d in decisions[:5]]

    if safety_meetings > 0:
        concern_en = f"{safety_meetings} of the recent meetings are safety-related and warrant close follow-up."
        concern_ar = f"{safety_meetings} من الاجتماعات الأخيرة متعلقة بالسلامة وتستدعي متابعة دقيقة."
    elif total_meetings > 0 and total_decisions < total_meetings / 2:
        concern_en = "Relatively few formal decisions are on record compared to the number of meetings held."
        concern_ar = "عدد القرارات الرسمية المسجّلة محدود مقارنة بعدد الاجتماعات المعقودة."
    elif total_meetings == 0:
        concern_en = "No recent meetings are on record."
        concern_ar = "لا توجد اجتماعات مسجّلة مؤخراً."
    else:
        concern_en = "No significant concern stands out in the available meeting data."
        concern_ar = "لا توجد مخاوف جوهرية بارزة في بيانات الاجتماعات المتاحة."

    recommendation_en = "Ensure every recent decision has a named owner and confirm follow-up items are being tracked to closure."
    recommendation_ar = "التأكد من تعيين مسؤول لكل قرار حديث ومتابعة تنفيذ بنود المتابعة حتى إغلاقها."

    if is_arabic:
        lines = [
            f"إجمالي الاجتماعات: {total_meetings}",
            f"إجمالي القرارات: {total_decisions}",
        ]
        if total_meetings > 0:
            lines.append(
                "بنود المتابعة: غير متاحة على مستوى المحفظة في هذا العرض — راجع اجتماعاً محدداً لعرض بنود العمل."
            )
        lines.append(f"أبرز ملاحظة: {concern_ar}")
        lines.append(f"التوصية: {recommendation_ar}")
        sources = sample_meeting_codes + sample_decision_codes
        if sources:
            lines.append(f"المصادر: {', '.join(sources)}")
        return "\n".join(lines)

    lines = [
        f"Total meetings: {total_meetings}",
        f"Total decisions: {total_decisions}",
    ]
    if total_meetings > 0:
        lines.append(
            "Follow-up items: not available at the portfolio level in this view — open a specific meeting to see its action items."
        )
    lines.append(f"Main concern: {concern_en}")
    lines.append(f"Recommendation: {recommendation_en}")
    sources = sample_meeting_codes + sample_decision_codes
    if sources:
        lines.append(f"Sources: {', '.join(sources)}")
    return "\n".join(lines)


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

        evidence_block = _build_evidence_block(all_evidence)
        context_block = ""
        if recent_msgs:
            ctx = build_conversation_context_block(recent_msgs)
            context_block = ctx + "\n\n" if ctx else ""

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
        SAME retrieval tools, LLM provider, grounding validator, RBAC, and
        citation/audit persistence as the general Copilot pipeline. There is
        NO keyword intent routing and retrieval NEVER varies by question —
        it always runs the same 4 procurement-scoped calls below (never
        execute_multi_domain_plan, never a portfolio-wide fallback), so an
        optional free-text `question` only changes what the LLM is asked to
        focus on in its answer, never what evidence is retrieved or cited.
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
        _extend(get_late_purchase_orders(db=db, scope=scope, project_id=project_id, limit=6).evidence)
        _extend(get_supplier_information(db=db, scope=scope, limit=6).evidence)
        _extend(get_project_overview(db=db, scope=scope, project_id=project_id, limit=8).evidence)

        domains_used = ["procurement", "suppliers", "project_overview"]
        tools_used = [
            "procurement_summary", "late_purchase_orders", "suppliers", "project_overview",
        ]

        provider = get_llm_provider()
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
                pipeline_start=pipeline_start, intent="procurement_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
            )

        evidence_block = _build_evidence_block(all_evidence)
        system_prompt = _procurement_agent_system_prompt(evidence_block, is_arabic)

        llm_response: Optional[LLMResponse] = None
        _gen_start = time.monotonic()
        try:
            llm_response = provider.generate(
                LLMRequest(system_prompt=system_prompt, user_prompt=question)
            )
            raw_answer = llm_response.content
        except ProviderUnavailableError as e:
            # TEMPORARY instrumentation — same provider_error investigation
            # as execute()'s generate_failure logging.
            cause = e.__cause__
            cause_response = getattr(cause, "response", None)
            logger.error(
                "DEBUG_TRACE step=procurement_agent_generate_failure "
                "elapsed_ms=%.1f evidence_count=%d wrapper_exc_type=%s "
                "wrapper_exc_msg=%r cause_exc_type=%s cause_exc_msg=%r "
                "response_received=%s http_status=%s",
                (time.monotonic() - _gen_start) * 1000, len(all_evidence),
                type(e).__name__, str(e),
                type(cause).__name__ if cause is not None else None,
                str(cause) if cause is not None else None,
                cause_response is not None,
                getattr(cause_response, "status_code", None),
                exc_info=True,
            )
            answer = (
                "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً."
                if is_arabic
                else "AI service is temporarily unavailable."
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="provider_error",
                evidence=all_evidence, llm_response=None,
                pipeline_start=pipeline_start, intent="procurement_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
                failure_category="provider_error",
            )

        if raw_answer.strip().startswith(_INSUFFICIENT_EVIDENCE_MARKER):
            # TEMPORARY instrumentation — logs the model's literal stated
            # reason, and how much of the evidence block it actually saw.
            logger.warning(
                "DEBUG_TRACE step=procurement_agent_insufficient raw_answer=%r "
                "evidence_count=%d evidence_block_chars=%d",
                raw_answer, len(all_evidence), len(evidence_block),
            )
            answer = self._validator.fallback_response(is_arabic)
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="insufficient_evidence",
                evidence=all_evidence, llm_response=llm_response,
                pipeline_start=pipeline_start, intent="procurement_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
            )

        grounding = self._validator.validate(
            question=question, answer=raw_answer, evidence=all_evidence,
        )
        if not grounding.is_grounded:
            answer = self._validator.fallback_response(is_arabic)
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="grounding_failed",
                evidence=all_evidence, llm_response=llm_response,
                pipeline_start=pipeline_start, intent="procurement_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
                failure_category="grounding_failed",
            )

        key_findings = _build_key_findings(all_evidence, "procurement", True)

        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=raw_answer, status="completed",
            evidence=all_evidence, llm_response=llm_response,
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
        """Meeting Intelligence Agent — same RBAC-scoped retrieval, LLM
        provider, grounding validator, and citation/audit persistence as the
        general Copilot pipeline.

        meeting_id given: fixed to ONE specific meeting's detail (decisions,
        action items, attendees) — get_meeting_detail() raises 404/403
        before this method ever runs if the meeting doesn't exist or the
        caller can't access its project.

        meeting_id=None: a portfolio-wide (or project-scoped, if project_id
        is given) meetings + decisions status summary — see
        _execute_meeting_agent_summary for its own bounded-timeout /
        deterministic-fallback handling.
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

        provider = get_llm_provider()
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
                pipeline_start=pipeline_start, intent="meeting_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
            )

        evidence_block = _build_evidence_block(all_evidence)
        system_prompt = _meeting_agent_system_prompt(evidence_block, is_arabic)

        llm_response: Optional[LLMResponse] = None
        try:
            llm_response = provider.generate(
                LLMRequest(system_prompt=system_prompt, user_prompt=question)
            )
            raw_answer = llm_response.content
        except ProviderUnavailableError:
            answer = (
                "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً."
                if is_arabic
                else "AI service is temporarily unavailable."
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="provider_error",
                evidence=all_evidence, llm_response=None,
                pipeline_start=pipeline_start, intent="meeting_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
                failure_category="provider_error",
            )

        if raw_answer.strip().startswith(_INSUFFICIENT_EVIDENCE_MARKER):
            answer = self._validator.fallback_response(is_arabic)
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="insufficient_evidence",
                evidence=all_evidence, llm_response=llm_response,
                pipeline_start=pipeline_start, intent="meeting_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
            )

        grounding = self._validator.validate(
            question=question, answer=raw_answer, evidence=all_evidence,
        )
        if not grounding.is_grounded:
            answer = self._validator.fallback_response(is_arabic)
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="grounding_failed",
                evidence=all_evidence, llm_response=llm_response,
                pipeline_start=pipeline_start, intent="meeting_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
                failure_category="grounding_failed",
            )

        key_findings = _build_key_findings(all_evidence, "meetings", True)

        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=raw_answer, status="completed",
            evidence=all_evidence, llm_response=llm_response,
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
        (get_recent_meetings, get_project_decisions). The LLM call is
        time-boxed to _MEETING_AGENT_LLM_TIMEOUT_S; a timeout, rate limit,
        empty/insufficient answer, or failed grounding check all fall back
        to _build_meeting_summary_fallback() — a real, evidence-grounded
        answer, never a raw provider-error string — so this endpoint always
        returns a usable answer within a few seconds.
        """
        pipeline_start = time.monotonic()
        is_arabic = language.lower().startswith("ar")

        meetings_result = get_recent_meetings(db=db, scope=scope, project_id=project_id, limit=15)
        decisions_result = get_project_decisions(db=db, scope=scope, project_id=project_id, limit=15)
        all_evidence: list[Evidence] = list(meetings_result.evidence) + list(decisions_result.evidence)
        domains_used = ["meetings", "decisions"]
        tools_used = ["recent_meetings", "project_decisions"]

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

        fallback_answer = _build_meeting_summary_fallback(
            meetings=meetings_result.data.get("meetings", []),
            decisions=decisions_result.data.get("decisions", []),
            is_arabic=is_arabic,
        )

        def _fallback_response(reason: str) -> dict[str, Any]:
            logger.info(
                "meeting_agent_summary_fallback reason=%s evidence_count=%d",
                reason, len(all_evidence),
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=fallback_answer, status="completed",
                evidence=all_evidence, llm_response=None,
                pipeline_start=pipeline_start, intent="meeting_agent",
                scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=domains_used, tools_used=tools_used,
                is_multi_domain=True, is_executive=True,
            )

        provider = get_llm_provider()
        if not provider.is_available():
            return _fallback_response("provider_unavailable")

        evidence_block = _build_evidence_block(all_evidence)
        system_prompt = _meeting_agent_system_prompt(evidence_block, is_arabic)

        future = _meeting_agent_executor.submit(
            provider.generate,
            LLMRequest(system_prompt=system_prompt, user_prompt=resolved_question),
        )
        try:
            llm_response = future.result(timeout=_MEETING_AGENT_LLM_TIMEOUT_S)
            raw_answer = llm_response.content
        except Exception as exc:
            return _fallback_response(f"{type(exc).__name__}: {exc}")

        if raw_answer.strip().startswith(_INSUFFICIENT_EVIDENCE_MARKER):
            return _fallback_response("insufficient_evidence")

        grounding = self._validator.validate(
            question=resolved_question, answer=raw_answer, evidence=all_evidence,
        )
        if not grounding.is_grounded:
            return _fallback_response("grounding_failed")

        key_findings = _build_key_findings(all_evidence, "meetings", True)
        return self._build_response(
            db=db, conv=conv, user_msg=user_msg,
            answer=raw_answer, status="completed",
            evidence=all_evidence, llm_response=llm_response,
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
