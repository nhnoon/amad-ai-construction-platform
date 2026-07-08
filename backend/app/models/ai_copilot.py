from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey, Boolean,
    DateTime, Index, ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(500), nullable=False, default="New Conversation")

    # Phase 3B: structured conversation state (JSONB, bounded, user-scoped)
    conversation_state = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages = relationship(
        "AIMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ai_conversations_user_id", "user_id"),
        Index("ix_ai_conversations_org_id", "organization_id"),
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="completed")
    model_name = Column(String(100), nullable=True)
    provider_name = Column(String(50), nullable=True)
    latency_ms = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

    # Phase 3B: context tracking
    original_question = Column(Text, nullable=True)
    resolved_query = Column(Text, nullable=True)
    clarification_required = Column(Boolean, nullable=True, default=False)
    context_refs_used = Column(Integer, nullable=True)
    domains_used = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("AIConversation", back_populates="messages")
    citations = relationship(
        "AICitation", back_populates="message", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ai_messages_conversation_id", "conversation_id"),
    )


class AICitation(Base):
    __tablename__ = "ai_citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(
        Integer,
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(50), nullable=False)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    label = Column(String(500), nullable=False)
    evidence_snippet = Column(Text, nullable=True)
    ui_metadata = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    message = relationship("AIMessage", back_populates="citations")

    __table_args__ = (
        Index("ix_ai_citations_message_id", "message_id"),
    )


class CopilotAuditLog(Base):
    __tablename__ = "copilot_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=True)
    conversation_id = Column(Integer, nullable=True)

    # Phase 3A fields
    intent = Column(String(100), nullable=True)
    provider_name = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False)
    latency_ms = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    evidence_source_count = Column(Integer, nullable=True)
    failure_category = Column(String(50), nullable=True)

    # Phase 3B: extended audit fields
    original_question = Column(Text, nullable=True)
    resolved_query = Column(Text, nullable=True)
    previous_intent = Column(String(100), nullable=True)
    resolved_intent = Column(String(100), nullable=True)
    domains_used = Column(JSONB, nullable=True)
    retrieval_tools_used = Column(JSONB, nullable=True)
    clarification_required = Column(Boolean, nullable=True)
    context_reference_count = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_copilot_audit_logs_user_id", "user_id"),
        Index("ix_copilot_audit_logs_org_id", "organization_id"),
        Index("ix_copilot_audit_logs_created_at", "created_at"),
    )
