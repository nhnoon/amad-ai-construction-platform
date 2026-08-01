from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import and_, or_
from typing import Optional
from ...ai.contract_extraction import get_contract_extraction, process_contract_extraction
from ...ai.document_access import create_document
from ...ai.document_ocr import get_document_ocr_result, process_document_ocr
from ...ai.document_storage import (
    archive_document,
    get_document_file,
    list_document_versions,
    save_document_version,
    unarchive_document,
)
from ...ai.scope import build_ai_scope
from ...config import settings
from ...core.deps import CurrentScope, CurrentUser, DbSession
from ...models.documents import Document, GeneratedDocument, Correspondence
from ...models.document_ocr import DocumentOCRResult
from ...models.contract_extraction import ContractExtraction
from ...schemas.documents import (
    DocumentCreateRequest, DocumentOut, GeneratedDocumentOut, CorrespondenceOut,
    DocumentVersionOut, DocumentVersionUploadOut,
)
from ...schemas.document_ocr import DocumentOCRResultOut
from ...schemas.contract_extraction import ContractExtractionOut

router = APIRouter(tags=["documents"])


def _to_version_out(version, *, is_current: bool) -> DocumentVersionOut:
    return DocumentVersionOut(
        version_number=version.version_number,
        original_filename=version.original_filename,
        mime_type=version.mime_type,
        file_size=version.file_size,
        checksum=version.checksum,
        uploaded_at=version.uploaded_at,
        uploaded_by=version.uploaded_by,
        is_current=is_current,
    )


def _download_response(result) -> Response:
    safe_filename = result.filename.replace('"', "")
    return Response(
        content=result.file_bytes,
        media_type=result.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-Document-Version": str(result.version_number),
        },
    )


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


def _to_contract_extraction_out(row: ContractExtraction) -> ContractExtractionOut:
    return ContractExtractionOut(
        document_id=row.document_id,
        status=row.status,
        validation_status=row.validation_status,
        provider=row.provider,
        model_name=row.model_name,
        extracted_fields=row.extracted_fields if row.status == "completed" else None,
        error_message=row.error_message,
    )


