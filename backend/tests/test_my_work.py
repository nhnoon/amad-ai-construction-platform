"""Tests for the Unified My Work Feed (Sprint 4 Part E, extended in
Sprint 5 with the "approval" branch — app/ai/my_work.py,
app/api/v1/my_work.py). Real Postgres DB (same pattern as
test_ownership_engine.py). Covers aggregation across all six original
entities, each filter, the four-level sort order, pagination headers,
cross-user isolation, and the Sprint 5 approval branch (including the
project_id=None / General Library case).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.ai.my_work import get_my_work
from app.ai.scope import build_ai_scope
from app.models.approvals import ApprovalRequest
from app.models.documents import Document
from app.models.meetings import Meeting, MeetingActionItem
from app.models.procurement import PurchaseRequest
from app.models.projects import ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from tests.conftest import TEST_USER_ID, TEST_USER_ORGANIZATION_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_OWNER = TEST_USER_ID
_OTHER_OWNER = 4  # real seeded site_engineer


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_from_today(n: int) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=n)).isoformat()


def _scope():
    from app.models.auth import UserAccount
    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=_OWNER, email="my-work-scope@test.local", full_name="My Work Scope",
            role="admin", is_active=True, hashed_password="x", organization_id=TEST_USER_ORGANIZATION_ID,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        return build_ai_scope(user, db)
    finally:
        db.close()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def meeting(db_session):
    row = Meeting(project_id=_REAL_PROJECT_ID, meeting_date=_today(), title="My Work Test Meeting", meeting_type="site")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(Meeting).filter(Meeting.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def six_owned_entities(db_session, meeting):
    """One owned row per entity type, for _OWNER — the full aggregation set."""
    risk = ProjectRisk(project_id=_REAL_PROJECT_ID, title="MyWork Risk", status="open", impact="high", owner_id=_OWNER)
    issue = ProjectIssue(project_id=_REAL_PROJECT_ID, title="MyWork Issue", status="open", severity="low", owner_id=_OWNER)
    action_item = MeetingActionItem(
        meeting_id=meeting, project_id=_REAL_PROJECT_ID, description="MyWork Action Item",
        owner="x", status="open", priority="medium", due_date=_days_from_today(-1), owner_id=_OWNER,
    )
    safety_event = SafetyEvent(
        project_id=_REAL_PROJECT_ID, subcontractor_id=1, event_date=_today(), severity="High",
        description="MyWork Safety Event", corrective_action="", status="Open", owner_id=_OWNER,
    )
    ncr = NCR(project_id=_REAL_PROJECT_ID, ncr_type="Quality", description="MyWork NCR", root_cause="x", issue_date=_today(), status="Open", owner_id=_OWNER)
    pr = PurchaseRequest(
        project_id=_REAL_PROJECT_ID, request_no="MYWORK-PR", status="Under Review", created_at=_today(),
        required_delivery_date=_days_from_today(3), owner_id=_OWNER,
    )
    rows = [risk, issue, action_item, safety_event, ncr, pr]
    db_session.add_all(rows)
    db_session.commit()
    for r in rows:
        db_session.refresh(r)
    ids = {
        "project_risk": risk.id, "project_issue": issue.id, "action_item": action_item.id,
        "safety_event": safety_event.id, "ncr": ncr.id, "purchase_request": pr.id,
    }
    yield ids
    db_session.query(ProjectRisk).filter(ProjectRisk.id == risk.id).delete()
    db_session.query(ProjectIssue).filter(ProjectIssue.id == issue.id).delete()
    db_session.query(MeetingActionItem).filter(MeetingActionItem.id == action_item.id).delete()
    db_session.query(SafetyEvent).filter(SafetyEvent.id == safety_event.id).delete()
    db_session.query(NCR).filter(NCR.id == ncr.id).delete()
    db_session.query(PurchaseRequest).filter(PurchaseRequest.id == pr.id).delete()
    db_session.commit()


@pytest.fixture
def foreign_owned_risk(db_session):
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Not My Risk", status="open", owner_id=_OTHER_OWNER)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ProjectRisk).filter(ProjectRisk.id == row.id).delete()
    db_session.commit()


class TestAggregation:
    def test_all_six_entities_appear(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"limit": 100})
        assert resp.status_code == 200
        body = resp.json()
        seen_types = set()
        for entity_type, entity_id in six_owned_entities.items():
            match = next((r for r in body if r["entity_type"] == entity_type and r["entity_id"] == entity_id), None)
            assert match is not None, f"missing {entity_type}"
            seen_types.add(entity_type)
            assert match["project_code"]
            assert match["action_url"]
        assert seen_types == set(six_owned_entities)

    def test_foreign_owned_row_is_excluded(self, client: TestClient, db_session, foreign_owned_risk):
        resp = client.get("/api/v1/my-work", params={"limit": 100})
        assert resp.status_code == 200
        assert all(r["entity_id"] != foreign_owned_risk or r["entity_type"] != "project_risk" for r in resp.json())


class TestFilters:
    def test_entity_type_filter(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"entity_type": "ncr", "limit": 100})
        assert resp.status_code == 200
        body = resp.json()
        assert all(r["entity_type"] == "ncr" for r in body)
        assert any(r["entity_id"] == six_owned_entities["ncr"] for r in body)

    def test_project_id_filter(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"project_id": _REAL_PROJECT_ID, "limit": 100})
        assert resp.status_code == 200
        assert all(r["project_id"] == _REAL_PROJECT_ID for r in resp.json())

    def test_status_filter(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"entity_type": "purchase_request", "status": "Under Review", "limit": 100})
        assert resp.status_code == 200
        assert any(r["entity_id"] == six_owned_entities["purchase_request"] for r in resp.json())

    def test_open_only_excludes_closed(self, client: TestClient, db_session, six_owned_entities):
        db_session.query(ProjectRisk).filter(ProjectRisk.id == six_owned_entities["project_risk"]).update({"status": "closed"})
        db_session.commit()
        resp = client.get("/api/v1/my-work", params={"entity_type": "project_risk", "open_only": True, "limit": 100})
        assert resp.status_code == 200
        assert all(r["entity_id"] != six_owned_entities["project_risk"] for r in resp.json())

    def test_overdue_filter(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"entity_type": "action_item", "overdue": True, "limit": 100})
        assert resp.status_code == 200
        body = resp.json()
        assert any(r["entity_id"] == six_owned_entities["action_item"] for r in body)
        assert all(r["is_overdue"] for r in body)

    def test_due_soon_filter(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"entity_type": "purchase_request", "due_soon": True, "limit": 100})
        assert resp.status_code == 200
        body = resp.json()
        assert any(r["entity_id"] == six_owned_entities["purchase_request"] for r in body)
        assert all(r["is_due_soon"] for r in body)

    def test_invalid_entity_type_is_422(self, client: TestClient):
        resp = client.get("/api/v1/my-work", params={"entity_type": "not_a_real_type"})
        assert resp.status_code == 422


class TestOrdering:
    def test_overdue_then_due_soon_then_priority(self, db_session, six_owned_entities):
        """action_item is overdue, purchase_request is due-soon, risk has
        high priority, issue has low priority — verifies the 4-level sort
        (overdue > due-soon > priority > newest) among just these four
        known rows, ignoring whatever else may already be in the feed."""
        scope = _scope()
        items, _ = get_my_work(db_session, scope, limit=200)
        known_ids = {
            (six_owned_entities["action_item"], "action_item"),
            (six_owned_entities["purchase_request"], "purchase_request"),
            (six_owned_entities["project_risk"], "project_risk"),
            (six_owned_entities["project_issue"], "project_issue"),
        }
        filtered = [i for i in items if (i["entity_id"], i["entity_type"]) in known_ids]
        order = [i["entity_type"] for i in filtered]
        assert order == ["action_item", "purchase_request", "project_risk", "project_issue"]


class TestPagination:
    def test_pagination_headers(self, client: TestClient, db_session, six_owned_entities):
        resp = client.get("/api/v1/my-work", params={"limit": 1, "skip": 0})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert int(resp.headers["X-Total-Count"]) >= 6


# ─────────────────────────────────────────────────────────────────────────
# Sprint 5 — the "approval" branch (assigned_reviewer_id == caller)
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def project_scoped_approval(db_session):
    pr = PurchaseRequest(project_id=_REAL_PROJECT_ID, request_no="MYWORK-APR", status="Under Review", created_at=_today())
    db_session.add(pr)
    db_session.commit()
    db_session.refresh(pr)
    approval = ApprovalRequest(
        organization_id=TEST_USER_ORGANIZATION_ID, project_id=_REAL_PROJECT_ID,
        entity_type="purchase_request", entity_id=pr.id, requested_by_user_id=_OTHER_OWNER,
        assigned_reviewer_id=_OWNER, status="Pending", risk_level="high",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)
    yield approval.id
    db_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).delete()
    db_session.query(PurchaseRequest).filter(PurchaseRequest.id == pr.id).delete()
    db_session.commit()


@pytest.fixture
def org_scoped_approval(db_session):
    """A General Library document approval — project_id is genuinely
    NULL, exercising the LEFT JOIN / optional project_code path."""
    doc = Document(
        organization_id=TEST_USER_ORGANIZATION_ID, doc_type="policy", title="MyWork Org Doc",
        doc_date=_today(), content_summary="x", version_number=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    approval = ApprovalRequest(
        organization_id=TEST_USER_ORGANIZATION_ID, project_id=None,
        entity_type="document", entity_id=doc.id, requested_by_user_id=_OTHER_OWNER,
        assigned_reviewer_id=_OWNER, status="Pending", risk_level="medium", target_version=1,
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)
    yield approval.id
    db_session.query(ApprovalRequest).filter(ApprovalRequest.id == approval.id).delete()
    db_session.query(Document).filter(Document.id == doc.id).delete()
    db_session.commit()


class TestApprovalBranch:
    def test_appears_when_assigned_to_me(self, client: TestClient, db_session, project_scoped_approval):
        resp = client.get("/api/v1/my-work", params={"entity_type": "approval", "limit": 100})
        assert resp.status_code == 200
        body = resp.json()
        match = next((r for r in body if r["entity_id"] == project_scoped_approval and r["entity_type"] == "approval"), None)
        assert match is not None
        assert match["status"] == "Pending"
        assert match["priority"] == "high"
        assert match["project_code"]
        assert match["action_url"] == f"/approvals/{project_scoped_approval}"

    def test_org_scoped_approval_has_null_project_and_does_not_crash(self, client: TestClient, db_session, org_scoped_approval):
        resp = client.get("/api/v1/my-work", params={"entity_type": "approval", "limit": 100})
        assert resp.status_code == 200
        match = next((r for r in resp.json() if r["entity_id"] == org_scoped_approval), None)
        assert match is not None
        assert match["project_id"] is None
        assert match["project_code"] is None

    def test_does_not_leak_to_requester_only(self, client: TestClient, db_session, project_scoped_approval):
        # _OTHER_OWNER is the requester, not the reviewer — GET /my-work as
        # the shared admin test user (assigned reviewer) must see it, but
        # requester-only visibility is intentionally NOT this feed's job
        # (see app/ai/my_work.py's module docstring — use
        # GET /approvals?requested_by_me=true instead).
        resp = client.get("/api/v1/my-work", params={"entity_type": "approval", "limit": 100})
        assert resp.status_code == 200
        assert any(r["entity_id"] == project_scoped_approval for r in resp.json())

    def test_does_not_break_six_existing_branches(self, client: TestClient, db_session, six_owned_entities, project_scoped_approval):
        resp = client.get("/api/v1/my-work", params={"limit": 100})
        assert resp.status_code == 200
        body = resp.json()
        for entity_type, entity_id in six_owned_entities.items():
            assert any(r["entity_type"] == entity_type and r["entity_id"] == entity_id for r in body)
        assert any(r["entity_type"] == "approval" and r["entity_id"] == project_scoped_approval for r in body)
