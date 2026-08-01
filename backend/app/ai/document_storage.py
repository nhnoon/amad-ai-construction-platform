"""Document Storage System (Sprint 1) — persistent, versioned, checksummed
file storage for Document rows, addressed through the StorageService
abstraction (app/storage/) rather than a hardcoded filesystem path.

Independent of, and unrelated to, app/ai/document_ocr.py's own disk write:
that module keeps a private, single-file-per-document working copy under
OCR_UPLOAD_DIR purely so it has bytes to re-extract text from on
reprocessing — it is not a document management feature and this module
does not change it. process_document_ocr() calls save_document_version()
below (in addition to its own existing behavior) so that uploading a file
through the existing OCR endpoint — today the only upload path the
frontend actually calls — also now results in permanent, versioned
storage. Nothing about OCR's own request/response contract changes.

Never modifies a Document's original creation-time metadata (project_id,
doc_type, title, doc_date, content_summary — see app/ai/document_access.py
::create_document for that). Only ever writes to the storage-snapshot
columns added by this sprint (storage_key, original_filename, mime_type,
file_size, checksum, uploaded_at, uploaded_by, version_number) plus
is_archived, and to the new document_versions table.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.ai.document_access import get_authorized_document
from app.ai.scope import AIAuthScope
from app.config import settings
from app.models.documents import Document, DocumentVersion
from app.storage import get_storage_service

logger = logging.getLogger(__name__)

# Same three types app/ai/document_ocr.py supports today. Kept as an
# explicit, sniffed allow-list rather than trusting the client-declared
# Content-Type/filename extension — broader format support (Office docs,
# plain text, CAD, etc.) needs its own magic-byte/structural validation and
# is intentionally out of scope for this sprint (see final report).
_SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]


class UnsupportedFileType(ValueError):
    pass


class FileTooLarge(ValueError):
    pass


def sniff_mime_type(file_bytes: bytes) -> str:
    """Content is sniffed from magic bytes, never trusted from the
    client-declared Content-Type or filename extension."""
    for magic, mime in _MAGIC_BYTES:
        if file_bytes.startswith(magic):
            return mime
    raise UnsupportedFileType(
        "Unsupported or unrecognized file type. Only PDF, PNG, and JPEG are supported."
    )


def _validate_upload(file_bytes: bytes) -> str:
    if not file_bytes:
        raise UnsupportedFileType("Uploaded file is empty.")
    if len(file_bytes) > settings.DOCUMENT_MAX_FILE_SIZE_BYTES:
        raise FileTooLarge(
            f"File exceeds the maximum allowed size of "
            f"{settings.DOCUMENT_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )
    return sniff_mime_type(file_bytes)


def _sanitize_display_filename(filename: str) -> str:
    """Display/metadata only — never used to construct a filesystem path.
    Strips control characters (including CR/LF, which would otherwise
    allow header injection if echoed into a Content-Disposition header)."""
    name = os.path.basename(filename or "upload")
    name = re.sub(r"[\x00-\x1f]", "", name)
    return name[:255] or "upload"


def _generate_storage_key(document_id: int, mime_type: str) -> str:
    """Always server-generated from a random UUID — never derived from the
    user-supplied filename — so a storage key can never be used to smuggle
    a path-traversal sequence into the storage layer. LocalStorageService
    independently re-validates this at the storage layer too (defense in
    depth), but no key produced here could ever trigger that check."""
    ext = _SUPPORTED_MIME_TYPES.get(mime_type, "")
    return f"documents/{document_id}/{uuid.uuid4().hex}{ext}"


def _current_version(db: Session, document: Document) -> Optional[DocumentVersion]:
    if not document.version_number:
        return None
    return (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_number == document.version_number,
        )
        .first()
    )


def _get_version(db: Session, document_id: int, version_number: int) -> Optional[DocumentVersion]:
    return (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.document_id == document_id,
            DocumentVersion.version_number == version_number,
        )
        .first()
    )


@dataclass
class VersionUploadResult:
    version: DocumentVersion
    is_duplicate: bool  # True: checksum matched the current version, no new row was created


def save_document_version(
    db: Session,
    scope: AIAuthScope,
    document_id: int,
    file_bytes: bytes,
    filename: str,
) -> VersionUploadResult:
    """Authorize, validate, and persist `file_bytes` as a new version of
    `document_id`. Deduplicates against the CURRENT version only, by
    SHA-256 checksum — re-uploading byte-identical content is a no-op
    (returns the existing current version, is_duplicate=True) rather than
    growing the version history. An archived document must be unarchived
    first (409) — archiving freezes a document's file history."""
    document = get_authorized_document(db, scope, document_id)
    if document.is_archived:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Document is archived; unarchive it before uploading a new version.",
        )

    try:
        mime_type = _validate_upload(file_bytes)
    except (UnsupportedFileType, FileTooLarge) as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))

    checksum = hashlib.sha256(file_bytes).hexdigest()

    current = _current_version(db, document)
    if current is not None and current.checksum == checksum:
        return VersionUploadResult(version=current, is_duplicate=True)

    next_version_number = (document.version_number or 0) + 1
    storage_key = _generate_storage_key(document_id, mime_type)
    storage = get_storage_service()
    storage.save(storage_key, file_bytes)

    original_filename = _sanitize_display_filename(filename)
    now = datetime.now(timezone.utc)

    version = DocumentVersion(
        document_id=document_id,
        version_number=next_version_number,
        storage_key=storage_key,
        storage_provider=settings.DOCUMENT_STORAGE_PROVIDER,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=len(file_bytes),
        checksum=checksum,
        uploaded_by=scope.user_id,
    )
    db.add(version)

    # Current-version snapshot only — original creation-time metadata
    # (title/doc_type/doc_date/content_summary/project_id) is never touched.
    document.storage_key = storage_key
    document.original_filename = original_filename
    document.mime_type = mime_type
    document.file_size = len(file_bytes)
    document.checksum = checksum
    document.uploaded_at = now
    document.uploaded_by = scope.user_id
    document.version_number = next_version_number

    db.commit()
    db.refresh(version)

    logger.info(
        "document_version_saved document_id=%s version_number=%s file_size=%s checksum=%s",
        document_id, next_version_number, version.file_size, checksum[:12],
    )
    return VersionUploadResult(version=version, is_duplicate=False)


