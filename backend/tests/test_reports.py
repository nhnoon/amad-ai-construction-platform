"""
Tests for Phase 4D — Executive Weekly Report endpoint.

GET /api/v1/reports/executive-weekly

Auth is overridden to admin in conftest.py — all requests are authenticated.
"""
import pytest
from fastapi.testclient import TestClient

VALID_STATUSES   = {"Excellent", "Good", "At Risk", "Critical", "Unknown"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}
EXPECTED_RISK_CATS = {"safety", "procurement", "quality", "schedule", "health"}


# ── Basic request ──────────────────────────────────────────────────────────────

class TestReportBasic:
    def test_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/reports/executive-weekly")
        assert resp.status_code == 200

    def test_content_type_json(self, client: TestClient):
        resp = client.get("/api/v1/reports/executive-weekly")
        assert "application/json" in resp.headers["content-type"]


# ── Top-level shape ────────────────────────────────────────────────────────────

class TestReportShape:
    def test_has_all_required_top_level_keys(self, client: TestClient):
        d = client.get("/api/v1/reports/executive-weekly").json()
        required = {
            "report_period", "generated_at", "portfolio_summary",
            "portfolio_status", "portfolio_score", "health_distribution",
            "top_priorities", "biggest_risks", "critical_alerts",
            "procurement_blockers", "safety_highlights", "quality_highlights",
            "recommended_actions", "sources",
        }
        assert required <= d.keys(), f"Missing keys: {required - d.keys()}"

    def test_portfolio_status_valid(self, client: TestClient):
        d = client.get("/api/v1/reports/executive-weekly").json()
        assert d["portfolio_status"] in VALID_STATUSES

    def test_portfolio_score_in_range(self, client: TestClient):
        score = client.get("/api/v1/reports/executive-weekly").json()["portfolio_score"]
        assert 0 <= score <= 100

    def test_portfolio_summary_non_empty(self, client: TestClient):
        summary = client.get("/api/v1/reports/executive-weekly").json()["portfolio_summary"]
        assert isinstance(summary, str) and len(summary) > 30

    def test_generated_at_is_string(self, client: TestClient):
        ga = client.get("/api/v1/reports/executive-weekly").json()["generated_at"]
        assert isinstance(ga, str) and len(ga) > 10

    def test_all_list_fields_are_lists(self, client: TestClient):
        d = client.get("/api/v1/reports/executive-weekly").json()
        for field in (
            "top_priorities", "biggest_risks", "critical_alerts",
            "procurement_blockers", "safety_highlights", "quality_highlights",
            "recommended_actions", "sources",
        ):
            assert isinstance(d[field], list), f"{field} should be a list"


# ── Report period ──────────────────────────────────────────────────────────────

class TestReportPeriod:
    def test_period_has_required_fields(self, client: TestClient):
        period = client.get("/api/v1/reports/executive-weekly").json()["report_period"]
        for field in ("start_date", "end_date", "week_number", "year", "label"):
            assert field in period, f"Missing period field: {field}"

    def test_period_start_is_monday(self, client: TestClient):
        from datetime import date
        period = client.get("/api/v1/reports/executive-weekly").json()["report_period"]
        start = date.fromisoformat(period["start_date"])
        assert start.weekday() == 0, f"start_date {start} is not Monday (weekday={start.weekday()})"

    def test_period_end_is_sunday(self, client: TestClient):
        from datetime import date
        period = client.get("/api/v1/reports/executive-weekly").json()["report_period"]
        end = date.fromisoformat(period["end_date"])
        assert end.weekday() == 6, f"end_date {end} is not Sunday (weekday={end.weekday()})"

    def test_period_span_is_6_days(self, client: TestClient):
        from datetime import date
        period = client.get("/api/v1/reports/executive-weekly").json()["report_period"]
        start = date.fromisoformat(period["start_date"])
        end = date.fromisoformat(period["end_date"])
        assert (end - start).days == 6

    def test_week_number_valid(self, client: TestClient):
        wn = client.get("/api/v1/reports/executive-weekly").json()["report_period"]["week_number"]
        assert 1 <= wn <= 53

    def test_year_is_reasonable(self, client: TestClient):
        year = client.get("/api/v1/reports/executive-weekly").json()["report_period"]["year"]
        assert 2020 <= year <= 2035

    def test_label_non_empty(self, client: TestClient):
        label = client.get("/api/v1/reports/executive-weekly").json()["report_period"]["label"]
        assert len(label) > 5


# ── Health distribution ────────────────────────────────────────────────────────

class TestHealthDistribution:
    def test_distribution_has_all_fields(self, client: TestClient):
        hd = client.get("/api/v1/reports/executive-weekly").json()["health_distribution"]
        for field in ("excellent", "good", "at_risk", "critical", "total", "average_score"):
            assert field in hd

    def test_distribution_sums_to_total(self, client: TestClient):
        hd = client.get("/api/v1/reports/executive-weekly").json()["health_distribution"]
        parts = hd["excellent"] + hd["good"] + hd["at_risk"] + hd["critical"]
        assert parts == hd["total"]

    def test_average_score_in_range(self, client: TestClient):
        avg = client.get("/api/v1/reports/executive-weekly").json()["health_distribution"]["average_score"]
        assert 0 <= avg <= 100

    def test_all_counts_non_negative(self, client: TestClient):
        hd = client.get("/api/v1/reports/executive-weekly").json()["health_distribution"]
        for k in ("excellent", "good", "at_risk", "critical", "total"):
            assert hd[k] >= 0


