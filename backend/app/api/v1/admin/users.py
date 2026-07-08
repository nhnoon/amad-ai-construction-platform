import secrets
from fastapi import APIRouter, HTTPException, status

from ....core.deps import DbSession
from ....core.security import hash_password
from ....models.auth import UserAccount
from ....schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserOut,
    PasswordResetResponse,
)

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("", response_model=list[AdminUserOut])
def list_users(db: DbSession):
    return db.query(UserAccount).order_by(UserAccount.created_at.desc()).all()


@router.post("", response_model=AdminUserOut, status_code=201)
def create_user(body: AdminUserCreate, db: DbSession):
    existing = db.query(UserAccount).filter(UserAccount.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = UserAccount(
        email=body.email,
        hashed_password=hash_password(body.temporary_password),
        full_name=body.full_name,
        role=body.role,
        organization_id=body.organization_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=AdminUserOut)
def get_user(user_id: int, db: DbSession):
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, body: AdminUserUpdate, db: DbSession):
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_password(user_id: int, db: DbSession):
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    temp_password = secrets.token_urlsafe(10)
    user.hashed_password = hash_password(temp_password)
    db.commit()
    return PasswordResetResponse(
        message=f"Password reset for {user.email}",
        temporary_password=temp_password,
    )
