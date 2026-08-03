"""Tests for Smart Alerts Center — Phase 4B.

All tests run against real seeded PostgreSQL data via the TestClient.
Auth is overridden to admin user in conftest.py.
"""
import pytest
from fastapi.testclient import TestClient


class TestAlertsList:
    def test_list_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200

    def test_list_response_shape(self, client: TestClient):
        data = client.get("/api/v1/alerts").json()
        assert "alerts" in data
        assert "total" in data
        assert isinstance(data["alerts"], list)
        assert isinstance(data["total"], int)

    def test_total_matches_list_length(self, client: TestClient):
        data = client.get("/api/v1/alerts").json()
        # total is the full count; list may be paginated by limit
        assert data["total"] >= len(data["alerts"])

    def test_alert_required_fields(self, client: TestClient):
        alerts = client.get("/api/v1/alerts").json()["alerts"]
        if not alerts:
            pytest.skip("No alerts in seeded data")
        a = alerts[0]
        for field in ("id", "title", "description", "severity", "category",
                      "source_type", "source_id", "detected_at", "recommended_action"):
            assert field in a, f"Missing field: {field}"

    def test_severity_values_valid(self, client: TestClient):
        valid = {"critical", "high", "medium", "low"}
        for a in client.get("/api/v1/alerts").json()["alerts"]:
            assert a["severity"] in valid

    def test_category_values_valid(self, client: TestClient):
        valid = {"health", "safety", "procurement", "quality", "schedule"}
        for a in client.get("/api/v1/alerts").json()["alerts"]:
            assert a["category"] in valid

    def test_sorted_by_severity_desc(self, client: TestClient):
        """Alerts must arrive critical → high → medium → low."""
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sevs = [sev_order[a["severity"]] for a in client.get("/api/v1/alerts").json()["alerts"]]
        assert sevs == sorted(sevs), "Alerts not sorted by severity"

    def test_no_duplicate_ids(self, client: TestClient):
        ids = [a["id"] for a in client.get("/api/v1/alerts").json()["alerts"]]
        assert len(ids) == len(set(ids)), "Duplicate alert IDs found"

    def test_seeded_data_generates_alerts(self, client: TestClient):
        """The seeded dataset should always produce at least one alert."""
        assert client.get("/api/v1/alerts").json()["total"] > 0

    def test_detected_at_is_iso_string(self, client: TestClient):
        alerts = client.get("/api/v1/alerts").json()["alerts"]
        if not alerts:
            pytest.skip("No alerts")
        dt = alerts[0]["detected_at"]
        assert "T" in dt, "detected_at is not ISO 8601"

    def test_recommended_action_non_empty(self, client: TestClient):
        for a in client.get("/api/v1/alerts").json()["alerts"]:
            assert a["recommended_action"].strip(), "Empty recommended_action found"

    def test_default_limit_is_100(self, client: TestClient):
        alerts = client.get("/api/v1/alerts").json()["alerts"]
        assert len(alerts) <= 100


