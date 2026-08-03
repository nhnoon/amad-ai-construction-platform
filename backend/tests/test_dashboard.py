"""
Dashboard aggregation correctness tests.
Verifies that delayed_projects counts ONLY status=='Delayed',
on_hold_projects counts ONLY status=='On Hold', and all
summary fields are present and match direct SQL counts.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import get_db
from tests.conftest import TestingSessionLocal


SUMMARY_URL = "/api/v1/dashboard/summary"


@pytest.fixture(scope="module")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_summary_returns_200(client: TestClient):
    r = client.get(SUMMARY_URL)
    assert r.status_code == 200


def test_summary_has_all_required_fields(client: TestClient):
    data = client.get(SUMMARY_URL).json()
    required = [
        "total_projects", "active_projects", "completed_projects",
        "delayed_projects", "on_hold_projects",
        "total_suppliers", "active_suppliers",
        "total_purchase_requests", "open_purchase_requests",
        "total_purchase_orders", "late_purchase_orders",
        "total_safety_events", "high_severity_events",
        "total_ncrs", "open_ncrs",
        "total_site_reports", "total_meetings", "total_decisions",
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"


def test_delayed_projects_counts_only_delayed_status(client: TestClient, db_session):
    """delayed_projects must count status=='Delayed' only — not 'On Hold'."""
    sql_delayed = db_session.execute(
        text("SELECT COUNT(*) FROM projects WHERE status = 'Delayed'")
    ).scalar()
    api_delayed = client.get(SUMMARY_URL).json()["delayed_projects"]
    assert api_delayed == sql_delayed, (
        f"API delayed_projects={api_delayed} does not match SQL count={sql_delayed}. "
        "Check that 'On Hold' projects are NOT included."
    )


def test_on_hold_projects_counts_only_on_hold_status(client: TestClient, db_session):
    """on_hold_projects must count status=='On Hold' only."""
    sql_on_hold = db_session.execute(
        text("SELECT COUNT(*) FROM projects WHERE status = 'On Hold'")
    ).scalar()
    api_on_hold = client.get(SUMMARY_URL).json()["on_hold_projects"]
    assert api_on_hold == sql_on_hold, (
        f"API on_hold_projects={api_on_hold} does not match SQL count={sql_on_hold}."
    )


def test_delayed_and_on_hold_are_separate(client: TestClient):
    """delayed_projects + on_hold_projects < total_projects (sanity check)."""
    data = client.get(SUMMARY_URL).json()
    assert data["delayed_projects"] + data["on_hold_projects"] <= data["total_projects"]


def test_project_status_counts_sum_to_total(client: TestClient):
    """Active + Delayed + On Hold + Completed should equal total_projects."""
    data = client.get(SUMMARY_URL).json()
    total = data["total_projects"]
    parts = (
        data["active_projects"]
        + data["delayed_projects"]
        + data["on_hold_projects"]
        + data["completed_projects"]
    )
    assert parts == total, (
        f"Status counts ({parts}) do not sum to total_projects ({total}). "
        "Are there projects with unexpected status values?"
    )


def test_open_purchase_requests_are_subset_of_total(client: TestClient):
    data = client.get(SUMMARY_URL).json()
    assert data["open_purchase_requests"] <= data["total_purchase_requests"]


def test_late_purchase_orders_are_subset_of_total(client: TestClient):
    data = client.get(SUMMARY_URL).json()
    assert data["late_purchase_orders"] <= data["total_purchase_orders"]


def test_open_ncrs_are_subset_of_total(client: TestClient):
    data = client.get(SUMMARY_URL).json()
    assert data["open_ncrs"] <= data["total_ncrs"]


def test_high_severity_events_are_subset_of_total(client: TestClient):
    data = client.get(SUMMARY_URL).json()
    assert data["high_severity_events"] <= data["total_safety_events"]


def test_open_ncrs_counts_non_closed_only(client: TestClient, db_session):
    """open_ncrs should count all NCRs that are NOT 'Closed'."""
    sql_open = db_session.execute(
        text("SELECT COUNT(*) FROM ncrs WHERE status != 'Closed'")
    ).scalar()
    api_open = client.get(SUMMARY_URL).json()["open_ncrs"]
    assert api_open == sql_open


def test_active_projects_match_sql(client: TestClient, db_session):
    sql_active = db_session.execute(
        text("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
    ).scalar()
    api_active = client.get(SUMMARY_URL).json()["active_projects"]
    assert api_active == sql_active


def test_high_severity_events_match_sql(client: TestClient, db_session):
    sql_high = db_session.execute(
        text("SELECT COUNT(*) FROM safety_events WHERE severity IN ('High', 'Critical')")
    ).scalar()
    api_high = client.get(SUMMARY_URL).json()["high_severity_events"]
    assert api_high == sql_high
