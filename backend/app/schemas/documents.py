from pydantic import BaseModel
from typing import Optional


class DocumentOut(BaseModel):
    id: int
    project_id: int
    doc_type: str
    title: str
    doc_date: str
    content_summary: str

    model_config = {"from_attributes": True}


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
