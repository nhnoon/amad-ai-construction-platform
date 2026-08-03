"""Regression tests for the risk-summary analytical answer.

Covers:
- Arabic: "ما هي المخاطر الرئيسية لهذه المشاريع؟"
- English: "What are the main risks for these projects?"
- detect_query_type returns "risk_summary" for both languages
- _answer_risk_summary produces grounded output (not generic)
- multi-turn context resolution (anaphoric "هذه المشاريع")
- cross-domain evidence (safety, NCR, delay, risk-register, late PO)
- ranked sections by priority
- Arabic response language
- citations (PRJ-code, SE-id, NCR-id, risk-register #id)
- empty evidence → None (no hallucination)
- pipeline multi-domain retrieval for risks intent
"""
from __future__ import annotations

import pytest

from app.ai.analyst import (
    _answer_risk_summary,
    compute_analytical_answer,
    detect_query_type,
)
from app.ai.retrieval.base import Evidence


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_project(pid: int, code: str, status: str = "Active", budget: float = 5_000_000) -> Evidence:
    return Evidence(
        source_type="project",
        source_id=code,
        label=f"Project {code} — Test Project {pid}",
        snippet=f"Project {code}: status={status}, budget={budget:.0f} SAR, planned_finish=2026-12-31",
        project_id=pid,
        ui_metadata={},
    )


def _make_safety(eid: int, pid: int, severity: str = "High", desc: str = "Unsafe access") -> Evidence:
    return Evidence(
        source_type="safety_event",
        source_id=str(eid),
        label=f"Safety Event SE-{eid}",
        snippet=f"SE-{eid}: severity={severity}, date=2026-01-15, description={desc}",
        project_id=pid,
        ui_metadata={},
    )


def _make_ncr(nid: int, pid: int, ncr_type: str = "Structural", status: str = "Open") -> Evidence:
    return Evidence(
        source_type="ncr",
        source_id=str(nid),
        label=f"NCR NCR-{nid}",
        snippet=f"NCR-{nid}: type={ncr_type}, status={status}, date=2026-02-01, description=Quality issue",
        project_id=pid,
        ui_metadata={},
    )


def _make_project_risk(rid: int, pid: int, title: str = "Schedule overrun",
                        prob: str = "High", impact: str = "High") -> Evidence:
    return Evidence(
        source_type="project_risk",
        source_id=str(rid),
        label=f"Risk #{rid} — {title}",
        snippet=f"Risk: {title} (probability={prob}, impact={impact}, status=Open)",
        project_id=pid,
        ui_metadata={},
    )


def _make_late_po(po_id: str, pid: int) -> Evidence:
    return Evidence(
        source_type="purchase_order",
        source_id=po_id,
        label=f"Late PO {po_id}",
        snippet=f"Late PO {po_id}: status=Overdue, delivery=2026-01-01, late=True, delay=30d",
        project_id=pid,
        ui_metadata={},
    )


