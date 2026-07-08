from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...core.deps import DbSession
from ...models.documents import Document, GeneratedDocument, Correspondence
from ...schemas.documents import DocumentOut, GeneratedDocumentOut, CorrespondenceOut

router = APIRouter(tags=["documents"])


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
