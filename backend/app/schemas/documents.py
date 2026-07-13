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

    model_config = {"from_attributes": True}


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
