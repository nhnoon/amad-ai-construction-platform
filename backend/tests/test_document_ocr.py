"""Tests for the Document OCR Foundation (app/ai/document_ocr.py).

Real Postgres DB (same pattern as test_meeting_memory.py). External OCR
(Tesseract) is mocked via the single _ocr_image() call point — this suite
does not require a real Tesseract install. Selectable-text PDF extraction
uses real PyMuPDF-generated PDFs (no external binary needed for that path).
"""
import os

import fitz
import pytest
from fastapi import HTTPException

import app.ai.document_ocr as ocr_module
from app.ai.document_ocr import (
    ExtractionOutcome,
    FileTooLarge,
    UnsupportedFileType,
    extract_document_text,
    get_document_ocr_result,
    process_document_ocr,
)
from app.ai.memory import get_memory_notes
from app.ai.scope import AIAuthScope
from app.models.document_ocr import DocumentOCRResult
from app.models.documents import Document

_REAL_PROJECT_ID = 1
_USER_A = 1  # admin@construction.ai — global read access


def _global_scope(user_id: int = _USER_A, org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id,
        user_id=user_id,
        user_role="admin",
        accessible_project_ids=(),
    )


def _restricted_scope(user_id: int = _USER_A, org_id: int = 1) -> AIAuthScope:
    """A non-global-read scope with no access to _REAL_PROJECT_ID."""
    return AIAuthScope(
        organization_id=org_id,
        user_id=user_id,
        user_role="site_engineer",
        accessible_project_ids=(999_999,),
    )


