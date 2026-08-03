"""
Regression tests for the Project Health Score Engine (Phase 4A).

Covers:
 - Pure unit tests for each scoring factor (no DB required)
 - API integration tests via TestClient
 - Copilot health-related query paths
"""
from __future__ import annotations

import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from app.ai.health_score import (
    compute_health_score,
    _schedule_penalty,
    _safety_penalty,
    _ncr_penalty,
    _procurement_penalty,
    _risk_penalty,
    _score_to_level,
)


# ── Helpers for building mock project objects ─────────────────────────────────

def _make_project(
    status="Active",
    planned_finish="2030-01-01",
    actual_finish=None,
    safety_events=None,
    ncrs=None,
    purchase_orders=None,
    risks=None,
):
    return SimpleNamespace(
        id=1,
        project_code="PRJ-TEST",
        project_name="Test Project",
        status=status,
        planned_finish=planned_finish,
        actual_finish=actual_finish,
        safety_events=safety_events or [],
        ncrs=ncrs or [],
        purchase_orders=purchase_orders or [],
        risks=risks or [],
    )


def _event(severity):
    return SimpleNamespace(severity=severity)


def _ncr(status):
    return SimpleNamespace(status=status)


def _po(is_late):
    return SimpleNamespace(is_late=is_late)


def _risk(status="open", impact="medium"):
    return SimpleNamespace(status=status, impact=impact)


# ── Unit: score_to_level ──────────────────────────────────────────────────────

def test_score_levels():
    assert _score_to_level(100) == "Excellent"
    assert _score_to_level(80) == "Excellent"
    assert _score_to_level(79) == "Good"
    assert _score_to_level(60) == "Good"
    assert _score_to_level(59) == "At Risk"
    assert _score_to_level(40) == "At Risk"
    assert _score_to_level(39) == "Critical"
    assert _score_to_level(0) == "Critical"


# ── Unit: schedule penalty ────────────────────────────────────────────────────

def test_schedule_completed_zero():
    proj = _make_project(status="Completed")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    assert penalty == 0.0
    assert reasons == []


def test_schedule_active_not_overdue():
    proj = _make_project(status="Active", planned_finish="2030-01-01")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    assert penalty == 0.0
    assert reasons == []


def test_schedule_delayed_no_date():
    proj = _make_project(status="Delayed", planned_finish="")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    assert penalty == 25.0
    assert any("Delayed" in r or "behind" in r for r in reasons)


def test_schedule_delayed_with_days():
    proj = _make_project(status="Delayed", planned_finish="2024-01-01")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    delay_days = (date(2026, 7, 7) - date(2024, 1, 1)).days  # ~917 days
    expected = min(25.0 + 0.3 * delay_days, 35.0)  # capped at 35
    assert penalty == pytest.approx(expected, abs=0.01)
    assert any(str(delay_days) in r for r in reasons)


def test_schedule_on_hold():
    proj = _make_project(status="On Hold")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    assert penalty == 15.0
    assert any("on hold" in r.lower() for r in reasons)


def test_schedule_suspended():
    proj = _make_project(status="Suspended")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    assert penalty == 30.0


def test_schedule_active_overdue():
    proj = _make_project(status="Active", planned_finish="2025-01-01")
    penalty, reasons = _schedule_penalty(proj, date(2026, 7, 7))
    delay_days = (date(2026, 7, 7) - date(2025, 1, 1)).days  # ~552 days → cap 20
    assert penalty == pytest.approx(min(1.0 * delay_days, 20.0))
    assert penalty <= 20.0


# ── Unit: safety penalty ──────────────────────────────────────────────────────

def test_safety_empty():
    penalty, reasons = _safety_penalty([])
    assert penalty == 0.0
    assert reasons == []


def test_safety_high_events():
    events = [_event("High")] * 3
    penalty, reasons = _safety_penalty(events)
    assert penalty == pytest.approx(9.0)  # 3 × 3.0
    assert any("High" in r for r in reasons)


def test_safety_cap_total():
    events = [_event("High")] * 20 + [_event("Medium")] * 20 + [_event("Low")] * 20
    penalty, _ = _safety_penalty(events)
    assert penalty == pytest.approx(25.0)  # total cap


