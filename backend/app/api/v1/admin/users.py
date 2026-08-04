from fastapi import APIRouter, HTTPException, status

from ....core.audit_log import AuditAction, AuditEntityType, AuditResult, record_audit_event
from ....core.deps import CurrentScope, DbSession
from ....core.security import generate_temporary_password, hash_password
from ....models.auth import UserAccount
from ....schemas.admin import (
    AdminUserCreate,
    AdminUserCreateResponse,
    AdminUserUpdate,
    AdminUserOut,
    PasswordResetResponse,
)

router = APIRouter(prefix="/admin/users", tags=["admin"])

# NOTE (Phase 2 — Security & Authentication Hardening): every handler below
# is scoped to the calling admin's own organization. Before this fix, none
# of these routes took the caller's scope into account at all — an admin
# in one organization could list, view, edit, deactivate, or reset the
# password of a user in ANY organization platform-wide, purely by knowing
# or guessing a user id. That is the same class of cross-tenant bug Phase 1
# fixed for project-scoped resources; "admin" is an organization-scoped
# role in this app (see app/ai/scope.py) — there is no platform-level
# super-admin — so this endpoint family needed the identical treatment.
# 404 (not 403) for a user that exists in another organization, matching
# the standardized policy from Phase 1 (app/ai/scope.py::get_project_or_404):
# existence is never revealed across the tenant boundary.


def _get_user_or_404(db, scope, user_id: int) -> UserAccount:
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if user is None or user.organization_id != scope.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("", response_model=list[AdminUserOut])
def list_users(db: DbSession, scope: CurrentScope):
    return (
        db.query(UserAccount)
        .filter(UserAccount.organization_id == scope.organization_id)
        .order_by(UserAccount.created_at.desc())
        .all()
    )


@router.post("", response_model=AdminUserCreateResponse, status_code=201)
def create_user(body: AdminUserCreate, db: DbSession, scope: CurrentScope):
    # organization_id is never client-supplied — always the authenticated
    # admin's own organization, determined server-side (same rule Phase 1
    # applied to POST /auth/register and POST /projects).
    if scope.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account is not associated with an organization; cannot create a user.",
        )
    existing = db.query(UserAccount).filter(UserAccount.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    temporary_password = generate_temporary_password()
    user = UserAccount(
        email=body.email,
        hashed_password=hash_password(temporary_password),
        full_name=body.full_name,
        role=body.role,
        organization_id=scope.organization_id,
        is_active=True,
        # Phase 2 — Security & Authentication Hardening: every admin-created
        # account must set its own password on first login.
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_event(
        entity_type=AuditEntityType.USER_ACCOUNT, entity_id=user.id, action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS, organization_id=scope.organization_id, actor_user_id=scope.user_id,
        after_state={"email": user.email, "role": user.role},
    )
    return AdminUserCreateResponse(user=user, temporary_password=temporary_password)


@router.get("/{user_id}", response_model=AdminUserOut)
def get_user(user_id: int, db: DbSession, scope: CurrentScope):
    return _get_user_or_404(db, scope, user_id)


@router.patch("/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, body: AdminUserUpdate, db: DbSession, scope: CurrentScope):
    user = _get_user_or_404(db, scope, user_id)
    changes = body.model_dump(exclude_unset=True)
    before_state = {field: getattr(user, field) for field in changes if field != "organization_id"}
    was_active = user.is_active
    for field, value in changes.items():
        if field == "organization_id":
            # Never allow reassigning a user out of the admin's own
            # organization via this endpoint — same rule as creation.
            continue
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    # A distinct "user_disable" action for the specific is_active
    # True -> False transition (Sprint 4's explicit "User disable" entity
    # to audit); any other field change on the same generic PATCH
    # endpoint is still recorded, just tagged as the broader "user_update".
    action = (
        AuditAction.USER_DISABLE
        if was_active and changes.get("is_active") is False
        else AuditAction.USER_UPDATE
    )
    after_state = {field: getattr(user, field) for field in changes if field != "organization_id"}
    record_audit_event(
        entity_type=AuditEntityType.USER_ACCOUNT, entity_id=user.id, action=action, result=AuditResult.SUCCESS,
        organization_id=scope.organization_id, actor_user_id=scope.user_id,
        before_state=before_state, after_state=after_state,
    )
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_password(user_id: int, db: DbSession, scope: CurrentScope):
    user = _get_user_or_404(db, scope, user_id)
    temp_password = generate_temporary_password()
    user.hashed_password = hash_password(temp_password)
    # A reset password is also a temporary one — force a real change on
    # the next login, same as account creation.
    user.must_change_password = True
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return PasswordResetResponse(
        message=f"Password reset for {user.email}",
        temporary_password=temp_password,
    )
