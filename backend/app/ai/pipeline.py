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
from app.ai.retrieval.meetings import get_project_decisions, get_recent_meetings
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

        if intent == "unknown":
            follow_ups = generate_follow_up_suggestions(
                intent="unknown",
                evidence=[],
                scope=scope,
                question=question,
                status="unsupported_intent",
            )
            answer = (
                "يمكنني المساعدة في المشاريع، المشتريات، السلامة، التقارير والاجتماعات."
                if is_arabic
                else (
                    "I can help with: project status, procurement, safety events, "
                    "NCRs, site reports, meetings, and supplier information."
                )
            )
            return self._build_response(
                db=db, conv=conv, user_msg=user_msg,
                answer=answer, status="unsupported_intent", evidence=[],
                llm_response=None, pipeline_start=pipeline_start,
                intent=intent, scope=scope, project_id=project_id,
                resolved_ctx=resolved_ctx, state=state,
                domains_used=[], tools_used=[],
                is_multi_domain=False, is_executive=False,
                follow_up_suggestions=follow_ups,
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
        try:
            llm_response = provider.generate(
                LLMRequest(
                    system_prompt=system_prompt,
                    user_prompt=resolved_ctx.resolved_query,
                )
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
