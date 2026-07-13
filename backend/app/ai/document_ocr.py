"""Document OCR Foundation — Phase 1 of AMAD Document Intelligence.

Extracts text from an uploaded PDF/PNG/JPG linked to an existing, authorized
Document record (app/models/documents.py) and stores one auditable
DocumentOCRResult row per document (app/models/document_ocr.py).

Deterministic, database- and disk-backed only:
  - selectable-text PDF pages are read directly via PyMuPDF — no OCR needed.
  - image files, and any scanned PDF page with no selectable text, go
    through Tesseract OCR via pytesseract IF a system Tesseract install is
    present (see _tesseract_available()). When it isn't, those pages/files
    fail safely (status="failed", clear error_message) instead of being
    silently skipped or fabricated.

No LLM/Hermes call anywhere in this module. No Copilot memory read/write.
No change to the existing Document metadata row.
"""
from __future__ import annotations

import io
import logging
import os
import re
import uuid
from dataclasses import dataclass
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image
from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.ai.document_access import get_authorized_document
from app.ai.scope import AIAuthScope
from app.config import settings
from app.models.document_ocr import DocumentOCRResult

logger = logging.getLogger(__name__)

_SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
# Content is sniffed from magic bytes, never trusted from the client-declared
# Content-Type / filename extension.
_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]

_MULTI_BLANK_LINE = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+\n")


class UnsupportedFileType(ValueError):
    pass


class FileTooLarge(ValueError):
    pass


@dataclass
class ExtractionOutcome:
    status: str  # completed | failed
    extracted_text: str = ""
    page_count: Optional[int] = None
    detected_language: Optional[str] = None
    extraction_method: Optional[str] = None
    confidence: Optional[float] = None
    error_message: Optional[str] = None


def _sniff_mime_type(file_bytes: bytes) -> str:
    for magic, mime in _MAGIC_BYTES:
        if file_bytes.startswith(magic):
            return mime
    raise UnsupportedFileType(
        "Unsupported or unrecognized file type. Only PDF, PNG, and JPEG are supported."
    )


