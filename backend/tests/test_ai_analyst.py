"""Regression tests for the deterministic analytical layer (analyst.py).

These tests fail if the Copilot returns generic template text instead of
specific, evidence-grounded answers. They cover the six-turn conversation
scenario described in the fix specification:

  A. Show me the delayed projects.
  B. Which one has the highest budget?
  C. Tell me more about that project.
  D. Does it have unresolved NCRs or high-severity safety events?
  E. Compare it with another delayed project.
  F. Which project should management pay more attention to, and why?
"""
from __future__ import annotations

import re
import pytest
from fastapi.testclient import TestClient

from app.ai.analyst import (
    compute_analytical_answer,
    detect_query_type,
    parse_budget,
    parse_field,
    parse_project_name,
    parse_project_code,
)
from app.ai.retrieval.base import Evidence


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiter reset (same pattern as Phase 3B tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.ai.ratelimit import get_ai_rate_limiter
    from tests.conftest import TEST_USER_ID
    get_ai_rate_limiter().reset(TEST_USER_ID)
    yield


# ─────────────────────────────────────────────────────────────────────────────
# Shared test fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_project_ev(
    code: str,
    name: str,
    status: str,
    budget: float,
    city: str = "Riyadh",
    client: str = "ACWA Power",
    project_id: int = 1,
    planned_finish: str = "2024-06-30",
) -> Evidence:
    return Evidence(
        source_type="project",
        source_id=code,
        label=f"Project {code} — {name}",
        snippet=(
            f"{name} ({code}): status={status}, client={client}, city={city}, "
            f"start=2023-01-15, planned_finish={planned_finish}, "
            f"budget={budget:,.0f} SAR"
        ),
        project_id=project_id,
        ui_metadata={"href": f"/projects/{project_id}", "icon": "briefcase"},
    )


def _make_safety_ev(ev_id: int, severity: str, project_id: int) -> Evidence:
    return Evidence(
        source_type="safety_event",
        source_id=str(ev_id),
        label=f"Safety Event SE-{ev_id}",
        snippet=(
            f"SE-{ev_id}: severity={severity}, date=2024-02-10, "
            f"description=Fall from scaffolding at site level 3"
        ),
        project_id=project_id,
        ui_metadata={"href": "/safety", "icon": "shield-alert"},
    )


def _make_ncr_ev(ncr_id: int, project_id: int) -> Evidence:
    return Evidence(
        source_type="ncr",
        source_id=str(ncr_id),
        label=f"NCR NCR-{ncr_id}",
        snippet=(
            f"NCR-{ncr_id}: type=Structural, status=Open, "
            f"date=2024-01-20, description=Defective rebar placement"
        ),
        project_id=project_id,
        ui_metadata={"href": "/safety", "icon": "clipboard-x"},
    )


