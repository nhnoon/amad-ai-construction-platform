"""Tests for the rebuilt Site Report Intelligence pipeline (AMAD AI-002).

Covers three layers independently:
  1. Deterministic evidence retrieval (app/ai/site_report_evidence.py) —
     report-scoped date windowing, no LLM involved.
  2. Deterministic risk scoring (app/ai/site_report_risk_scoring.py) —
     transparent, reproducible, no LLM involved.
  3. The reasoning layer (app/ai/site_report_reasoning.py) — the one Hermes
     call, tested via FakeLLMProvider with both a valid structured response
     and various failure modes, so no test in this suite makes a real
     Hermes call (matches the established pattern in test_contract_extraction.py).

Uses real seeded project/site-report data (project_id=1) rather than
fixtures, matching the pattern already used in test_ai_meeting_routing.py.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.ai.site_report_reasoning as reasoning_module
from app.ai.providers.base import ProviderUnavailableError
from app.ai.providers.fake import FakeLLMProvider
from app.ai.site_report_evidence import gather_report_evidence
from app.ai.site_report_intelligence import analyze_site_report, build_site_report_intelligence
from app.ai.site_report_reasoning import generate_report_reasoning
from app.ai.site_report_risk_scoring import compute_report_risk_score
from app.database import SessionLocal

_PROJECT_ID = 1
# Confirmed present in seed data via live smoke test during implementation —
# a project-1 report with real safety/NCR/procurement evidence in its window.
_REPORT_WITH_EVIDENCE = 982
# An adjacent, earlier report for the same project with a mostly-empty window.
_REPORT_SPARSE = 702


def _valid_reasoning_json(report_id: int, evidence_code: str) -> str:
    """Compact schema (AMAD AI Stabilization Part A §3) — replaces the old
    14-section shape. See app/ai/site_report_reasoning.py's module
    docstring for why."""
    return json.dumps({
        "insufficient_evidence": False,
        "insufficient_evidence_reason": None,
        "executive_summary": f"Report {report_id} shows active work with one notable finding.",
        "key_findings": [
            {
                "category": "quality", "priority": "High",
                "statement": "Reinforcement exposure noted on site.",
                "evidence_codes": [evidence_code],
            },
        ],
        "critical_risks": [],
        "recommended_actions": [
            {
                "category": "quality", "priority": "High",
                "statement": "Close the open NCR before further pours.",
                "evidence_codes": [evidence_code],
            },
        ],
        "missing_information": ["When is the reinforcement inspection scheduled?"],
        "trend_summary": "",
    })


class TestEvidenceGathering:
    def test_two_reports_same_project_get_different_evidence_windows(self):
        """The core bug being fixed: different reports for the same
        project must not see identical evidence."""
        db = SessionLocal()
        try:
            ev_a = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            ev_b = gather_report_evidence(db, _PROJECT_ID, _REPORT_SPARSE)
            codes_a = {i.code for i in ev_a.evidence_items}
            codes_b = {i.code for i in ev_b.evidence_items}
            assert codes_a != codes_b, "different reports produced identical evidence sets"
        finally:
            db.close()

    def test_evidence_items_are_scoped_within_the_window(self):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            for s in ev.safety_events:
                from app.ai.site_report_evidence import parse_report_date
                d = parse_report_date(s.event_date)
                assert d is not None
                if ev.window_start is not None:
                    assert ev.window_start < d <= ev.window_end
        finally:
            db.close()

    def test_missing_report_raises_value_error(self):
        db = SessionLocal()
        try:
            with pytest.raises(ValueError):
                gather_report_evidence(db, _PROJECT_ID, 999_999_999)
        finally:
            db.close()

    def test_evidence_codes_are_unique_and_well_formed(self):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            codes = [i.code for i in ev.evidence_items]
            assert len(codes) == len(set(codes)), "duplicate evidence codes"
            assert all("-" in c for c in codes)
        finally:
            db.close()


class TestRiskScoring:
    def test_score_is_deterministic_across_repeated_calls(self):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            r1 = compute_report_risk_score(ev)
            r2 = compute_report_risk_score(ev)
            assert r1.total == r2.total
            assert [c.points for c in r1.components] == [c.points for c in r2.components]
        finally:
            db.close()

    def test_score_is_bounded_0_to_100(self):
        db = SessionLocal()
        try:
            for report_id in (_REPORT_WITH_EVIDENCE, _REPORT_SPARSE):
                ev = gather_report_evidence(db, _PROJECT_ID, report_id)
                risk = compute_report_risk_score(ev)
                assert 0 <= risk.total <= 100
                assert risk.level in ("Low", "Medium", "High", "Critical")
        finally:
            db.close()

    def test_two_reports_get_different_scores(self):
        """Direct regression test for 'output must never be identical
        unless the reports themselves are nearly identical' (requirement 10)."""
        db = SessionLocal()
        try:
            ev_a = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            ev_b = gather_report_evidence(db, _PROJECT_ID, _REPORT_SPARSE)
            risk_a = compute_report_risk_score(ev_a)
            risk_b = compute_report_risk_score(ev_b)
            assert risk_a.total != risk_b.total
        finally:
            db.close()

    def test_every_component_has_a_documented_rationale(self):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            for c in risk.components:
                assert c.rationale and len(c.rationale) > 10
                assert c.points <= c.max_points
        finally:
            db.close()

    def test_points_only_awarded_with_supporting_evidence_refs(self):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            for c in risk.components:
                if c.points > 0 and c.key != "adverse_weather":
                    assert c.evidence_refs, f"{c.key} scored points with no evidence_refs"
        finally:
            db.close()


