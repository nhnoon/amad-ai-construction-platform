"""AMAD AI-003 — Knowledge Access Layer regression tests.

Proves, via automated tests against the real seeded PostgreSQL dataset
(not mocks), that Hermes is grounded on actual AMAD records rather than a
generic language model. Covers the eight required proof points:

  1. Meeting retrieval
  2. Procurement retrieval
  3. Project retrieval
  4. Multi-domain retrieval (meeting -> decisions -> procurement, scoped
     to the meeting's own project — the ticket's own example question)
  5. Unknown IDs produce evidence-insufficient responses, not crashes or
     invented facts
  6. Modifying seeded data changes retrieval (and therefore Hermes) output
  7. Organization isolation
  8. The Hermes prompt actually contains the retrieved evidence

Uses the same real-DB `db_session`/`client` fixtures as
tests/test_ai_retrieval.py and tests/test_ai_meeting_routing.py, and the
same FakeLLMProvider-based end-to-end pattern for tests that need to
inspect what actually reaches the LLM.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.intent import route_intent
from app.ai.planner import execute_multi_domain_plan
from app.ai.retrieval.meetings import get_meeting_detail
from app.ai.retrieval.procurement import get_procurement_summary
from app.ai.retrieval.projects import get_project_overview
from app.ai.retrieval.documents import get_recent_documents, get_document_detail
from app.ai.scope import AIAuthScope


def _global_scope(user_id: int = 999, org_id: int = 1) -> AIAuthScope:
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


# ── 1. Meeting retrieval ──────────────────────────────────────────────────

class TestMeetingRetrieval:
    def test_meeting_detail_is_real_seeded_data(self, db_session):
        result = get_meeting_detail(db_session, _global_scope(), meeting_id=1)
        assert result.has_data
        source_types = {e.source_type for e in result.evidence}
        assert "meeting" in source_types
        assert any("MTG-1" in e.label for e in result.evidence)

    def test_meeting_evidence_carries_project_id(self, db_session):
        result = get_meeting_detail(db_session, _global_scope(), meeting_id=1)
        meeting_ev = next(e for e in result.evidence if e.source_type == "meeting")
        assert meeting_ev.project_id is not None


# ── 2. Procurement retrieval ────────────────────────────────────────────────

class TestProcurementRetrieval:
    def test_procurement_summary_returns_real_records(self, db_session):
        result = get_procurement_summary(db_session, _global_scope(), limit=5)
        assert "purchase_requests" in result.data
        assert "purchase_orders" in result.data
        source_types = {e.source_type for e in result.evidence}
        assert source_types & {"purchase_request", "purchase_order"}


# ── 3. Project retrieval ────────────────────────────────────────────────────

class TestProjectRetrieval:
    def test_project_overview_returns_real_records(self, db_session):
        result = get_project_overview(db_session, _global_scope(), limit=5)
        assert result.has_data
        assert any(e.source_type == "project" for e in result.evidence)


# ── 4. Multi-domain retrieval (the ticket's own example) ───────────────────

class TestMultiDomainRetrieval:
    """"What decisions from MTG-1 could delay procurement?" must chain
    Meeting -> Decisions -> Procurement, scoped to MTG-1's own project —
    not the whole portfolio. Regression coverage for two real bugs fixed
    together: (a) intent.py's meeting short-circuit used to force
    is_multi_domain=False unconditionally; (b) planner.py's multi-domain
    plan only scoped project_overview to the meeting's project, leaving
    every other domain (procurement included) to silently query the
    entire portfolio."""

    def test_routes_as_multi_domain_with_procurement_secondary(self):
        routed = route_intent("What decisions from MTG-1 could delay procurement?")
        assert routed.intent == "meetings"
        assert routed.meeting_id == 1
        assert routed.is_multi_domain is True
        assert "procurement" in routed.secondary_intents

    def test_plain_meeting_question_stays_single_domain(self):
        """No false positive: a question naming only a meeting must not
        spuriously pick up unrelated secondary domains."""
        routed = route_intent("What happened in MTG-1?")
        assert routed.is_multi_domain is False
        assert routed.secondary_intents == []

    def test_multi_domain_plan_scopes_procurement_to_meeting_project(self, db_session):
        scope = _global_scope()
        meeting = get_meeting_detail(db_session, scope, meeting_id=1)
        meeting_project_id = meeting.data["project_id"]

        plan = execute_multi_domain_plan(
            domains=["meetings", "procurement"],
            db=db_session, scope=scope,
            project_id=None,  # question named a meeting, not a project
            meeting_id=1, ncr_id=None,
        )

        assert plan.is_multi_domain is True
        assert "meetings" in plan.domains_used
        assert "procurement" in plan.domains_used

        procurement_evidence = [
            e for e in plan.evidence
            if e.source_type in ("purchase_request", "purchase_order")
        ]
        # The real bug: before the fix, procurement evidence here came
        # from an unfiltered, portfolio-wide sample instead of MTG-1's
        # own project — this asserts every procurement item retrieved
        # alongside MTG-1 belongs to the SAME project as the meeting.
        assert procurement_evidence, "expected procurement evidence in the plan"
        for e in procurement_evidence:
            assert e.project_id == meeting_project_id, (
                f"procurement evidence {e.label} has project_id={e.project_id}, "
                f"expected {meeting_project_id} (MTG-1's project)"
            )


# ── 5. Unknown IDs -> evidence-insufficient, not fabricated ────────────────

class TestUnknownIdsProduceInsufficientEvidence:
    def test_unknown_meeting_id_raises_404_not_fabricated_data(self, db_session):
        """The retrieval layer itself must refuse to invent a meeting that
        doesn't exist — raises 404 rather than returning empty-but-successful
        data that could be misread as 'no meetings ever happened'."""
        with pytest.raises(HTTPException) as exc:
            get_meeting_detail(db_session, _global_scope(), meeting_id=99999999)
        assert exc.value.status_code == 404

    def test_unknown_document_id_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc:
            get_document_detail(db_session, _global_scope(), document_id=99999999)
        assert exc.value.status_code == 404

    def test_pipeline_converts_unknown_meeting_404_to_insufficient_evidence(
        self, client: TestClient, monkeypatch
    ):
        """End-to-end: the pipeline must not crash or 500 on a named entity
        that doesn't exist — it must reach Hermes with empty evidence, and
        the grounding-aware fake provider must say so explicitly instead of
        inventing an answer."""
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "mock")
        from app.ai.providers.factory import reset_provider
        reset_provider()

        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What happened in MTG-99999999?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence_count"] == 0
        assert data["status"] == "insufficient_evidence"
        # The grounding validator's fallback message, not a fabricated
        # meeting summary — proves the pipeline never invents facts for
        # an entity that does not exist in the dataset.
        assert "evidence" in data["answer"].lower() or "sufficient" in data["answer"].lower()


# ── 6. Modifying seeded data changes retrieval (and Hermes) output ─────────

class TestSeededDataChangesOutput:
    def test_new_document_appears_in_retrieval_after_insert(self, db_session):
        from app.models.documents import Document

        marker = "ZZZ_AI003_REGRESSION_MARKER_UNIQUE_TEXT_ZZZ"
        scope = _global_scope()

        before = get_recent_documents(db_session, scope, limit=200)
        assert not any(marker in e.snippet for e in before.evidence)

        doc = Document(
            project_id=None,
            organization_id=1,
            doc_type="test",
            title="AI-003 regression test document",
            doc_date="2026-07-13",
            content_summary=marker,
        )
        db_session.add(doc)
        db_session.commit()
        doc_id = doc.id
        try:
            after = get_recent_documents(db_session, scope, limit=200)
            assert any(marker in e.snippet for e in after.evidence), (
                "newly inserted document did not appear in retrieval evidence"
            )
        finally:
            db_session.query(Document).filter(Document.id == doc_id).delete()
            db_session.commit()

        gone = get_recent_documents(db_session, scope, limit=200)
        assert not any(marker in e.snippet for e in gone.evidence)


# ── 7. Organization isolation ───────────────────────────────────────────────

class TestOrganizationIsolation:
    def test_general_library_document_blocked_across_organizations(self, db_session):
        """General Library documents (project_id NULL) are organization-
        scoped, not project-scoped — a caller from a different organization
        must be denied even with an otherwise-valid document id."""
        from app.models.documents import Document

        gl_doc = (
            db_session.query(Document)
            .filter(Document.project_id.is_(None), Document.organization_id.isnot(None))
            .first()
        )
        if gl_doc is None:
            pytest.skip("no seeded General Library document to test against")

        same_org_scope = AIAuthScope(
            organization_id=gl_doc.organization_id, user_id=1, user_role="admin",
            accessible_project_ids=(),
        )
        other_org_scope = AIAuthScope(
            organization_id=gl_doc.organization_id + 999, user_id=2, user_role="admin",
            accessible_project_ids=(),
        )

        # Same org: allowed.
        result = get_document_detail(db_session, same_org_scope, document_id=gl_doc.id)
        assert result.has_data

        # Different org: denied, even though has_global_read is True for
        # both — the organization axis is independent of the project-read
        # axis (see AIAuthScope.enforce_organization_access).
        with pytest.raises(HTTPException) as exc:
            get_document_detail(db_session, other_org_scope, document_id=gl_doc.id)
        assert exc.value.status_code == 403

    def test_recent_documents_excludes_other_org_general_library(self, db_session):
        from app.models.documents import Document

        gl_doc = (
            db_session.query(Document)
            .filter(Document.project_id.is_(None), Document.organization_id.isnot(None))
            .first()
        )
        if gl_doc is None:
            pytest.skip("no seeded General Library document to test against")

        other_org_scope = AIAuthScope(
            organization_id=gl_doc.organization_id + 999, user_id=3, user_role="admin",
            accessible_project_ids=(),
        )
        result = get_recent_documents(db_session, other_org_scope, limit=200)
        assert not any(e.source_id == str(gl_doc.id) for e in result.evidence)


# ── 8. The Hermes prompt actually contains the retrieved evidence ──────────

class _CapturingProvider:
    """Wraps FakeLLMProvider to record the exact prompt Hermes would
    receive, so the test can assert on the raw prompt text rather than
    inferring it indirectly from the answer."""

    def __init__(self):
        from app.ai.providers.fake import FakeLLMProvider
        self._inner = FakeLLMProvider()
        self.last_system_prompt: str = ""
        self.last_user_prompt: str = ""

    @property
    def provider_name(self):
        return self._inner.provider_name

    @property
    def model_name(self):
        return self._inner.model_name

    def is_available(self):
        return True

    def generate(self, request):
        self.last_system_prompt = request.system_prompt
        self.last_user_prompt = request.user_prompt
        return self._inner.generate(request)


class TestHermesPromptContainsEvidence:
    def test_meeting_prompt_contains_real_evidence_not_just_question(
        self, monkeypatch
    ):
        from app.database import SessionLocal
        from app.models.auth import UserAccount
        from app.ai.scope import build_ai_scope
        from app.ai.pipeline import CopilotPipeline

        capturing = _CapturingProvider()
        monkeypatch.setattr("app.ai.pipeline.get_llm_provider", lambda: capturing)

        db = SessionLocal()
        try:
            user = db.query(UserAccount).filter(
                UserAccount.email == "admin@construction.ai"
            ).first()
            scope = build_ai_scope(user, db)
            pipeline = CopilotPipeline()
            result = pipeline.execute(
                question="What happened in MTG-1?", scope=scope, db=db,
            )
        finally:
            db.close()

        assert "EVIDENCE:" in capturing.last_system_prompt
        assert "[No evidence retrieved]" not in capturing.last_system_prompt
        assert "MTG-1" in capturing.last_system_prompt
        # Instructs the model to ground itself only in supplied evidence —
        # not to answer from general knowledge.
        assert "ONLY" in capturing.last_system_prompt.upper() or "only" in capturing.last_system_prompt
        assert result["evidence_count"] > 0
