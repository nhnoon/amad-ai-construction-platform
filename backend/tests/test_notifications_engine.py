"""Tests for the Notifications Engine (Sprint 4 — app/ai/notification_service.py,
app/api/v1/notifications.py). Real Postgres DB (same pattern as
test_ownership_engine.py / test_workflow_engine.py). Covers: assignment/
reassignment/unassignment notification creation, self-assignment producing
none, the dedup primitive, unread/read/read-all + isolation + pagination/
filtering via HTTP, workflow status/completed/reopened/due-date/purchase-
request-decision notifications, Part F's ownership-consistency 409 (and
that it's a no-op when owner_id is None), and transaction safety (a
notification failure must never affect the underlying write).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from app.ai.notification_service import notify, notify_assignment
from app.ai.ownership_engine import (
    AssignmentEvent,
    assign_action_item,
    assign_project_risk,
    unassign_project_risk,
)
from app.ai.scope import AIAuthScope
from app.ai.workflow_engine import (
    update_action_item,
    update_ncr,
    update_project_issue,
    update_project_risk,
    update_purchase_request,
    update_safety_event,
)
from app.models.assignment_history import AssignmentHistory
from app.models.meetings import Meeting, MeetingActionItem
from app.models.notifications import Notification
from app.models.organizations import Organization, ProjectMembership
from app.models.procurement import PurchaseRequest
from app.models.projects import ProjectIssue, ProjectRisk
from app.models.safety import NCR, SafetyEvent
from app.schemas.meetings import MeetingActionItemUpdate
from app.schemas.procurement import PurchaseRequestUpdate
from app.schemas.projects import ProjectIssueUpdate, ProjectRiskUpdate
from app.schemas.safety import NCRUpdate, SafetyEventUpdate
from tests.conftest import TEST_USER_ID, TEST_USER_ORGANIZATION_ID, TestingSessionLocal

_REAL_PROJECT_ID = 1
_ORG_A = TEST_USER_ORGANIZATION_ID
_MANAGER_USER_ID = TEST_USER_ID  # real seeded admin — global read, manager authority
_ENGINEER_USER_ID = 4  # real seeded site_engineer, org 1
_PM_USER_ID = 3  # real seeded project_manager (global read), org 1


def _scope(user_id: int = _MANAGER_USER_ID, org_id: int = _ORG_A, role: str = "admin", membership_roles=None) -> AIAuthScope:
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"notif-scope-{user_id}@test.local", full_name="Notif Scope Test",
            role=role, is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        base = build_ai_scope(user, db)
        if membership_roles:
            return AIAuthScope(
                organization_id=base.organization_id, user_id=base.user_id, user_role=base.user_role,
                accessible_project_ids=tuple(set(base.accessible_project_ids) | set(membership_roles)),
                project_membership_roles={**base.project_membership_roles, **membership_roles},
            )
        return base
    finally:
        db.close()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _delete_notifications_for(db_session, entity_type: str, entity_id: int) -> None:
    db_session.query(Notification).filter(Notification.entity_type == entity_type, Notification.entity_id == entity_id).delete()
    db_session.commit()


@pytest.fixture
def engineer_membership(db_session):
    row = ProjectMembership(user_id=_ENGINEER_USER_ID, project_id=_REAL_PROJECT_ID, role_on_project="site_engineer", is_active=True)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(ProjectMembership).filter(ProjectMembership.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def risk(db_session):
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Notif Test Risk", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "project_risk", row.id)
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "project_risk", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(ProjectRisk).filter(ProjectRisk.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def owned_risk(db_session):
    """A risk pre-owned by the engineer, bypassing the assignment engine
    entirely, so workflow-notification tests aren't muddied by an extra
    assignment notification."""
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Notif Owned Risk", status="open", owner_id=_ENGINEER_USER_ID)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "project_risk", row.id)
    db_session.query(ProjectRisk).filter(ProjectRisk.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def unowned_risk(db_session):
    row = ProjectRisk(project_id=_REAL_PROJECT_ID, title="Notif Unowned Risk", status="open")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "project_risk", row.id)
    db_session.query(ProjectRisk).filter(ProjectRisk.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def owned_issue(db_session):
    row = ProjectIssue(project_id=_REAL_PROJECT_ID, title="Notif Owned Issue", status="open", owner_id=_ENGINEER_USER_ID)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "project_issue", row.id)
    db_session.query(ProjectIssue).filter(ProjectIssue.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def meeting(db_session):
    row = Meeting(project_id=_REAL_PROJECT_ID, meeting_date="2026-08-02", title="Notif Test Meeting", meeting_type="site")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    db_session.query(Meeting).filter(Meeting.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def owned_action_item(db_session, meeting):
    row = MeetingActionItem(
        meeting_id=meeting, project_id=_REAL_PROJECT_ID, description="Notif owned action item",
        owner="Engineer Text", status="open", due_date="2026-08-10", owner_id=_ENGINEER_USER_ID,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "action_item", row.id)
    db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "action_item", AssignmentHistory.entity_id == row.id).delete()
    db_session.query(MeetingActionItem).filter(MeetingActionItem.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def owned_safety_event(db_session):
    row = SafetyEvent(
        project_id=_REAL_PROJECT_ID, subcontractor_id=1, event_date="2026-08-02", severity="Medium",
        description="Notif owned safety event", corrective_action="", status="Open", owner_id=_ENGINEER_USER_ID,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "safety_event", row.id)
    db_session.query(SafetyEvent).filter(SafetyEvent.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def owned_ncr(db_session):
    row = NCR(
        project_id=_REAL_PROJECT_ID, ncr_type="Quality", description="Notif owned NCR",
        root_cause="Unknown", issue_date="2026-08-02", status="Open", owner_id=_ENGINEER_USER_ID,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    yield row.id
    _delete_notifications_for(db_session, "ncr", row.id)
    db_session.query(NCR).filter(NCR.id == row.id).delete()
    db_session.commit()


@pytest.fixture
def owned_purchase_request(db_session):
    def _make(status: str):
        row = PurchaseRequest(project_id=_REAL_PROJECT_ID, request_no=f"NOTIF-{status[:4]}", status=status, created_at="2026-08-02", owner_id=_ENGINEER_USER_ID)
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row.id
    created = []

    def factory(status: str) -> int:
        rid = _make(status)
        created.append(rid)
        return rid

    yield factory
    for rid in created:
        _delete_notifications_for(db_session, "purchase_request", rid)
        db_session.query(PurchaseRequest).filter(PurchaseRequest.id == rid).delete()
    db_session.commit()


@pytest.fixture
def notif_batch(db_session):
    """Manually-created Notification rows for isolation/pagination/filter
    tests that don't need a real assignment/workflow trigger."""
    created_ids = []

    def make(**overrides) -> Notification:
        defaults = dict(
            organization_id=_ORG_A, recipient_user_id=_MANAGER_USER_ID, actor_user_id=_ENGINEER_USER_ID,
            project_id=_REAL_PROJECT_ID, event_type="status_changed", entity_type="project_risk", entity_id=999_999,
            title="Test notification", message="Test message", severity="info", action_url="/x",
        )
        defaults.update(overrides)
        row = Notification(**defaults)
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        created_ids.append(row.id)
        return row

    yield make
    db_session.query(Notification).filter(Notification.id.in_(created_ids)).delete(synchronize_session=False)
    db_session.commit()


