from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Integer, String, Text,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Document(Base):
    """A document is either project-scoped (project_id set) or a
    General Library / organization-scoped document (project_id NULL,
    organization_id required). See the "documents may be organization-level"
    product requirement — every document must belong to exactly one of the
    two, enforced by ck_documents_project_or_org below.

    Document Storage System (Sprint 1): the fields below storage_key are a
    denormalized snapshot of this document's CURRENT (latest, non-archived)
    version — the authoritative, append-only history lives in
    DocumentVersion. All of them are nullable/defaulted so a document that
    predates this migration, or that was created but never had a file
    uploaded, reads back exactly as before (see app/ai/document_access.py::
    create_document, which never touches these). storage_key is an internal
    storage-provider key only — never returned by the API, same precedent
    as DocumentOCRResult.storage_path."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    # Required for General Library documents (project_id IS NULL); may also
    # be set (denormalized) on project documents for consistent tenancy
    # scoping, matching the pattern already used on document_ocr_results /
    # contract_extractions / ai_memory_notes.
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    doc_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    doc_date = Column(String(50), nullable=False)
    content_summary = Column(Text, nullable=False)

    # ── Document Storage System (Sprint 1) — current-version snapshot ────
    storage_key = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True, index=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )
    version_number = Column(Integer, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false", index=True)

    project = relationship("Project", back_populates="documents")
    claim_evidence = relationship("ClaimEvidence", back_populates="document")
    versions = relationship(
        "DocumentVersion", back_populates="document",
        order_by="DocumentVersion.version_number.desc()",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "project_id IS NOT NULL OR organization_id IS NOT NULL",
            name="ck_documents_project_or_org",
        ),
    )


class DocumentVersion(Base):
    """Append-only version history for a Document's uploaded file, written
    by app/ai/document_storage.py::save_document_version. Never updated or
    reused in place — a new upload with different content always adds a
    new row with the next version_number; byte-identical re-uploads (same
    SHA-256 checksum as the current version) are deduplicated and create no
    row at all. storage_key/storage_provider address the actual bytes via
    the StorageService abstraction (app/storage/) and are never returned by
    the API."""

    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    storage_key = Column(String(500), nullable=False)
    storage_provider = Column(String(20), nullable=False, default="local")
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False, index=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    uploaded_by = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)

    document = relationship("Document", back_populates="versions")

    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number",
            name="uq_document_versions_document_id_version_number",
        ),
    )


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    related_record_id = Column(Integer, nullable=False)
    document_date = Column(String(50), nullable=False)
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    project = relationship("Project", back_populates="generated_documents")


class Correspondence(Base):
    __tablename__ = "correspondence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    related_record_type = Column(String(100), nullable=False)
    related_record_id = Column(Integer, nullable=False)
    sent_date = Column(String(50), nullable=False)
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    project = relationship("Project", back_populates="correspondence")
    claim_evidence = relationship("ClaimEvidence", back_populates="correspondence")
