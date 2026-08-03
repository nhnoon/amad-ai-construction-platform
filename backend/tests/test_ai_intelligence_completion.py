"""AMAD AI-003 — Hermes Intelligence Completion (Site Reports + Memory).

Part 1 (Site Report Intelligence): regression coverage for the root-cause
fixes to the "endless loading / finishes without a result" bug —
  - a missing/null required sub-field in one recommended_actions/
    priority_matrix item no longer discards an otherwise-successful,
    well-cited Hermes response (app/ai/site_report_reasoning.py)
  - an unexpected exception (not just Hermes/JSON failures, which were
    already handled) can no longer reach the client as a bare 500
    (app/ai/site_report_intelligence.py, app/api/v1/site_reports.py)

Part 2 (Memory): regression coverage proving the structured memory store
(app/ai/memory_records.py) is genuinely stored, retrieved, ranked,
injected into the Hermes prompt alongside live dataset evidence, respects
organization isolation, and is written automatically (not just by manual
test setup) from real API call sites.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.ai.site_report_reasoning as reasoning_module
from app.ai.providers.fake import FakeLLMProvider
from app.ai.scope import AIAuthScope
from app.ai.site_report_evidence import gather_report_evidence
from app.ai.site_report_intelligence import analyze_site_report
from app.ai.site_report_reasoning import generate_report_reasoning
from app.ai.site_report_risk_scoring import compute_report_risk_score
from app.ai.memory_records import record_memory, search_memory_records, build_memory_record_block
from app.database import SessionLocal
from app.models.copilot_memory import AIMemoryRecord

_PROJECT_ID = 1
_REPORT_WITH_EVIDENCE = 982

_REAL_MEETING_ID = 1
_REAL_MEETING_PROJECT_ID = 23


def _global_scope(user_id: int = 1, org_id: int = 1) -> AIAuthScope:
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


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _cleanup_memory_records(db_session):
    db_session.query(AIMemoryRecord).filter(AIMemoryRecord.title.like("ZZZ_TEST%")).delete(synchronize_session=False)
    db_session.commit()
    yield
    db_session.query(AIMemoryRecord).filter(AIMemoryRecord.title.like("ZZZ_TEST%")).delete(synchronize_session=False)
    db_session.commit()


def _valid_reasoning_json(report_id: int, evidence_code: str) -> str:
    """Compact schema (AMAD AI Stabilization Part A §3) — see
    app/ai/site_report_reasoning.py's module docstring."""
    return json.dumps({
        "insufficient_evidence": False,
        "insufficient_evidence_reason": None,
        "executive_summary": f"Report {report_id} summary.",
        "key_findings": [
            {"category": "quality", "priority": "High", "statement": "Finding one.", "evidence_codes": [evidence_code]},
        ],
        "critical_risks": [],
        "recommended_actions": [
            {"category": "quality", "priority": "High", "statement": "Close NCR.", "evidence_codes": [evidence_code]},
        ],
        "missing_information": [],
        "trend_summary": "",
    })


# ── Part 1: Site Report Intelligence ────────────────────────────────────────