# ─────────────────────────────────────────────────────────────────────────
# Part B — Assignment notifications
# ─────────────────────────────────────────────────────────────────────────
class TestAssignmentNotifications:
    def test_assign_creates_notification_for_new_owner(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        n = (
            db_session.query(Notification)
            .filter(Notification.entity_type == "project_risk", Notification.entity_id == risk, Notification.recipient_user_id == _ENGINEER_USER_ID)
            .first()
        )
        assert n is not None
        assert n.event_type == "assigned"
        assert n.actor_user_id == _MANAGER_USER_ID
        assert n.is_read is False
        assert n.organization_id == _ORG_A

    def test_self_assignment_creates_no_notification(self, db_session, risk, engineer_membership):
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        assign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assert db_session.query(Notification).filter(Notification.entity_type == "project_risk", Notification.entity_id == risk).count() == 0

    def test_self_release_creates_no_notification(self, db_session, risk, engineer_membership):
        scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        assign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        unassign_project_risk(db_session, scope, _REAL_PROJECT_ID, risk)
        assert db_session.query(Notification).filter(Notification.entity_type == "project_risk", Notification.entity_id == risk).count() == 0

    def test_reassignment_notifies_new_owner_and_previous_owner(self, db_session, risk, engineer_membership):
        # actor (manager) assigns to engineer, then reassigns to PM — actor
        # is a genuine third party throughout, so both branches fire.
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _PM_USER_ID)

        new_owner_notifs = (
            db_session.query(Notification)
            .filter(Notification.entity_type == "project_risk", Notification.entity_id == risk, Notification.recipient_user_id == _PM_USER_ID)
            .all()
        )
        assert len(new_owner_notifs) == 1
        assert new_owner_notifs[0].event_type == "reassigned"

        previous_owner_notifs = (
            db_session.query(Notification)
            .filter(Notification.entity_type == "project_risk", Notification.entity_id == risk, Notification.recipient_user_id == _ENGINEER_USER_ID)
            .all()
        )
        # engineer got 1 notification for being assigned initially, plus 1
        # for being reassigned away.
        assert len(previous_owner_notifs) == 2
        assert {n.event_type for n in previous_owner_notifs} == {"assigned", "reassigned"}

    def test_unassignment_notifies_previous_owner(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        unassign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk)
        n = (
            db_session.query(Notification)
            .filter(Notification.entity_type == "project_risk", Notification.entity_id == risk, Notification.recipient_user_id == _ENGINEER_USER_ID, Notification.event_type == "unassigned")
            .first()
        )
        assert n is not None
        assert n.actor_user_id == _MANAGER_USER_ID

    def test_action_item_assignment_also_notifies(self, db_session, meeting, engineer_membership):
        item = MeetingActionItem(meeting_id=meeting, project_id=_REAL_PROJECT_ID, description="Notif AI item", owner="x", status="open")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        try:
            assign_action_item(db_session, _scope(), _REAL_PROJECT_ID, item.id, _ENGINEER_USER_ID)
            n = db_session.query(Notification).filter(Notification.entity_type == "action_item", Notification.entity_id == item.id).first()
            assert n is not None
            assert n.event_type == "assigned"
        finally:
            _delete_notifications_for(db_session, "action_item", item.id)
            db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "action_item", AssignmentHistory.entity_id == item.id).delete()
            db_session.query(MeetingActionItem).filter(MeetingActionItem.id == item.id).delete()
            db_session.commit()


