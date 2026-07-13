"""Contract Intelligence Extractor — Phase 2 of AMAD Document Intelligence.

Stores one auditable, validated structured-JSON extraction per Document,
derived from the OCR text already stored in DocumentOCRResult (Phase 1) via
the configured LLM provider (Hermes). Stored separately from the OCR text
table — this table never duplicates extracted_text, only a bounded raw LLM
response (for audit) plus the validated structured fields.

Not read by app/ai/pipeline.py, not written to Copilot memory — see
app/ai/contract_extraction.py.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base


class ContractExtraction(Base):
    __tablename__ = "contract_extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    ocr_result_id = Column(
        Integer,
        ForeignKey("document_ocr_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Denormalized scoping snapshot, matching document_ocr_results.
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    # NULL for a General Library (organization-scoped) document — see
    # Document.project_id in app/models/documents.py.
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    requested_by = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(String(20), nullable=False, default="pending")  # pending|processing|completed|failed
    validation_status = Column(String(20), nullable=True)  # valid|invalid

    provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Bounded raw LLM output, kept for audit/debugging — never the input
    # OCR text (that stays solely in document_ocr_results).
    raw_response = Column(Text, nullable=True)
    extracted_fields = Column(JSONB, nullable=True)
    validation_errors = Column(Text, nullable=True)
    error_message = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("document_id", name="uq_contract_extractions_document_id"),
    )