# ─────────────────────────────────────────────────────────────────────────────
# detect_query_type
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectQueryTypeRiskSummary:
    def test_arabic_canonical(self):
        q = "ما هي المخاطر الرئيسية لهذه المشاريع؟"
        assert detect_query_type(q) == "risk_summary"

    def test_arabic_variant_no_raiisiyya(self):
        assert detect_query_type("ما هي المخاطر في هذه المشاريع؟") == "risk_summary"

    def test_arabic_ما_المخاطر(self):
        assert detect_query_type("ما المخاطر الأساسية لهذه المشاريع؟") == "risk_summary"

    def test_arabic_ملخص_مخاطر(self):
        assert detect_query_type("أعطني ملخص المخاطر للمشاريع") == "risk_summary"

    def test_english_main_risks(self):
        assert detect_query_type("What are the main risks for these projects?") == "risk_summary"

    def test_english_key_risks(self):
        assert detect_query_type("What are the key risks?") == "risk_summary"

    def test_english_risk_summary(self):
        assert detect_query_type("Give me a risk summary for these projects.") == "risk_summary"

    def test_english_top_risks(self):
        assert detect_query_type("Show me the top risks for this project.") == "risk_summary"

    def test_english_what_are_risks(self):
        assert detect_query_type("What are the risks we should be aware of?") == "risk_summary"

    def test_risk_summary_not_overridden_by_count(self):
        # "What are the main risks" should not fall into "count"
        assert detect_query_type("What are the main risks?") == "risk_summary"

    def test_unrelated_does_not_match(self):
        assert detect_query_type("What is the highest budget project?") != "risk_summary"


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — empty / minimal evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummaryEmpty:
    def test_empty_evidence_returns_none(self):
        assert _answer_risk_summary([], is_ar=True) is None

    def test_no_risk_bearing_evidence_returns_none(self):
        # Only non-risk evidence (e.g. meetings) — should still try with projects
        assert _answer_risk_summary([], is_ar=False) is None


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — safety risks
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummarySafety:
    def test_english_safety_risks_present(self):
        ev = [
            _make_project(1, "PRJ-0001", "Active"),
            _make_safety(10, 1, "High", "Worker fall from scaffolding"),
            _make_safety(11, 1, "Medium", "Chemical spill"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "Safety Risks" in result
        assert "SE-10" in result
        assert "2 event" in result or "2 event(s)" in result

    def test_arabic_safety_risks_present(self):
        ev = [
            _make_project(1, "PRJ-0001", "Active"),
            _make_safety(10, 1, "High", "سقوط عامل"),
        ]
        result = _answer_risk_summary(ev, is_ar=True)
        assert result is not None
        assert "مخاطر السلامة" in result
        assert "SE-10" in result

    def test_high_severity_listed_first(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_safety(20, 1, "High", "Critical fall"),
            _make_safety(21, 1, "Low", "Minor slip"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "1 high-severity" in result
        idx_high = result.find("SE-20")
        idx_low = result.find("SE-21")
        # High-severity appears before low-severity in output
        assert idx_high < idx_low or idx_low == -1

    def test_affected_project_code_cited_for_safety(self):
        ev = [
            _make_project(5, "PRJ-0005", "Active"),
            _make_safety(30, 5, "High", "Equipment failure"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "PRJ-0005" in result


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — schedule risks
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummarySchedule:
    def test_delayed_projects_listed_english(self):
        ev = [
            _make_project(1, "PRJ-0001", "Delayed"),
            _make_project(2, "PRJ-0002", "Delayed"),
            _make_project(3, "PRJ-0003", "Active"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "Schedule Risks" in result
        assert "PRJ-0001" in result
        assert "PRJ-0002" in result
        assert "2 delayed" in result

    def test_delayed_projects_arabic(self):
        ev = [
            _make_project(1, "PRJ-0001", "Delayed"),
            _make_project(2, "PRJ-0002", "On Hold"),
        ]
        result = _answer_risk_summary(ev, is_ar=True)
        assert result is not None
        assert "الجدول الزمني" in result
        assert "PRJ-0001" in result

    def test_on_hold_projects_shown(self):
        ev = [_make_project(1, "PRJ-0001", "On Hold")]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "on-hold" in result.lower()
        assert "PRJ-0001" in result


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — quality risks (NCRs)
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummaryNCR:
    def test_open_ncrs_listed_english(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_ncr(5, 1, "Structural"),
            _make_ncr(6, 1, "Electrical"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "Quality Risks" in result
        assert "NCR-5" in result
        assert "2 open NCR" in result

    def test_open_ncrs_arabic(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_ncr(7, 1, "Plumbing"),
        ]
        result = _answer_risk_summary(ev, is_ar=True)
        assert result is not None
        assert "الجودة" in result
        assert "NCR-7" in result


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — formal risk register
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummaryRegister:
    def test_risk_register_shown_english(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_project_risk(100, 1, "Cost overrun", "High", "High"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "Risk Register" in result
        assert "#100" in result
        assert "Cost overrun" in result

    def test_risk_register_arabic(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_project_risk(101, 1, "تأخر في التوريد", "High", "Medium"),
        ]
        result = _answer_risk_summary(ev, is_ar=True)
        assert result is not None
        assert "سجل المخاطر" in result
        assert "#101" in result

    def test_high_impact_risks_prioritised(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_project_risk(200, 1, "Low risk item", "Low", "Low"),
            _make_project_risk(201, 1, "Critical risk item", "High", "High"),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        idx_critical = result.find("#201")
        idx_low = result.find("#200")
        # Critical (high) risk appears before low risk in the listing
        assert idx_critical < idx_low or idx_low == -1


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — procurement risks (late POs)
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummaryProcurement:
    def test_late_pos_shown(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_late_po("PO-9001", 1),
        ]
        result = _answer_risk_summary(ev, is_ar=False)
        assert result is not None
        assert "Procurement Risks" in result or "procurement" in result.lower()
        assert "PO-9001" in result

    def test_late_po_arabic(self):
        ev = [
            _make_project(1, "PRJ-0001"),
            _make_late_po("PO-9002", 1),
        ]
        result = _answer_risk_summary(ev, is_ar=True)
        assert result is not None
        assert "مشتريات" in result


# ─────────────────────────────────────────────────────────────────────────────
# _answer_risk_summary — cross-domain ranked output
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerRiskSummaryCrossDomain:
    @pytest.fixture
    def full_evidence(self):
        return [
            _make_project(1, "PRJ-0001", "Delayed", 15_000_000),
            _make_project(2, "PRJ-0002", "Active", 8_000_000),
            _make_project(3, "PRJ-0003", "On Hold", 3_000_000),
            _make_safety(10, 1, "High", "Worker fall"),
            _make_safety(11, 2, "Medium", "Near miss"),
            _make_ncr(5, 1, "Structural"),
            _make_ncr(6, 3, "Mechanical"),
            _make_project_risk(100, 1, "Budget overrun", "High", "High"),
            _make_project_risk(101, 2, "Vendor delay", "Medium", "High"),
            _make_late_po("PO-9001", 2),
        ]

    def test_english_output_has_all_categories(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=False)
        assert result is not None
        assert "Safety Risks" in result
        assert "Schedule Risks" in result
        assert "Quality Risks" in result
        assert "Risk Register" in result
        assert "Procurement Risks" in result

    def test_arabic_output_has_main_categories(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=True)
        assert result is not None
        assert "مخاطر السلامة" in result
        assert "الجدول الزمني" in result
        assert "الجودة" in result

    def test_safety_section_appears_before_schedule(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=False)
        assert result is not None
        idx_safety = result.find("Safety Risks")
        idx_schedule = result.find("Schedule Risks")
        assert idx_safety < idx_schedule

    def test_project_codes_appear_across_sections(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=False)
        assert result is not None
        assert "PRJ-0001" in result
        assert "PRJ-0002" in result or "PRJ-0003" in result

    def test_citations_in_sources_line_english(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=False)
        assert result is not None
        assert "Sources:" in result
        assert "[SE-10]" in result

    def test_citations_in_sources_line_arabic(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=True)
        assert result is not None
        assert "المصادر:" in result

    def test_title_arabic(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=True)
        assert result is not None
        assert "ملخص المخاطر" in result

    def test_title_english(self, full_evidence):
        result = _answer_risk_summary(full_evidence, is_ar=False)
        assert result is not None
        assert "Main Risk Summary" in result


# ─────────────────────────────────────────────────────────────────────────────
# compute_analytical_answer — end-to-end dispatch
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeAnalyticalAnswerRisk:
    @pytest.fixture
    def evidence(self):
        return [
            _make_project(1, "PRJ-0001", "Delayed"),
            _make_safety(10, 1, "High", "Critical fall"),
            _make_ncr(5, 1, "Structural"),
            _make_project_risk(100, 1, "Budget overrun", "High", "High"),
        ]

    def test_arabic_question_triggers_risk_summary(self, evidence):
        q = "ما هي المخاطر الرئيسية لهذه المشاريع؟"
        result = compute_analytical_answer(q, evidence)
        assert result is not None
        # Must be Arabic output
        arabic_chars = sum(1 for c in result if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 10, "Expected Arabic text in response"
        assert "ملخص المخاطر" in result

    def test_english_question_triggers_risk_summary(self, evidence):
        q = "What are the main risks for these projects?"
        result = compute_analytical_answer(q, evidence)
        assert result is not None
        assert "Main Risk Summary" in result
        assert "Safety Risks" in result

    def test_arabic_response_not_english(self, evidence):
        q = "ما هي المخاطر الرئيسية لهذه المشاريع؟"
        result = compute_analytical_answer(q, evidence)
        assert result is not None
        # Should NOT contain generic English boilerplate
        assert "Safety Risks" not in result
        assert "Schedule Risks" not in result
        # Should contain Arabic counterparts
        assert "مخاطر السلامة" in result

    def test_no_generic_fallback_for_risk_question(self, evidence):
        """Risk question must NOT fall through to the generic FakeLLM path."""
        q = "What are the main risks for these projects?"
        result = compute_analytical_answer(q, evidence)
        assert result is not None, (
            "compute_analytical_answer must return a grounded answer, not None"
        )

    def test_empty_evidence_returns_none(self):
        q = "What are the main risks for these projects?"
        result = compute_analytical_answer(q, [])
        assert result is None

    def test_arabic_variant_key_risks(self):
        ev = [_make_project(1, "PRJ-0001", "Delayed"), _make_safety(1, 1, "High")]
        result = compute_analytical_answer("ما المخاطر الأساسية لهذه المشاريع؟", ev)
        assert result is not None
        assert "ملخص المخاطر" in result

    def test_risk_summary_cites_evidence_ids(self, evidence):
        q = "What are the main risks for these projects?"
        result = compute_analytical_answer(q, evidence)
        assert result is not None
        assert "SE-10" in result or "NCR-5" in result or "#100" in result


# ─────────────────────────────────────────────────────────────────────────────
# Multi-turn context resolution (unit-level — context_resolver carries project_ids)
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiTurnContext:
    """Verify that context_resolver recognises هذه as an anaphoric marker."""

    def _state_with_projects(self, project_ids: list[int], intent: str = "project_overview"):
        """Return a real ConversationState pre-loaded with project ids."""
        from app.ai.conversation_state import ConversationState
        s = ConversationState()
        s.apply_turn(
            intent=intent,
            evidence_ids=[],
            project_ids=project_ids,
            supplier_ids=[],
            answer_summary="",
        )
        return s

    def test_هذه_triggers_is_anaphoric(self):
        """The word هذه must trigger is_anaphoric."""
        from app.ai.context_resolver import is_anaphoric
        assert is_anaphoric("ما هي المخاطر الرئيسية لهذه المشاريع؟")

    def test_resolve_context_injects_previous_project_ids(self):
        """Resolving a هذه-query with prior context injects project ids."""
        from app.ai.context_resolver import resolve_context, RecentMessage
        state = self._state_with_projects([1, 2, 3])
        q = "ما هي المخاطر الرئيسية لهذه المشاريع؟"
        ctx = resolve_context(q, state, [])
        assert ctx.is_follow_up is True
        assert ctx.hint_project_ids == [1, 2, 3]

    def test_resolve_context_second_set_of_projects(self):
        """Works with a different project id set."""
        from app.ai.context_resolver import resolve_context, RecentMessage
        state = self._state_with_projects([7, 8])
        q = "ما هي المخاطر الرئيسية لهذه المشاريع؟"
        ctx = resolve_context(q, state, [])
        assert ctx.hint_project_ids == [7, 8]

    def test_resolve_context_no_prior_context_requests_clarification(self):
        """Without prior context, an anaphoric risk query requests clarification."""
        from app.ai.context_resolver import resolve_context
        from app.ai.conversation_state import ConversationState
        state = ConversationState()  # empty — no prior projects
        q = "ما هي المخاطر الرئيسية لهذه المشاريع؟"
        ctx = resolve_context(q, state, [])
        assert ctx.clarification_needed is True


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline multi-domain retrieval for "risks" intent
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def _db():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def _admin_scope():
    from app.ai.scope import AIAuthScope
    return AIAuthScope(
        organization_id=None,
        user_id=1,
        user_role="admin",
        accessible_project_ids=(),
    )


class TestPipelineRisksMultiDomain:
    """Verify _dispatch_single_retrieval for 'risks' returns multi-domain evidence."""

    def test_risks_dispatch_returns_retrieval_result(self, _db, _admin_scope):
        from app.ai.pipeline import _dispatch_single_retrieval
        from app.ai.retrieval.base import RetrievalResult
        result = _dispatch_single_retrieval("risks", _db, _admin_scope, None)
        assert isinstance(result, RetrievalResult)

    def test_risks_dispatch_evidence_source_types_are_valid(self, _db, _admin_scope):
        from app.ai.pipeline import _dispatch_single_retrieval
        result = _dispatch_single_retrieval("risks", _db, _admin_scope, None)
        allowed = {"project", "project_risk", "safety_event", "ncr", "purchase_order"}
        for ev in result.evidence:
            assert ev.source_type in allowed, f"Unexpected source_type: {ev.source_type}"

    def test_risks_dispatch_data_is_multi_domain_flag(self, _db, _admin_scope):
        from app.ai.pipeline import _dispatch_single_retrieval
        result = _dispatch_single_retrieval("risks", _db, _admin_scope, None)
        assert result.data.get("multi_domain") is True