class TestDeduplication:
    def test_identical_notify_calls_collapse_to_one_row(self, db_session, risk):
        kwargs = dict(
            organization_id=_ORG_A, recipient_user_id=_ENGINEER_USER_ID, actor_user_id=_MANAGER_USER_ID,
            project_id=_REAL_PROJECT_ID, event_type="assigned", entity_type="project_risk", entity_id=risk,
            title="Assigned: Notif Test Risk", message="You were assigned.", severity="info", action_url="/x",
            deduplication_key=f"assign:project_risk:{risk}:{_ENGINEER_USER_ID}:assigned:{_ENGINEER_USER_ID}:None",
        )
        notify(db_session, **kwargs)
        notify(db_session, **kwargs)
        rows = db_session.query(Notification).filter(Notification.entity_type == "project_risk", Notification.entity_id == risk).all()
        assert len(rows) == 1

    def test_dedup_does_not_affect_assignment_history_audit_trail(self, db_session, risk, engineer_membership):
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        history = db_session.query(AssignmentHistory).filter(AssignmentHistory.entity_type == "project_risk", AssignmentHistory.entity_id == risk).all()
        assert len(history) == 2  # audit trail unaffected by any notification-level dedup


class TestTransactionSafety:
    def test_notification_failure_does_not_break_the_assignment(self, db_session, risk, engineer_membership, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("simulated notification backend failure")

        monkeypatch.setattr("app.ai.notification_service.notify", boom)
        updated = assign_project_risk(db_session, _scope(), _REAL_PROJECT_ID, risk, _ENGINEER_USER_ID)
        assert updated.owner_id == _ENGINEER_USER_ID  # the real write still succeeded


# ─────────────────────────────────────────────────────────────────────────
# Part C — Workflow notifications
# ─────────────────────────────────────────────────────────────────────────
class TestWorkflowStatusNotifications:
    def test_risk_status_change_notifies_owner(self, db_session, owned_risk):
        update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, owned_risk, ProjectRiskUpdate(status="mitigating"))
        n = db_session.query(Notification).filter(Notification.entity_type == "project_risk", Notification.entity_id == owned_risk).first()
        assert n is not None
        assert n.event_type == "status_changed"
        assert n.recipient_user_id == _ENGINEER_USER_ID

    def test_issue_resolved_is_item_completed(self, db_session, owned_issue):
        update_project_issue(db_session, _scope(), _REAL_PROJECT_ID, owned_issue, ProjectIssueUpdate(status="Resolved", resolution="Fixed it"))
        n = db_session.query(Notification).filter(Notification.entity_type == "project_issue", Notification.entity_id == owned_issue).first()
        assert n is not None
        assert n.event_type == "item_completed"

    def test_action_item_completed_then_reopened(self, db_session, owned_action_item):
        update_action_item(db_session, _scope(), _REAL_PROJECT_ID, owned_action_item, MeetingActionItemUpdate(status="Completed", completed_at="2026-08-02"))
        update_action_item(db_session, _scope(), _REAL_PROJECT_ID, owned_action_item, MeetingActionItemUpdate(status="open"))
        events = (
            db_session.query(Notification.event_type)
            .filter(Notification.entity_type == "action_item", Notification.entity_id == owned_action_item, Notification.event_type.in_(["item_completed", "item_reopened"]))
            .order_by(Notification.id.asc())
            .all()
        )
        assert [e[0] for e in events] == ["item_completed", "item_reopened"]

    def test_action_item_due_date_changed_notifies_owner(self, db_session, owned_action_item):
        update_action_item(db_session, _scope(), _REAL_PROJECT_ID, owned_action_item, MeetingActionItemUpdate(due_date="2026-09-01"))
        n = db_session.query(Notification).filter(Notification.entity_type == "action_item", Notification.entity_id == owned_action_item, Notification.event_type == "due_date_changed").first()
        assert n is not None
        assert "2026-09-01" in n.message

    def test_safety_event_closed_notifies_owner(self, db_session, owned_safety_event):
        update_safety_event(db_session, _scope(), _REAL_PROJECT_ID, owned_safety_event, SafetyEventUpdate(status="Closed", corrective_action="Fixed"))
        n = db_session.query(Notification).filter(Notification.entity_type == "safety_event", Notification.entity_id == owned_safety_event).first()
        assert n is not None
        assert n.event_type == "item_completed"

    def test_ncr_closed_notifies_owner(self, db_session, owned_ncr):
        update_ncr(db_session, _scope(), _REAL_PROJECT_ID, owned_ncr, NCRUpdate(status="Closed", corrective_action="Fixed"))
        n = db_session.query(Notification).filter(Notification.entity_type == "ncr", Notification.entity_id == owned_ncr).first()
        assert n is not None
        assert n.event_type == "item_completed"

    def test_status_change_by_owner_themselves_creates_no_notification(self, db_session, owned_risk):
        engineer_scope = _scope(user_id=_ENGINEER_USER_ID, role="site_engineer", membership_roles={_REAL_PROJECT_ID: "site_engineer"})
        update_project_risk(db_session, engineer_scope, _REAL_PROJECT_ID, owned_risk, ProjectRiskUpdate(status="mitigating"))
        assert db_session.query(Notification).filter(Notification.entity_type == "project_risk", Notification.entity_id == owned_risk).count() == 0

    def test_status_change_on_unowned_row_creates_no_notification(self, db_session, unowned_risk):
        update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, unowned_risk, ProjectRiskUpdate(status="mitigating"))
        assert db_session.query(Notification).filter(Notification.entity_type == "project_risk", Notification.entity_id == unowned_risk).count() == 0


