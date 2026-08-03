"""Tests for the Contract Intelligence Extractor (app/ai/contract_extraction.py).

Real Postgres DB (same pattern as test_document_ocr.py). The LLM provider is
always mocked via FakeLLMProvider/a local stub — no real Hermes call is made
anywhere in this suite. OCR is never re-run: tests seed DocumentOCRResult
rows directly with known extracted_text, exactly like Phase 2 would find
after Phase 1 has already completed.
"""
import json

import pytest
from fastapi import HTTPException

import app.ai.contract_extraction as extraction_module
from app.ai.contract_extraction import (
    ContractFields,
    get_contract_extraction,
    process_contract_extraction,
)
from app.ai.document_ocr import process_document_ocr
from app.ai.memory import get_memory_notes
from app.ai.providers.base import LLMResponse, ProviderUnavailableError
from app.ai.providers.fake import FakeLLMProvider
from app.ai.scope import AIAuthScope
from app.models.contract_extraction import ContractExtraction
from app.models.document_ocr import DocumentOCRResult
from app.models.documents import Document

_REAL_PROJECT_ID = 1
_USER_A = 1  # admin@construction.ai

_SAMPLE_CONTRACT_TEXT = (
    "CONSTRUCTION CONTRACT\n\n"
    "This Agreement is entered into between the Ministry of Education "
    "(the Employer) and Al-Rashid Construction Co. (the Contractor) for "
    "the Construction of School Building - Phase 2, project reference "
    "PRJ-0023.\n\n"
    "Contract Value: SAR 12,500,000\n"
    "Commencement Date: 2025-01-15\n"
    "Completion Date: 2026-06-30\n\n"
    "Payment shall be made monthly within 30 days of a certified interim "
    "payment certificate. Retention of 5% shall be withheld until the "
    "final completion certificate is issued. Liquidated damages of 0.1% "
    "of the contract value per day of delay shall apply, capped at 10%. "
    "The Contractor shall maintain Contractor's All Risk insurance for "
    "the full contract value."
)

_VALID_JSON_RESPONSE = json.dumps(
    {
        "contract_title": "Construction of School Building - Phase 2",
        "project_code": "PRJ-0023",
        "employer": "Ministry of Education",
        "contractor": "Al-Rashid Construction Co.",
        "contract_value": "12,500,000",
        "currency": "SAR",
        "start_date": "2025-01-15",
        "completion_date": "2026-06-30",
        "payment_terms": "Monthly progress payments within 30 days of certified IPC",
        "retention": "5% retained until final completion certificate",
        "liquidated_damages": "0.1% of contract value per day of delay, capped at 10%",
        "insurance": "Contractor's All Risk insurance for full contract value",
        "key_obligations": ["Complete works per approved drawings", "Maintain site safety"],
        "risks": ["Potential delay due to permit approval", "Material price volatility"],
    }
)


def _global_scope(user_id: int = _USER_A, org_id: int = 1) -> AIAuthScope:
    """Phase 1 regression fix: build via the real build_ai_scope() against
    a transient admin user linked to org_id, so accessible_project_ids
    reflects that organization's real seeded projects instead of relying
    on the since-removed has_global_read bypass."""
    from datetime import datetime, timezone
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"scope-test-{user_id}@test.local", full_name="Scope Test",
            role="admin", is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        return build_ai_scope(user, db)
    finally:
        db.close()