def _validate_upload(file_bytes: bytes) -> str:
    if not file_bytes:
        raise UnsupportedFileType("Uploaded file is empty.")
    if len(file_bytes) > settings.OCR_MAX_FILE_SIZE_BYTES:
        raise FileTooLarge(
            f"File exceeds the maximum allowed size of "
            f"{settings.OCR_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )
    return _sniff_mime_type(file_bytes)


def _normalize_whitespace(text: str) -> str:
    """Collapse trailing whitespace and excess blank lines without
    destroying table/line structure (tabs and single line breaks are kept)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _TRAILING_SPACES.sub("\n", text)
    text = _MULTI_BLANK_LINE.sub("\n\n", text)
    return text.strip()


def _tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_image(image: "Image.Image") -> str:
    """Isolated single call point so tests can monkeypatch OCR without a
    real Tesseract install (see backend/tests/test_document_ocr.py)."""
    import pytesseract
    return pytesseract.image_to_string(image)


def _detect_language(text: str) -> Optional[str]:
    sample = text.strip()
    if len(sample) < 20:
        return None
    try:
        from langdetect import detect
        return detect(sample)
    except Exception:
        return None


def _extract_pdf(file_bytes: bytes) -> ExtractionOutcome:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return ExtractionOutcome(status="failed", error_message="Could not open PDF file.")

    page_texts: list[str] = []
    pages_needing_ocr = 0
    ocr_ready = _tesseract_available()
    ocr_used = False
    page_count = 0

    try:
        page_count = doc.page_count
        for page in doc:
            text = page.get_text("text") or ""
            if text.strip():
                page_texts.append(text)
                continue
            # No selectable text on this page — likely a scanned image page.
            if ocr_ready:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                try:
                    page_texts.append(_ocr_image(img))
                    ocr_used = True
                except Exception:
                    page_texts.append("")
                    pages_needing_ocr += 1
            else:
                page_texts.append("")
                pages_needing_ocr += 1
    finally:
        doc.close()

    combined = _normalize_whitespace("\n\n".join(page_texts))

    if not combined:
        return ExtractionOutcome(
            status="failed",
            page_count=page_count,
            error_message=(
                "Document has no selectable text and requires OCR, but no "
                "OCR engine (Tesseract) is installed on this server."
                if pages_needing_ocr
                else "No text could be extracted from this document."
            ),
        )

    if ocr_used and any(t.strip() for t in page_texts):
        method = "mixed"
    elif ocr_used:
        method = "ocr_tesseract"
    else:
        method = "pdf_text_layer"

    truncated = combined[: settings.OCR_MAX_EXTRACTED_TEXT_CHARS]
    return ExtractionOutcome(
        status="completed",
        extracted_text=truncated,
        page_count=page_count,
        detected_language=_detect_language(truncated),
        extraction_method=method,
        error_message=(
            f"{pages_needing_ocr} page(s) had no selectable text and OCR is "
            "unavailable; those pages were left blank."
            if pages_needing_ocr
            else None
        ),
    )


def _extract_image(file_bytes: bytes) -> ExtractionOutcome:
    if not _tesseract_available():
        return ExtractionOutcome(
            status="failed",
            error_message=(
                "OCR engine (Tesseract) is not installed on this server; "
                "image text extraction is unavailable."
            ),
        )
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Exception:
        return ExtractionOutcome(status="failed", error_message="Could not open image file.")

    try:
        text = _ocr_image(image)
    except Exception:
        return ExtractionOutcome(status="failed", error_message="OCR extraction failed.")

    normalized = _normalize_whitespace(text)
    if not normalized:
        return ExtractionOutcome(
            status="failed", page_count=1,
            error_message="No text could be detected in this image.",
        )

    truncated = normalized[: settings.OCR_MAX_EXTRACTED_TEXT_CHARS]
    return ExtractionOutcome(
        status="completed",
        extracted_text=truncated,
        page_count=1,
        detected_language=_detect_language(truncated),
        extraction_method="ocr_tesseract",
    )


def extract_document_text(file_bytes: bytes) -> ExtractionOutcome:
    """Pure extraction — no DB, no auth, no filesystem write. Raises
    UnsupportedFileType/FileTooLarge for invalid input; otherwise never
    raises — extraction-time failures are returned as status="failed"."""
    mime_type = _validate_upload(file_bytes)
    if mime_type == "application/pdf":
        return _extract_pdf(file_bytes)
    return _extract_image(file_bytes)


def _sanitize_display_filename(filename: str) -> str:
    name = os.path.basename(filename or "upload")
    name = re.sub(r"[\x00-\x1f]", "", name)
    return name[:255] or "upload"


def _safe_storage_filename(document_id: int, mime_type: str) -> str:
    ext = _SUPPORTED_MIME_TYPES[mime_type]
    return f"{document_id}_{uuid.uuid4().hex}{ext}"


def _delete_if_exists(path: Optional[str]) -> None:
    if not path:
        return
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        logger.warning("document_ocr_cleanup_failed document_id_context=unavailable")


def process_document_ocr(
    db: Session,
    scope: AIAuthScope,
    document_id: int,
    file_bytes: bytes,
    filename: str,
) -> DocumentOCRResult:
    """Authorize, validate, store the upload, extract text, and persist one
    auditable DocumentOCRResult row (upserted per document_id — reprocessing
    replaces the previous result rather than accumulating duplicates)."""
    document = get_authorized_document(db, scope, document_id)

    try:
        mime_type = _validate_upload(file_bytes)
    except (UnsupportedFileType, FileTooLarge) as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))

    row = (
        db.query(DocumentOCRResult)
        .filter(DocumentOCRResult.document_id == document_id)
        .first()
    )
    previous_storage_path = row.storage_path if row else None
    if row is None:
        row = DocumentOCRResult(document_id=document_id, project_id=document.project_id)
        db.add(row)

    row.status = "processing"
    row.organization_id = document.organization_id
    row.project_id = document.project_id
    row.requested_by = scope.user_id
    row.source_filename = _sanitize_display_filename(filename)
    row.mime_type = mime_type
    row.file_size_bytes = len(file_bytes)
    row.error_message = None

    os.makedirs(settings.OCR_UPLOAD_DIR, exist_ok=True)
    storage_name = _safe_storage_filename(document_id, mime_type)
    storage_path = os.path.join(settings.OCR_UPLOAD_DIR, storage_name)
    with open(storage_path, "wb") as f:
        f.write(file_bytes)
    row.storage_path = storage_path
    db.flush()

    # One stored file per document — remove the previous one now that the
    # new file has been written successfully (never duplicate).
    if previous_storage_path and previous_storage_path != storage_path:
        _delete_if_exists(previous_storage_path)

    try:
        outcome = extract_document_text(file_bytes)
    except (UnsupportedFileType, FileTooLarge) as e:
        outcome = ExtractionOutcome(status="failed", error_message=str(e))
    except Exception:
        logger.exception("document_ocr_extraction_error document_id=%s", document_id)
        outcome = ExtractionOutcome(status="failed", error_message="Extraction failed unexpectedly.")

    row.status = outcome.status
    row.extracted_text = outcome.extracted_text or None
    row.page_count = outcome.page_count
    row.detected_language = outcome.detected_language
    row.extraction_method = outcome.extraction_method
    row.confidence = outcome.confidence
    row.error_message = outcome.error_message
    db.commit()
    db.refresh(row)

    logger.info(
        "document_ocr_processed document_id=%s status=%s page_count=%s "
        "extraction_method=%s text_length=%s",
        document_id, row.status, row.page_count, row.extraction_method,
        len(row.extracted_text) if row.extracted_text else 0,
    )
    return row


def get_document_ocr_result(
    db: Session, scope: AIAuthScope, document_id: int
) -> DocumentOCRResult:
    get_authorized_document(db, scope, document_id)

    row = (
        db.query(DocumentOCRResult)
        .filter(DocumentOCRResult.document_id == document_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No OCR result exists for this document yet.",
        )
    return row
