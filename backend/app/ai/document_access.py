"""Shared document fetch/authorize/create helpers.

Single source of truth for "does this scope have access to this document"
— used by both app/ai/document_ocr.py and app/ai/contract_extraction.py so
the project-vs-general authorization branch exists in exactly one place.

A document is either project-scoped (project_id set — authorized via the
caller's project membership/role) or a General Library, organization-scoped
document (project_id NULL, organization_id required — authorized via the
caller's organization membership only). See app/models/documents.py.
"""
from __future__ import annotations

from datetime import timezone, datetime
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.models.documents import Document

_MAX_TITLE_LEN = 255


def enforce_document_access(scope: AIAuthScope, document: Document) -> None:
    if document.project_id is not None:
        scope.enforce_project_access(document.project_id)
    else:
        scope.enforce_organization_access(document.organization_id)


def get_authorized_document(db: Session, scope: AIAuthScope, document_id: int) -> Document:
    """Fetch a document by id and authorize it for this scope (project
    membership for project documents, same-organization for General
    Library documents). Raises 404 if missing, 403 if not authorized."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Document not found")
    enforce_document_access(scope, document)
    return document


def create_document(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int],
    title: str,
    doc_type: str = "uploaded",
) -> Document:
    """Create a new Document row — either project-scoped (project_id given,
    membership enforced) or a General Library document (project_id=None,
    organization_id=scope.organization_id). Does not touch any file/OCR
    state; see app/ai/document_ocr.py for that."""
    if project_id is not None:
        scope.enforce_project_access(project_id)
        organization_id = scope.organization_id
    else:
        if scope.organization_id is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Your account is not associated with an organization; "
                "cannot upload a General Library document.",
            )
        organization_id = scope.organization_id

    clean_title = (title or "Untitled document").strip()[:_MAX_TITLE_LEN] or "Untitled document"

    document = Document(
        project_id=project_id,
        organization_id=organization_id,
        doc_type=doc_type,
        title=clean_title,
        doc_date=datetime.now(timezone.utc).date().isoformat(),
        content_summary="",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