def _make_pdf_bytes(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_document(db_session):
    """A fresh, throwaway Document row (real FK to project 1) for each test."""
    doc = Document(
        project_id=_REAL_PROJECT_ID,
        doc_type="test_ocr",
        title="OCR Foundation Test Document",
        doc_date="2026-07-13",
        content_summary="Created by automated OCR foundation tests; safe to delete.",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    # Snapshot original metadata to prove OCR never mutates it (test #13).
    original = {
        "project_id": doc.project_id, "doc_type": doc.doc_type, "title": doc.title,
        "doc_date": doc.doc_date, "content_summary": doc.content_summary,
    }

    yield doc_id, original

    ocr_row = (
        db_session.query(DocumentOCRResult)
        .filter(DocumentOCRResult.document_id == doc_id)
        .first()
    )
    if ocr_row and ocr_row.storage_path and os.path.isfile(ocr_row.storage_path):
        os.remove(ocr_row.storage_path)
    db_session.query(DocumentOCRResult).filter(
        DocumentOCRResult.document_id == doc_id
    ).delete()
    db_session.query(Document).filter(Document.id == doc_id).delete()
    db_session.commit()


class TestSelectableTextPDFExtraction:
    def test_selectable_text_pdf_extracts_directly(self):
        pdf_bytes = _make_pdf_bytes(["Hello Construction World"])
        outcome = extract_document_text(pdf_bytes)
        assert outcome.status == "completed"
        assert "Hello Construction World" in outcome.extracted_text
        assert outcome.extraction_method == "pdf_text_layer"
        assert outcome.page_count == 1

    def test_multi_page_pdf_preserves_page_count(self):
        pdf_bytes = _make_pdf_bytes(["Page one text", "Page two text"])
        outcome = extract_document_text(pdf_bytes)
        assert outcome.status == "completed"
        assert outcome.page_count == 2
        assert "Page one text" in outcome.extracted_text
        assert "Page two text" in outcome.extracted_text


class TestImageOCRPathMocked:
    def test_image_ocr_uses_mocked_engine(self, monkeypatch):
        monkeypatch.setattr(ocr_module, "_tesseract_available", lambda: True)
        monkeypatch.setattr(ocr_module, "_ocr_image", lambda image: "Mocked OCR output text")

        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")

        outcome = extract_document_text(buf.getvalue())
        assert outcome.status == "completed"
        assert outcome.extracted_text == "Mocked OCR output text"
        assert outcome.extraction_method == "ocr_tesseract"

    def test_image_ocr_fails_safely_when_tesseract_unavailable(self, monkeypatch):
        monkeypatch.setattr(ocr_module, "_tesseract_available", lambda: False)

        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")

        outcome = extract_document_text(buf.getvalue())
        assert outcome.status == "failed"
        assert "Tesseract" in outcome.error_message


class TestUnsupportedFileType:
    def test_unsupported_bytes_raise(self):
        with pytest.raises(UnsupportedFileType):
            extract_document_text(b"this is not a pdf or image, just text bytes")

    def test_empty_file_raises(self):
        with pytest.raises(UnsupportedFileType):
            extract_document_text(b"")

    def test_process_document_ocr_returns_400_for_unsupported_type(
        self, db_session, test_document
    ):
        doc_id, _ = test_document
        with pytest.raises(HTTPException) as exc_info:
            process_document_ocr(
                db_session, _global_scope(), doc_id,
                b"not a real document", "notes.txt",
            )
        assert exc_info.value.status_code == 400


class TestMissingDocument:
    def test_process_missing_document_raises_404(self, db_session):
        pdf_bytes = _make_pdf_bytes(["irrelevant"])
        with pytest.raises(HTTPException) as exc_info:
            process_document_ocr(
                db_session, _global_scope(), 999_999_999, pdf_bytes, "test.pdf",
            )
        assert exc_info.value.status_code == 404

    def test_get_missing_document_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_document_ocr_result(db_session, _global_scope(), 999_999_999)
        assert exc_info.value.status_code == 404


class TestUnauthorizedAccess:
    def test_unauthorized_process_blocked(self, db_session, test_document):
        doc_id, _ = test_document
        pdf_bytes = _make_pdf_bytes(["secret"])
        with pytest.raises(HTTPException) as exc_info:
            process_document_ocr(
                db_session, _restricted_scope(), doc_id, pdf_bytes, "test.pdf",
            )
        assert exc_info.value.status_code == 403

    def test_unauthorized_read_blocked(self, db_session, test_document):
        doc_id, _ = test_document
        with pytest.raises(HTTPException) as exc_info:
            get_document_ocr_result(db_session, _restricted_scope(), doc_id)
        assert exc_info.value.status_code == 403


class TestResultNotYetAvailable:
    def test_reading_before_processing_returns_404(self, db_session, test_document):
        doc_id, _ = test_document
        with pytest.raises(HTTPException) as exc_info:
            get_document_ocr_result(db_session, _global_scope(), doc_id)
        assert exc_info.value.status_code == 404


class TestExtractionFailureStoredAsFailed:
    def test_corrupt_pdf_stored_as_failed_not_raised(self, db_session, test_document):
        doc_id, _ = test_document
        corrupt_pdf = b"%PDF-1.4\nthis is not a valid pdf body\n%%EOF"
        row = process_document_ocr(
            db_session, _global_scope(), doc_id, corrupt_pdf, "corrupt.pdf",
        )
        assert row.status == "failed"
        assert row.error_message


class TestSuccessfulResultPersisted:
    def test_successful_extraction_persists_row(self, db_session, test_document):
        doc_id, _ = test_document
        pdf_bytes = _make_pdf_bytes(["Persisted extraction content"])
        row = process_document_ocr(
            db_session, _global_scope(), doc_id, pdf_bytes, "test.pdf",
        )
        assert row.status == "completed"
        assert "Persisted extraction content" in row.extracted_text

        fetched = get_document_ocr_result(db_session, _global_scope(), doc_id)
        assert fetched.id == row.id
        assert fetched.status == "completed"


class TestRepeatedProcessing:
    def test_repeated_processing_updates_single_row(self, db_session, test_document):
        doc_id, _ = test_document
        first = process_document_ocr(
            db_session, _global_scope(), doc_id,
            _make_pdf_bytes(["First version"]), "v1.pdf",
        )
        second = process_document_ocr(
            db_session, _global_scope(), doc_id,
            _make_pdf_bytes(["Second version"]), "v2.pdf",
        )
        assert first.id == second.id  # same row, upserted not duplicated

        count = (
            db_session.query(DocumentOCRResult)
            .filter(DocumentOCRResult.document_id == doc_id)
            .count()
        )
        assert count == 1
        assert "Second version" in second.extracted_text
        assert "First version" not in second.extracted_text


class TestMaximumTextBound:
    def test_extracted_text_is_truncated_to_configured_limit(self, monkeypatch):
        monkeypatch.setattr(ocr_module.settings, "OCR_MAX_EXTRACTED_TEXT_CHARS", 50)
        long_text = "A" * 500
        pdf_bytes = _make_pdf_bytes([long_text])
        outcome = extract_document_text(pdf_bytes)
        assert outcome.status == "completed"
        assert len(outcome.extracted_text) <= 50


class TestNoLLMCall:
    def test_process_document_ocr_never_calls_llm_provider(
        self, db_session, test_document, monkeypatch
    ):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("document OCR must never call get_llm_provider()")

        monkeypatch.setattr(
            "app.ai.providers.factory.get_llm_provider", _fail_if_called
        )
        doc_id, _ = test_document
        row = process_document_ocr(
            db_session, _global_scope(), doc_id,
            _make_pdf_bytes(["No LLM call here"]), "test.pdf",
        )
        assert row.status == "completed"


class TestNoMemoryWrite:
    def test_process_document_ocr_never_writes_memory(self, db_session, test_document, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("document OCR must never write Copilot memory")

        monkeypatch.setattr("app.ai.memory.append_memory_note", _fail_if_called)
        monkeypatch.setattr("app.ai.memory.set_memory_notes", _fail_if_called)

        doc_id, _ = test_document
        before = get_memory_notes(db_session, _global_scope())
        process_document_ocr(
            db_session, _global_scope(), doc_id,
            _make_pdf_bytes(["No memory write here"]), "test.pdf",
        )
        after = get_memory_notes(db_session, _global_scope())
        assert before == after


class TestOriginalDocumentUnchanged:
    def test_original_document_metadata_unchanged_after_ocr(self, db_session, test_document):
        doc_id, original = test_document
        process_document_ocr(
            db_session, _global_scope(), doc_id,
            _make_pdf_bytes(["Some content"]), "test.pdf",
        )
        db_session.expire_all()
        doc = db_session.query(Document).filter(Document.id == doc_id).first()
        assert doc.project_id == original["project_id"]
        assert doc.doc_type == original["doc_type"]
        assert doc.title == original["title"]
        assert doc.doc_date == original["doc_date"]
        assert doc.content_summary == original["content_summary"]
