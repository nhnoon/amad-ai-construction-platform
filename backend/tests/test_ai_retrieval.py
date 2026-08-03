"""Tests for AI retrieval tools — authorization filtering and evidence generation."""
import pytest
from fastapi import HTTPException

from app.ai.scope import AIAuthScope
from app.ai.retrieval.projects import get_project_overview, get_project_risks
from app.ai.retrieval.procurement import (
    get_procurement_summary,
    get_supplier_information,
    get_late_purchase_orders,
)
from app.ai.retrieval.safety import get_safety_summary, get_open_ncrs
from app.ai.retrieval.site_reports import get_recent_site_reports, get_recent_daily_activities
from app.ai.retrieval.meetings import get_recent_meetings, get_project_decisions
from app.ai.intent import route_intent


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


def _restricted_scope(project_ids: tuple, org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id,
        user_id=10,
        user_role="site_engineer",
        accessible_project_ids=project_ids,
    )


def _no_access_scope(org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id,
        user_id=20,
        user_role="viewer",
        accessible_project_ids=(),
    )


class TestProjectRetrieval:
    def test_global_scope_retrieves_projects(self, db_session):
        result = get_project_overview(db_session, _global_scope(), limit=5)
        assert result.has_data

    def test_global_scope_returns_evidence(self, db_session):
        result = get_project_overview(db_session, _global_scope(), limit=3)
        assert len(result.evidence) > 0
        for ev in result.evidence:
            assert ev.source_type == "project"
            assert ev.label
            assert ev.snippet

    def test_no_access_scope_returns_empty(self, db_session):
        result = get_project_overview(db_session, _no_access_scope())
        assert not result.has_data

    def test_unauthorized_project_raises_403(self, db_session):
        scope = _restricted_scope(project_ids=(9999,))
        with pytest.raises(HTTPException) as exc:
            get_project_overview(db_session, scope, project_id=1)
        assert exc.value.status_code == 403

    def test_global_scope_can_access_any_project(self, db_session):
        result = get_project_overview(db_session, _global_scope(), project_id=1)
        assert result.data

    def test_risks_global_scope(self, db_session):
        result = get_project_risks(db_session, _global_scope(), limit=5)
        assert result.data.get("risks") is not None

    def test_risks_cross_project_blocked(self, db_session):
        scope = _restricted_scope(project_ids=(9998,))
        with pytest.raises(HTTPException):
            get_project_risks(db_session, scope, project_id=1)


class TestProcurementRetrieval:
    def test_global_scope_gets_procurement(self, db_session):
        result = get_procurement_summary(db_session, _global_scope(), limit=5)
        assert "purchase_requests" in result.data
        assert "purchase_orders" in result.data

    def test_no_access_returns_empty(self, db_session):
        result = get_procurement_summary(db_session, _no_access_scope())
        assert not result.has_data

    def test_supplier_retrieval_no_auth_required(self, db_session):
        result = get_supplier_information(db_session, _global_scope(), limit=5)
        assert "suppliers" in result.data

    def test_supplier_evidence_format(self, db_session):
        result = get_supplier_information(db_session, _global_scope(), limit=3)
        for ev in result.evidence:
            assert ev.source_type == "supplier"

    def test_late_orders_no_access_returns_empty(self, db_session):
        result = get_late_purchase_orders(db_session, _no_access_scope())
        assert result.data.get("total", 0) == 0


class TestSafetyRetrieval:
    def test_global_scope_gets_safety_events(self, db_session):
        result = get_safety_summary(db_session, _global_scope(), limit=5)
        assert "safety_events" in result.data

    def test_no_access_returns_empty(self, db_session):
        result = get_safety_summary(db_session, _no_access_scope())
        assert not result.has_data

    def test_ncrs_global_scope(self, db_session):
        result = get_open_ncrs(db_session, _global_scope(), limit=5)
        assert "ncrs" in result.data

    def test_ncrs_no_access_empty(self, db_session):
        result = get_open_ncrs(db_session, _no_access_scope())
        assert result.data.get("total", 0) == 0

    def test_safety_evidence_has_source_type(self, db_session):
        result = get_safety_summary(db_session, _global_scope(), limit=3)
        for ev in result.evidence:
            assert ev.source_type == "safety_event"


class TestSiteReportRetrieval:
    def test_global_scope_gets_reports(self, db_session):
        result = get_recent_site_reports(db_session, _global_scope(), limit=5)
        assert "reports" in result.data

    def test_no_access_returns_empty(self, db_session):
        result = get_recent_site_reports(db_session, _no_access_scope())
        assert result.data.get("total", 0) == 0

    def test_daily_activities_global(self, db_session):
        result = get_recent_daily_activities(db_session, _global_scope(), limit=5)
        assert "activities" in result.data


class TestMeetingsRetrieval:
    def test_global_scope_gets_meetings(self, db_session):
        result = get_recent_meetings(db_session, _global_scope(), limit=5)
        assert "meetings" in result.data

    def test_decisions_global_scope(self, db_session):
        result = get_project_decisions(db_session, _global_scope(), limit=5)
        assert "decisions" in result.data

    def test_no_access_meetings_empty(self, db_session):
        result = get_recent_meetings(db_session, _no_access_scope())
        assert result.data.get("total", 0) == 0


class TestIntentRouter:
    def test_project_intent(self):
        r = route_intent("What is the status of project PRJ-001?")
        assert r.intent == "project_overview"
        assert not r.unsupported

    def test_procurement_intent(self):
        r = route_intent("Show me all purchase orders")
        assert r.intent == "procurement"

    def test_suppliers_intent(self):
        r = route_intent("List our suppliers")
        assert r.intent == "suppliers"

    def test_safety_intent(self):
        r = route_intent("Any safety incidents this month?")
        assert r.intent == "safety"

    def test_ncr_intent(self):
        r = route_intent("Show me open NCRs")
        assert r.intent == "ncr"

    def test_site_reports_intent(self):
        r = route_intent("Show recent site reports")
        assert r.intent == "site_reports"

    def test_meetings_intent(self):
        r = route_intent("What meetings happened last week?")
        assert r.intent == "meetings"

    def test_unknown_intent(self):
        r = route_intent("What is the weather like in Dubai?")
        assert r.unsupported is True

    def test_arabic_project_intent(self):
        r = route_intent("ما هو وضع المشروع؟")
        assert r.intent == "project_overview"

    def test_arabic_procurement_intent(self):
        r = route_intent("أرني المشتريات")
        assert r.intent == "procurement"

    def test_project_id_hint_preserved(self):
        r = route_intent("Show me site reports", hint_project_id=42)
        assert r.project_id == 42

    def test_project_code_extracted(self):
        r = route_intent("Give me details on PRJ-005")
        assert r.project_code == "PRJ-005"


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