class TestReasoningLayer:
    def _use_fake_provider(self, monkeypatch, provider: FakeLLMProvider) -> None:
        monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: provider)

    def test_valid_json_response_produces_completed_result(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            real_code = ev.evidence_items[0].code
            self._use_fake_provider(monkeypatch, FakeLLMProvider(fixed_response=_valid_reasoning_json(ev.report.id, real_code)))

            result = generate_report_reasoning(ev, risk)
            assert result.status == "completed"
            assert result.output is not None
            assert real_code in result.output.key_findings[0].evidence_codes
            assert real_code in result.output.citations
        finally:
            db.close()

    def test_finding_without_evidence_citation_is_dropped(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            data = json.loads(_valid_reasoning_json(ev.report.id, ev.evidence_items[0].code))
            data["key_findings"] = [
                {"category": "quality", "priority": "High", "statement": "No citation at all.", "evidence_codes": []},
            ]
            self._use_fake_provider(monkeypatch, FakeLLMProvider(fixed_response=json.dumps(data)))

            result = generate_report_reasoning(ev, risk)
            assert result.status == "completed"
            assert result.output.key_findings == []
            assert result.dropped_unsupported_count >= 1
        finally:
            db.close()

    def test_finding_with_fabricated_evidence_code_is_dropped(self, monkeypatch):
        """Citing a code that doesn't exist in the evidence bundle must be
        treated the same as no citation — this is what makes 'every
        conclusion must cite evidence' an enforced guarantee, not a request
        the model can satisfy with a fake-looking bracket."""
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            data = json.loads(_valid_reasoning_json(ev.report.id, ev.evidence_items[0].code))
            data["key_findings"] = [
                {"category": "quality", "priority": "High", "statement": "Fabricated finding.", "evidence_codes": ["NCR-999999"]},
            ]
            self._use_fake_provider(monkeypatch, FakeLLMProvider(fixed_response=json.dumps(data)))

            result = generate_report_reasoning(ev, risk)
            assert result.output.key_findings == []
        finally:
            db.close()

    def test_malformed_json_returns_unavailable_not_a_crash_or_fake_fallback(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            self._use_fake_provider(monkeypatch, FakeLLMProvider(fixed_response="not json at all"))

            result = generate_report_reasoning(ev, risk)
            assert result.status == "unavailable"
            assert result.output is None
            assert result.error_message
        finally:
            db.close()

    def test_provider_unavailable_returns_unavailable_status(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            self._use_fake_provider(monkeypatch, FakeLLMProvider(simulate_unavailable=True))

            result = generate_report_reasoning(ev, risk)
            assert result.status == "unavailable"
        finally:
            db.close()

    def test_insufficient_evidence_flag_is_preserved(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_SPARSE)
            risk = compute_report_risk_score(ev)
            data = json.loads(_valid_reasoning_json(ev.report.id, ev.evidence_items[0].code))
            data["insufficient_evidence"] = True
            data["insufficient_evidence_reason"] = "No safety, quality, or procurement evidence in this window."
            self._use_fake_provider(monkeypatch, FakeLLMProvider(fixed_response=json.dumps(data)))

            result = generate_report_reasoning(ev, risk)
            assert result.output.insufficient_evidence is True
            assert "No safety" in result.output.insufficient_evidence_reason
        finally:
            db.close()


class TestOrchestration:
    def test_analyze_never_raises_when_reasoning_unavailable(self, monkeypatch):
        monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: FakeLLMProvider(simulate_unavailable=True))
        db = SessionLocal()
        try:
            out = analyze_site_report(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            assert out.reasoning_status == "unavailable"
            assert out.confidence_score >= 0  # risk score still computed
            assert out.risk_score_breakdown.total == out.confidence_score
            assert out.recommended_actions == []
        finally:
            db.close()

    def test_analyze_missing_report_raises_value_error(self):
        db = SessionLocal()
        try:
            with pytest.raises(ValueError):
                analyze_site_report(db, _PROJECT_ID, 999_999_999)
        finally:
            db.close()

    def test_intelligence_view_does_not_touch_the_llm_provider(self, monkeypatch):
        """GET .../intelligence must stay fast and Hermes-free."""
        def _fail_if_called():
            raise AssertionError("build_site_report_intelligence must never call the LLM provider")
        monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: _fail_if_called())
        db = SessionLocal()
        try:
            result = build_site_report_intelligence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            assert result.report["report_id"] == _REPORT_WITH_EVIDENCE
        finally:
            db.close()


class TestApiEndpoints:
    def test_intelligence_endpoint_returns_200(self, client: TestClient):
        resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/site-reports/{_REPORT_WITH_EVIDENCE}/intelligence")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == _REPORT_WITH_EVIDENCE

    def test_intelligence_endpoint_404_for_missing_report(self, client: TestClient):
        resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/site-reports/999999999/intelligence")
        assert resp.status_code == 404

    def test_analyze_endpoint_returns_200_with_new_schema_fields(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: FakeLLMProvider(simulate_unavailable=True))
        resp = client.post(f"/api/v1/projects/{_PROJECT_ID}/site-reports/{_REPORT_WITH_EVIDENCE}/analyze")
        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "reasoning_status", "risk_score_breakdown", "major_findings", "schedule_findings",
            "procurement_findings", "equipment_issues", "weather_impact", "blocked_activities",
            "critical_risks", "priority_matrix", "next_site_visit_focus", "questions_for_site_team",
            "trend_analysis", "contradictions",
        ):
            assert key in data, f"missing new schema field: {key}"

    def test_analyze_endpoint_404_for_missing_report(self, client: TestClient):
        resp = client.post(f"/api/v1/projects/{_PROJECT_ID}/site-reports/999999999/analyze")
        assert resp.status_code == 404

    def test_cards_endpoint_still_works(self, client: TestClient):
        resp = client.get(f"/api/v1/projects/{_PROJECT_ID}/site-reports/cards")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class _TimeoutProvider:
    """Raises ProviderTimeoutError from generate() — distinct from
    FakeLLMProvider's simulate_unavailable, which never calls generate()
    at all (is_available() itself returns False). This exercises the
    actual timeout path a real Hermes subprocess timeout takes."""

    def __init__(self):
        self.call_count = 0

    @property
    def provider_name(self):
        return "fake-timeout"

    @property
    def model_name(self):
        return "fake-model-v1"

    def is_available(self):
        return True

    def generate(self, request):
        from app.ai.providers.base import ProviderTimeoutError
        self.call_count += 1
        raise ProviderTimeoutError("simulated Hermes subprocess timeout")


class TestPerformanceAndFallback:
    """AMAD AI Stabilization Part A — never more than one Hermes call per
    analysis, a real timeout produces reasoning_status="timed_out" (not a
    generic "unavailable"), and malformed JSON is repaired locally rather
    than triggering a second generation call."""

    def test_provider_timeout_sets_timed_out_status(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            provider = _TimeoutProvider()
            monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: provider)

            result = generate_report_reasoning(ev, risk)
            assert result.status == "timed_out"
            assert provider.call_count == 1, "a timeout must not trigger a retry generation call"
        finally:
            db.close()

    def test_timed_out_endpoint_shows_exact_required_message(self, client: TestClient, monkeypatch):
        provider = _TimeoutProvider()
        monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: provider)
        resp = client.post(f"/api/v1/projects/{_PROJECT_ID}/site-reports/{_REPORT_WITH_EVIDENCE}/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reasoning_status"] == "timed_out"
        assert data["executive_summary"] == "AI reasoning was unavailable; evidence-based analysis is shown."
        # Deterministic evidence/risk score still present even on timeout.
        assert data["risk_score_breakdown"]["total"] >= 0
        assert len(data["source_attribution"]) > 0

    def test_trailing_comma_json_is_repaired_locally_not_via_second_call(self, monkeypatch):
        """A trailing comma is exactly the kind of small-model JSON mistake
        the bounded local repair exists for — must be recovered WITHOUT a
        second call to the provider."""
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            code = ev.evidence_items[0].code
            good = json.loads(_valid_reasoning_json(ev.report.id, code))
            raw = json.dumps(good)
            # Inject a trailing comma before the final closing brace.
            broken = raw[:-1] + ",}"

            class _CountingProvider:
                call_count = 0

                @property
                def provider_name(self):
                    return "fake"

                @property
                def model_name(self):
                    return "fake-model-v1"

                def is_available(self):
                    return True

                def generate(self, request):
                    _CountingProvider.call_count += 1
                    from app.ai.providers.base import LLMResponse
                    return LLMResponse(
                        content=broken, model="fake-model-v1", provider="fake",
                        prompt_tokens=0, completion_tokens=0, latency_ms=0.0,
                    )

            monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: _CountingProvider())
            result = generate_report_reasoning(ev, risk)
            assert result.status == "completed", "trailing-comma JSON must be recovered by the bounded local repair"
            assert _CountingProvider.call_count == 1, "repair must not trigger a second generation call"
        finally:
            db.close()

    def test_genuinely_unrepairable_json_falls_back_without_second_call(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            risk = compute_report_risk_score(ev)
            provider = FakeLLMProvider(fixed_response="not json at all, and no amount of local repair fixes this")
            monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: provider)

            result = generate_report_reasoning(ev, risk)
            assert result.status == "unavailable"
            assert provider.call_count == 1, "an unrepairable response must not trigger a second generation call"
        finally:
            db.close()