def test_safety_high_sub_cap():
    events = [_event("High")] * 10  # 10 × 3 = 30, sub-cap is 15
    penalty, _ = _safety_penalty(events)
    assert penalty == pytest.approx(15.0)


# ── Unit: NCR penalty ─────────────────────────────────────────────────────────

def test_ncr_all_closed():
    ncrs = [_ncr("Closed")] * 10
    penalty, reasons = _ncr_penalty(ncrs)
    assert penalty == 0.0
    assert reasons == []


def test_ncr_open_penalty():
    ncrs = [_ncr("Open")] * 5 + [_ncr("Closed")] * 2
    penalty, reasons = _ncr_penalty(ncrs)
    assert penalty == pytest.approx(7.5)  # 5 × 1.5
    assert "5 Open NCRs" in reasons[0]


def test_ncr_cap():
    ncrs = [_ncr("Open")] * 50  # 50 × 1.5 = 75 → capped at 20
    penalty, _ = _ncr_penalty(ncrs)
    assert penalty == pytest.approx(20.0)


def test_ncr_under_corrective_action():
    ncrs = [_ncr("Under Corrective Action")] * 4
    penalty, reasons = _ncr_penalty(ncrs)
    assert penalty == pytest.approx(6.0)  # treated as open
    assert len(reasons) == 1


# ── Unit: procurement penalty ─────────────────────────────────────────────────

def test_po_none_late():
    penalty, reasons = _procurement_penalty([_po(False)] * 10)
    assert penalty == 0.0
    assert reasons == []


def test_po_late_penalty():
    pos = [_po(True)] * 5 + [_po(False)] * 10
    penalty, reasons = _procurement_penalty(pos)
    assert penalty == pytest.approx(4.0)  # 5 × 0.8
    assert "5 Late Purchase Orders" in reasons[0]


def test_po_cap():
    pos = [_po(True)] * 100  # 100 × 0.8 = 80 → capped at 15
    penalty, _ = _procurement_penalty(pos)
    assert penalty == pytest.approx(15.0)


# ── Unit: risk penalty ────────────────────────────────────────────────────────

def test_risk_no_open():
    risks = [_risk(status="closed")] * 5
    penalty, reasons = _risk_penalty(risks)
    assert penalty == 0.0
    assert reasons == []


def test_risk_open_high():
    risks = [_risk(status="open", impact="high")] * 2
    penalty, reasons = _risk_penalty(risks)
    assert penalty == pytest.approx(6.0)  # 2 × 3.0, sub-cap = 6
    assert len(reasons) == 1


def test_risk_total_cap():
    # High sub-cap=6, medium sub-cap=4 → total=10, hits overall cap of 10
    risks = [_risk(status="open", impact="high")] * 10 + [_risk(status="open", impact="medium")] * 10
    penalty, _ = _risk_penalty(risks)
    assert penalty == pytest.approx(10.0)  # total cap


# ── Unit: compute_health_score ────────────────────────────────────────────────

def test_perfect_project():
    proj = _make_project(
        status="Active",
        planned_finish="2030-01-01",
        safety_events=[],
        ncrs=[_ncr("Closed")] * 5,
        purchase_orders=[_po(False)] * 10,
        risks=[],
    )
    result = compute_health_score(proj, today=date(2026, 7, 7))
    assert result.score == 100
    assert result.level == "Excellent"
    assert result.reasons == []


def test_completed_project_score():
    proj = _make_project(
        status="Completed",
        planned_finish="2023-01-01",
        safety_events=[_event("High")] * 2,
        ncrs=[_ncr("Open")] * 3,
        purchase_orders=[_po(True)] * 5,
    )
    result = compute_health_score(proj, today=date(2026, 7, 7))
    # Completed → schedule_penalty = 0; other factors still apply
    assert result.schedule_penalty == 0.0
    assert result.score < 100
    assert result.level in ("Excellent", "Good", "At Risk", "Critical")


