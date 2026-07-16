"""Document, OCR text, and contract extraction retrieval tools.

Documents are either project-scoped (project_id set) or General Library,
organization-scoped documents (project_id NULL, organization_id set) — see
app/models/documents.py and app/ai/document_access.py, which is the single
source of truth for per-document authorization reused here.

Follows the same RBAC + bounded-query conventions as the other retrieval
modules (see app/ai/retrieval/site_reports.py): explicit project_id ->
enforce_project_access; otherwise accessible_project_ids/has_global_read.
General Library documents (project_id IS NULL) are only included when the
caller's organization matches, mirroring list_all_documents() in
app/api/v1/documents.py.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ai.document_access import get_authorized_document
from app.ai.scope import AIAuthScope
from app.models.contract_extraction import ContractExtraction
from app.models.document_ocr import DocumentOCRResult
from app.models.documents import Document
from .base import Evidence, RetrievalResult

_SUMMARY_SNIPPET_LEN = 300
_OCR_SNIPPET_LEN = 500


def _document_evidence(doc: Document, ocr: Optional[DocumentOCRResult]) -> Evidence:
    """Build one Evidence item for a document, preferring OCR extracted
    text (when completed) over the stored content_summary — same
    preference order as site_report_evidence.py's evidence builder."""
    if ocr is not None and ocr.status == "completed" and ocr.extracted_text:
        snippet = (
            f"DOC-{doc.id} ({doc.title}, type={doc.doc_type}, OCR text): "
            f"{ocr.extracted_text[:_OCR_SNIPPET_LEN]}"
        )
    elif ocr is not None and ocr.status == "failed":
        snippet = (
            f"DOC-{doc.id} ({doc.title}, type={doc.doc_type}): OCR extraction failed. "
            f"Summary on file: {doc.content_summary[:_SUMMARY_SNIPPET_LEN] or 'none'}"
        )
    else:
        snippet = (
            f"DOC-{doc.id} ({doc.title}, type={doc.doc_type}): "
            f"{doc.content_summary[:_SUMMARY_SNIPPET_LEN] or 'no summary on file'}"
        )
    return Evidence(
        source_type="document",
        source_id=str(doc.id),
        label=f"Document DOC-{doc.id}",
        snippet=snippet,
        project_id=doc.project_id,
        ui_metadata={"href": "/documents", "icon": "file-text"},
    )


def get_recent_documents(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 10,
) -> RetrievalResult:
    """Recent documents, project-scoped or organization-wide General
    Library, with OCR text folded in when available."""
    q = db.query(Document)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(Document.project_id == project_id)
    else:
        project_ids = list(scope.accessible_project_ids)
        conditions = []
        if scope.has_global_read:
            conditions.append(Document.project_id.isnot(None))
        elif project_ids:
            conditions.append(Document.project_id.in_(project_ids))
        if scope.organization_id is not None:
            conditions.append(
                Document.project_id.is_(None)
                & (Document.organization_id == scope.organization_id)
            )
        if not conditions:
            return RetrievalResult(data={"documents": [], "total": 0}, evidence=[])
        q = q.filter(or_(*conditions))

    documents = q.order_by(Document.id.desc()).limit(limit).all()
    if not documents:
        return RetrievalResult(data={"documents": [], "total": 0}, evidence=[])

    doc_ids = [d.id for d in documents]
    ocr_by_doc = {
        o.document_id: o
        for o in db.query(DocumentOCRResult).filter(DocumentOCRResult.document_id.in_(doc_ids)).all()
    }

    rows = []
    evidence = []
    for d in documents:
        ocr = ocr_by_doc.get(d.id)
        rows.append({
            "id": d.id,
            "project_id": d.project_id,
            "title": d.title,
            "doc_type": d.doc_type,
            "doc_date": d.doc_date,
            "ocr_status": ocr.status if ocr is not None else "not_requested",
        })
        evidence.append(_document_evidence(d, ocr))

    return RetrievalResult(data={"documents": rows, "total": len(rows)}, evidence=evidence)


def get_document_detail(
    db: Session,
    scope: AIAuthScope,
    document_id: int,
) -> RetrievalResult:
    """Full detail for ONE specific document: the document itself, its OCR
    text (if completed), and contract extraction fields (if completed).
    Raises 404/403 via get_authorized_document — same conventions as
    get_meeting_detail() in retrieval/meetings.py."""
    document = get_authorized_document(db=db, scope=scope, document_id=document_id)

    ocr = (
        db.query(DocumentOCRResult)
        .filter(DocumentOCRResult.document_id == document_id)
        .first()
    )
    evidence: list[Evidence] = [_document_evidence(document, ocr)]

    contract = (
        db.query(ContractExtraction)
        .filter(ContractExtraction.document_id == document_id)
        .first()
    )
    if contract is not None and contract.status == "completed":
        fields = contract.extracted_fields or {}
        # Bound the field list — contracts can have many extracted fields;
        # keep the prompt compact by summarizing key/value pairs only.
        field_summary = ", ".join(
            f"{k}={v}" for k, v in list(fields.items())[:12]
        ) or "no fields extracted"
        evidence.append(Evidence(
            source_type="contract_extraction",
            source_id=str(contract.id),
            label=f"Contract Extraction for DOC-{document.id}",
            snippet=(
                f"Contract extraction for DOC-{document.id} "
                f"(validation={contract.validation_status}): {field_summary}"
            ),
            project_id=document.project_id,
            ui_metadata={"href": "/documents", "icon": "file-signature"},
        ))

    return RetrievalResult(
        data={
            "document_id": document.id,
            "project_id": document.project_id,
            "title": document.title,
            "doc_type": document.doc_type,
            "doc_date": document.doc_date,
            "ocr_status": ocr.status if ocr is not None else "not_requested",
            "has_contract_extraction": contract is not None and contract.status == "completed",
        },
        evidence=evidence,
    )