@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document_route(
    body: DocumentCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Create a Document row — either a General Library document
    (project_id omitted, organization-scoped) or a project document
    (project_id given, membership-enforced). See app/ai/document_access.py.
    File upload and OCR happen separately via POST /documents/{id}/ocr."""
    scope = build_ai_scope(current_user, db)
    doc = create_document(
        db=db, scope=scope, project_id=body.project_id,
        title=body.title, doc_type=body.doc_type,
    )
    return doc


@router.get("/documents", response_model=list[DocumentOut])
def list_all_documents(
    current_user: CurrentUser,
    db: DbSession,
    scope: str = Query("all", pattern="^(all|general|project)$"),
    project_id: Optional[int] = None,
    include_archived: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List documents visible to the caller, filtered by destination:
    - scope=general: only organization-scoped General Library documents
      (project_id IS NULL) in the caller's own organization.
    - scope=project: only project documents the caller can access
      (optionally narrowed to one project_id).
    - scope=all (default): both, each still properly scoped.

    Archived documents (Document Storage System, Sprint 1) are excluded by
    default — pass include_archived=true to see them too. Every document
    created before this sprint has is_archived=False, so this filter
    changes nothing for existing data."""
    ai_scope = build_ai_scope(current_user, db)

    general_filter = and_(
        Document.project_id.is_(None),
        Document.organization_id == ai_scope.organization_id,
    )

    project_filter = Document.project_id.isnot(None)
    if not ai_scope.has_global_read:
        allowed = list(ai_scope.accessible_project_ids) or [-1]
        project_filter = and_(project_filter, Document.project_id.in_(allowed))
    if project_id is not None:
        ai_scope.enforce_project_access(project_id)
        project_filter = and_(project_filter, Document.project_id == project_id)

    if scope == "general":
        q = db.query(Document).filter(general_filter)
    elif scope == "project":
        q = db.query(Document).filter(project_filter)
    else:
        q = db.query(Document).filter(or_(general_filter, project_filter))

    if not include_archived:
        q = q.filter(Document.is_archived.is_(False))

    return q.order_by(Document.id.desc()).offset(skip).limit(limit).all()


@router.post(
    "/documents/{document_id}/ocr",
    response_model=DocumentOCRResultOut,
)
async def start_document_ocr_unified(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    """Same as POST /projects/{project_id}/documents/{doc_id}/ocr, but
    works for both project documents and General Library documents — the
    document itself carries whichever scoping applies (see
    app/ai/document_access.py). No business logic is duplicated: this
    calls the exact same service function as the project-scoped route."""
    scope = build_ai_scope(current_user, db)
    file_bytes = await file.read()
    row = process_document_ocr(
        db=db, scope=scope, document_id=document_id,
        file_bytes=file_bytes, filename=file.filename or "upload",
    )
    return _to_ocr_result_out(row)


@router.get(
    "/documents/{document_id}/ocr",
    response_model=DocumentOCRResultOut,
)
def read_document_ocr_unified(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    scope = build_ai_scope(current_user, db)
    row = get_document_ocr_result(db=db, scope=scope, document_id=document_id)
    return _to_ocr_result_out(row)


@router.post(
    "/documents/{document_id}/contract-extraction",
    response_model=ContractExtractionOut,
)
def start_contract_extraction_unified(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    scope = build_ai_scope(current_user, db)
    row = process_contract_extraction(db=db, scope=scope, document_id=document_id)
    return _to_contract_extraction_out(row)


@router.get(
    "/documents/{document_id}/contract-extraction",
    response_model=ContractExtractionOut,
)
def read_contract_extraction_unified(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    scope = build_ai_scope(current_user, db)
    row = get_contract_extraction(db=db, scope=scope, document_id=document_id)
    return _to_contract_extraction_out(row)


# ── Document Storage System (Sprint 1) ───────────────────────────────────
# Persistent, versioned, checksummed file storage — independent of OCR.
# Works for both project documents and General Library documents, same
# unified/project-scoped pairing as the ocr/contract-extraction routes
# above (get_authorized_document, called inside every service function
# below, is the single authorization boundary either route shape hits).

@router.post(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionUploadOut,
    status_code=201,
)
async def upload_document_version_unified(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    """Store `file` as a new version of this document (or, if its content
    is byte-identical to the current version, return the existing one
    unchanged — see save_document_version's checksum dedup). Does not run
    OCR or contract extraction; use POST .../ocr for that."""
    scope = build_ai_scope(current_user, db)
    file_bytes = await file.read()
    result = save_document_version(db, scope, document_id, file_bytes, file.filename or "upload")
    out = _to_version_out(result.version, is_current=True)
    return DocumentVersionUploadOut(**out.model_dump(), is_duplicate=result.is_duplicate)


@router.get("/documents/{document_id}/versions", response_model=list[DocumentVersionOut])
def list_document_versions_unified(document_id: int, current_user: CurrentUser, db: DbSession):
    scope = build_ai_scope(current_user, db)
    document, versions = list_document_versions(db, scope, document_id)
    return [_to_version_out(v, is_current=(v.version_number == document.version_number)) for v in versions]


@router.get("/documents/{document_id}/download")
def download_document_unified(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
    version: Optional[int] = None,
):
    """Download the current version's file, or a specific historical
    version via ?version=N — every previous version remains retrievable."""
    scope = build_ai_scope(current_user, db)
    result = get_document_file(db, scope, document_id, version_number=version)
    return _download_response(result)


@router.post("/documents/{document_id}/archive", response_model=DocumentOut)
def archive_document_unified(document_id: int, current_user: CurrentUser, db: DbSession):
    """Soft delete only — nothing is ever permanently removed. See
    archive_document() for what this does and does not do."""
    scope = build_ai_scope(current_user, db)
    return archive_document(db, scope, document_id)


@router.post("/documents/{document_id}/unarchive", response_model=DocumentOut)
def unarchive_document_unified(document_id: int, current_user: CurrentUser, db: DbSession):
    scope = build_ai_scope(current_user, db)
    return unarchive_document(db, scope, document_id)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentOut])
def list_documents(
    project_id: int,
    db: DbSession,
    scope: CurrentScope,
    doc_type: Optional[str] = None,
    include_archived: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    scope.enforce_project_access(project_id)
    q = db.query(Document).filter(Document.project_id == project_id)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    if not include_archived:
        q = q.filter(Document.is_archived.is_(False))
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/documents/{doc_id}", response_model=DocumentOut)
def get_document(project_id: int, doc_id: int, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(project_id)
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.project_id == project_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _get_project_document_or_404(db: DbSession, project_id: int, doc_id: int) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.project_id == project_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post(
    "/projects/{project_id}/documents/{doc_id}/versions",
    response_model=DocumentVersionUploadOut,
    status_code=201,
)
async def upload_document_version(
    project_id: int,
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    _get_project_document_or_404(db, project_id, doc_id)
    scope = build_ai_scope(current_user, db)
    file_bytes = await file.read()
    result = save_document_version(db, scope, doc_id, file_bytes, file.filename or "upload")
    out = _to_version_out(result.version, is_current=True)
    return DocumentVersionUploadOut(**out.model_dump(), is_duplicate=result.is_duplicate)


@router.get(
    "/projects/{project_id}/documents/{doc_id}/versions",
    response_model=list[DocumentVersionOut],
)
def list_document_versions_route(project_id: int, doc_id: int, current_user: CurrentUser, db: DbSession):
    _get_project_document_or_404(db, project_id, doc_id)
    scope = build_ai_scope(current_user, db)
    document, versions = list_document_versions(db, scope, doc_id)
    return [_to_version_out(v, is_current=(v.version_number == document.version_number)) for v in versions]


@router.get("/projects/{project_id}/documents/{doc_id}/download")
def download_document(
    project_id: int,
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
    version: Optional[int] = None,
):
    _get_project_document_or_404(db, project_id, doc_id)
    scope = build_ai_scope(current_user, db)
    result = get_document_file(db, scope, doc_id, version_number=version)
    return _download_response(result)


@router.post("/projects/{project_id}/documents/{doc_id}/archive", response_model=DocumentOut)
def archive_document_route(project_id: int, doc_id: int, current_user: CurrentUser, db: DbSession):
    _get_project_document_or_404(db, project_id, doc_id)
    scope = build_ai_scope(current_user, db)
    return archive_document(db, scope, doc_id)


@router.post("/projects/{project_id}/documents/{doc_id}/unarchive", response_model=DocumentOut)
def unarchive_document_route(project_id: int, doc_id: int, current_user: CurrentUser, db: DbSession):
    _get_project_document_or_404(db, project_id, doc_id)
    scope = build_ai_scope(current_user, db)
    return unarchive_document(db, scope, doc_id)


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


@router.post(
    "/projects/{project_id}/documents/{doc_id}/contract-extraction",
    response_model=ContractExtractionOut,
)
def start_contract_extraction(
    project_id: int,
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Extract structured contract fields from the OCR text already stored
    for this document (Phase 1) via the configured LLM provider. Does not
    re-run OCR and does not write to Copilot memory (see
    app/ai/contract_extraction.py)."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.project_id == project_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    scope = build_ai_scope(current_user, db)
    row = process_contract_extraction(db=db, scope=scope, document_id=doc_id)
    return _to_contract_extraction_out(row)


@router.get(
    "/projects/{project_id}/documents/{doc_id}/contract-extraction",
    response_model=ContractExtractionOut,
)
def read_contract_extraction(
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
    row = get_contract_extraction(db=db, scope=scope, document_id=doc_id)
    return _to_contract_extraction_out(row)


@router.get("/projects/{project_id}/generated-documents", response_model=list[GeneratedDocumentOut])
def list_generated_documents(
    project_id: int,
    db: DbSession,
    scope: CurrentScope,
    doc_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    scope.enforce_project_access(project_id)
    q = db.query(GeneratedDocument).filter(GeneratedDocument.project_id == project_id)
    if doc_type:
        q = q.filter(GeneratedDocument.type == doc_type)
    return q.offset(skip).limit(limit).all()


@router.get("/projects/{project_id}/correspondence", response_model=list[CorrespondenceOut])
def list_correspondence(
    project_id: int,
    db: DbSession,
    scope: CurrentScope,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    scope.enforce_project_access(project_id)
    return (
        db.query(Correspondence)
        .filter(Correspondence.project_id == project_id)
        .offset(skip).limit(limit).all()
    )
