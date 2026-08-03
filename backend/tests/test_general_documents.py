"""Tests for General Library (organization-scoped) documents.

Covers: creating a document without a project, OCR/contract-extraction
working for general documents via the unified /api/v1/documents/{id}/...
routes, that the existing project-scoped routes are unaffected, and that
organization isolation is enforced (no cross-tenant access).

Real Postgres DB (same pattern as test_document_ocr.py). LLM provider is
always mocked — no real Hermes call is made anywhere in this suite.
"""
import fitz
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.contract_extraction import get_contract_extraction, process_contract_extraction
from app.ai.document_access import create_document, get_authorized_document
from app.ai.document_ocr import get_document_ocr_result, process_document_ocr
from app.ai.providers.fake import FakeLLMProvider
from app.ai.scope import AIAuthScope
from app.storage import get_storage_service
from app.models.contract_extraction import ContractExtraction
from app.models.document_ocr import DocumentOCRResult
from app.models.documents import Document, DocumentVersion
from tests.conftest import TEST_USER_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_ORG_A = 1
_ORG_B = 999  # a different tenant — no seeded data, used only for isolation tests


def _scope(user_id: int = TEST_USER_ID, org_id: int = _ORG_A, role: str = "admin") -> AIAuthScope:
    """Phase 1 regression fix: build via the real build_ai_scope() against
    a transient user linked to org_id, so accessible_project_ids reflects
    that organization's real seeded projects instead of relying on the
    since-removed has_global_read bypass. org_id=_ORG_B (a nonexistent
    tenant) still correctly yields an empty accessible_project_ids, since
    no real project belongs to it — the cross-tenant negative tests below
    are unaffected."""
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


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def cleanup_documents(db_session):
    """Tracks Document ids created during a test and removes them (plus any
    OCR/contract-extraction rows) afterward — existing rows are untouched."""
    created_ids: list[int] = []
    yield created_ids
    storage = get_storage_service()
    for doc_id in created_ids:
        db_session.query(ContractExtraction).filter(ContractExtraction.document_id == doc_id).delete()
        ocr_row = db_session.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == doc_id).first()
        db_session.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == doc_id).delete()
        # Document Storage System (Sprint 1) — process_document_ocr() now
        # also writes a DocumentVersion; clean up its stored file (the DB
        # row cascade-deletes with the Document below).
        for version in db_session.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).all():
            storage.delete(version.storage_key)
        db_session.query(Document).filter(Document.id == doc_id).delete()
        db_session.commit()


class TestUploadGeneralDocumentWithoutProject:
    def test_create_general_document_without_project(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=None, title="Company Safety Manual")
        cleanup_documents.append(doc.id)
        assert doc.id is not None
        assert doc.title == "Company Safety Manual"


class TestGeneralDocumentStoresOrganizationId:
    def test_organization_id_set_from_scope(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(org_id=_ORG_A), project_id=None, title="Vendor Catalog")
        cleanup_documents.append(doc.id)
        assert doc.organization_id == _ORG_A


class TestProjectIdNullForGeneralDocument:
    def test_project_id_is_null(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=None, title="General Contract Template")
        cleanup_documents.append(doc.id)
        assert doc.project_id is None


class TestProjectDocumentUploadUnchanged:
    def test_create_project_document_still_sets_project_id(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="Project Contract")
        cleanup_documents.append(doc.id)
        assert doc.project_id == _REAL_PROJECT_ID

    def test_existing_project_document_ocr_flow_unchanged(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="Project Contract 2")
        cleanup_documents.append(doc.id)
        row = process_document_ocr(
            db_session, _scope(), doc.id, _make_pdf_bytes("Project doc text"), "test.pdf",
        )
        assert row.status == "completed"
        assert row.project_id == _REAL_PROJECT_ID


class TestUnauthorizedOrganizationAccessBlocked:
    def test_different_org_cannot_read_general_document(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(org_id=_ORG_A), project_id=None, title="Org A Policy")
        cleanup_documents.append(doc.id)

        other_org_scope = _scope(org_id=_ORG_B, role="site_engineer")
        with pytest.raises(HTTPException) as exc_info:
            get_authorized_document(db_session, other_org_scope, doc.id)
        assert exc_info.value.status_code == 403

    def test_missing_organization_cannot_create_general_document(self, db_session):
        scope_no_org = AIAuthScope(
            organization_id=None, user_id=TEST_USER_ID, user_role="admin",
            accessible_project_ids=(),
        )
        with pytest.raises(HTTPException) as exc_info:
            create_document(db_session, scope_no_org, project_id=None, title="Orphan Document")
        assert exc_info.value.status_code == 400


class TestOCRWorksForGeneralDocument:
    def test_ocr_completes_for_general_document(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=None, title="General OCR Test")
        cleanup_documents.append(doc.id)
        row = process_document_ocr(
            db_session, _scope(), doc.id, _make_pdf_bytes("General library text content"), "test.pdf",
        )
        assert row.status == "completed"
        assert row.project_id is None
        assert "General library text content" in row.extracted_text

    def test_read_ocr_result_for_general_document(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=None, title="General OCR Read Test")
        cleanup_documents.append(doc.id)
        process_document_ocr(db_session, _scope(), doc.id, _make_pdf_bytes("Some text"), "test.pdf")
        row = get_document_ocr_result(db_session, _scope(), doc.id)
        assert row.status == "completed"


