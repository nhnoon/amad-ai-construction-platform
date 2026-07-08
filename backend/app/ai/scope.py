"""AI Authorization Scope — builds a permission context before any retrieval.

Rules:
- inactive users are denied
- cross-organization access is impossible
- admin/executive have global read access
- project_manager has global read access
- other roles are limited to their project memberships
- authorization is applied in backend retrieval code; the LLM never filters data
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import UserAccount
from app.models.organizations import ProjectMembership

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
        if self.has_global_read:
            return True
        return project_id in self.accessible_project_ids

    def enforce_project_access(self, project_id: int) -> None:
        """Raise 403 if the scope does not allow access to ``project_id``."""
        if not self.can_access_project(project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )

    def filter_project_ids(self, project_ids: list[int]) -> list[int]:
        """Return only those project IDs the scope is allowed to see."""
        if self.has_global_read:
            return project_ids
        allowed = set(self.accessible_project_ids)
        return [pid for pid in project_ids if pid in allowed]


def build_ai_scope(user: UserAccount, db: Session) -> AIAuthScope:
    """Build the AI auth scope for a given authenticated user.

    Raises 403 for inactive users.
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

    accessible_ids = tuple(m.project_id for m in memberships)
    roles = {m.project_id: m.role_on_project for m in memberships}

    return AIAuthScope(
        organization_id=user.organization_id,
        user_id=user.id,
        user_role=user.role,
        accessible_project_ids=accessible_ids,
        project_membership_roles=roles,
    )
