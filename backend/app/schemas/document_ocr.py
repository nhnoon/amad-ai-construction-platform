from typing import Optional
from pydantic import BaseModel


class DocumentOCRResultOut(BaseModel):
    """Bounded, auditable OCR result. Never includes storage_path (internal
    server path) and never returns unlimited extracted text — text_preview
    is capped at settings.OCR_TEXT_PREVIEW_CHARS."""

    document_id: int
    status: str
    page_count: Optional[int] = None
    detected_language: Optional[str] = None
    extraction_method: Optional[str] = None
    text_preview: str = ""
    text_length: int = 0
    text_truncated: bool = False
    error_message: Optional[str] = None

    model_config = {"from_attributes": False}
