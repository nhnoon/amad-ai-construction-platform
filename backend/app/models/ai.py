from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

try:
    from pgvector.sqlalchemy import Vector
    _PGVECTOR_AVAILABLE = True
except ImportError:
    _PGVECTOR_AVAILABLE = False


class AIMemory(Base):
    __tablename__ = "ai_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    embedding = Column(Vector(1536) if _PGVECTOR_AVAILABLE else Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.8)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=False, default="ai_agent")


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_name = Column(String(100), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    input_summary = Column(Text, nullable=False)
    output_summary = Column(Text, nullable=False)
    memory_ids_used = Column(JSONB, nullable=True)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    approved_by = Column(String(255), nullable=True)
    approval_status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    action_type = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    risk_level = Column(String(20), nullable=False, default="medium")
    status = Column(String(50), nullable=False, default="pending")
    requested_by = Column(String(100), nullable=False, default="ai_agent")
    reviewed_by = Column(String(255), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
