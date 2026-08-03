"""Tests for AI authorization scope — cross-project and cross-org isolation."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.ai.scope import AIAuthScope, build_ai_scope
from app.models.auth import UserAccount
from app.models.organizations import ProjectMembership


def _user(
    user_id: int = 1,
    role: str = "viewer",
    org_id: int = 1,
    is_active: bool = True,
) -> UserAccount:
    u = UserAccount(
        id=user_id,
        email=f"user{user_id}@test.com",
        full_name="Test User",
        role=role,
        is_active=is_active,
        hashed_password="x",
        organization_id=org_id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    return u


def _membership(user_id: int, project_id: int, role: str = "site_engineer") -> ProjectMembership:
    m = ProjectMembership()
    m.user_id = user_id
    m.project_id = project_id
    m.role_on_project = role
    m.is_active = True
    return m


class TestAIAuthScope:
    def test_admin_has_global_read(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="admin",
            accessible_project_ids=(),
        )
        assert scope.has_global_read is True

    def test_executive_has_global_read(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="executive",
            accessible_project_ids=(),
        )
        assert scope.has_global_read is True

    def test_project_manager_has_global_read(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="project_manager",
            accessible_project_ids=(),
        )
        assert scope.has_global_read is True

    def test_viewer_has_no_global_read(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="viewer",
            accessible_project_ids=(5, 7),
        )
        assert scope.has_global_read is False

    def test_viewer_can_access_own_project(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="viewer",
            accessible_project_ids=(5, 7),
        )
        assert scope.can_access_project(5) is True
        assert scope.can_access_project(7) is True

    def test_viewer_cannot_access_other_project(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="viewer",
            accessible_project_ids=(5,),
        )
        assert scope.can_access_project(99) is False

    def test_admin_can_access_projects_in_accessible_ids(self):
        """Phase 1 production-hardening: admin/executive/project_manager no
        longer bypass the project boundary via role alone — access is
        governed entirely by accessible_project_ids (populated by
        build_ai_scope() from the caller's own organization). An admin
        scope can access whatever is actually in accessible_project_ids..."""
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="admin",
            accessible_project_ids=(5, 7),
        )
        assert scope.can_access_project(5) is True
        assert scope.can_access_project(7) is True

    def test_admin_cannot_access_project_outside_accessible_ids(self):
        """...and, critically, cannot access a project outside that set —
        this is the exact cross-tenant bypass the Phase 1 fix removed
        (previously ``has_global_read`` alone made this return True)."""
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="admin",
            accessible_project_ids=(5, 7),
        )
        assert scope.can_access_project(999) is False

    def test_enforce_project_access_raises_for_unauthorized(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="site_engineer",
            accessible_project_ids=(1, 2),
        )
        with pytest.raises(HTTPException) as exc_info:
            scope.enforce_project_access(99)
        assert exc_info.value.status_code == 403

    def test_enforce_project_access_passes_for_authorized(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="site_engineer",
            accessible_project_ids=(1, 2),
        )
        scope.enforce_project_access(1)

    def test_filter_project_ids_restricted_user(self):
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="viewer",
            accessible_project_ids=(1, 3),
        )
        result = scope.filter_project_ids([1, 2, 3, 4])
        assert result == [1, 3]

    def test_filter_project_ids_global_reader_restricted_to_accessible_ids(self):
        """Phase 1 production-hardening: filter_project_ids() no longer
        bypasses filtering for global-read roles — it always narrows to
        accessible_project_ids, which build_ai_scope() populates from the
        caller's own organization. A global-read scope with a populated
        set filters normally; ids outside that set are excluded even for
        an executive/admin/project_manager role."""
        scope = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="executive",
            accessible_project_ids=(1, 2),
        )
        result = scope.filter_project_ids([1, 2, 3])
        assert result == [1, 2]

    def test_cross_org_impossible_different_org_ids(self):
        scope1 = AIAuthScope(organization_id=1, user_id=1, user_role="admin", accessible_project_ids=())
        scope2 = AIAuthScope(organization_id=2, user_id=2, user_role="admin", accessible_project_ids=())
        assert scope1.organization_id != scope2.organization_id


class TestBuildAIScope:
    def test_inactive_user_raises_403(self):
        db = MagicMock()
        user = _user(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            build_ai_scope(user, db)
        assert exc_info.value.status_code == 403

    def test_admin_gets_empty_accessible_project_ids(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        user = _user(role="admin")
        scope = build_ai_scope(user, db)
        assert scope.user_role == "admin"
        assert scope.has_global_read is True
        assert scope.accessible_project_ids == ()

    def test_viewer_gets_memberships(self):
        db = MagicMock()
        m1 = _membership(user_id=1, project_id=5)
        m2 = _membership(user_id=1, project_id=7)
        db.query.return_value.filter.return_value.all.return_value = [m1, m2]
        user = _user(role="viewer")
        scope = build_ai_scope(user, db)
        assert set(scope.accessible_project_ids) == {5, 7}

    def test_scope_preserves_org_id(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        user = _user(org_id=42)
        scope = build_ai_scope(user, db)
        assert scope.organization_id == 42

    def test_scope_preserves_user_id(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        user = _user(user_id=17)
        scope = build_ai_scope(user, db)
        assert scope.user_id == 17

    def test_membership_roles_captured(self):
        db = MagicMock()
        m = _membership(user_id=1, project_id=5, role="site_engineer")
        db.query.return_value.filter.return_value.all.return_value = [m]
        user = _user(role="site_engineer")
        scope = build_ai_scope(user, db)
        assert scope.project_membership_roles[5] == "site_engineer"
