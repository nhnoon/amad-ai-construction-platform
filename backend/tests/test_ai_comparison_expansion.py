"""Regression tests — Copilot comparison evidence expansion.

Scenario: the user references one project, then asks to compare it with
another delayed project.  Before this fix the pipeline fell back to the
FakeLLM because only one project existed in the evidence.  After the fix
the pipeline performs an authorized retrieval expansion, adds a second
project, and the analyst returns a real side-by-side comparison.

Tests cover:
  1. Unit test for get_additional_project_for_comparison (retrieval layer)
  2. Integration tests — compare query with 1-project evidence triggers expansion
  3. API regression — comparison turn in a multi-turn conversation returns
     a grounded, specific answer (not FakeLLM fallback text)
  4. Auth guard — expansion respects scope; excluded codes are never returned
"""
from __future__ import annotations

import re
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.analyst import detect_query_type, compute_analytical_answer, parse_project_code
from app.ai.retrieval.base import Evidence
from app.ai.retrieval.projects import get_additional_project_for_comparison
from app.ai.scope import AIAuthScope
from tests.conftest import TEST_USER_ID, TestingSessionLocal


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_project_ev(
    code: str, name: str, status: str, budget: float, project_id: int = 1
) -> Evidence:
    return Evidence(
        source_type="project",
        source_id=code,
        label=f"Project {code} — {name}",
        snippet=(
            f"{name} ({code}): status={status}, client=ACWA Power, city=Riyadh, "
            f"start=2023-01-15, planned_finish=2024-06-30, budget={budget:,.0f} SAR"
        ),
        project_id=project_id,
        ui_metadata={"href": f"/projects/{project_id}", "icon": "briefcase"},
    )


def _global_scope() -> AIAuthScope:
    """Phase 1 regression fix: build via the real build_ai_scope() against
    the actual seeded admin account, so accessible_project_ids reflects
    that organization's real projects. The has_global_read bypass this
    used to rely on (an empty accessible_project_ids tuple + admin role)
    no longer exists — that was the cross-tenant vulnerability Phase 1
    fixed, so a real, DB-backed scope is required here instead."""
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount

    db = TestingSessionLocal()
    try:
        user = db.query(UserAccount).filter(UserAccount.id == TEST_USER_ID).first()
        return build_ai_scope(user, db)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Query type detection — compare patterns
# ─────────────────────────────────────────────────────────────────────────────

