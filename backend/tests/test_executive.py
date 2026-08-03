"""
Tests for Phase 4C — Executive Intelligence endpoint.

GET /api/v1/executive

Auth is overridden to admin in conftest.py — all requests are authenticated.
401 behaviour is verified separately via API smoke tests.
"""
import pytest
from fastapi.testclient import TestClient

VALID_STATUSES   = {"Excellent", "Good", "At Risk", "Critical", "Unknown"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}
EXPECTED_CATS    = {"safety", "procurement", "quality", "schedule", "health"}


# ── Basic request ──────────────────────────────────────────────────────────────

class TestExecutiveBasic:
    def test_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/executive")
        assert resp.status_code == 200

    def test_content_type_json(self, client: TestClient):
        resp = client.get("/api/v1/executive")
        assert "application/json" in resp.headers["content-type"]


# ── Response shape ─────────────────────────────────────────────────────────────

class TestExecutiveShape:
    def test_has_all_required_top_level_keys(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        required = {
            "portfolio_status", "portfolio_score", "executive_summary",
            "total_projects", "critical_count", "at_risk_count",
            "good_count", "excellent_count",
            "top_priorities", "biggest_risks",
            "best_projects", "attention_required",
        }
        assert required <= d.keys()

    def test_portfolio_status_is_valid_level(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        assert d["portfolio_status"] in VALID_STATUSES

    def test_portfolio_score_in_range(self, client: TestClient):
        score = client.get("/api/v1/executive").json()["portfolio_score"]
        assert 0 <= score <= 100

    def test_executive_summary_non_empty(self, client: TestClient):
        summary = client.get("/api/v1/executive").json()["executive_summary"]
        assert isinstance(summary, str) and len(summary) > 20

    def test_all_list_fields_are_lists(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        for field in ("top_priorities", "biggest_risks", "best_projects", "attention_required"):
            assert isinstance(d[field], list), f"{field} should be a list"

    def test_counts_are_non_negative(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        for key in ("total_projects", "critical_count", "at_risk_count",
                    "good_count", "excellent_count"):
            assert d[key] >= 0

    def test_level_counts_sum_to_total(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        parts = (d["critical_count"] + d["at_risk_count"]
                 + d["good_count"] + d["excellent_count"])
        assert parts == d["total_projects"], f"parts={parts} != total={d['total_projects']}"


# ── Risk categories ────────────────────────────────────────────────────────────

class TestBiggestRisks:
    def test_exactly_five_risk_categories(self, client: TestClient):
        risks = client.get("/api/v1/executive").json()["biggest_risks"]
        assert len(risks) == 5

    def test_risk_category_names_correct(self, client: TestClient):
        cats = {r["category"] for r in client.get("/api/v1/executive").json()["biggest_risks"]}
        assert cats == EXPECTED_CATS

    def test_risk_severity_values_valid(self, client: TestClient):
        for r in client.get("/api/v1/executive").json()["biggest_risks"]:
            assert r["severity"] in VALID_SEVERITIES, (
                f"category={r['category']} has invalid severity={r['severity']}"
            )

    def test_risk_count_non_negative(self, client: TestClient):
        for r in client.get("/api/v1/executive").json()["biggest_risks"]:
            assert r["count"] >= 0

    def test_risk_detail_non_empty(self, client: TestClient):
        for r in client.get("/api/v1/executive").json()["biggest_risks"]:
            assert len(r["detail"]) > 10

    def test_risk_label_non_empty(self, client: TestClient):
        for r in client.get("/api/v1/executive").json()["biggest_risks"]:
            assert r["label"]


# ── Project list constraints ───────────────────────────────────────────────────

class TestProjectLists:
    def test_top_priorities_capped_at_5(self, client: TestClient):
        assert len(client.get("/api/v1/executive").json()["top_priorities"]) <= 5

    def test_best_projects_capped_at_5(self, client: TestClient):
        assert len(client.get("/api/v1/executive").json()["best_projects"]) <= 5

    def test_attention_required_capped_at_6(self, client: TestClient):
        assert len(client.get("/api/v1/executive").json()["attention_required"]) <= 6

    def test_best_projects_are_good_or_excellent(self, client: TestClient):
        for p in client.get("/api/v1/executive").json()["best_projects"]:
            assert p["level"] in ("Excellent", "Good"), (
                f"{p['project_code']} has level {p['level']} — expected Good/Excellent"
            )

    def test_attention_projects_are_critical_or_at_risk(self, client: TestClient):
        for p in client.get("/api/v1/executive").json()["attention_required"]:
            assert p["level"] in ("Critical", "At Risk"), (
                f"{p['project_code']} has level {p['level']} — expected Critical/At Risk"
            )

    def test_top_priorities_sorted_worst_first(self, client: TestClient):
        scores = [p["score"] for p in client.get("/api/v1/executive").json()["top_priorities"]]
        assert scores == sorted(scores), "Priorities should be ascending score (worst first)"

    def test_project_brief_required_fields(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        all_briefs = d["top_priorities"] + d["best_projects"] + d["attention_required"]
        if not all_briefs:
            pytest.skip("No project briefs in response")
        required = {"project_id", "project_code", "project_name",
                    "status", "score", "level", "primary_reason"}
        for brief in all_briefs:
            missing = required - brief.keys()
            assert not missing, f"Brief missing fields: {missing}"

    def test_brief_score_in_range(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        for brief in d["top_priorities"] + d["best_projects"] + d["attention_required"]:
            assert 0 <= brief["score"] <= 100

    def test_priority_reason_non_empty(self, client: TestClient):
        for p in client.get("/api/v1/executive").json()["top_priorities"]:
            assert p["primary_reason"], f"Empty reason for {p['project_code']}"


# ── Seeded data expectations ───────────────────────────────────────────────────

class TestSeededData:
    def test_portfolio_has_projects(self, client: TestClient):
        assert client.get("/api/v1/executive").json()["total_projects"] > 0

    def test_seeded_produces_top_priorities(self, client: TestClient):
        assert len(client.get("/api/v1/executive").json()["top_priorities"]) > 0

    def test_seeded_produces_all_risk_categories(self, client: TestClient):
        assert len(client.get("/api/v1/executive").json()["biggest_risks"]) == 5

    def test_summary_contains_portfolio_score(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        assert str(d["portfolio_score"]) in d["executive_summary"]

    def test_summary_reflects_portfolio_status(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        keywords = {
            "Excellent": "excellently",
            "Good":      "good standing",
            "At Risk":   "at risk",
            "Critical":  "critical",
            "Unknown":   "available",
        }
        expected = keywords.get(d["portfolio_status"], "")
        if expected:
            assert expected.lower() in d["executive_summary"].lower(), (
                f"Expected '{expected}' in summary for status {d['portfolio_status']}"
            )

    def test_critical_summary_mentions_intervention(self, client: TestClient):
        d = client.get("/api/v1/executive").json()
        if d["critical_count"] > 0:
            assert (
                "intervention" in d["executive_summary"].lower()
                or "critical" in d["executive_summary"].lower()
            )