class TestPurchaseRequestDecisionNotifications:
    def test_approved(self, db_session, owned_purchase_request):
        pr_id = owned_purchase_request("Under Review")
        update_purchase_request(db_session, _scope(), pr_id, PurchaseRequestUpdate(status="Approved"))
        n = db_session.query(Notification).filter(Notification.entity_type == "purchase_request", Notification.entity_id == pr_id).first()
        assert n is not None
        assert n.event_type == "purchase_request_approved"

    def test_rejected_requires_reason_and_notifies(self, db_session, owned_purchase_request):
        pr_id = owned_purchase_request("Under Review")
        update_purchase_request(db_session, _scope(), pr_id, PurchaseRequestUpdate(status="Rejected", rework_reason="Budget"))
        n = db_session.query(Notification).filter(Notification.entity_type == "purchase_request", Notification.entity_id == pr_id).first()
        assert n is not None
        assert n.event_type == "purchase_request_rejected"
        assert n.severity == "warning"

    def test_returned_to_requester(self, db_session, owned_purchase_request):
        pr_id = owned_purchase_request("Pending Clarification")
        update_purchase_request(db_session, _scope(), pr_id, PurchaseRequestUpdate(status="Returned to Requester", rework_reason="Missing spec"))
        n = db_session.query(Notification).filter(Notification.entity_type == "purchase_request", Notification.entity_id == pr_id).first()
        assert n is not None
        assert n.event_type == "purchase_request_returned"

    def test_non_decision_status_hop_is_not_notified(self, db_session, owned_purchase_request):
        pr_id = owned_purchase_request("Under Review")
        update_purchase_request(db_session, _scope(), pr_id, PurchaseRequestUpdate(status="Needs Rework"))
        assert db_session.query(Notification).filter(Notification.entity_type == "purchase_request", Notification.entity_id == pr_id).count() == 0


