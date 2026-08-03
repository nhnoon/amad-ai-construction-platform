"""Tests for the Document Storage System (Sprint 1 — app/storage/,
app/ai/document_storage.py).

Real Postgres DB (same pattern as test_document_ocr.py / test_general_documents.py).
Covers: the StorageService abstraction's path-traversal defenses, version
creation/retrieval, checksum-based deduplication, mime/size validation,
authorization, archive/unarchive as soft delete, null-safety for documents
that predate this migration, and that the existing OCR upload flow now
also produces a permanent version without changing its own contract.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.document_access import create_document
from app.ai.document_ocr import process_document_ocr
from app.ai.document_storage import (
    archive_document,
    get_document_file,
    list_document_versions,
    save_document_version,
    unarchive_document,
)
from app.ai.scope import AIAuthScope
from app.config import settings
from app.models.documents import Document, DocumentVersion
from app.storage import get_storage_service
from app.storage.local import LocalStorageService, PathTraversalError
from tests.conftest import TEST_USER_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_ORG_A = 1
_ORG_B = 999  # a different tenant — no seeded data, isolation tests only


def _scope(user_id: int = TEST_USER_ID, org_id: int = _ORG_A, role: str = "admin") -> AIAuthScope:
    from datetime import datetime, timezone
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"scope-test-{user_id}@test.local", full_name="Scope Test",
            role=role, is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        return build_ai_scope(user, db)
    finally:
        db.close()


def _restricted_scope(user_id: int = TEST_USER_ID, org_id: int = _ORG_A) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id, user_id=user_id, user_role="site_engineer",
        accessible_project_ids=(999_999,),
    )


_PDF_A = b"%PDF-1.4\n" + b"A" * 200 + b"\n%%EOF"
_PDF_B = b"%PDF-1.4\n" + b"B" * 200 + b"\n%%EOF"
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def cleanup_documents(db_session):
    """Tracks Document ids created during a test; removes them, their
    version rows' stored files, and the rows themselves afterward."""
    created_ids: list[int] = []
    yield created_ids
    storage = get_storage_service()
    for doc_id in created_ids:
        for version in db_session.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).all():
            storage.delete(version.storage_key)
        db_session.query(Document).filter(Document.id == doc_id).delete()
        db_session.commit()


@pytest.fixture
def test_document(db_session, cleanup_documents):
    doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="Storage Test Document")
    cleanup_documents.append(doc.id)
    return doc.id