# ── Biggest risks ──────────────────────────────────────────────────────────────

class TestBiggestRisks:
    def test_exactly_five_categories(self, client: TestClient):
        risks = client.get("/api/v1/reports/executive-weekly").json()["biggest_risks"]
        assert len(risks) == 5

    def test_risk_category_names_correct(self, client: TestClient):
        cats = {r["category"] for r in client.get("/api/v1/reports/executive-weekly").json()["biggest_risks"]}
        assert cats == EXPECTED_RISK_CATS

    def test_risk_severities_valid(self, client: TestClient):
        for r in client.get("/api/v1/reports/executive-weekly").json()["biggest_risks"]:
            assert r["severity"] in VALID_SEVERITIES

    def test_risk_counts_non_negative(self, client: TestClient):
        for r in client.get("/api/v1/reports/executive-weekly").json()["biggest_risks"]:
            assert r["count"] >= 0

    def test_risk_detail_non_empty(self, client: TestClient):
        for r in client.get("/api/v1/reports/executive-weekly").json()["biggest_risks"]:
            assert len(r["detail"]) > 10


# ── Top priorities ─────────────────────────────────────────────────────────────

class TestTopPriorities:
    def test_capped_at_5(self, client: TestClient):
        assert len(client.get("/api/v1/reports/executive-weekly").json()["top_priorities"]) <= 5

    def test_sorted_worst_first(self, client: TestClient):
        scores = [p["score"] for p in client.get("/api/v1/reports/executive-weekly").json()["top_priorities"]]
        assert scores == sorted(scores)

    def test_priority_brief_required_fields(self, client: TestClient):
        priorities = client.get("/api/v1/reports/executive-weekly").json()["top_priorities"]
        if not priorities:
            pytest.skip("No priorities in response")
        required = {"project_id", "project_code", "project_name", "status", "score", "level", "primary_reason"}
        for p in priorities:
            assert required <= p.keys()

    def test_priority_score_in_range(self, client: TestClient):
        for p in client.get("/api/v1/reports/executive-weekly").json()["top_priorities"]:
            assert 0 <= p["score"] <= 100


# ── Critical alerts ────────────────────────────────────────────────────────────

class TestCriticalAlerts:
    def test_capped_at_10(self, client: TestClient):
        assert len(client.get("/api/v1/reports/executive-weekly").json()["critical_alerts"]) <= 10

    def test_alert_required_fields(self, client: TestClient):
        alerts = client.get("/api/v1/reports/executive-weekly").json()["critical_alerts"]
        if not alerts:
            pytest.skip("No alerts in report")
        required = {"severity", "category", "title", "description"}
        for a in alerts:
            assert required <= a.keys()

    def test_alert_severity_valid(self, client: TestClient):
        for a in client.get("/api/v1/reports/executive-weekly").json()["critical_alerts"]:
            assert a["severity"] in VALID_SEVERITIES

    def test_alerts_sorted_by_severity(self, client: TestClient):
        sev_ord = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sevs = [sev_ord.get(a["severity"], 4) for a in client.get("/api/v1/reports/executive-weekly").json()["critical_alerts"]]
        assert sevs == sorted(sevs)

    def test_seeded_data_produces_alerts(self, client: TestClient):
        assert len(client.get("/api/v1/reports/executive-weekly").json()["critical_alerts"]) > 0


# ── Recommended actions ────────────────────────────────────────────────────────

class TestRecommendedActions:
    def test_at_least_one_action(self, client: TestClient):
        assert len(client.get("/api/v1/reports/executive-weekly").json()["recommended_actions"]) > 0

    def test_action_required_fields(self, client: TestClient):
        actions = client.get("/api/v1/reports/executive-weekly").json()["recommended_actions"]
        required = {"priority", "area", "action", "rationale"}
        for a in actions:
            assert required <= a.keys()

    def test_actions_priority_sequential(self, client: TestClient):
        priorities = [a["priority"] for a in client.get("/api/v1/reports/executive-weekly").json()["recommended_actions"]]
        assert priorities == sorted(priorities)
        assert priorities[0] == 1

    def test_action_text_non_empty(self, client: TestClient):
        for a in client.get("/api/v1/reports/executive-weekly").json()["recommended_actions"]:
            assert len(a["action"]) > 10
            assert len(a["rationale"]) > 10


# ── Sources ────────────────────────────────────────────────────────────────────

class TestSources:
    def test_has_sources(self, client: TestClient):
        assert len(client.get("/api/v1/reports/executive-weekly").json()["sources"]) > 0

    def test_source_required_fields(self, client: TestClient):
        for s in client.get("/api/v1/reports/executive-weekly").json()["sources"]:
            assert "source" in s and "record_count" in s and "description" in s

    def test_record_counts_positive(self, client: TestClient):
        for s in client.get("/api/v1/reports/executive-weekly").json()["sources"]:
            assert s["record_count"] >= 0

    def test_has_health_source(self, client: TestClient):
        sources = client.get("/api/v1/reports/executive-weekly").json()["sources"]
        names = [s["source"] for s in sources]
        assert any("Health" in n for n in names)

    def test_has_procurement_source(self, client: TestClient):
        sources = client.get("/api/v1/reports/executive-weekly").json()["sources"]
        names = [s["source"] for s in sources]
        assert any("Purchase" in n or "Procurement" in n for n in names)