def test_critical_project():
    proj = _make_project(
        status="Delayed",
        planned_finish="2024-01-01",
        safety_events=[_event("High")] * 8,
        ncrs=[_ncr("Open")] * 15,
        purchase_orders=[_po(True)] * 20,
        risks=[_risk("open", "high")] * 5,
    )
    result = compute_health_score(proj, today=date(2026, 7, 7))
    assert result.score <= 39
    assert result.level == "Critical"
    assert len(result.reasons) > 0


def test_score_clamped_0_100():
    proj = _make_project(
        status="Delayed",
        planned_finish="2020-01-01",
        safety_events=[_event("Critical")] * 100,
        ncrs=[_ncr("Open")] * 200,
        purchase_orders=[_po(True)] * 200,
        risks=[_risk("open", "high")] * 100,
    )
    result = compute_health_score(proj, today=date(2026, 7, 7))
    assert 0 <= result.score <= 100
    assert result.level == "Critical"


def test_reasons_list_has_content_for_bad_project():
    proj = _make_project(
        status="Delayed",
        planned_finish="2024-01-01",
        safety_events=[_event("High")] * 3,
        ncrs=[_ncr("Open")] * 8,
        purchase_orders=[_po(True)] * 10,
    )
    result = compute_health_score(proj, today=date(2026, 7, 7))
    assert len(result.reasons) >= 3  # delay + safety + NCR + PO


# ── API integration tests ─────────────────────────────────────────────────────

def test_list_health_scores(client):
    resp = client.get("/api/v1/projects/health-scores")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Sorted by score ascending (worst first)
    scores = [item["score"] for item in data]
    assert scores == sorted(scores)


def test_health_score_fields(client):
    resp = client.get("/api/v1/projects/health-scores")
    assert resp.status_code == 200
    item = resp.json()[0]
    required = {"project_id", "project_code", "project_name", "status",
                "score", "level", "reasons", "schedule_penalty",
                "safety_penalty", "ncr_penalty", "procurement_penalty", "risk_penalty"}
    assert required.issubset(item.keys())


def test_health_score_valid_ranges(client):
    resp = client.get("/api/v1/projects/health-scores")
    assert resp.status_code == 200
    valid_levels = {"Excellent", "Good", "At Risk", "Critical"}
    for item in resp.json():
        assert 0 <= item["score"] <= 100, f"Score out of range: {item['score']}"
        assert item["level"] in valid_levels, f"Invalid level: {item['level']}"
        assert isinstance(item["reasons"], list)


def test_get_project_health(client):
    resp = client.get("/api/v1/projects/1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == 1
    assert 0 <= data["score"] <= 100
    assert data["level"] in ("Excellent", "Good", "At Risk", "Critical")


def test_get_project_health_not_found(client):
    resp = client.get("/api/v1/projects/999999/health")
    assert resp.status_code == 404


def test_delayed_projects_score_lower_than_completed(client):
    scores_resp = client.get("/api/v1/projects/health-scores")
    assert scores_resp.status_code == 200
    all_scores = scores_resp.json()

    delayed = [s for s in all_scores if s["status"] == "Delayed"]
    completed = [s for s in all_scores if s["status"] == "Completed"]

    if delayed and completed:
        avg_delayed = sum(s["score"] for s in delayed) / len(delayed)
        avg_completed = sum(s["score"] for s in completed) / len(completed)
        assert avg_delayed < avg_completed, (
            f"Expected delayed avg ({avg_delayed:.1f}) < completed avg ({avg_completed:.1f})"
        )


def test_health_score_reasons_list(client):
    resp = client.get("/api/v1/projects/health-scores")
    assert resp.status_code == 200
    data = resp.json()
    # At least some projects should have reasons
    projects_with_reasons = [p for p in data if len(p["reasons"]) > 0]
    assert len(projects_with_reasons) > 0


def test_health_score_consistency(client):
    """Health score from list must match individual project endpoint."""
    list_resp = client.get("/api/v1/projects/health-scores")
    assert list_resp.status_code == 200
    list_data = {item["project_id"]: item for item in list_resp.json()}

    for pid in list(list_data.keys())[:3]:
        single_resp = client.get(f"/api/v1/projects/{pid}/health")
        assert single_resp.status_code == 200
        single = single_resp.json()
        assert single["score"] == list_data[pid]["score"]
        assert single["level"] == list_data[pid]["level"]