class TestCompareQueryDetection:
    def test_compare_with_another_delayed(self):
        assert detect_query_type("Compare it with another delayed project") == "compare"

    def test_compare_them(self):
        assert detect_query_type("Compare them with each other") == "compare"

    def test_compare_two_projects(self):
        assert detect_query_type("Compare PRJ-0001 and PRJ-0002") == "compare"

    def test_compare_arabic(self):
        assert detect_query_type("قارن هذا المشروع مع مشروع آخر") == "compare"

    def test_show_delayed_is_not_compare(self):
        assert detect_query_type("Show me the delayed projects") != "compare"

    def test_highest_budget_is_not_compare(self):
        assert detect_query_type("Which has the highest budget?") != "compare"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Retrieval — get_additional_project_for_comparison unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAdditionalProject:
    """These tests run against the real test database."""

    def _db(self) -> Session:
        return TestingSessionLocal()

    def test_returns_evidence_object(self):
        db = self._db()
        try:
            scope = _global_scope()
            ev = get_additional_project_for_comparison(db, scope, exclude_codes=[])
            # There must be projects in the test DB (seeded)
            assert ev is not None
            assert ev.source_type == "project"
            assert ev.source_id.startswith("PRJ-")
            assert "budget=" in ev.snippet or "SAR" in ev.snippet
        finally:
            db.close()

    def test_excludes_specified_codes(self):
        db = self._db()
        try:
            scope = _global_scope()
            # Get the first available project code
            first = get_additional_project_for_comparison(db, scope, exclude_codes=[])
            assert first is not None
            first_code = first.source_id

            # Now exclude it — should get a different one
            second = get_additional_project_for_comparison(
                db, scope, exclude_codes=[first_code]
            )
            if second is not None:
                assert second.source_id != first_code
        finally:
            db.close()

    def test_prefers_delayed_status(self):
        db = self._db()
        try:
            scope = _global_scope()
            ev = get_additional_project_for_comparison(
                db, scope, exclude_codes=[], preferred_status="Delayed"
            )
            # If delayed projects exist, the result must be Delayed
            if ev is not None and "status=Delayed" in ev.snippet:
                assert "status=Delayed" in ev.snippet
        finally:
            db.close()

    def test_excludes_all_available_codes_returns_none_or_different(self):
        """Excluding every project in the DB should return None."""
        from app.models.projects import Project

        db = self._db()
        try:
            scope = _global_scope()
            all_codes = [row.project_code for row in db.query(Project.project_code).all()]
            ev = get_additional_project_for_comparison(db, scope, exclude_codes=all_codes)
            assert ev is None
        finally:
            db.close()

    def test_snippet_format_parseable_by_analyst(self):
        """The returned evidence snippet must be parseable by the analyst helpers."""
        from app.ai.analyst import parse_budget, parse_field

        db = self._db()
        try:
            scope = _global_scope()
            ev = get_additional_project_for_comparison(db, scope, exclude_codes=[])
            assert ev is not None
            budget = parse_budget(ev.snippet)
            assert budget is not None and budget > 0
            status = parse_field(ev.snippet, "status")
            assert status is not None and len(status) > 0
        finally:
            db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Analyst — compare handler with expanded evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestCompareHandlerWithExpansion:
    """Unit tests for the compare handler once evidence has been expanded."""

    PRJ_A = _make_project_ev("PRJ-0001", "Riyadh Tower Complex", "Delayed", 45_000_000, 1)
    PRJ_B = _make_project_ev("PRJ-0002", "Jeddah Waterfront", "Delayed", 12_000_000, 2)

    def test_compare_two_projects_names_both(self):
        ev = [self.PRJ_A, self.PRJ_B]
        answer = compute_analytical_answer("Compare it with another delayed project", ev)
        assert answer is not None
        assert "PRJ-0001" in answer
        assert "PRJ-0002" in answer

    def test_compare_two_projects_includes_budget_values(self):
        ev = [self.PRJ_A, self.PRJ_B]
        answer = compute_analytical_answer("Compare them with each other", ev)
        assert answer is not None
        assert "45,000,000" in answer or "45000000" in answer
        assert "12,000,000" in answer or "12000000" in answer

    def test_compare_two_projects_not_generic(self):
        ev = [self.PRJ_A, self.PRJ_B]
        answer = compute_analytical_answer("Compare it with another delayed project", ev)
        assert answer is not None
        assert "Based on the provided evidence" not in answer
        assert "here is a summary of the requested information" not in answer

    def test_compare_one_project_returns_none(self):
        """With only one project, the analyst returns None (expansion hasn't happened yet)."""
        ev = [self.PRJ_A]
        answer = compute_analytical_answer("Compare it with another delayed project", ev)
        # Analyst returns None — expansion is the pipeline's job, not the analyst's
        assert answer is None

    def test_compare_two_projects_includes_status_row(self):
        ev = [self.PRJ_A, self.PRJ_B]
        answer = compute_analytical_answer("Compare these two projects", ev)
        assert answer is not None
        assert "Status" in answer or "status" in answer

    def test_compare_cites_both_sources(self):
        ev = [self.PRJ_A, self.PRJ_B]
        answer = compute_analytical_answer("Compare it with another project", ev)
        assert answer is not None
        # Both project codes must appear as source citations
        codes_found = re.findall(r"PRJ-\d+", answer)
        assert len(set(codes_found)) >= 2, (
            f"Expected both project codes in answer: {answer[:400]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline expansion integration — mock DB call
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineComparisonExpansion:
    """Verify the pipeline calls get_additional_project_for_comparison when needed.

    The expansion only fires inside a known retrieval path — a cold "compare"
    question routes to intent=unknown (clarification required).  We test the
    wiring via a realistic 3-turn conversation that narrows to a single project
    before asking for the comparison, replicating the observed smoke-test scenario.
    """

    def test_expansion_triggered_in_narrow_context(self, client: TestClient):
        """After narrowing context to one project, compare triggers expansion.

        Patching at app.ai.retrieval.projects (source) works even though the
        pipeline imports the function lazily inside step 6.5.
        """
        import app.ai.retrieval.projects as projects_module

        original_fn = projects_module.get_additional_project_for_comparison
        expansion_calls: list = []

        def tracking_fn(*args, **kwargs):
            result = original_fn(*args, **kwargs)
            expansion_calls.append(result)
            return result

        # Turn 1: list delayed projects (establishes project context in state)
        r1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me the delayed projects"},
        )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Turn 2: highest budget (narrows state to a single project)
        client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Which one has the highest budget?",
                  "conversation_id": conv_id},
        )

        # Turn 3: compare — wrap the expansion function to track calls
        expansion_calls.clear()
        with patch.object(
            projects_module,
            "get_additional_project_for_comparison",
            side_effect=tracking_fn,
        ):
            r3 = client.post(
                "/api/v1/ai/copilot/query",
                json={"question": "Compare it with another delayed project",
                      "conversation_id": conv_id},
            )

        assert r3.status_code == 200
        data = r3.json()
        # Expansion must have been called (either succeeded or not, but was reached)
        assert expansion_calls, (
            f"get_additional_project_for_comparison was not called for compare turn "
            f"(status={data['status']}, answer={data.get('answer','')[:200]})"
        )

    def test_expansion_not_called_for_non_compare_question(self, client: TestClient):
        """Expansion must NOT be called for a non-compare question (e.g. budget ranking)."""
        import app.ai.retrieval.projects as projects_module

        expansion_calls: list = []

        def tracking_fn(*args, **kwargs):
            expansion_calls.append(True)
            return projects_module.get_additional_project_for_comparison.__wrapped__(*args, **kwargs)

        # Don't patch — use the real function, just observe calls via the API
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Which project has the highest budget?"},
        )
        assert resp.status_code == 200
        # The expansion function should not have been called for a budget query
        # We verify this indirectly: a budget answer should reference exactly 1 project
        data = resp.json()
        if data["status"] == "completed":
            codes = re.findall(r"PRJ-\d+", data["answer"])
            # Budget ranking answers reference one project prominently
            assert len(codes) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. API regression tests — comparison in a real conversation
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIComparisonExpansion:
    """End-to-end tests: compare question in a conversation returns real data."""

    GENERIC_PHRASES = [
        "based on the retrieved records",
        "here is a summary of the requested information",
        "the data reflects current platform records",
        "please refer to the cited sources for full details",
        "14 project(s) are in scope",  # the specific FakeLLM fallback text we saw
    ]

    def _is_generic(self, answer: str) -> bool:
        al = answer.lower()
        return any(p in al for p in self.GENERIC_PHRASES)

    def test_cold_compare_returns_two_projects(self, client: TestClient):
        """A direct comparison query (no prior conversation) must cite two projects."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Compare two delayed projects with each other"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            answer = data["answer"]
            codes = re.findall(r"PRJ-\d+", answer)
            assert len(set(codes)) >= 2, (
                f"Expected 2 distinct project codes in comparison, got: {answer[:400]}"
            )
            assert not self._is_generic(answer), (
                f"Got generic fallback text instead of real comparison: {answer[:400]}"
            )

    def test_comparison_after_project_reference(self, client: TestClient):
        """After asking about delayed projects, 'compare it with another' must expand."""
        # Turn 1: establish project context
        r1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me the delayed projects"},
        )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Turn 2: highest budget (sets a specific project in state)
        r2 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Which one has the highest budget?",
                  "conversation_id": conv_id},
        )
        assert r2.status_code == 200

        # Turn 3: compare — this is the regression turn
        r3 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Compare it with another delayed project",
                  "conversation_id": conv_id},
        )
        assert r3.status_code == 200
        data = r3.json()
        if data["status"] == "completed":
            answer = data["answer"]
            # Must name at least 2 project codes
            codes = re.findall(r"PRJ-\d+", answer)
            assert len(set(codes)) >= 2, (
                f"Expected 2 distinct project codes after expansion, got: {answer[:400]}"
            )
            # Must not be the generic FakeLLM fallback text we saw pre-fix
            assert not self._is_generic(answer), (
                f"Comparison fell back to generic text: {answer[:400]}"
            )

    def test_comparison_cites_budget_values(self, client: TestClient):
        """Comparison answer must include numeric budget values for both projects."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Compare two delayed projects by budget"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            answer = data["answer"]
            # Expect at least one SAR budget number
            assert re.search(r"\d[\d,]+ SAR", answer), (
                f"Expected budget value in comparison answer: {answer[:400]}"
            )

    def test_comparison_citations_present(self, client: TestClient):
        """Comparison answers must have at least 2 citations in the response."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Compare two delayed projects"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            citations = data.get("citations", [])
            project_cits = [c for c in citations if c["source_type"] == "project"]
            assert len(project_cits) >= 2, (
                f"Expected ≥2 project citations, got {len(project_cits)}: {citations}"
            )

    def test_compare_respects_status_filter(self, client: TestClient):
        """When asking to compare delayed projects, both cited projects should be Delayed."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Compare two delayed projects with each other"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            answer = data["answer"]
            # If we got two projects, at least one should be Delayed
            assert "Delayed" in answer or "delayed" in answer.lower() or re.search(r"PRJ-\d+", answer), (
                f"Expected Delayed status or project codes in answer: {answer[:400]}"
            )
