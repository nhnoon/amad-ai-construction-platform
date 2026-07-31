"""AI Authorization Scope — builds a permission context before any retrieval.

Rules:
- inactive users are denied
- cross-organization access is impossible
- admin/executive/project_manager have global read access WITHIN THEIR OWN
  ORGANIZATION (not, as before Phase 1 production-hardening, platform-wide
  across every organization — see build_ai_scope())
- other roles are limited to their project memberships
- authorization is applied in backend retrieval code; the LLM never filters data

Phase 1 production-hardening note: ``has_global_read`` used to make
``can_access_project()``/``filter_project_ids()`` bypass the organization
boundary entirely for admin/executive/project_manager — the exact
cross-tenant gap an independent audit flagged. The fix lives entirely in
``build_ai_scope()``: for a global-read user, ``accessible_project_ids`` is
now pre-populated with every project in *their own organization* (a single
extra query at scope-build time), instead of being left empty and bypassed.
``can_access_project()``/``filter_project_ids()`` themselves no longer special-
case ``has_global_read`` at all — every caller of ``enforce_project_access``/
``can_access_project`` across the AI retrieval layer (dozens of call sites)
is fixed automatically, with no change needed at any of those call sites.
``has_global_read`` remains available as a role-level signal for the few
places that use it for something other than project-list scoping (e.g. "may
this user edit/delete a memory record they don't own").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import UserAccount
from app.models.organizations import ProjectMembership
from app.models.projects import Project

_GLOBAL_READ_ROLES = frozenset({"admin", "executive", "project_manager"})


@dataclass(frozen=True)
class AIAuthScope:
    organization_id: Optional[int]
    user_id: int
    user_role: str
    accessible_project_ids: tuple[int, ...]
    project_membership_roles: dict[int, str] = field(default_factory=dict)

    @property
    def has_global_read(self) -> bool:
        return self.user_role in _GLOBAL_READ_ROLES

    def can_access_project(self, project_id: int) -> bool:
        return project_id in self.accessible_project_ids

    def enforce_project_access(self, project_id: int) -> None:
        """Raise 403 if the scope does not allow access to ``project_id``."""
        if not self.can_access_project(project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )

    def enforce_organization_access(self, organization_id: Optional[int]) -> None:
        """Raise 403 unless ``organization_id`` matches the caller's own
        organization. Used for organization-scoped resources that have no
        project (e.g. General Library documents) — deliberately does NOT
        grant global-read roles a cross-organization bypass; project-level
        global read and organization membership are separate axes."""
        if organization_id is None or self.organization_id is None or organization_id != self.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document",
            )

    def filter_project_ids(self, project_ids: list[int]) -> list[int]:
        """Return only those project IDs the scope is allowed to see."""
        allowed = set(self.accessible_project_ids)
        return [pid for pid in project_ids if pid in allowed]


def build_ai_scope(user: UserAccount, db: Session) -> AIAuthScope:
    """Build the AI auth scope for a given authenticated user.

    Raises 403 for inactive users.

    ``accessible_project_ids`` is the single source of truth every retrieval
    call site filters by:
      - global-read roles (admin/executive/project_manager) get every
        project belonging to their OWN organization, plus any explicit
        membership they hold (e.g. on a project in another org, if that was
        ever deliberately granted) — never every project platform-wide.
      - a global-read user with no organization at all gets only their
        explicit memberships (no silent fallback to platform-wide data).
      - all other roles get exactly their active project memberships, as
        before.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    memberships = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.user_id == user.id,
            ProjectMembership.is_active.is_(True),
        )
        .all()
    )
    member_project_ids = {m.project_id for m in memberships}
    roles = {m.project_id: m.role_on_project for m in memberships}

    if user.role in _GLOBAL_READ_ROLES and user.organization_id is not None:
        org_project_ids = {
            pid for (pid,) in (
                db.query(Project.id)
                .filter(Project.organization_id == user.organization_id)
                .all()
            )
        }
        accessible_ids = tuple(org_project_ids | member_project_ids)
    else:
        accessible_ids = tuple(member_project_ids)

    return AIAuthScope(
        organization_id=user.organization_id,
        user_id=user.id,
        user_role=user.role,
        accessible_project_ids=accessible_ids,
        project_membership_roles=roles,
    )


def get_project_or_404(db: Session, scope: AIAuthScope, project_id: int) -> Project:
    """Fetch a project applying one consistent existence/tenant/permission
    ordering (Phase 1 production-hardening — previously some routes checked
    ``enforce_project_access`` before confirming the project even existed,
    which meant a nonexistent ID returned 403 in some places and 404 in
    others, an inconsistent IDOR policy):

    - project does not exist                                -> 404
    - project exists in another organization                 -> 404 (existence hidden)
    - project exists in the caller's own organization,
      but the caller lacks permission (e.g. no membership)    -> 403
    - authorized, same-organization access                    -> the row

    Never checks scope before existence in a way that would let a caller
    distinguish "doesn't exist" from "exists in another organization" via
    the status code.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None or project.organization_id != scope.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not scope.can_access_project(project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )
    return project
