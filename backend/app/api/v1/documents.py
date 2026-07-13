from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from typing import Optional
from ...ai.document_ocr import get_document_ocr_result, process_document_ocr
from ...ai.scope import build_ai_scope
from ...config import settings
from ...core.deps import CurrentUser, DbSession
from ...models.documents import Document, GeneratedDocument, Correspondence
from ...models.document_ocr import DocumentOCRResult
from ...schemas.documents import DocumentOut, GeneratedDocumentOut, CorrespondenceOut
from ...schemas.document_ocr import DocumentOCRResultOut

router = APIRouter(tags=["documents"])


def _to_ocr_result_out(row: DocumentOCRResult) -> DocumentOCRResultOut:
    text = row.extracted_text or ""
    limit = settings.OCR_TEXT_PREVIEW_CHARS
    return DocumentOCRResultOut(
        document_id=row.document_id,
        status=row.status,
        page_count=row.page_count,
        detected_language=row.detected_language,
        extraction_method=row.extraction_method,
        text_preview=text[:limit],
        text_length=len(text),
        text_truncated=len(text) > limit,
        error_message=row.error_message,
    )


@router.get("/projects/{project_id}/documents", response_model=list[DocumentOut])
def list_documents(
    project_id: int,
    db: DbSession,
    doc_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Document).filter(Document.project_id == project_id)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/documents/{doc_id}", response_model=DocumentOut)
def get_document(project_id: int, doc_id: int, db: DbSession):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.project_id == project_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post(
    "/projects/{project_id}/documents/{doc_id}/ocr",
    response_model=DocumentOCRResultOut,
)
async def start_document_ocr(
    project_id: int,
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    """Extract text from an uploaded PDF/PNG/JPEG and store it as an
    auditable, bounded OCR result linked to this document. Does not call
    Hermes/an LLM and does not write to Copilot memory (see
    app/ai/document_ocr.py)."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.project_id == project_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    scope = build_ai_scope(current_user, db)
    file_bytes = await file.read()
    row = process_document_ocr(
        db=db,
        scope=scope,
        document_id=doc_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload",
    )
    return _to_ocr_result_out(row)


@router.get(
    "/projects/{project_id}/documents/{doc_id}/ocr",
    response_model=DocumentOCRResultOut,
)
def read_document_ocr(
    project_id: int,
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.project_id == project_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    scope = build_ai_scope(current_user, db)
    row = get_document_ocr_result(db=db, scope=scope, document_id=doc_id)
    return _to_ocr_result_out(row)


@router.get("/projects/{project_id}/generated-documents", response_model=list[GeneratedDocumentOut])
def list_generated_documents(
    project_id: int,
    db: DbSession,
    doc_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(GeneratedDocument).filter(GeneratedDocument.project_id == project_id)
    if doc_type:
        q = q.filter(GeneratedDocument.type == doc_type)
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/correspondence", response_model=list[CorrespondenceOut])
def list_correspondence(
    project_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return (
        db.query(Correspondence)
        .filter(Correspondence.project_id == project_id)
        .offset(skip).limit(limit).all()
    )
