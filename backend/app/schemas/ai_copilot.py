from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class CopilotQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[int] = None
    project_id: Optional[int] = None


class MemoryGroupItem(BaseModel):
    """One memory line, deterministically parsed — see
    app/ai/memory_reader.py::group_memory_notes(). Fields the line doesn't
    actually contain are null; never invented."""

    title: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None
    importance: Optional[str] = None


class MemoryGroups(BaseModel):
    meeting: list[MemoryGroupItem] = Field(default_factory=list)
    project: list[MemoryGroupItem] = Field(default_factory=list)
    decision: list[MemoryGroupItem] = Field(default_factory=list)
    supplier: list[MemoryGroupItem] = Field(default_factory=list)
    other: list[MemoryGroupItem] = Field(default_factory=list)


class MemoryOut(BaseModel):
    """Read-only view of the authenticated user's bounded Copilot memory
    (app/ai/memory.py). No new business logic — a thin HTTP read wrapper
    around get_memory_notes()/get_user_profile_memory(), plus deterministic
    marker-based grouping (app/ai/memory_reader.py) for the AI Center's
    Memory Viewer."""

    memory_notes: str
    profile_memory: str
    groups: MemoryGroups


class ProcurementAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: Optional[int] = None
    conversation_id: Optional[int] = None
    language: str = Field(default="en", pattern="^(en|ar)$")
    question: Optional[str] = Field(default=None, max_length=2000)


class MeetingAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # meeting_id given: single-meeting detail. meeting_id omitted: a
    # portfolio-wide (or project_id-scoped) meetings status summary — see
    # CopilotPipeline.execute_meeting_agent.
    meeting_id: Optional[int] = None
    project_id: Optional[int] = None
    conversation_id: Optional[int] = None
    language: str = Field(default="en", pattern="^(en|ar)$")
    question: Optional[str] = Field(default=None, max_length=2000)


class CitationOut(BaseModel):
    id: int
    source_type: str
    source_id: str
    label: str
    evidence_snippet: Optional[str] = None
    ui_metadata: Optional[dict[str, Any]] = None


class CopilotQueryResponse(BaseModel):
    # Phase 3A core fields
    conversation_id: int
    message_id: int
    answer: str
    status: str
    intent: str
    citations: list[CitationOut]
    confidence: str
    model: Optional[str] = None
    provider: Optional[str] = None
    latency_ms: float
    evidence_count: int

    # Phase 3B: rich answer structure (all optional for backward compatibility)
    short_summary: Optional[str] = None
    key_findings: Optional[list[str]] = None
    comparison_data: Optional[dict[str, Any]] = None
    follow_up_suggestions: Optional[list[str]] = None

    # Phase 3B: clarification
    clarification_required: bool = False
    clarification_question: Optional[str] = None
    clarification_options: Optional[list[str]] = None

    # Phase 3B: auditability
    resolved_query: Optional[str] = None
    domains_used: Optional[list[str]] = None
    is_multi_domain: bool = False

    # Phase 3C: structured render blocks (frontend renders these directly)
    render_blocks: Optional[list[dict[str, Any]]] = None


class ConversationOut(BaseModel):
    id: int
    organization_id: Optional[int]
    user_id: int
    project_id: Optional[int]
    title: str
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    status: str
    model_name: Optional[str] = None
    provider_name: Optional[str] = None
    latency_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    # Phase 3B
    original_question: Optional[str] = None
    resolved_query: Optional[str] = None
    clarification_required: Optional[bool] = None
    domains_used: Optional[list[str]] = None

    created_at: Any

    model_config = ConfigDict(from_attributes=True)