# ─────────────────────────────────────────────────────────────────────────
# Part F — Ownership consistency policy
# ─────────────────────────────────────────────────────────────────────────
class TestOwnershipConsistencyPolicy:
    def test_owner_text_patch_rejected_once_owner_id_is_set(self, db_session, owned_risk):
        with pytest.raises(HTTPException) as exc_info:
            update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, owned_risk, ProjectRiskUpdate(owner="Someone Else"))
        assert exc_info.value.status_code == 409

    def test_owner_text_patch_still_allowed_when_owner_id_is_null(self, db_session, unowned_risk):
        updated = update_project_risk(db_session, _scope(), _REAL_PROJECT_ID, unowned_risk, ProjectRiskUpdate(owner="Legacy Name"))
        assert updated.owner == "Legacy Name"


# ─────────────────────────────────────────────────────────────────────────
# Part D — Notifications API (HTTP)
# ─────────────────────────────────────────────────────────────────────────
class TestNotificationsApi:
    def test_list_unread_only_and_summary(self, client: TestClient, db_session, notif_batch):
        notif_batch(severity="info", event_type="status_changed", is_read=False)
        notif_batch(severity="warning", event_type="item_reopened", is_read=False)
        notif_batch(severity="info", event_type="assigned", is_read=True, read_at=datetime.now(timezone.utc))

        resp = client.get("/api/v1/notifications", params={"unread_only": True})
        assert resp.status_code == 200
        body = resp.json()
        assert all(not n["is_read"] for n in body)
        assert "deduplication_key" not in body[0]

        summary = client.get("/api/v1/notifications/summary")
        assert summary.status_code == 200
        s = summary.json()
        assert s["unread_count"] >= 2
        assert s["unread_by_severity"].get("info", 0) >= 1
        assert s["unread_by_severity"].get("warning", 0) >= 1

    def test_filter_by_event_type_and_severity(self, client: TestClient, db_session, notif_batch):
        notif_batch(event_type="due_date_changed", severity="critical")
        resp = client.get("/api/v1/notifications", params={"event_type": "due_date_changed", "severity": "critical"})
        assert resp.status_code == 200
        assert all(n["event_type"] == "due_date_changed" and n["severity"] == "critical" for n in resp.json())

    def test_pagination_headers(self, client: TestClient, db_session, notif_batch):
        for _ in range(3):
            notif_batch(event_type="status_changed")
        resp = client.get("/api/v1/notifications", params={"limit": 1, "skip": 0})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert int(resp.headers["X-Total-Count"]) >= 3

    def test_mark_read_and_read_all(self, client: TestClient, db_session, notif_batch):
        n1 = notif_batch(is_read=False)
        n2 = notif_batch(is_read=False)

        resp = client.patch(f"/api/v1/notifications/{n1.id}/read")
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

        resp_all = client.post("/api/v1/notifications/read-all")
        assert resp_all.status_code == 200
        assert resp_all.json()["updated_count"] >= 1

        db_session.refresh(n2)
        assert n2.is_read is True

    def test_mark_read_on_missing_notification_is_404(self, client: TestClient):
        resp = client.patch("/api/v1/notifications/999999999/read")
        assert resp.status_code == 404

    def test_isolation_by_recipient(self, client: TestClient, db_session, notif_batch):
        foreign = notif_batch(recipient_user_id=_ENGINEER_USER_ID)
        resp = client.get("/api/v1/notifications", params={"limit": 100})
        assert resp.status_code == 200
        assert all(n["id"] != foreign.id for n in resp.json())

        resp_read = client.patch(f"/api/v1/notifications/{foreign.id}/read")
        assert resp_read.status_code == 404

    def test_isolation_by_organization(self, client: TestClient, db_session):
        org = Organization(name="Notif Cross Org", slug=f"notif-cross-org-{datetime.now(timezone.utc).timestamp()}")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        foreign_org_notif = Notification(
            organization_id=org.id, recipient_user_id=_MANAGER_USER_ID, actor_user_id=_ENGINEER_USER_ID,
            project_id=None, event_type="status_changed", entity_type="project_risk", entity_id=999_999,
            title="Cross org", message="Should not be visible", severity="info",
        )
        db_session.add(foreign_org_notif)
        db_session.commit()
        db_session.refresh(foreign_org_notif)
        try:
            resp = client.get("/api/v1/notifications", params={"limit": 100})
            assert resp.status_code == 200
            assert all(n["id"] != foreign_org_notif.id for n in resp.json())
            resp_read = client.patch(f"/api/v1/notifications/{foreign_org_notif.id}/read")
            assert resp_read.status_code == 404
        finally:
            db_session.query(Notification).filter(Notification.id == foreign_org_notif.id).delete()
            db_session.query(Organization).filter(Organization.id == org.id).delete()
            db_session.commit()