def _restricted_scope(user_id: int = _USER_A, org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id, user_id=user_id, user_role="site_engineer",
        accessible_project_ids=(999_999,),
    )


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def document_with_completed_ocr(db_session):
    """A Document + a DocumentOCRResult already status="completed" — exactly
    the state Phase 2 should find without ever calling OCR itself."""
    doc = Document(
        project_id=_REAL_PROJECT_ID,
        doc_type="test_contract",
        title="Contract Extraction Test Document",
        doc_date="2026-07-13",
        content_summary="Created by automated contract-extraction tests; safe to delete.",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    ocr_row = DocumentOCRResult(
        document_id=doc_id,
        project_id=_REAL_PROJECT_ID,
        status="completed",
        source_filename="test_contract.pdf",
        mime_type="application/pdf",
        file_size_bytes=len(_SAMPLE_CONTRACT_TEXT),
        storage_path="/nonexistent/test/path.pdf",
        extracted_text=_SAMPLE_CONTRACT_TEXT,
        page_count=1,
        extraction_method="pdf_text_layer",
    )
    db_session.add(ocr_row)
    db_session.commit()

    yield doc_id

    db_session.query(ContractExtraction).filter(
        ContractExtraction.document_id == doc_id
    ).delete()
    db_session.query(DocumentOCRResult).filter(
        DocumentOCRResult.document_id == doc_id
    ).delete()
    db_session.query(Document).filter(Document.id == doc_id).delete()
    db_session.commit()


@pytest.fixture
def document_without_ocr(db_session):
    """A Document with no OCR result at all."""
    doc = Document(
        project_id=_REAL_PROJECT_ID,
        doc_type="test_contract_no_ocr",
        title="Contract Extraction Test Document (no OCR)",
        doc_date="2026-07-13",
        content_summary="Created by automated contract-extraction tests; safe to delete.",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    yield doc_id

    db_session.query(ContractExtraction).filter(
        ContractExtraction.document_id == doc_id
    ).delete()
    db_session.query(Document).filter(Document.id == doc_id).delete()
    db_session.commit()


def _use_fake_provider(monkeypatch, fixed_response: str) -> FakeLLMProvider:
    provider = FakeLLMProvider(fixed_response=fixed_response)
    monkeypatch.setattr(extraction_module, "get_llm_provider", lambda: provider)
    return provider


# ── Retry / deterministic-fallback fixtures ─────────────────────────────

# Explicitly "Label: value" formatted text — unlike _SAMPLE_CONTRACT_TEXT
# (which writes retention/liquidated damages as flowing prose), this is
# what the deterministic fallback extractor is designed to parse.
_LABELED_CONTRACT_TEXT = (
    "CONSTRUCTION CONTRACT\n\n"
    "Contract Title: Riyadh Hospital Extension Works\n"
    "Project Code: PRJ-0099\n"
    "Employer: Ministry of Health\n"
    "Contractor: Gulf Builders LLC\n"
    "Contract Value: SAR 8,750,000\n"
    "Commencement Date: 2025-03-01\n"
    "Completion Date: 2026-09-30\n"
    "Payment Terms: Monthly certified progress payments\n"
    "Retention: 5% of each payment certificate\n"
    "Liquidated Damages: 0.05% of contract value per day, capped at 8%\n"
    "Insurance: Contractor's All Risk policy for the full contract value\n"
)


@pytest.fixture
def document_with_labeled_ocr(db_session):
    """Same shape as document_with_completed_ocr, but with clean
    "Label: value" OCR text — used to exercise the deterministic fallback
    extractor specifically."""
    doc = Document(
        project_id=_REAL_PROJECT_ID,
        doc_type="test_contract_labeled",
        title="Labeled Contract Extraction Test Document",
        doc_date="2026-07-13",
        content_summary="Created by automated contract-extraction tests; safe to delete.",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    ocr_row = DocumentOCRResult(
        document_id=doc_id,
        project_id=_REAL_PROJECT_ID,
        status="completed",
        source_filename="labeled_contract.pdf",
        mime_type="application/pdf",
        file_size_bytes=len(_LABELED_CONTRACT_TEXT),
        storage_path="/nonexistent/test/labeled.pdf",
        extracted_text=_LABELED_CONTRACT_TEXT,
        page_count=1,
        extraction_method="pdf_text_layer",
    )
    db_session.add(ocr_row)
    db_session.commit()

    yield doc_id

    db_session.query(ContractExtraction).filter(ContractExtraction.document_id == doc_id).delete()
    db_session.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == doc_id).delete()
    db_session.query(Document).filter(Document.id == doc_id).delete()
    db_session.commit()


class _SequencedProvider:
    """Returns a different canned response on each successive call — lets
    tests exercise "fails once, succeeds on retry" and "fails both times"
    without a real Hermes call. Tracks system_prompts so tests can assert
    the retry prompt contains the required exact instruction text."""

    provider_name = "hermes"
    model_name = "test-model"

    def __init__(self, responses: list[str]):
        self._responses = responses
        self.call_count = 0
        self.system_prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    def generate(self, request):
        self.system_prompts.append(request.system_prompt)
        idx = min(self.call_count, len(self._responses) - 1)
        content = self._responses[idx]
        self.call_count += 1
        return LLMResponse(content=content, model=self.model_name, provider=self.provider_name)


def _use_sequenced_provider(monkeypatch, responses: list[str]) -> _SequencedProvider:
    provider = _SequencedProvider(responses)
    monkeypatch.setattr(extraction_module, "get_llm_provider", lambda: provider)
    return provider


class TestValidJSONExtraction:
    def test_valid_json_produces_completed_result(self, db_session, document_with_completed_ocr, monkeypatch):
        _use_fake_provider(monkeypatch, _VALID_JSON_RESPONSE)
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)

        assert row.status == "completed"
        assert row.validation_status == "valid"
        assert row.extracted_fields["contract_title"] == "Construction of School Building - Phase 2"
        assert row.extracted_fields["project_code"] == "PRJ-0023"
        assert row.extracted_fields["currency"] == "SAR"
        assert row.extracted_fields["key_obligations"] == [
            "Complete works per approved drawings", "Maintain site safety",
        ]
        assert row.provider == "fake"

    def test_json_wrapped_in_markdown_fence_still_parses(self, db_session, document_with_completed_ocr, monkeypatch):
        fenced = f"Here is the extraction:\n```json\n{_VALID_JSON_RESPONSE}\n```"
        _use_fake_provider(monkeypatch, fenced)
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.extracted_fields["project_code"] == "PRJ-0023"

    def test_unsupported_extra_field_is_dropped(self, db_session, document_with_completed_ocr, monkeypatch):
        data = json.loads(_VALID_JSON_RESPONSE)
        data["signatory_names"] = ["Someone Important"]
        _use_fake_provider(monkeypatch, json.dumps(data))
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert "signatory_names" not in row.extracted_fields


class TestInvalidJSONHandling:
    """document_with_completed_ocr's text has a few explicitly labeled
    lines (Contract Value:, Commencement Date:, Completion Date:), so once
    Hermes fails twice (original + retry) the deterministic fallback now
    rescues these cases into a completed/fallback_valid result instead of
    an outright failure — see TestBothHermesAndFallbackFail for a case
    where even the fallback finds nothing and status genuinely is
    "failed"."""

    def test_malformed_json_is_rescued_by_fallback(self, db_session, document_with_completed_ocr, monkeypatch):
        provider = _use_fake_provider(monkeypatch, "This is not JSON at all, sorry.")
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.validation_status == "fallback_valid"
        assert row.extracted_fields["contract_value"] == "12,500,000"
        assert provider.call_count == 2  # original + one retry, both malformed

    def test_wrong_type_field_is_rescued_by_fallback(self, db_session, document_with_completed_ocr, monkeypatch):
        data = json.loads(_VALID_JSON_RESPONSE)
        data["key_obligations"] = "not a list, just a string"
        _use_fake_provider(monkeypatch, json.dumps(data))
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.validation_status == "fallback_valid"

    def test_json_array_instead_of_object_is_rescued_by_fallback(self, db_session, document_with_completed_ocr, monkeypatch):
        _use_fake_provider(monkeypatch, json.dumps(["not", "an", "object"]))
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.validation_status == "fallback_valid"


class TestMissingDocument:
    def test_process_missing_document_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            process_contract_extraction(db_session, _global_scope(), 999_999_999)
        assert exc_info.value.status_code == 404

    def test_get_missing_document_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_contract_extraction(db_session, _global_scope(), 999_999_999)
        assert exc_info.value.status_code == 404


class TestUnauthorizedAccess:
    def test_unauthorized_process_blocked(self, db_session, document_with_completed_ocr):
        doc_id = document_with_completed_ocr
        with pytest.raises(HTTPException) as exc_info:
            process_contract_extraction(db_session, _restricted_scope(), doc_id)
        assert exc_info.value.status_code == 403

    def test_unauthorized_read_blocked(self, db_session, document_with_completed_ocr):
        doc_id = document_with_completed_ocr
        with pytest.raises(HTTPException) as exc_info:
            get_contract_extraction(db_session, _restricted_scope(), doc_id)
        assert exc_info.value.status_code == 403


class TestRequiresCompletedOCR:
    def test_missing_ocr_result_returns_404(self, db_session, document_without_ocr):
        """No OCR row exists at all yet — reuses get_document_ocr_result's
        own 404 (distinct from the 400 case below, where an OCR row exists
        but never reached status="completed")."""
        doc_id = document_without_ocr
        with pytest.raises(HTTPException) as exc_info:
            process_contract_extraction(db_session, _global_scope(), doc_id)
        assert exc_info.value.status_code == 404

    def test_incomplete_ocr_status_returns_400(self, db_session, document_without_ocr):
        doc_id = document_without_ocr
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        ocr_row = DocumentOCRResult(
            document_id=doc_id, project_id=_REAL_PROJECT_ID, status="failed",
            source_filename="x.pdf", mime_type="application/pdf",
            file_size_bytes=10, storage_path="/nonexistent/x.pdf",
            error_message="OCR engine unavailable",
        )
        db.add(ocr_row)
        db.commit()
        db.close()

        with pytest.raises(HTTPException) as exc_info:
            process_contract_extraction(db_session, _global_scope(), doc_id)
        assert exc_info.value.status_code == 400


class TestReusesExistingOCRTextWithoutRerunningOCR:
    def test_ocr_is_never_re_run(self, db_session, document_with_completed_ocr, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("contract extraction must never re-run OCR")

        monkeypatch.setattr("app.ai.document_ocr.process_document_ocr", _fail_if_called)
        _use_fake_provider(monkeypatch, _VALID_JSON_RESPONSE)
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"

    def test_llm_receives_the_stored_ocr_text(self, db_session, document_with_completed_ocr, monkeypatch):
        captured = {}

        class _CapturingProvider(FakeLLMProvider):
            def generate(self, request):
                captured["user_prompt"] = request.user_prompt
                return LLMResponse(
                    content=_VALID_JSON_RESPONSE, model="fake-model-v1", provider="fake",
                )

        monkeypatch.setattr(extraction_module, "get_llm_provider", lambda: _CapturingProvider())
        doc_id = document_with_completed_ocr

        process_contract_extraction(db_session, _global_scope(), doc_id)
        assert "Al-Rashid Construction Co." in captured["user_prompt"]
        assert "PRJ-0023" in captured["user_prompt"]


class TestRepeatedProcessing:
    def test_repeated_processing_updates_single_row(self, db_session, document_with_completed_ocr, monkeypatch):
        doc_id = document_with_completed_ocr

        _use_fake_provider(monkeypatch, _VALID_JSON_RESPONSE)
        first = process_contract_extraction(db_session, _global_scope(), doc_id)

        second_data = json.loads(_VALID_JSON_RESPONSE)
        second_data["contract_title"] = "Amended Title"
        _use_fake_provider(monkeypatch, json.dumps(second_data))
        second = process_contract_extraction(db_session, _global_scope(), doc_id)

        assert first.id == second.id
        count = (
            db_session.query(ContractExtraction)
            .filter(ContractExtraction.document_id == doc_id)
            .count()
        )
        assert count == 1
        assert second.extracted_fields["contract_title"] == "Amended Title"


class TestProviderUnavailable:
    def test_provider_error_is_rescued_by_fallback_when_text_has_labels(
        self, db_session, document_with_completed_ocr, monkeypatch
    ):
        class _BrokenProvider:
            provider_name = "hermes"
            model_name = "test-model"

            def is_available(self):
                return False

            def generate(self, request):
                raise ProviderUnavailableError("Hermes executable not found on PATH")

        monkeypatch.setattr(extraction_module, "get_llm_provider", lambda: _BrokenProvider())
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        # Provider unreachable -> no retry (nothing to retry), straight to
        # fallback, which finds labeled fields in this fixture's text.
        assert row.status == "completed"
        assert row.validation_status == "fallback_valid"
        assert row.provider == "hermes"  # metadata still shows Hermes was attempted

    def test_provider_error_with_no_labeled_text_stays_failed(self, db_session, monkeypatch):
        doc = Document(
            project_id=_REAL_PROJECT_ID, doc_type="test_contract_unavailable",
            title="Provider Unavailable Test Doc", doc_date="2026-07-13",
            content_summary="Created by automated tests; safe to delete.",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        doc_id = doc.id
        unlabeled_text = "No colon-labeled fields exist anywhere in this short passage."
        ocr_row = DocumentOCRResult(
            document_id=doc_id, project_id=_REAL_PROJECT_ID, status="completed",
            source_filename="unavailable.pdf", mime_type="application/pdf",
            file_size_bytes=len(unlabeled_text), storage_path="/nonexistent/unavailable.pdf",
            extracted_text=unlabeled_text, page_count=1, extraction_method="pdf_text_layer",
        )
        db_session.add(ocr_row)
        db_session.commit()

        class _BrokenProvider:
            provider_name = "hermes"
            model_name = "test-model"

            def is_available(self):
                return False

            def generate(self, request):
                raise ProviderUnavailableError("Hermes executable not found on PATH")

        try:
            monkeypatch.setattr(extraction_module, "get_llm_provider", lambda: _BrokenProvider())
            row = process_contract_extraction(db_session, _global_scope(), doc_id)
            assert row.status == "failed"
            assert "unavailable" in row.error_message.lower()
        finally:
            db_session.query(ContractExtraction).filter(ContractExtraction.document_id == doc_id).delete()
            db_session.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == doc_id).delete()
            db_session.query(Document).filter(Document.id == doc_id).delete()
            db_session.commit()


class TestNoMemoryWrite:
    def test_process_contract_extraction_never_writes_memory(
        self, db_session, document_with_completed_ocr, monkeypatch
    ):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("contract extraction must never write Copilot memory")

        monkeypatch.setattr("app.ai.memory.append_memory_note", _fail_if_called)
        monkeypatch.setattr("app.ai.memory.set_memory_notes", _fail_if_called)
        _use_fake_provider(monkeypatch, _VALID_JSON_RESPONSE)
        doc_id = document_with_completed_ocr

        before = get_memory_notes(db_session, _global_scope())
        process_contract_extraction(db_session, _global_scope(), doc_id)
        after = get_memory_notes(db_session, _global_scope())
        assert before == after


class TestSuccessfulResultPersisted:
    def test_successful_extraction_is_readable_afterwards(
        self, db_session, document_with_completed_ocr, monkeypatch
    ):
        _use_fake_provider(monkeypatch, _VALID_JSON_RESPONSE)
        doc_id = document_with_completed_ocr

        process_contract_extraction(db_session, _global_scope(), doc_id)
        fetched = get_contract_extraction(db_session, _global_scope(), doc_id)
        assert fetched.status == "completed"
        assert fetched.extracted_fields["employer"] == "Ministry of Education"


class TestStoredSeparatelyFromOCRText:
    def test_ocr_text_row_is_untouched_by_extraction(
        self, db_session, document_with_completed_ocr, monkeypatch
    ):
        _use_fake_provider(monkeypatch, _VALID_JSON_RESPONSE)
        doc_id = document_with_completed_ocr

        process_contract_extraction(db_session, _global_scope(), doc_id)

        db_session.expire_all()
        ocr_row = (
            db_session.query(DocumentOCRResult)
            .filter(DocumentOCRResult.document_id == doc_id)
            .first()
        )
        assert ocr_row.extracted_text == _SAMPLE_CONTRACT_TEXT
        assert ocr_row.status == "completed"


class TestJSONRobustness:
    def test_prose_around_json_still_parses(self, db_session, document_with_completed_ocr, monkeypatch):
        wrapped = f"Sure, here is the extraction:\n\n{_VALID_JSON_RESPONSE}\n\nLet me know if you need anything else!"
        _use_fake_provider(monkeypatch, wrapped)
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.validation_status == "valid"
        assert row.extracted_fields["project_code"] == "PRJ-0023"

    def test_balanced_extraction_ignores_trailing_unbalanced_brace(
        self, db_session, document_with_completed_ocr, monkeypatch
    ):
        # A second, unrelated/unbalanced "{" after the real object must not
        # confuse extraction (this is exactly what a naive first-{-to-last-}
        # span would get wrong).
        wrapped = f"{_VALID_JSON_RESPONSE}\n\nNote: pricing may change { {'unrelated': True} }"
        _use_fake_provider(monkeypatch, wrapped)
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.extracted_fields["project_code"] == "PRJ-0023"


class TestRetryOnInvalidJSON:
    def test_invalid_json_then_successful_retry(self, db_session, document_with_completed_ocr, monkeypatch):
        provider = _use_sequenced_provider(monkeypatch, ["this is not json at all", _VALID_JSON_RESPONSE])
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.validation_status == "valid"
        assert provider.call_count == 2
        assert "Return exactly one valid JSON object. No markdown, no explanation, no trailing text." in provider.system_prompts[1]

    def test_only_one_retry_is_attempted(self, db_session, document_with_completed_ocr, monkeypatch):
        provider = _use_sequenced_provider(monkeypatch, ["not json", "still not json", _VALID_JSON_RESPONSE])
        doc_id = document_with_completed_ocr

        process_contract_extraction(db_session, _global_scope(), doc_id)
        # Exactly 2 calls (original + one retry) — the third canned
        # response (valid JSON) must never be reached.
        assert provider.call_count == 2


class TestDeterministicFallback:
    def test_fallback_succeeds_when_hermes_fails_twice(
        self, db_session, document_with_labeled_ocr, monkeypatch
    ):
        provider = _use_sequenced_provider(monkeypatch, ["not json", "still not json"])
        doc_id = document_with_labeled_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.status == "completed"
        assert row.validation_status == "fallback_valid"
        assert provider.call_count == 2  # hermes still attempted (+ one retry)
        # provider metadata still shows Hermes was attempted, not "fallback"
        assert row.provider == "hermes"

    def test_fallback_extracts_contract_value_dates_retention_and_liquidated_damages(
        self, db_session, document_with_labeled_ocr, monkeypatch
    ):
        _use_sequenced_provider(monkeypatch, ["not json", "still not json"])
        doc_id = document_with_labeled_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        fields = row.extracted_fields
        assert fields["contract_value"] == "8,750,000"
        assert fields["currency"] == "SAR"
        assert fields["start_date"] == "2025-03-01"
        assert fields["completion_date"] == "2026-09-30"
        assert fields["retention"] == "5% of each payment certificate"
        assert fields["liquidated_damages"] == "0.05% of contract value per day, capped at 8%"

    def test_fallback_does_not_invent_absent_fields(self, db_session, document_with_completed_ocr, monkeypatch):
        # document_with_completed_ocr's text has NO "Label: value" lines for
        # key_obligations/risks, and describes retention/liquidated damages
        # as prose (not "Retention: ..."), so the fallback must leave those
        # null rather than guessing from the prose.
        _use_sequenced_provider(monkeypatch, ["not json", "still not json"])
        doc_id = document_with_completed_ocr

        row = process_contract_extraction(db_session, _global_scope(), doc_id)
        assert row.validation_status == "fallback_valid"
        assert row.extracted_fields["key_obligations"] is None
        assert row.extracted_fields["risks"] is None
        assert row.extracted_fields["retention"] is None
        assert row.extracted_fields["liquidated_damages"] is None
        # But the clearly labeled lines in that same fixture ARE found:
        assert row.extracted_fields["contract_value"] == "12,500,000"
        assert row.extracted_fields["start_date"] == "2025-01-15"

class TestBothHermesAndFallbackFail:
    def test_status_is_failed_when_nothing_extractable(self, db_session, monkeypatch):
        doc = Document(
            project_id=_REAL_PROJECT_ID, doc_type="test_contract_unlabeled",
            title="Unlabeled Document", doc_date="2026-07-13",
            content_summary="Created by automated tests; safe to delete.",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        doc_id = doc.id

        unlabeled_text = "This document mentions a contract but has no colon-labeled fields anywhere in it at all."
        ocr_row = DocumentOCRResult(
            document_id=doc_id, project_id=_REAL_PROJECT_ID, status="completed",
            source_filename="unlabeled.pdf", mime_type="application/pdf",
            file_size_bytes=len(unlabeled_text), storage_path="/nonexistent/unlabeled.pdf",
            extracted_text=unlabeled_text, page_count=1, extraction_method="pdf_text_layer",
        )
        db_session.add(ocr_row)
        db_session.commit()

        try:
            _use_sequenced_provider(monkeypatch, ["not json", "still not json"])
            row = process_contract_extraction(db_session, _global_scope(), doc_id)
            assert row.status == "failed"
            assert row.validation_status == "invalid"
            assert row.error_message
        finally:
            db_session.query(ContractExtraction).filter(ContractExtraction.document_id == doc_id).delete()
            db_session.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == doc_id).delete()
            db_session.query(Document).filter(Document.id == doc_id).delete()
            db_session.commit()


class TestFallbackDoesNotAffectOCRMemoryOrCopilot:
    def test_ocr_row_unchanged_after_fallback(self, db_session, document_with_labeled_ocr, monkeypatch):
        _use_sequenced_provider(monkeypatch, ["not json", "still not json"])
        doc_id = document_with_labeled_ocr

        process_contract_extraction(db_session, _global_scope(), doc_id)

        db_session.expire_all()
        ocr_row = db_session.query(DocumentOCRResult).filter(DocumentOCRResult.document_id == doc_id).first()
        assert ocr_row.extracted_text == _LABELED_CONTRACT_TEXT
        assert ocr_row.status == "completed"

    def test_no_memory_write_when_fallback_used(self, db_session, document_with_labeled_ocr, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("contract extraction must never write Copilot memory")

        monkeypatch.setattr("app.ai.memory.append_memory_note", _fail_if_called)
        monkeypatch.setattr("app.ai.memory.set_memory_notes", _fail_if_called)
        _use_sequenced_provider(monkeypatch, ["not json", "still not json"])
        doc_id = document_with_labeled_ocr

        before = get_memory_notes(db_session, _global_scope())
        process_contract_extraction(db_session, _global_scope(), doc_id)
        after = get_memory_notes(db_session, _global_scope())
        assert before == after

    def test_no_pipeline_import_in_contract_extraction_module(self):
        # Contract extraction must stay unwired from the Copilot pipeline —
        # a static guarantee, not just a runtime one.
        import inspect
        import app.ai.contract_extraction as mod
        source = inspect.getsource(mod)
        assert "app.ai.pipeline" not in source
        assert "import pipeline" not in source