class TestAlertsFilter:
    def test_filter_by_severity_critical(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"severity": "critical"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["severity"] == "critical"

    def test_filter_by_severity_high(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"severity": "high"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["severity"] == "high"

    def test_filter_by_severity_medium(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"severity": "medium"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["severity"] == "medium"

    def test_filter_by_category_health(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"category": "health"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["category"] == "health"

    def test_filter_by_category_safety(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"category": "safety"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["category"] == "safety"

    def test_filter_by_category_procurement(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"category": "procurement"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["category"] == "procurement"

    def test_filter_by_category_quality(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"category": "quality"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["category"] == "quality"

    def test_filter_by_category_schedule(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"category": "schedule"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["category"] == "schedule"

    def test_filter_by_project_id(self, client: TestClient):
        all_alerts = client.get("/api/v1/alerts").json()["alerts"]
        with_project = [a for a in all_alerts if a.get("project_id")]
        if not with_project:
            pytest.skip("No alerts with project_id in seeded data")
        pid = with_project[0]["project_id"]
        filtered = client.get("/api/v1/alerts", params={"project_id": pid}).json()
        assert filtered["status_code"] != 422 if "status_code" in filtered else True
        for a in filtered["alerts"]:
            assert a["project_id"] == pid

    def test_unknown_severity_returns_empty(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"severity": "nonexistent"}).json()
        assert data["alerts"] == []
        assert data["total"] == 0

    def test_unknown_category_returns_empty(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"category": "nonexistent"}).json()
        assert data["alerts"] == []
        assert data["total"] == 0

    def test_limit_param(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"limit": 3}).json()
        assert len(data["alerts"]) <= 3

    def test_offset_pagination(self, client: TestClient):
        total = client.get("/api/v1/alerts").json()["total"]
        if total < 2:
            pytest.skip("Not enough alerts to test pagination")
        page1 = client.get("/api/v1/alerts", params={"limit": 1, "offset": 0}).json()["alerts"]
        page2 = client.get("/api/v1/alerts", params={"limit": 1, "offset": 1}).json()["alerts"]
        assert len(page1) == 1
        assert len(page2) == 1
        assert page1[0]["id"] != page2[0]["id"]

    def test_severity_and_category_combined(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"severity": "high", "category": "safety"})
        assert resp.status_code == 200
        for a in resp.json()["alerts"]:
            assert a["severity"] == "high"
            assert a["category"] == "safety"

    def test_limit_boundary_max(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"limit": 500})
        assert resp.status_code == 200

    def test_limit_too_large_rejected(self, client: TestClient):
        resp = client.get("/api/v1/alerts", params={"limit": 501})
        assert resp.status_code == 422


class TestAlertsSummary:
    def test_summary_returns_200(self, client: TestClient):
        assert client.get("/api/v1/alerts/summary").status_code == 200

    def test_summary_shape(self, client: TestClient):
        data = client.get("/api/v1/alerts/summary").json()
        for field in ("total", "critical", "high", "medium", "low", "by_category"):
            assert field in data

    def test_severity_counts_non_negative(self, client: TestClient):
        data = client.get("/api/v1/alerts/summary").json()
        for sev in ("total", "critical", "high", "medium", "low"):
            assert data[sev] >= 0

    def test_severity_sum_equals_total(self, client: TestClient):
        data = client.get("/api/v1/alerts/summary").json()
        computed = data["critical"] + data["high"] + data["medium"] + data["low"]
        assert computed == data["total"]

    def test_by_category_is_dict(self, client: TestClient):
        data = client.get("/api/v1/alerts/summary").json()
        assert isinstance(data["by_category"], dict)

    def test_by_category_sum_equals_total(self, client: TestClient):
        data = client.get("/api/v1/alerts/summary").json()
        cat_total = sum(data["by_category"].values())
        assert cat_total == data["total"]

    def test_category_keys_are_valid(self, client: TestClient):
        valid = {"health", "safety", "procurement", "quality", "schedule"}
        data = client.get("/api/v1/alerts/summary").json()
        for key in data["by_category"]:
            assert key in valid, f"Invalid category key: {key}"

    def test_seeded_data_has_alerts(self, client: TestClient):
        data = client.get("/api/v1/alerts/summary").json()
        assert data["total"] > 0

    def test_filter_counts_match_summary(self, client: TestClient):
        """Each severity filter result count must equal the summary count."""
        summary = client.get("/api/v1/alerts/summary").json()
        for sev in ("critical", "high", "medium", "low"):
            filtered_total = client.get(
                "/api/v1/alerts", params={"severity": sev, "limit": 500}
            ).json()["total"]
            assert summary[sev] == filtered_total, (
                f"summary.{sev}={summary[sev]} != filter count {filtered_total}"
            )

    def test_category_filter_counts_match_summary(self, client: TestClient):
        """Each category filter result count must equal the summary by_category count."""
        summary = client.get("/api/v1/alerts/summary").json()
        for cat, expected in summary["by_category"].items():
            filtered_total = client.get(
                "/api/v1/alerts", params={"category": cat, "limit": 500}
            ).json()["total"]
            assert expected == filtered_total, (
                f"summary.by_category[{cat}]={expected} != filter count {filtered_total}"
            )


class TestAlertsAlertTypes:
    """Verify that specific alert type categories appear in seeded data."""

    def test_health_alerts_present(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"category": "health"}).json()
        assert data["total"] > 0, "No health alerts generated from seeded data"

    def test_safety_alerts_present(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"category": "safety"}).json()
        assert data["total"] > 0, "No safety alerts generated from seeded data"

    def test_procurement_alerts_present(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"category": "procurement"}).json()
        assert data["total"] > 0, "No procurement alerts generated from seeded data"

    def test_schedule_alerts_present(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"category": "schedule"}).json()
        assert data["total"] > 0, "No schedule alerts generated from seeded data"

    def test_critical_severity_alerts_present(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"severity": "critical"}).json()
        assert data["total"] > 0, "No critical alerts generated from seeded data"

    def test_high_severity_alerts_present(self, client: TestClient):
        data = client.get("/api/v1/alerts", params={"severity": "high"}).json()
        assert data["total"] > 0, "No high severity alerts generated from seeded data"

    def test_health_alerts_have_project_id(self, client: TestClient):
        alerts = client.get("/api/v1/alerts", params={"category": "health"}).json()["alerts"]
        for a in alerts:
            assert a["project_id"] is not None, "Health alert missing project_id"

    def test_safety_event_alerts_have_safety_source_type(self, client: TestClient):
        alerts = client.get("/api/v1/alerts", params={"category": "safety"}).json()["alerts"]
        source_types = {a["source_type"] for a in alerts}
        assert "safety_event" in source_types or "project_safety" in source_types

    def test_procurement_alerts_have_project_id(self, client: TestClient):
        alerts = client.get("/api/v1/alerts", params={"category": "procurement"}).json()["alerts"]
        for a in alerts:
            assert a["project_id"] is not None, "Procurement alert missing project_id"