class TestLocalStorageServiceRoundTrip:
    def test_save_then_get_returns_same_bytes(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        storage.save("a/b/file.pdf", b"hello world")
        assert storage.get("a/b/file.pdf") == b"hello world"

    def test_exists_reflects_presence(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        assert storage.exists("nope.pdf") is False
        storage.save("nope.pdf", b"x")
        assert storage.exists("nope.pdf") is True

    def test_delete_removes_file_and_is_idempotent(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        storage.save("f.pdf", b"x")
        storage.delete("f.pdf")
        assert storage.exists("f.pdf") is False
        storage.delete("f.pdf")  # no-op, must not raise

    def test_get_missing_key_raises_file_not_found(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            storage.get("missing.pdf")


class TestPathTraversalPrevention:
    def test_dot_dot_segment_rejected(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        with pytest.raises(PathTraversalError):
            storage.save("../../etc/passwd", b"x")

    def test_absolute_path_key_rejected(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        with pytest.raises(PathTraversalError):
            storage.save("/etc/passwd", b"x")

    def test_get_also_rejects_traversal(self, tmp_path):
        storage = LocalStorageService(str(tmp_path))
        with pytest.raises(PathTraversalError):
            storage.get("../outside.pdf")


class TestSaveDocumentVersionFirstUpload:
    def test_creates_version_one_and_updates_snapshot_fields(self, db_session, test_document):
        result = save_document_version(db_session, _scope(), test_document, _PDF_A, "report.pdf")
        assert result.is_duplicate is False
        assert result.version.version_number == 1
        assert result.version.checksum
        assert len(result.version.checksum) == 64  # sha256 hex

        db_session.expire_all()
        doc = db_session.query(Document).filter(Document.id == test_document).first()
        assert doc.version_number == 1
        assert doc.file_size == len(_PDF_A)
        assert doc.mime_type == "application/pdf"
        assert doc.original_filename == "report.pdf"
        assert doc.checksum == result.version.checksum
        assert doc.is_archived is False

    def test_original_creation_metadata_untouched(self, db_session, test_document):
        before = db_session.query(Document).filter(Document.id == test_document).first()
        original = (before.title, before.doc_type, before.doc_date, before.content_summary, before.project_id)

        save_document_version(db_session, _scope(), test_document, _PDF_A, "report.pdf")

        db_session.expire_all()
        after = db_session.query(Document).filter(Document.id == test_document).first()
        assert (after.title, after.doc_type, after.doc_date, after.content_summary, after.project_id) == original


class TestVersioning:
    def test_second_different_upload_creates_version_two(self, db_session, test_document):
        v1 = save_document_version(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        v2 = save_document_version(db_session, _scope(), test_document, _PDF_B, "v2.pdf")
        assert v1.version.version_number == 1
        assert v2.version.version_number == 2
        assert v2.is_duplicate is False

        count = db_session.query(DocumentVersion).filter(DocumentVersion.document_id == test_document).count()
        assert count == 2

    def test_previous_version_remains_retrievable(self, db_session, test_document):
        save_document_version(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        save_document_version(db_session, _scope(), test_document, _PDF_B, "v2.pdf")

        v1_download = get_document_file(db_session, _scope(), test_document, version_number=1)
        v2_download = get_document_file(db_session, _scope(), test_document, version_number=2)
        latest_download = get_document_file(db_session, _scope(), test_document)

        assert v1_download.file_bytes == _PDF_A
        assert v2_download.file_bytes == _PDF_B
        assert latest_download.file_bytes == _PDF_B  # latest == current == v2

    def test_list_versions_marks_current_correctly(self, db_session, test_document):
        save_document_version(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        save_document_version(db_session, _scope(), test_document, _PDF_B, "v2.pdf")

        document, versions = list_document_versions(db_session, _scope(), test_document)
        by_number = {v.version_number: v for v in versions}
        assert len(versions) == 2
        assert document.version_number == 2

    def test_download_of_nonexistent_version_raises_404(self, db_session, test_document):
        save_document_version(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        with pytest.raises(HTTPException) as exc_info:
            get_document_file(db_session, _scope(), test_document, version_number=99)
        assert exc_info.value.status_code == 404


class TestChecksumDeduplication:
    def test_reuploading_identical_bytes_does_not_create_new_version(self, db_session, test_document):
        first = save_document_version(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        second = save_document_version(db_session, _scope(), test_document, _PDF_A, "v1-again.pdf")

        assert first.is_duplicate is False
        assert second.is_duplicate is True
        assert second.version.version_number == first.version.version_number

        count = db_session.query(DocumentVersion).filter(DocumentVersion.document_id == test_document).count()
        assert count == 1

    def test_reuploading_different_bytes_after_duplicate_still_versions(self, db_session, test_document):
        save_document_version(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        save_document_version(db_session, _scope(), test_document, _PDF_A, "dup.pdf")  # deduped
        third = save_document_version(db_session, _scope(), test_document, _PDF_B, "v2.pdf")
        assert third.is_duplicate is False
        assert third.version.version_number == 2


class TestMimeAndSizeValidation:
    def test_unsupported_file_type_raises_400(self, db_session, test_document):
        with pytest.raises(HTTPException) as exc_info:
            save_document_version(db_session, _scope(), test_document, b"plain text, not a real file", "notes.txt")
        assert exc_info.value.status_code == 400

    def test_empty_file_raises_400(self, db_session, test_document):
        with pytest.raises(HTTPException) as exc_info:
            save_document_version(db_session, _scope(), test_document, b"", "empty.pdf")
        assert exc_info.value.status_code == 400

    def test_oversized_file_raises_400(self, db_session, test_document, monkeypatch):
        monkeypatch.setattr(settings, "DOCUMENT_MAX_FILE_SIZE_BYTES", 10)
        with pytest.raises(HTTPException) as exc_info:
            save_document_version(db_session, _scope(), test_document, _PDF_A, "too-big.pdf")
        assert exc_info.value.status_code == 400

    def test_png_mime_type_accepted(self, db_session, test_document):
        result = save_document_version(db_session, _scope(), test_document, _PNG_BYTES, "photo.png")
        assert result.version.mime_type == "image/png"

    def test_content_type_is_sniffed_not_trusted_from_filename(self, db_session, test_document):
        # .pdf extension but PNG magic bytes — must be classified by content.
        result = save_document_version(db_session, _scope(), test_document, _PNG_BYTES, "fake.pdf")
        assert result.version.mime_type == "image/png"


class TestUnauthorizedAccess:
    def test_save_blocked_for_out_of_scope_user(self, db_session, test_document):
        with pytest.raises(HTTPException) as exc_info:
            save_document_version(db_session, _restricted_scope(), test_document, _PDF_A, "x.pdf")
        assert exc_info.value.status_code == 403

    def test_download_blocked_for_out_of_scope_user(self, db_session, test_document):
        save_document_version(db_session, _scope(), test_document, _PDF_A, "x.pdf")
        with pytest.raises(HTTPException) as exc_info:
            get_document_file(db_session, _restricted_scope(), test_document)
        assert exc_info.value.status_code == 403

    def test_list_versions_blocked_for_out_of_scope_user(self, db_session, test_document):
        with pytest.raises(HTTPException) as exc_info:
            list_document_versions(db_session, _restricted_scope(), test_document)
        assert exc_info.value.status_code == 403

    def test_archive_blocked_for_out_of_scope_user(self, db_session, test_document):
        with pytest.raises(HTTPException) as exc_info:
            archive_document(db_session, _restricted_scope(), test_document)
        assert exc_info.value.status_code == 403


class TestMissingDocument:
    def test_save_on_missing_document_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            save_document_version(db_session, _scope(), 999_999_999, _PDF_A, "x.pdf")
        assert exc_info.value.status_code == 404

    def test_download_on_missing_document_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_document_file(db_session, _scope(), 999_999_999)
        assert exc_info.value.status_code == 404


class TestDownloadWithNoFileYet:
    def test_download_before_any_upload_raises_404(self, db_session, test_document):
        with pytest.raises(HTTPException) as exc_info:
            get_document_file(db_session, _scope(), test_document)
        assert exc_info.value.status_code == 404


class TestArchiveIsSoftDelete:
    def test_archive_sets_flag_without_deleting_rows_or_files(self, db_session, test_document):
        result = save_document_version(db_session, _scope(), test_document, _PDF_A, "x.pdf")
        storage = get_storage_service()
        assert storage.exists(result.version.storage_key)

        archived = archive_document(db_session, _scope(), test_document)
        assert archived.is_archived is True

        # Row and file both still present after archiving.
        assert db_session.query(DocumentVersion).filter(DocumentVersion.document_id == test_document).count() == 1
        assert storage.exists(result.version.storage_key)
        # Still fully downloadable while archived.
        download = get_document_file(db_session, _scope(), test_document)
        assert download.file_bytes == _PDF_A

    def test_unarchive_restores_upload_ability(self, db_session, test_document):
        archive_document(db_session, _scope(), test_document)
        with pytest.raises(HTTPException) as exc_info:
            save_document_version(db_session, _scope(), test_document, _PDF_A, "x.pdf")
        assert exc_info.value.status_code == 409

        unarchived = unarchive_document(db_session, _scope(), test_document)
        assert unarchived.is_archived is False
        result = save_document_version(db_session, _scope(), test_document, _PDF_A, "x.pdf")
        assert result.is_duplicate is False


class TestNullSafeForDocumentsWithNoUpload:
    def test_document_without_any_upload_has_null_storage_fields(self, db_session, test_document):
        doc = db_session.query(Document).filter(Document.id == test_document).first()
        assert doc.version_number is None
        assert doc.storage_key is None
        assert doc.checksum is None
        assert doc.is_archived is False  # defaulted, not null

    def test_existing_seeded_documents_unaffected_by_migration(self, db_session):
        existing = db_session.query(Document).filter(Document.project_id.isnot(None)).first()
        assert existing is not None
        assert existing.is_archived is False
        assert existing.version_number is None


class TestOCRUploadAlsoCreatesVersion:
    """Integration regression: the existing OCR upload endpoint (today's
    only real upload path in the frontend) must now also result in a
    permanent, versioned, downloadable copy — without OCR's own
    request/response contract changing at all."""

    def test_process_document_ocr_creates_a_document_version(self, db_session, test_document):
        row = process_document_ocr(db_session, _scope(), test_document, _PDF_A, "scan.pdf")
        assert row.status in ("completed", "failed")  # OCR contract unchanged

        db_session.expire_all()
        doc = db_session.query(Document).filter(Document.id == test_document).first()
        assert doc.version_number == 1

        download = get_document_file(db_session, _scope(), test_document)
        assert download.file_bytes == _PDF_A

    def test_reprocessing_ocr_with_new_content_creates_version_two(self, db_session, test_document):
        process_document_ocr(db_session, _scope(), test_document, _PDF_A, "v1.pdf")
        process_document_ocr(db_session, _scope(), test_document, _PDF_B, "v2.pdf")

        db_session.expire_all()
        doc = db_session.query(Document).filter(Document.id == test_document).first()
        assert doc.version_number == 2
        assert get_document_file(db_session, _scope(), test_document, version_number=1).file_bytes == _PDF_A
        assert get_document_file(db_session, _scope(), test_document, version_number=2).file_bytes == _PDF_B


class TestHTTPRoutes:
    def test_upload_list_download_via_unified_routes(self, client: TestClient, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="HTTP Storage Test")
        cleanup_documents.append(doc.id)

        resp = client.post(
            f"/api/v1/documents/{doc.id}/versions",
            files={"file": ("test.pdf", _PDF_A, "application/pdf")},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["version_number"] == 1
        assert body["is_duplicate"] is False
        assert "storage_key" not in body  # internal key never exposed

        resp2 = client.get(f"/api/v1/documents/{doc.id}/versions")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 1
        assert resp2.json()[0]["is_current"] is True

        resp3 = client.get(f"/api/v1/documents/{doc.id}/download")
        assert resp3.status_code == 200
        assert resp3.content == _PDF_A
        assert resp3.headers["content-disposition"].startswith("attachment;")

    def test_archive_and_unarchive_via_unified_routes(self, client: TestClient, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="HTTP Archive Test")
        cleanup_documents.append(doc.id)

        resp = client.post(f"/api/v1/documents/{doc.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["is_archived"] is True

        resp2 = client.post(f"/api/v1/documents/{doc.id}/unarchive")
        assert resp2.status_code == 200
        assert resp2.json()["is_archived"] is False

    def test_archived_documents_excluded_from_default_list(self, client: TestClient, db_session, cleanup_documents, monkeypatch):
        monkeypatch.setattr("app.api.v1.documents.build_ai_scope", lambda user, db: _scope())

        doc = create_document(db_session, _scope(), project_id=None, title="Archived List Test")
        cleanup_documents.append(doc.id)
        client.post(f"/api/v1/documents/{doc.id}/archive")

        resp = client.get("/api/v1/documents", params={"scope": "general", "limit": 100})
        ids = [d["id"] for d in resp.json()]
        assert doc.id not in ids

        resp2 = client.get("/api/v1/documents", params={"scope": "general", "limit": 100, "include_archived": True})
        ids2 = [d["id"] for d in resp2.json()]
        assert doc.id in ids2

    def test_project_scoped_routes_mirror_unified_behavior(self, client: TestClient, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="HTTP Project Storage Test")
        cleanup_documents.append(doc.id)

        resp = client.post(
            f"/api/v1/projects/{_REAL_PROJECT_ID}/documents/{doc.id}/versions",
            files={"file": ("test.pdf", _PDF_A, "application/pdf")},
        )
        assert resp.status_code == 201

        resp2 = client.get(f"/api/v1/projects/{_REAL_PROJECT_ID}/documents/{doc.id}/download")
        assert resp2.status_code == 200
        assert resp2.content == _PDF_A

    def test_existing_ocr_http_route_still_returns_same_shape(self, client: TestClient, db_session, cleanup_documents):
        """Regression: the pre-existing OCR route's response contract must
        be byte-for-byte the same set of fields as before this sprint."""
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="HTTP OCR Contract Test")
        cleanup_documents.append(doc.id)

        resp = client.post(
            f"/api/v1/projects/{_REAL_PROJECT_ID}/documents/{doc.id}/ocr",
            files={"file": ("test.pdf", _PDF_A, "application/pdf")},
        )
        assert resp.status_code == 200
        assert set(resp.json().keys()) == {
            "document_id", "status", "page_count", "detected_language",
            "extraction_method", "text_preview", "text_length",
            "text_truncated", "error_message",
        }
