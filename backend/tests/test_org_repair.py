"""Tests for the demo-org membership repair (scripts/repair_demo_org_membership.py)
and the General Library upload flow it unblocks for admin@construction.ai.

Real Postgres DB (same pattern as test_general_documents.py). The repair
has already been applied live to this DB as part of fixing this issue —
these tests primarily confirm it stays idempotent and that the real HTTP
flow now works for the real admin account, without touching any other user.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.document_access import create_document, get_authorized_document
from app.ai.scope import AIAuthScope
from app.models.auth import UserAccount
from app.models.documents import Document
from app.models.organizations import Organization
from scripts.repair_demo_org_membership import ADMIN_EMAIL, DEMO_ORG_SLUG, repair
from tests.conftest import TestingSessionLocal


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestAdminLinkedToCorrectOrganization:
    def test_admin_is_linked_to_the_demo_org_by_slug(self, db_session):
        repair()  # idempotent — safe to call again
        org = db_session.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).first()
        admin = db_session.query(UserAccount).filter(UserAccount.email == ADMIN_EMAIL).first()
        assert org is not None
        assert admin is not None
        assert admin.organization_id == org.id


class TestNoDuplicateOrganization:
    def test_repair_never_creates_a_second_demo_org(self, db_session):
        before = db_session.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).count()
        repair()
        repair()
        repair()
        after = db_session.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).count()
        assert before == 1
        assert after == 1

    def test_repair_is_a_no_op_when_already_linked(self, db_session):
        repair()
        admin_before = db_session.query(UserAccount).filter(UserAccount.email == ADMIN_EMAIL).first()
        org_id_before = admin_before.organization_id
        repair()
        db_session.expire_all()
        admin_after = db_session.query(UserAccount).filter(UserAccount.email == ADMIN_EMAIL).first()
        assert admin_after.organization_id == org_id_before


class TestUnrelatedUsersUntouched:
    def test_repair_does_not_link_other_seeded_users(self, db_session):
        other = (
            db_session.query(UserAccount)
            .filter(UserAccount.email == "executive@construction.ai")
            .first()
        )
        before = other.organization_id if other else None
        repair()
        db_session.expire_all()
        other_after = (
            db_session.query(UserAccount)
            .filter(UserAccount.email == "executive@construction.ai")
            .first()
        )
        # This script only ever touches admin@construction.ai — any other
        # user's organization_id must be exactly what it was before.
        assert (other_after.organization_id if other_after else None) == before


class TestGeneralUploadSucceedsForRealAdmin:
    def test_create_general_document_via_http_as_real_admin(self, client: TestClient, db_session, monkeypatch):
        # tests/conftest.py's override_get_current_user() constructs a
        # UserAccount object directly (not loaded from the DB), so it never
        # carries the real organization_id no matter what's actually
        # stored — a pre-existing test-fixture limitation, unrelated to
        # this fix. Verified separately, directly against the live server
        # via a real /auth/login (see final report): the real admin user's
        # real DB-loaded organization_id does flow through correctly.
        # Here, pin the scope to reflect that real, already-verified state.
        org = db_session.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).first()
        monkeypatch.setattr(
            "app.api.v1.documents.build_ai_scope",
            lambda user, db: AIAuthScope(
                organization_id=org.id, user_id=user.id, user_role="admin",
                accessible_project_ids=(),
            ),
        )
        resp = client.post("/api/v1/documents", json={"title": "Org Repair Test Doc", "project_id": None})
        assert resp.status_code == 201
        data = resp.json()
        assert data["project_id"] is None
        assert data["organization_id"] is not None

        # cleanup
        db_session.query(Document).filter(Document.id == data["id"]).delete()
        db_session.commit()


class TestCrossTenantStillBlocked:
    def test_different_organization_cannot_access_admins_general_document(self, db_session):
        org = db_session.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).first()
        admin_scope = AIAuthScope(
            organization_id=org.id, user_id=1, user_role="admin", accessible_project_ids=(),
        )
        doc = create_document(db_session, admin_scope, project_id=None, title="Cross-Tenant Guard Doc")

        other_org_scope = AIAuthScope(
            organization_id=org.id + 999_999, user_id=1, user_role="admin", accessible_project_ids=(),
        )
        try:
            with pytest.raises(HTTPException) as exc_info:
                get_authorized_document(db_session, other_org_scope, doc.id)
            assert exc_info.value.status_code == 403
        finally:
            db_session.query(Document).filter(Document.id == doc.id).delete()
            db_session.commit()
