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


class StructuredMemoryOut(BaseModel):
    """One AIMemoryRecord row (app/ai/memory_records.py) — the durable,
    cross-conversation knowledge store, distinct from the bounded note-
    blob groups above."""

    id: int
    source: str
    category: str
    title: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    project_id: Optional[int] = None
    project_code: Optional[str] = None
    citation: Optional[str] = None
    confidence: int
    # Deterministic, computed from category/source/confidence — not a
    # stored column (Product UX Phase 1 explicitly avoids a schema
    # change). See app/ai/memory_records.py::derive_priority.
    priority: str
    created_at: str
    can_delete: bool
    can_edit: bool


class MemoryCreateRequest(BaseModel):
    """Body for POST /ai/memory — the Memory Center's "Add Memory" form.
    Structured counterpart to the free-form "remember that..." chat
    command; always writes source="user"."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    summary: str = Field(..., min_length=1, max_length=1000)
    category: str = Field(...)
    project_code: Optional[str] = None


class MemoryUpdateRequest(BaseModel):
    """Body for PATCH /ai/memory/{id} — the Memory Center's "Edit Memory"
    form. All fields optional; only provided fields are changed."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    summary: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    category: Optional[str] = None


class MemoryOut(BaseModel):
    """The authenticated user's Copilot memory. memory_notes/profile_memory/
    groups are the original read-only view of the bounded per-user blobs
    (app/ai/memory.py); structured_memories/category_counts are additive —
    real AIMemoryRecord rows (app/ai/memory_records.py), RBAC-scoped to
    this caller's organization/projects, not just this one user's own
    writes. Existing consumers reading only the original three fields are
    unaffected."""

    memory_notes: str
    profile_memory: str
    groups: MemoryGroups
    structured_memories: list[StructuredMemoryOut] = Field(default_factory=list)
    category_counts: dict[str, int] = Field(default_factory=dict)


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
