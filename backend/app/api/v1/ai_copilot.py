"""AI Copilot endpoints — Phase 3B multi-turn conversational intelligence.

Security controls:
- question length enforced at schema level (max 2000 chars)
- rate limiting (20 req/min per user via in-memory sliding window)
- conversation ownership verification
- organization isolation (scope-enforced before retrieval)
- project authorization (scope-enforced before retrieval)
- no stack traces / provider secrets in error responses
- conversation state is always user+org scoped
"""
from __future__ import annotations

import logging
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.ai.pipeline import CopilotPipeline
from app.ai.ratelimit import get_ai_rate_limiter
from app.ai.scope import build_ai_scope
from app.core.deps import CurrentUser, DbSession
from app.models.ai_copilot import AIConversation, AIMessage
from app.schemas.ai_copilot import (
    ConversationOut,
    CopilotQueryRequest,
    CopilotQueryResponse,
    MeetingAgentRequest,
    MessageOut,
    ProcurementAgentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])
_pipeline = CopilotPipeline()


@router.post("/copilot/query", response_model=CopilotQueryResponse, status_code=200)
def copilot_query(
    body: CopilotQueryRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CopilotQueryResponse:
    limiter = get_ai_rate_limiter()
    if not limiter.is_allowed(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before sending more AI requests.",
        )

    scope = build_ai_scope(current_user, db)
    logger.info(
        "copilot_query user_id=%s org_id=%s global_read=%s question_len=%d",
        scope.user_id,
        scope.organization_id,
        scope.has_global_read,
        len(body.question),
    )

    try:
        result = _pipeline.execute(
            question=body.question,
            scope=scope,
            db=db,
            project_id=body.project_id,
            conversation_id=body.conversation_id,
        )
    except HTTPException:
        raise
    except Exception:
        logger.error(
            "copilot_pipeline_error user_id=%s\n%s",
            scope.user_id,
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI pipeline error. Please try again.",
        )

    logger.info(
        "copilot_result user_id=%s intent=%s status=%s domains=%s evidence=%d "
        "is_multi=%s clarify=%s latency_ms=%.1f",
        scope.user_id,
        result.get("intent"),
        result.get("status"),
        result.get("domains_used"),
        result.get("evidence_count", 0),
        result.get("is_multi_domain"),
        result.get("clarification_required"),
        result.get("latency_ms", 0),
    )

    return CopilotQueryResponse(
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
        answer=result["answer"],
        status=result["status"],
        intent=result["intent"],
        citations=result["citations"],
        confidence=result["confidence"],
        model=result.get("model"),
        provider=result.get("provider"),
        latency_ms=result["latency_ms"],
        evidence_count=result["evidence_count"],
        # Phase 3B
        short_summary=result.get("short_summary"),
        key_findings=result.get("key_findings"),
        comparison_data=result.get("comparison_data"),
        follow_up_suggestions=result.get("follow_up_suggestions") or [],
        clarification_required=result.get("clarification_required", False),
        clarification_question=result.get("clarification_question"),
        clarification_options=result.get("clarification_options") or [],
        resolved_query=result.get("resolved_query"),
        domains_used=result.get("domains_used") or [],
        is_multi_domain=result.get("is_multi_domain", False),
        # Phase 3C: structured render blocks
        render_blocks=result.get("render_blocks") or [],
    )


@router.post("/agents/procurement", response_model=CopilotQueryResponse, status_code=200)
def procurement_agent(
    body: ProcurementAgentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CopilotQueryResponse:
    """Procurement Intelligence Agent — fixed-scope specialist over the same
    RBAC-scoped retrieval, LLM provider, grounding, and citation pipeline as
    /copilot/query (see app/ai/pipeline.py:execute_procurement_agent)."""
    limiter = get_ai_rate_limiter()
    if not limiter.is_allowed(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before sending more AI requests.",
        )

    scope = build_ai_scope(current_user, db)
    logger.info(
        "procurement_agent_query user_id=%s org_id=%s project_id=%s language=%s",
        scope.user_id, scope.organization_id, body.project_id, body.language,
    )

    try:
        result = _pipeline.execute_procurement_agent(
            scope=scope,
            db=db,
            project_id=body.project_id,
            conversation_id=body.conversation_id,
            language=body.language,
            question=body.question,
        )
    except HTTPException:
        raise
    except Exception:
        logger.error(
            "procurement_agent_error user_id=%s\n%s",
            scope.user_id,
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI pipeline error. Please try again.",
        )

    logger.info(
        "procurement_agent_result user_id=%s status=%s evidence=%d latency_ms=%.1f",
        scope.user_id,
        result.get("status"),
        result.get("evidence_count", 0),
        result.get("latency_ms", 0),
    )

    return CopilotQueryResponse(
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
        answer=result["answer"],
        status=result["status"],
        intent=result["intent"],
        citations=result["citations"],
        confidence=result["confidence"],
        model=result.get("model"),
        provider=result.get("provider"),
        latency_ms=result["latency_ms"],
        evidence_count=result["evidence_count"],
        short_summary=result.get("short_summary"),
        key_findings=result.get("key_findings"),
        comparison_data=result.get("comparison_data"),
        follow_up_suggestions=result.get("follow_up_suggestions") or [],
        clarification_required=result.get("clarification_required", False),
        clarification_question=result.get("clarification_question"),
        clarification_options=result.get("clarification_options") or [],
        resolved_query=result.get("resolved_query"),
        domains_used=result.get("domains_used") or [],
        is_multi_domain=result.get("is_multi_domain", False),
        render_blocks=result.get("render_blocks") or [],
    )


@router.post("/agents/meeting", response_model=CopilotQueryResponse, status_code=200)
def meeting_agent(
    body: MeetingAgentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CopilotQueryResponse:
    """Meeting Intelligence Agent — reuses the same RBAC-scoped retrieval,
    LLM provider, grounding, and citation pipeline as /copilot/query (see
    app/ai/pipeline.py:execute_meeting_agent). meeting_id given: fixed-scope
    specialist over ONE specific meeting. meeting_id omitted: a
    portfolio-wide meetings status summary."""
    limiter = get_ai_rate_limiter()
    if not limiter.is_allowed(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before sending more AI requests.",
        )

    scope = build_ai_scope(current_user, db)
    logger.info(
        "meeting_agent_query user_id=%s org_id=%s meeting_id=%s language=%s",
        scope.user_id, scope.organization_id, body.meeting_id, body.language,
    )

    try:
        result = _pipeline.execute_meeting_agent(
            scope=scope,
            db=db,
            meeting_id=body.meeting_id,
            conversation_id=body.conversation_id,
            language=body.language,
            project_id=body.project_id,
            question=body.question,
        )
    except HTTPException:
        raise
    except Exception:
        logger.error(
            "meeting_agent_error user_id=%s\n%s",
            scope.user_id,
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI pipeline error. Please try again.",
        )

    logger.info(
        "meeting_agent_result user_id=%s status=%s evidence=%d latency_ms=%.1f",
        scope.user_id,
        result.get("status"),
        result.get("evidence_count", 0),
        result.get("latency_ms", 0),
    )

    return CopilotQueryResponse(
        conversation_id=result["conversation_id"],
        message_id=result["message_id"],
        answer=result["answer"],
        status=result["status"],
        intent=result["intent"],
        citations=result["citations"],
        confidence=result["confidence"],
        model=result.get("model"),
        provider=result.get("provider"),
        latency_ms=result["latency_ms"],
        evidence_count=result["evidence_count"],
        short_summary=result.get("short_summary"),
        key_findings=result.get("key_findings"),
        comparison_data=result.get("comparison_data"),
        follow_up_suggestions=result.get("follow_up_suggestions") or [],
        clarification_required=result.get("clarification_required", False),
        clarification_question=result.get("clarification_question"),
        clarification_options=result.get("clarification_options") or [],
        resolved_query=result.get("resolved_query"),
        domains_used=result.get("domains_used") or [],
        is_multi_domain=result.get("is_multi_domain", False),
        render_blocks=result.get("render_blocks") or [],
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    current_user: CurrentUser,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[ConversationOut]:
    convs = (
        db.query(AIConversation)
        .filter(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return convs


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationOut:
    conv = db.query(AIConversation).filter(
        AIConversation.id == conversation_id
    ).first()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if conv.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return conv


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageOut]
)
def list_messages(
    conversation_id: int,
    current_user: CurrentUser,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[MessageOut]:
    conv = db.query(AIConversation).filter(
        AIConversation.id == conversation_id
    ).first()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if conv.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = (
        db.query(AIMessage)
        .filter(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return messages
