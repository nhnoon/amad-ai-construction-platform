"""Document OCR Foundation — auditable text-extraction results.

One bounded row per Document (upsert on reprocess, not append-only), linking
back to the existing app/models/documents.py::Document record. Never
duplicates or modifies the original Document metadata row — this table only
stores the extraction outcome (status, text, diagnostics) plus the on-disk
location of the uploaded source file used to produce it.

Not read by app/ai/pipeline.py, not written to Copilot memory, no LLM
involvement — see app/ai/document_ocr.py for the extraction service.
"""
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base


class DocumentOCRResult(Base):
    __tablename__ = "document_ocr_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Denormalized scoping snapshot, matching the pattern already used on
    # ai_conversations / ai_user_profile_memory.
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(String(20), nullable=False, default="pending")  # pending|processing|completed|failed

    source_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    # Internal server path only — never returned by the API.
    storage_path = Column(String(500), nullable=False)

    detected_language = Column(String(20), nullable=True)
    page_count = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extraction_method = Column(String(50), nullable=True)  # pdf_text_layer|ocr_tesseract|mixed
    confidence = Column(Float, nullable=True)
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
        UniqueConstraint("document_id", name="uq_document_ocr_results_document_id"),
    )