class TestEvidenceCompaction:
    """AMAD AI Stabilization Part A — strict per-domain caps applied before
    evidence reaches the prompt, on the single largest report in the
    entire seeded dataset (45 raw in-window rows)."""

    _LARGE_PROJECT_ID = 45
    _LARGE_REPORT_ID = 1198

    def test_largest_report_in_dataset_is_compacted_under_caps(self):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, self._LARGE_PROJECT_ID, self._LARGE_REPORT_ID)
            assert ev.evidence_before_count > len(ev.evidence_items), (
                "compaction must reduce the evidence count on a large report"
            )
            by_cat: dict[str, int] = {}
            for item in ev.evidence_items:
                by_cat[item.category] = by_cat.get(item.category, 0) + 1
            assert by_cat.get("safety", 0) <= 3
            assert by_cat.get("quality", 0) <= 3
            assert by_cat.get("procurement", 0) <= 3
            assert by_cat.get("meeting", 0) <= 2
            assert by_cat.get("document", 0) <= 3
        finally:
            db.close()

    def test_evidence_block_prompt_size_bounded_even_for_largest_report(self):
        from app.ai.site_report_reasoning import _format_evidence_block
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, self._LARGE_PROJECT_ID, self._LARGE_REPORT_ID)
            risk = compute_report_risk_score(ev)
            block = _format_evidence_block(ev, risk)
            # Ticket's own measured baseline for a NORMAL report was ~4,650-
            # 5,500 chars total prompt; the single largest report in the
            # dataset must not exceed that just for its evidence block.
            assert len(block) < 5000, f"evidence block for the largest report is {len(block)} chars"
        finally:
            db.close()


class TestAnalysisCache:
    def test_second_call_with_unchanged_evidence_skips_hermes(self, monkeypatch):
        db = SessionLocal()
        try:
            ev = gather_report_evidence(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            code = ev.evidence_items[0].code
            provider = FakeLLMProvider(fixed_response=_valid_reasoning_json(_REPORT_WITH_EVIDENCE, code))
            monkeypatch.setattr(reasoning_module, "get_llm_provider", lambda: provider)

            from app.ai.site_report_intelligence import _ANALYSIS_CACHE
            _ANALYSIS_CACHE.clear()

            first = analyze_site_report(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            assert first.reasoning_status == "completed"
            assert provider.call_count == 1

            second = analyze_site_report(db, _PROJECT_ID, _REPORT_WITH_EVIDENCE)
            assert second.reasoning_status == "completed"
            assert provider.call_count == 1, "unchanged evidence must be served from cache, not a second Hermes call"
            assert second.executive_summary == first.executive_summary
        finally:
            from app.ai.site_report_intelligence import _ANALYSIS_CACHE
            _ANALYSIS_CACHE.clear()
            db.close()
