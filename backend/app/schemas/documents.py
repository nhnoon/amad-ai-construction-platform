from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class DocumentOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    organization_id: Optional[int] = None
    doc_type: str
    title: str
    doc_date: str
    content_summary: str

    # ── Document Storage System (Sprint 1) — current-version snapshot.
    # All Optional/None-safe: a document created before this migration, or
    # that never had a file uploaded, simply has these as None/False.
    # storage_key (the internal storage-provider key) is intentionally
    # NEVER exposed here — same precedent as DocumentOCRResult.storage_path.
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    uploaded_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    version_number: Optional[int] = None
    is_archived: bool = False

    model_config = {"from_attributes": True}


class DocumentVersionOut(BaseModel):
    """One entry in a document's version history. storage_key is never
    exposed — download by version_number via GET .../download?version=N."""

    version_number: int
    original_filename: str
    mime_type: str
    file_size: int
    checksum: str
    uploaded_at: datetime
    uploaded_by: Optional[int] = None
    is_current: bool

    model_config = {"from_attributes": True}


class DocumentVersionUploadOut(DocumentVersionOut):
    # True when the uploaded bytes matched the current version's checksum
    # exactly — no new version was created, this is the existing one.
    is_duplicate: bool


class DocumentCreateRequest(BaseModel):
    """project_id=None creates a General Library (organization-scoped)
    document; project_id set creates a project document. Exactly the same
    Document row shape either way — see app/ai/document_access.py."""

    project_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=255)
    doc_type: str = Field(default="uploaded", max_length=100)

    model_config = {"extra": "forbid"}


class GeneratedDocumentOut(BaseModel):
    id: int
    file_name: str
    type: str
    project_id: int
    related_record_id: int
    document_date: str
    sender: str
    recipient: str
    subject: str
    body: str

    model_config = {"from_attributes": True}


class CorrespondenceOut(BaseModel):
    id: int
    project_id: int
    related_record_type: str
    related_record_id: int
    sent_date: str
    sender: str
    recipient: str
    subject: str
    body: str

    model_config = {"from_attributes": True}
