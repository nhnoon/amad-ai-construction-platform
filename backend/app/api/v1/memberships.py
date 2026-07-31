from fastapi import APIRouter, HTTPException, status

from ...ai.scope import get_project_or_404
from ...core.deps import CurrentScope, DbSession
from ...models.organizations import ProjectMembership
from ...models.auth import UserAccount
from ...schemas.admin import ProjectMembershipCreate, ProjectMembershipOut

router = APIRouter(prefix="/projects/{project_id}/memberships", tags=["memberships"])


@router.get("", response_model=list[ProjectMembershipOut])
def list_memberships(project_id: int, db: DbSession, scope: CurrentScope):
    get_project_or_404(db, scope, project_id)
    return (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id)
        .order_by(ProjectMembership.created_at.desc())
        .all()
    )


@router.post("", response_model=ProjectMembershipOut, status_code=201)
def add_membership(project_id: int, body: ProjectMembershipCreate, db: DbSession, scope: CurrentScope):
    get_project_or_404(db, scope, project_id)
    user = db.query(UserAccount).filter(UserAccount.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = db.query(ProjectMembership).filter(
        ProjectMembership.user_id == body.user_id,
        ProjectMembership.project_id == project_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this project",
        )
    membership = ProjectMembership(
        user_id=body.user_id,
        project_id=project_id,
        role_on_project=body.role_on_project,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{user_id}", status_code=204)
def remove_membership(project_id: int, user_id: int, db: DbSession, scope: CurrentScope):
    get_project_or_404(db, scope, project_id)
    membership = db.query(ProjectMembership).filter(
        ProjectMembership.user_id == user_id,
        ProjectMembership.project_id == project_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    db.delete(membership)
    db.commit()
