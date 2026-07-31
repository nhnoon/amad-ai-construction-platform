from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.sql import func

from ...config import settings
from ...core.deps import DbSession, RawCurrentUser, require_roles
from ...core.login_security import client_ip_from_request, login_ip_rate_limiter
from ...core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from ...models.auth import UserAccount
from ...schemas.auth import ChangePasswordRequest, UserRegister, UserLogin, UserOut, TokenResponse

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
    # Phase 1 production-hardening: a new user must always inherit the
    # creating admin's own organization — never client-supplied (there is
    # no organization_id field on UserRegister at all) and never left
    # unset. An admin with no organization of their own cannot create a
    # user, since there would be nothing correct to assign.
    if _admin.organization_id is None:
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
    user = UserAccount(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
        organization_id=_admin.organization_id,
        # Phase 2 — Security & Authentication Hardening: an admin choosing
        # this user's initial password is still a shared-secret handoff —
        # force a real, private password on first login, same as
        # POST /admin/users.
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: DbSession, request: Request):
    # Phase 2 — Security & Authentication Hardening.
    # Layer 1: per-IP sliding-window throttle, checked before any database
    # work — the cheapest possible check, so a flood can't even reach
    # credential verification.
    client_ip = client_ip_from_request(request)
    if not login_ip_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user = db.query(UserAccount).filter(UserAccount.email == body.email).first()

    # Layer 2: per-account lockout, DB-persisted so it survives restarts.
    # Checked — and rejected — before password verification, so a locked
    # account never leaks whether the supplied password would have been
    # correct, and continued hammering never extends the lockout window;
    # it always expires on its own after LOGIN_LOCKOUT_MINUTES.
    if user is not None and user.locked_until is not None and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed login attempts. Try again later.",
        )

    if not user or not verify_password(body.password, user.hashed_password):
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.LOGIN_LOCKOUT_MINUTES
                )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = func.now()
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: RawCurrentUser):
    # Deliberately uses the raw (un-gated) dependency, not CurrentUser —
    # a user who must change their password still needs to be able to
    # learn that fact (and their own identity) to reach the Change
    # Password screen at all.
    return current_user


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    body: ChangePasswordRequest,
    db: DbSession,
    current_user: RawCurrentUser,
):
    """Self-service password change (Phase 2 — Security & Authentication
    Hardening). Deliberately uses the raw dependency so this remains
    reachable precisely when must_change_password is true — it is the one
    and only escape hatch from that gate. Requires the current password
    (not just a valid session) so a hijacked/left-open session can't be
    used to lock the real owner out by itself. Clears must_change_password
    and any lockout state, and issues a fresh token so the client doesn't
    need a second login."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    current_user.hashed_password = hash_password(body.new_password)
    current_user.must_change_password = False
    current_user.failed_login_attempts = 0
    current_user.locked_until = None
    db.commit()
    db.refresh(current_user)
    token = create_access_token(subject=current_user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(current_user))