class TestSiteReportSuccess:
    def test_analysis_returns_successfully_with_valid_response(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            code = ev.evidence_items[0].code
            monkeypatch.setattr(
                reasoning_module, "get_llm_provider",
                lambda: FakeLLMProvider(fixed_response=_valid_reasoning_json(ev.report.id, code)),
            )
            result = generate_report_reasoning(ev, risk)
            assert result.status == "completed"
            assert result.output.executive_summary
        finally:
            db.close()


# TestMalformedHermesOutputRecovered originally lived here, testing the
# same "one malformed sub-item must not discard the whole response"
# guarantee against the (now superseded) wide 14-field schema. That
# guarantee still holds and is tested more thoroughly, against the
# current compact schema, in
# tests/test_site_report_intelligence.py::TestMalformedHermesOutputRecovered
# — not duplicated here.


class TestSiteReportNeverHangsOrCrashesUncleanly:
    def test_unexpected_evidence_gathering_error_returns_structured_result_not_a_crash(self, monkeypatch):
        """API-contract fix: analyze_site_report() must never let an
        unexpected exception escape uncaught — it always returns a valid
        SiteReportAnalysisOut, even when evidence gathering itself breaks
        for a reason other than 'report not found'."""
        import app.ai.site_report_intelligence as sri

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated unexpected failure")

        monkeypatch.setattr(sri, "gather_report_evidence", _boom)
        db = SessionLocal()
        try:
            out = analyze_site_report(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            assert out.reasoning_status == "unavailable"
            assert out.reasoning_error is not None
            assert out.executive_summary  # never blank/None — always explains itself
        finally:
            db.close()

    def test_analyze_endpoint_returns_200_not_500_on_unexpected_error(self, client: TestClient, monkeypatch):
        import app.ai.site_report_intelligence as sri

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated unexpected failure")

        monkeypatch.setattr(sri, "gather_report_evidence", _boom)
        resp = client.post(f"/api/v1/projects/{_PROJECT_ID}/site-reports/{_REPORT_WITH_EVIDENCE}/analyze")
        assert resp.status_code == 200, "an unexpected backend error must never surface as a bare 500 here"
        data = resp.json()
        assert data["reasoning_status"] == "unavailable"


# ── Part 2: Memory ──────────────────────────────────────────────────────────

class TestMemoryIsStored:
    def test_record_memory_writes_a_real_row(self, db_session):
        rec = record_memory(
            db_session, _global_scope(),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST memory storage", summary="Test summary content.",
            keywords=["test", "storage"], citation="MTG-999", project_id=23,
        )
        assert rec.id is not None
        fetched = db_session.query(AIMemoryRecord).filter(AIMemoryRecord.id == rec.id).first()
        assert fetched is not None
        assert fetched.summary == "Test summary content."


class TestMemoryIsRetrieved:
    def test_search_returns_matching_record(self, db_session):
        record_memory(
            db_session, _global_scope(),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST unique retrieval marker", summary="Retrieval test content.",
            keywords=["uniqueretrievalxyz"], citation="MTG-998", project_id=23,
        )
        results = search_memory_records(db_session, _global_scope(), "uniqueretrievalxyz", project_id=23)
        assert len(results) == 1
        assert results[0].title == "ZZZ_TEST unique retrieval marker"

    def test_search_excludes_unrelated_records(self, db_session):
        record_memory(
            db_session, _global_scope(),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST unrelated", summary="Completely unrelated content about weather.",
            keywords=["weather"], citation="MTG-997", project_id=23,
        )
        results = search_memory_records(db_session, _global_scope(), "procurement delays scaffolding", project_id=23)
        assert all(r.title != "ZZZ_TEST unrelated" for r in results)


class TestMemoryAffectsLaterAnswers:
    def test_prompt_contains_matched_memory_record(self, db_session):
        rec = record_memory(
            db_session, _global_scope(),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST MTG-1 prompt injection check",
            summary="ZZZ_TEST_MARKER: procurement team must expedite long-lead items.",
            keywords=["procurement", "MTG-1", "expedite"], citation="MTG-1", project_id=23,
        )
        results = search_memory_records(db_session, _global_scope(), "What did we decide about procurement in MTG-1?", project_id=23)
        block = build_memory_record_block(results)
        assert "ZZZ_TEST_MARKER" in block
        assert "HISTORICAL MEMORY" in block

    def test_changing_memory_changes_the_search_result(self, db_session):
        rec = record_memory(
            db_session, _global_scope(),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST changeable memory", summary="ZZZ_TEST_ORIGINAL content about cranes.",
            keywords=["cranexyz"], citation="MTG-996", project_id=23,
        )
        before = search_memory_records(db_session, _global_scope(), "cranexyz", project_id=23)
        assert any("ZZZ_TEST_ORIGINAL" in r.summary for r in before)

        db_session.query(AIMemoryRecord).filter(AIMemoryRecord.id == rec.id).delete()
        db_session.commit()
        record_memory(
            db_session, _global_scope(),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST changeable memory", summary="ZZZ_TEST_UPDATED content about cranexyz.",
            keywords=["cranexyz"], citation="MTG-996", project_id=23,
        )
        after = search_memory_records(db_session, _global_scope(), "cranexyz", project_id=23)
        assert any("ZZZ_TEST_UPDATED" in r.summary for r in after)
        assert not any("ZZZ_TEST_ORIGINAL" in r.summary for r in after)


class TestMemoryOrganizationIsolation:
    def test_other_organization_cannot_see_the_record(self, db_session):
        record_memory(
            db_session, _global_scope(org_id=1),
            source="meeting", category="meeting_summary",
            title="ZZZ_TEST org isolation marker", summary="ZZZ_TEST_ORG1_ONLY content.",
            keywords=["orgisolationxyz"], citation="MTG-995", project_id=23,
        )
        other_org_scope = AIAuthScope(
            organization_id=999, user_id=2, user_role="admin", accessible_project_ids=(),
        )
        results = search_memory_records(db_session, other_org_scope, "orgisolationxyz")
        assert not any("ZZZ_TEST_ORG1_ONLY" in r.summary for r in results)

        same_org_results = search_memory_records(db_session, _global_scope(org_id=1), "orgisolationxyz", project_id=23)
        assert any("ZZZ_TEST_ORG1_ONLY" in r.summary for r in same_org_results)


class TestDatasetRetrievalStillWorks:
    def test_project_overview_retrieval_unaffected_by_memory_changes(self, db_session):
        from app.ai.retrieval.projects import get_project_overview
        result = get_project_overview(db_session, _global_scope(), limit=3)
        assert result.has_data


class TestPromptContainsBothEvidenceAndMemory:
    def test_pipeline_prompt_has_evidence_and_memory_sections(self, monkeypatch):
        from app.database import SessionLocal as SL
        from app.models.auth import UserAccount
        from app.ai.scope import build_ai_scope
        from app.ai.pipeline import CopilotPipeline
        import app.ai.pipeline as pipeline_mod

        db = SL()
        try:
            user = db.query(UserAccount).filter(UserAccount.email == "admin@construction.ai").first()
            scope = build_ai_scope(user, db)
            rec = record_memory(
                db, scope,
                source="meeting", category="meeting_summary",
                title="ZZZ_TEST both-sections marker",
                summary="ZZZ_TEST_BOTH_MARKER: prior procurement decision detail.",
                keywords=["procurement", "MTG-1"], citation="MTG-1", project_id=23,
            )

            class _Capturing:
                def __init__(self):
                    self.last_system_prompt = ""

                @property
                def provider_name(self):
                    return "fake"

                @property
                def model_name(self):
                    return "fake-model-v1"

                def is_available(self):
                    return True

                def generate(self, request):
                    self.last_system_prompt = request.system_prompt
                    from app.ai.providers.fake import FakeLLMProvider
                    return FakeLLMProvider().generate(request)

            capturing = _Capturing()
            monkeypatch.setattr(pipeline_mod, "get_llm_provider", lambda: capturing)

            pipeline = CopilotPipeline()
            pipeline.execute(
                question="What did we previously decide about procurement in MTG-1?",
                scope=scope, db=db,
            )

            assert "EVIDENCE:" in capturing.last_system_prompt
            assert "ZZZ_TEST_BOTH_MARKER" in capturing.last_system_prompt
            assert "HISTORICAL MEMORY" in capturing.last_system_prompt

            db.query(AIMemoryRecord).filter(AIMemoryRecord.id == rec.id).delete()
            db.commit()
        finally:
            db.close()


class TestAutomaticMemoryWriting:
    """Proves memory is written automatically from real API call sites,
    not only when a test manually calls the writer — the actual gap the
    audit found (a real, tested writer existed for meetings, but nothing
    in the running application ever called it)."""

    def test_creating_a_meeting_writes_memory_automatically(self, client: TestClient, db_session):
        db_session.query(AIMemoryRecord).filter(
            AIMemoryRecord.source == "meeting", AIMemoryRecord.project_id == _REAL_MEETING_PROJECT_ID,
        ).delete()
        db_session.commit()

        resp = client.post(
            f"/api/v1/projects/{_REAL_MEETING_PROJECT_ID}/meetings",
            json={"title": "ZZZ_TEST automatic memory meeting", "meeting_date": "2026-07-16", "meeting_type": "Technical"},
        )
        assert resp.status_code == 201
        meeting_id = resp.json()["id"]

        rec = (
            db_session.query(AIMemoryRecord)
            .filter(AIMemoryRecord.source == "meeting", AIMemoryRecord.citation == f"MTG-{meeting_id}")
            .first()
        )
        assert rec is not None, "creating a meeting via the real API must write memory automatically"
        assert "ZZZ_TEST automatic memory meeting" in rec.title

        db_session.query(AIMemoryRecord).filter(AIMemoryRecord.id == rec.id).delete()
        db_session.commit()
