from sqlalchemy import CheckConstraint, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Document(Base):
    """A document is either project-scoped (project_id set) or a
    General Library / organization-scoped document (project_id NULL,
    organization_id required). See the "documents may be organization-level"
    product requirement — every document must belong to exactly one of the
    two, enforced by ck_documents_project_or_org below."""

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

    project = relationship("Project", back_populates="documents")
    claim_evidence = relationship("ClaimEvidence", back_populates="document")

    __table_args__ = (
        CheckConstraint(
            "project_id IS NOT NULL OR organization_id IS NOT NULL",
            name="ck_documents_project_or_org",
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
