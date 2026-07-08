from typing import Annotated
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.sql import func

from ...core.deps import DbSession, CurrentUser, require_roles
from ...core.security import hash_password, verify_password, create_access_token
from ...models.auth import UserAccount
from ...schemas.auth import UserRegister, UserLogin, UserOut, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Admin-only guard — public registration is intentionally disabled.
# New users must be created by an admin via POST /api/v1/admin/users.
# This endpoint is retained for programmatic admin use and test compatibility.
_admin_required = require_roles("admin")


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="Admin-only: register a new user",
    description=(
        "Creates a new user account. **Requires admin role.** "
        "Public self-registration is disabled by design — this is a B2B platform "
        "where user accounts are provisioned by an administrator. "
        "Prefer POST /admin/users for the admin management UI."
    ),
)
def register(
    body: UserRegister,
    db: DbSession,
    _admin: Annotated[UserAccount, _admin_required],
):
    existing = db.query(UserAccount).filter(UserAccount.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = UserAccount(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: DbSession):
    user = db.query(UserAccount).filter(UserAccount.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    user.last_login = func.now()
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: CurrentUser):
    return current_user