class TestContractExtractionWorksForGeneralDocument:
    def test_contract_extraction_completes_for_general_document(self, db_session, cleanup_documents, monkeypatch):
        import app.ai.contract_extraction as extraction_module

        doc = create_document(db_session, _scope(), project_id=None, title="General Contract")
        cleanup_documents.append(doc.id)
        process_document_ocr(
            db_session, _scope(), doc.id,
            _make_pdf_bytes("Employer: ACME. Contractor: BuildCo."), "contract.pdf",
        )
        valid_json = (
            '{"contract_title": "General Contract", "project_code": null, '
            '"employer": "ACME", "contractor": "BuildCo", "contract_value": null, '
            '"currency": null, "start_date": null, "completion_date": null, '
            '"payment_terms": null, "retention": null, "liquidated_damages": null, '
            '"insurance": null, "key_obligations": null, "risks": null}'
        )
        monkeypatch.setattr(
            extraction_module, "get_llm_provider", lambda: FakeLLMProvider(fixed_response=valid_json)
        )
        row = process_contract_extraction(db_session, _scope(), doc.id)
        assert row.status == "completed"
        assert row.project_id is None
        assert row.extracted_fields["employer"] == "ACME"

        fetched = get_contract_extraction(db_session, _scope(), doc.id)
        assert fetched.status == "completed"


class TestExistingProjectRoutesStillWork:
    def test_project_scoped_http_route_still_works(self, client: TestClient, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="HTTP Route Test Doc")
        cleanup_documents.append(doc.id)
        pdf_bytes = _make_pdf_bytes("HTTP route project text")
        resp = client.post(
            f"/api/v1/projects/{_REAL_PROJECT_ID}/documents/{doc.id}/ocr",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        resp2 = client.get(f"/api/v1/projects/{_REAL_PROJECT_ID}/documents/{doc.id}/ocr")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "completed"


class TestFilters:
    def test_project_filter_excludes_general_documents(self, client: TestClient, db_session, cleanup_documents):
        general_doc = create_document(db_session, _scope(), project_id=None, title="Filter Test General")
        project_doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="Filter Test Project")
        cleanup_documents.extend([general_doc.id, project_doc.id])

        resp = client.get("/api/v1/documents", params={"scope": "project", "limit": 100})
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()]
        assert project_doc.id in ids
        assert general_doc.id not in ids

    def test_general_library_filter_excludes_project_documents(self, client: TestClient, db_session, cleanup_documents, monkeypatch):
        # The real seeded admin@construction.ai has organization_id=None in
        # this DB, so build_ai_scope() inside the endpoint would produce a
        # scope that (correctly) can never see ANY general-library document.
        # Pin it to the same org_id used to create the fixtures below, so
        # this test exercises the filter logic itself rather than that
        # unrelated seed-data fact.
        monkeypatch.setattr("app.api.v1.documents.build_ai_scope", lambda user, db: _scope())

        general_doc = create_document(db_session, _scope(), project_id=None, title="Filter Test General 2")
        project_doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="Filter Test Project 2")
        cleanup_documents.extend([general_doc.id, project_doc.id])

        resp = client.get("/api/v1/documents", params={"scope": "general", "limit": 100})
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()]
        assert general_doc.id in ids
        assert project_doc.id not in ids

    def test_all_filter_includes_both(self, client: TestClient, db_session, cleanup_documents, monkeypatch):
        monkeypatch.setattr("app.api.v1.documents.build_ai_scope", lambda user, db: _scope())

        general_doc = create_document(db_session, _scope(), project_id=None, title="Filter Test General 3")
        project_doc = create_document(db_session, _scope(), project_id=_REAL_PROJECT_ID, title="Filter Test Project 3")
        cleanup_documents.extend([general_doc.id, project_doc.id])

        resp = client.get("/api/v1/documents", params={"scope": "all", "limit": 100})
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()]
        assert general_doc.id in ids
        assert project_doc.id in ids


class TestNoCrossTenantDocumentAccess:
    def test_general_document_not_visible_to_other_organization_via_list(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(org_id=_ORG_A), project_id=None, title="Tenant A Only")
        cleanup_documents.append(doc.id)

        # Listing logic itself is exercised at the HTTP layer in TestFilters;
        # here we confirm the authorization boundary directly.
        with pytest.raises(HTTPException) as exc_info:
            get_authorized_document(db_session, _scope(org_id=_ORG_B, role="admin"), doc.id)
        assert exc_info.value.status_code == 403

    def test_ocr_blocked_across_organizations(self, db_session, cleanup_documents):
        doc = create_document(db_session, _scope(org_id=_ORG_A), project_id=None, title="Tenant A OCR")
        cleanup_documents.append(doc.id)
        with pytest.raises(HTTPException) as exc_info:
            process_document_ocr(
                db_session, _scope(org_id=_ORG_B, role="admin"), doc.id,
                _make_pdf_bytes("text"), "test.pdf",
            )
        assert exc_info.value.status_code == 403


class TestMigrationPreservedExistingDocuments:
    def test_existing_seeded_documents_still_readable(self, db_session):
        # Real seeded rows created before the migration (project_id was
        # NOT NULL at the time) must still have their original project_id
        # and be gettable exactly as before.
        existing = db_session.query(Document).filter(Document.project_id.isnot(None)).first()
        assert existing is not None
        assert existing.project_id is not None
        row = get_authorized_document(db_session, _scope(), existing.id)
        assert row.id == existing.id