def list_document_versions(
    db: Session, scope: AIAuthScope, document_id: int
) -> tuple[Document, list[DocumentVersion]]:
    document = get_authorized_document(db, scope, document_id)
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .all()
    )
    return document, versions


@dataclass
class DownloadResult:
    file_bytes: bytes
    filename: str
    mime_type: str
    version_number: int


def get_document_file(
    db: Session,
    scope: AIAuthScope,
    document_id: int,
    version_number: Optional[int] = None,
) -> DownloadResult:
    """Fetch the stored bytes for a document's current version, or a
    specific historical version_number — every previous version remains
    retrievable exactly like the current one, same authorization boundary
    (project membership / organization membership) as every other document
    read in this app."""
    document = get_authorized_document(db, scope, document_id)

    target_version_number = version_number if version_number is not None else document.version_number
    if not target_version_number:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="This document has no stored file yet.",
        )

    version = _get_version(db, document_id, target_version_number)
    if version is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Version {target_version_number} not found for this document.",
        )

    storage = get_storage_service()
    if not storage.exists(version.storage_key):
        logger.error(
            "document_version_file_missing document_id=%s version_number=%s",
            document_id, version.version_number,
        )
        raise HTTPException(
            status_code=http_status.HTTP_410_GONE,
            detail="The stored file for this version is missing from storage.",
        )

    file_bytes = storage.get(version.storage_key)
    return DownloadResult(
        file_bytes=file_bytes,
        filename=version.original_filename,
        mime_type=version.mime_type,
        version_number=version.version_number,
    )


def archive_document(db: Session, scope: AIAuthScope, document_id: int) -> Document:
    """Soft delete only — sets is_archived. No row (Document, DocumentVersion)
    and no stored file is ever removed; archiving is fully reversible via
    unarchive_document()."""
    document = get_authorized_document(db, scope, document_id)
    document.is_archived = True
    db.commit()
    db.refresh(document)
    return document


def unarchive_document(db: Session, scope: AIAuthScope, document_id: int) -> Document:
    document = get_authorized_document(db, scope, document_id)
    document.is_archived = False
    db.commit()
    db.refresh(document)
    return document