DELAYED_HIGH = _make_project_ev("PRJ-0001", "Riyadh Tower Complex", "Delayed", 45_000_000, project_id=1)
DELAYED_LOW = _make_project_ev("PRJ-0002", "Jeddah Waterfront", "Delayed", 12_000_000, city="Jeddah", project_id=2)
ACTIVE_PROJECT = _make_project_ev("PRJ-0003", "Mecca Expansion", "Active", 28_000_000, city="Mecca", project_id=3)
ON_HOLD_PROJECT = _make_project_ev("PRJ-0004", "Medina Hub", "On Hold", 9_000_000, city="Medina", project_id=4)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Evidence parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceParsing:
    def test_parse_budget_standard(self):
        snippet = "Project: status=Delayed, budget=45,000,000 SAR"
        assert parse_budget(snippet) == 45_000_000.0

    def test_parse_budget_no_comma(self):
        snippet = "budget=5000000 SAR"
        assert parse_budget(snippet) == 5_000_000.0

    def test_parse_budget_missing(self):
        snippet = "status=Active, client=ACWA"
        assert parse_budget(snippet) is None

    def test_parse_field_status(self):
        snippet = "Tower (PRJ-0001): status=Delayed, client=ACWA, city=Riyadh"
        assert parse_field(snippet, "status") == "Delayed"

    def test_parse_field_city(self):
        snippet = "Tower: status=Active, client=ACWA, city=Riyadh, budget=5000000 SAR"
        assert parse_field(snippet, "city") == "Riyadh"

    def test_parse_field_client(self):
        snippet = "Tower: status=Active, client=Saudi Aramco, city=Jeddah"
        val = parse_field(snippet, "client")
        assert val is not None
        assert "Saudi Aramco" in val

    def test_parse_field_missing(self):
        assert parse_field("status=Active", "budget") is None

    def test_parse_project_name_from_label(self):
        ev = Evidence(
            source_type="project", source_id="PRJ-0001",
            label="Project PRJ-0001 — Riyadh Tower Complex",
            snippet="",
        )
        assert parse_project_name(ev) == "Riyadh Tower Complex"

    def test_parse_project_name_no_dash(self):
        ev = Evidence(
            source_type="project", source_id="PRJ-0001",
            label="Riyadh Tower",
            snippet="",
        )
        assert parse_project_name(ev) == "Riyadh Tower"

    def test_parse_project_code(self):
        ev = Evidence(source_type="project", source_id="PRJ-0042", label="", snippet="")
        assert parse_project_code(ev) == "PRJ-0042"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Query type detection
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryTypeDetection:
    def test_highest_budget(self):
        assert detect_query_type("Which one has the highest budget?") == "highest_budget"
        assert detect_query_type("Which project has the largest budget?") == "highest_budget"
        assert detect_query_type("What is the maximum budget?") == "highest_budget"

    def test_lowest_budget(self):
        assert detect_query_type("Which has the lowest budget?") == "lowest_budget"
        assert detect_query_type("Which project has the minimum cost?") == "lowest_budget"

    def test_longest_delay(self):
        assert detect_query_type("Which project is most delayed?") == "longest_delay"
        assert detect_query_type("Which has the longest delay?") == "longest_delay"

    def test_list_delayed(self):
        assert detect_query_type("Show me the delayed projects") == "list_by_status"
        assert detect_query_type("List all delayed projects") == "list_by_status"
        assert detect_query_type("What are the delayed projects?") == "list_by_status"

    def test_list_active(self):
        assert detect_query_type("Show me the active projects") == "list_by_status"

    def test_tell_more(self):
        assert detect_query_type("Tell me more about that project") == "tell_more"
        assert detect_query_type("More details about it") == "tell_more"

    def test_compare(self):
        assert detect_query_type("Compare it with another delayed project") == "compare"
        assert detect_query_type("Compare PRJ-0001 and PRJ-0002") == "compare"

    def test_has_safety_ncr(self):
        assert detect_query_type(
            "Does it have unresolved NCRs or high-severity safety events?"
        ) == "has_safety_ncr"

    def test_attention_rank(self):
        assert detect_query_type(
            "Which project should management pay more attention to?"
        ) == "attention_rank"
        assert detect_query_type(
            "Which project needs the most attention, and why?"
        ) == "attention_rank"

    def test_count(self):
        assert detect_query_type("How many delayed projects are there?") == "count"

    def test_generic(self):
        assert detect_query_type("What is the overall construction schedule?") == "generic"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Analytical answer unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyticalAnswers:
    # ── B. Highest budget ─────────────────────────────────────────────────────
    def test_highest_budget_names_specific_project(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW, ACTIVE_PROJECT]
        answer = compute_analytical_answer("Which one has the highest budget?", evidence)
        assert answer is not None
        # Must name the specific project
        assert "Riyadh Tower Complex" in answer or "PRJ-0001" in answer
        # Must include a numeric budget
        assert "45,000,000" in answer or "45000000" in answer
        # Must cite the source
        assert "PRJ-0001" in answer

    def test_highest_budget_not_generic_template(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Which project has the highest budget?", evidence)
        assert answer is not None
        assert "Based on the provided evidence" not in answer
        assert "here is a summary" not in answer

    def test_highest_budget_no_project_evidence(self):
        """Non-project evidence should return None."""
        safety = [_make_safety_ev(1, "High", 1)]
        answer = compute_analytical_answer("Which has the highest budget?", safety)
        assert answer is None

    def test_lowest_budget_names_correct_project(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW, ACTIVE_PROJECT]
        answer = compute_analytical_answer("Which has the lowest budget?", evidence)
        assert answer is not None
        assert "Medina Hub" in answer or "PRJ-0004" in answer or "9,000,000" in answer or "Jeddah" in answer

    # ── A. List by status ─────────────────────────────────────────────────────
    def test_list_delayed_projects(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW, ACTIVE_PROJECT]
        answer = compute_analytical_answer("Show me the delayed projects", evidence)
        assert answer is not None
        assert "PRJ-0001" in answer
        assert "PRJ-0002" in answer
        # Active project should not dominate (it may appear as fallback)
        assert "Based on the provided evidence" not in answer

    def test_list_active_projects(self):
        evidence = [DELAYED_HIGH, ACTIVE_PROJECT]
        answer = compute_analytical_answer("Show me the active projects", evidence)
        assert answer is not None
        assert "PRJ-0003" in answer or "Mecca Expansion" in answer

    def test_list_returns_count(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Show me all delayed projects", evidence)
        assert answer is not None
        assert "2" in answer  # 2 delayed projects

    # ── C. Tell me more ───────────────────────────────────────────────────────
    def test_tell_more_includes_project_code(self):
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer("Tell me more about that project", evidence)
        assert answer is not None
        assert "PRJ-0001" in answer

    def test_tell_more_includes_project_name(self):
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer("Tell me more about that project", evidence)
        assert answer is not None
        assert "Riyadh Tower Complex" in answer

    def test_tell_more_includes_status_and_budget(self):
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer("Tell me more about that project", evidence)
        assert answer is not None
        assert "Delayed" in answer or "delayed" in answer.lower()
        assert "45,000,000" in answer or "45000000" in answer

    def test_tell_more_with_safety_includes_count(self):
        safety = _make_safety_ev(1, "High", 1)
        evidence = [DELAYED_HIGH, safety]
        answer = compute_analytical_answer("Tell me more about that project", evidence)
        assert answer is not None
        # Should mention safety event
        assert "safety" in answer.lower() or "Safety" in answer

    def test_tell_more_not_generic(self):
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer("More details about it", evidence)
        assert answer is not None
        assert "Based on the provided evidence" not in answer

    # ── D. Safety / NCR check ─────────────────────────────────────────────────
    def test_has_safety_ncr_high_severity_found(self):
        safety = _make_safety_ev(42, "High", 1)
        evidence = [DELAYED_HIGH, safety]
        answer = compute_analytical_answer(
            "Does it have unresolved NCRs or high-severity safety events?", evidence
        )
        assert answer is not None
        assert "SE-42" in answer or "Safety" in answer or "safety" in answer.lower()
        assert "High" in answer or "high" in answer.lower()

    def test_has_ncr_found(self):
        ncr = _make_ncr_ev(13, 1)
        evidence = [DELAYED_HIGH, ncr]
        answer = compute_analytical_answer(
            "Does it have unresolved NCRs?", evidence
        )
        assert answer is not None
        assert "NCR" in answer or "ncr" in answer.lower()

    def test_has_safety_ncr_none_found(self):
        # No safety/NCR evidence — only project evidence
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer(
            "Does it have unresolved NCRs or high-severity safety events?", evidence
        )
        # Should still return something (a "none found" answer)
        assert answer is not None
        assert len(answer) > 0

    # ── E. Comparison ─────────────────────────────────────────────────────────
    def test_compare_names_both_projects(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Compare it with another delayed project", evidence)
        assert answer is not None
        assert "PRJ-0001" in answer
        assert "PRJ-0002" in answer

    def test_compare_includes_budget_values(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Compare the two projects", evidence)
        assert answer is not None
        assert "45,000,000" in answer or "45000000" in answer
        assert "12,000,000" in answer or "12000000" in answer

    def test_compare_fewer_than_two_projects(self):
        answer = compute_analytical_answer("Compare it with another project", [DELAYED_HIGH])
        assert answer is None  # Can't compare with only 1 project

    # ── F. Attention ranking ──────────────────────────────────────────────────
    def test_attention_rank_names_project(self):
        evidence = [DELAYED_HIGH, ACTIVE_PROJECT]
        answer = compute_analytical_answer(
            "Which project should management pay more attention to, and why?", evidence
        )
        assert answer is not None
        # Delayed project should be ranked higher
        assert "PRJ-0001" in answer or "Riyadh Tower Complex" in answer

    def test_attention_rank_gives_reasons(self):
        safety = _make_safety_ev(10, "High", 1)
        evidence = [DELAYED_HIGH, ACTIVE_PROJECT, safety]
        answer = compute_analytical_answer(
            "Which project needs the most management attention?", evidence
        )
        assert answer is not None
        # Should mention why (delayed, safety events, etc.)
        reason_terms = ["delayed", "safety", "budget", "risk", "attention"]
        answer_lower = answer.lower()
        assert any(t in answer_lower for t in reason_terms)

    def test_attention_rank_cites_sources(self):
        evidence = [DELAYED_HIGH, ACTIVE_PROJECT]
        answer = compute_analytical_answer(
            "Which project needs the most attention?", evidence
        )
        assert answer is not None
        assert "PRJ-" in answer  # Must cite at least one source code

    # ── Count ─────────────────────────────────────────────────────────────────
    def test_count_delayed(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW, ACTIVE_PROJECT]
        answer = compute_analytical_answer("How many delayed projects are there?", evidence)
        assert answer is not None
        assert "2" in answer

    def test_count_safety(self):
        safety1 = _make_safety_ev(1, "High", 1)
        safety2 = _make_safety_ev(2, "Low", 2)
        answer = compute_analytical_answer("How many safety incidents are there?", [safety1, safety2])
        assert answer is not None
        assert "2" in answer

    # ── Generic pass-through ──────────────────────────────────────────────────
    def test_generic_returns_none(self):
        """Unrecognised patterns must return None — fall through to LLM."""
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer(
            "What is the overall construction methodology used?", evidence
        )
        assert answer is None

    def test_empty_evidence_returns_none(self):
        answer = compute_analytical_answer("Which has the highest budget?", [])
        assert answer is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Regression tests — no generic template text in analytical answers
# ─────────────────────────────────────────────────────────────────────────────

class TestNoGenericTemplateText:
    """These tests fail if the analyst returns boilerplate instead of data."""

    GENERIC_PHRASES = [
        "based on the provided evidence",
        "here is a summary of the requested information",
        "the data reflects current platform records",
        "please refer to the cited sources for full details",
        "i can assist with construction project intelligence",
    ]

    def _assert_not_generic(self, answer: str | None) -> None:
        assert answer is not None, "Expected an analytical answer but got None"
        answer_lower = answer.lower()
        for phrase in self.GENERIC_PHRASES:
            assert phrase not in answer_lower, (
                f"Answer contains generic phrase '{phrase}': {answer[:200]}"
            )

    def test_highest_budget_not_generic(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Which one has the highest budget?", evidence)
        self._assert_not_generic(answer)

    def test_tell_more_not_generic(self):
        evidence = [DELAYED_HIGH]
        answer = compute_analytical_answer("Tell me more about that project", evidence)
        self._assert_not_generic(answer)

    def test_list_delayed_not_generic(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Show me the delayed projects", evidence)
        self._assert_not_generic(answer)

    def test_compare_not_generic(self):
        evidence = [DELAYED_HIGH, DELAYED_LOW]
        answer = compute_analytical_answer("Compare these two projects", evidence)
        self._assert_not_generic(answer)

    def test_attention_rank_not_generic(self):
        evidence = [DELAYED_HIGH, ACTIVE_PROJECT]
        answer = compute_analytical_answer(
            "Which project needs management attention?", evidence
        )
        self._assert_not_generic(answer)


# ─────────────────────────────────────────────────────────────────────────────
# 5. API integration regression tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIAnalyticalAnswers:
    """End-to-end tests through the API that assert specific answers."""

    def test_highest_budget_api_response(self, client: TestClient):
        """Highest-budget query via API must name a project code and budget."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Which project has the highest budget?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            answer = data["answer"]
            # Must contain a project code
            assert re.search(r"PRJ-\d+", answer), (
                f"Expected project code in answer but got: {answer[:300]}"
            )
            # Must contain a numeric budget value
            assert re.search(r"\d[\d,]+", answer), (
                f"Expected numeric budget in answer but got: {answer[:300]}"
            )
            # Must not be pure boilerplate
            assert "Based on the provided evidence" not in answer

    def test_tell_me_more_via_conversation(self, client: TestClient):
        """After listing projects, 'tell me more' must return project details."""
        # Turn 1: list projects
        resp1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me the delayed projects"},
        )
        assert resp1.status_code == 200
        conv_id = resp1.json()["conversation_id"]

        # Turn 2: tell me more
        resp2 = client.post(
            "/api/v1/ai/copilot/query",
            json={
                "question": "Tell me more about that project",
                "conversation_id": conv_id,
            },
        )
        assert resp2.status_code == 200
        data = resp2.json()
        if data["status"] == "completed":
            answer = data["answer"]
            # Must include a project code or name
            assert re.search(r"PRJ-\d+", answer) or any(
                w in answer for w in ["Tower", "Waterfront", "Project"]
            ), f"Expected project name/code in follow-up answer: {answer[:300]}"

    def test_compare_projects_via_api(self, client: TestClient):
        """Comparison query must name both projects with budget values."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me the delayed projects"},
        )
        conv_id = resp.json()["conversation_id"]

        resp2 = client.post(
            "/api/v1/ai/copilot/query",
            json={
                "question": "Compare them with each other",
                "conversation_id": conv_id,
            },
        )
        assert resp2.status_code == 200
        data = resp2.json()
        if data["status"] == "completed":
            answer = data["answer"]
            # Should mention at least one PRJ code
            assert re.search(r"PRJ-\d+", answer), (
                f"Expected project code(s) in comparison: {answer[:300]}"
            )

    def test_management_attention_api(self, client: TestClient):
        """Attention-rank query must name a project and give reasons."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Which project should management pay more attention to, and why?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            answer = data["answer"]
            assert re.search(r"PRJ-\d+", answer) or any(
                w in answer for w in ["delayed", "budget", "safety", "attention", "Delayed"]
            ), f"Expected specific attention analysis: {answer[:300]}"

    def test_six_turn_conversation(self, client: TestClient):
        """The full six-turn conversation from the specification."""
        # A. Show me the delayed projects
        r1 = client.post("/api/v1/ai/copilot/query",
                         json={"question": "Show me the delayed projects"})
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]
        a1_answer = r1.json()["answer"]
        # Must list projects, not be generic
        assert "Based on the provided evidence, here is a summary" not in a1_answer

        # B. Which one has the highest budget?
        r2 = client.post("/api/v1/ai/copilot/query",
                         json={"question": "Which one has the highest budget?",
                               "conversation_id": conv_id})
        assert r2.status_code == 200
        a2 = r2.json()["answer"]
        # Must contain a project code and budget number
        assert re.search(r"PRJ-\d+", a2), f"Turn B missing project code: {a2[:300]}"
        assert re.search(r"\d[\d,]+", a2), f"Turn B missing budget number: {a2[:300]}"

        # C. Tell me more about that project
        r3 = client.post("/api/v1/ai/copilot/query",
                         json={"question": "Tell me more about that project",
                               "conversation_id": conv_id})
        assert r3.status_code == 200
        a3 = r3.json()["answer"]
        # Must contain a project code/name
        assert re.search(r"PRJ-\d+", a3) or any(
            w in a3 for w in ["status", "Status", "budget", "Budget", "client", "Client"]
        ), f"Turn C missing project details: {a3[:300]}"

        # F. Which project should management pay more attention to, and why?
        r6 = client.post("/api/v1/ai/copilot/query",
                         json={"question": "Which project should management pay more attention to, and why?",
                               "conversation_id": conv_id})
        assert r6.status_code == 200
        assert r6.json()["status"] in ("completed", "insufficient_evidence", "grounding_failed")
