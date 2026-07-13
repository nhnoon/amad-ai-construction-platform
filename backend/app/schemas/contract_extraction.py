from typing import Optional
from pydantic import BaseModel


class ContractExtractionOut(BaseModel):
    """Auditable, validated contract extraction result. Never includes the
    raw OCR input text or the full raw LLM response — only the validated,
    supported fields (and error details, if any)."""

    document_id: int
    status: str
    validation_status: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    extracted_fields: Optional[dict] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": False}
