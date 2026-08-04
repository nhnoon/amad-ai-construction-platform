from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.sql import func

from ...config import settings
from ...core.audit_log import AuditAction, AuditEntityType, AuditResult, record_audit_event
from ...core.deps import DbSession, RawCurrentUser, require_roles
from ...core.login_security import client_ip_from_request, login_ip_rate_limiter
from ...core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from ...core.session_security import (
    RefreshOutcome,
    create_session,
    get_active_sessions,
    revoke_all_for_user,
    revoke_token,
    rotate_refresh_token,
)
from ...models.auth import UserAccount
from ...schemas.auth import (
    ChangePasswordRequest,
    LoginResponse,
    LogoutAllResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    SessionOut,
    UserRegister,
    UserLogin,
    UserOut,
    TokenResponse,
)

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


@router.post("/login", response_model=LoginResponse)
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
        record_audit_event(
            entity_type=AuditEntityType.USER_ACCOUNT, entity_id=user.id, action=AuditAction.LOGIN,
            result=AuditResult.DENIED, organization_id=user.organization_id, actor_user_id=user.id,
            reason="account_locked",
        )
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
        record_audit_event(
            entity_type=AuditEntityType.USER_ACCOUNT, entity_id=user.id if user else None,
            action=AuditAction.LOGIN, result=AuditResult.FAILURE,
            organization_id=user.organization_id if user else None, actor_user_id=user.id if user else None,
            reason="incorrect_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        record_audit_event(
            entity_type=AuditEntityType.USER_ACCOUNT, entity_id=user.id, action=AuditAction.LOGIN,
            result=AuditResult.DENIED, organization_id=user.organization_id, actor_user_id=user.id,
            reason="account_disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = func.now()
    db.commit()
    db.refresh(user)
    access_token = create_access_token(subject=user.email)
    # RC1 Phase 1 Sprint 1 — Identity & Session Security: every login
    # starts a brand-new session (refresh-token family), independent of
    # any other sessions the user already has open elsewhere — concurrent
    # devices are first-class, not something that requires special-casing.
    refresh_token, _session = create_session(
        db, user, request, remember_me=body.remember_me, device=body.device,
    )
    record_audit_event(
        entity_type=AuditEntityType.USER_ACCOUNT, entity_id=user.id, action=AuditAction.LOGIN,
        result=AuditResult.SUCCESS, organization_id=user.organization_id, actor_user_id=user.id,
        project_id=None,
    )
    return LoginResponse(
        access_token=access_token, refresh_token=refresh_token, user=UserOut.model_validate(user),
    )


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
        record_audit_event(
            entity_type=AuditEntityType.USER_ACCOUNT, entity_id=current_user.id,
            action=AuditAction.PASSWORD_CHANGE, result=AuditResult.FAILURE,
            organization_id=current_user.organization_id, actor_user_id=current_user.id,
            reason="incorrect_current_password",
        )
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
    record_audit_event(
        entity_type=AuditEntityType.USER_ACCOUNT, entity_id=current_user.id,
        action=AuditAction.PASSWORD_CHANGE, result=AuditResult.SUCCESS,
        organization_id=current_user.organization_id, actor_user_id=current_user.id,
    )
    return TokenResponse(access_token=token, user=UserOut.model_validate(current_user))


@router.post("/refresh", response_model=LoginResponse)
def refresh(body: RefreshRequest, db: DbSession, request: Request):
    """RC1 Phase 1 Sprint 1 — Identity & Session Security. Rotates the
    presented refresh token: the old one is revoked and a new one is
    issued in the same session (family), alongside a fresh short-lived
    access token. See app/core/session_security.py::rotate_refresh_token
    for reuse detection — a token presented a second time (already
    rotated or already logged out) revokes its whole session instead of
    silently failing, since that pattern only happens on replay/theft."""
    result = rotate_refresh_token(db, body.refresh_token, request, device=body.device)
    if result.outcome == RefreshOutcome.REUSED:
        actor_id = result.row.user_id if result.row else None
        record_audit_event(
            entity_type=AuditEntityType.SESSION, entity_id=result.row.id if result.row else None,
            action=AuditAction.REFRESH, result=AuditResult.DENIED, actor_user_id=actor_id,
            reason="refresh_token_reused",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used; session revoked. Please log in again.",
        )
    if result.outcome in (RefreshOutcome.INVALID, RefreshOutcome.EXPIRED):
        actor_id = result.row.user_id if result.row else None
        record_audit_event(
            entity_type=AuditEntityType.SESSION, entity_id=result.row.id if result.row else None,
            action=AuditAction.REFRESH, result=AuditResult.FAILURE, actor_user_id=actor_id,
            reason=result.outcome.value,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    access_token = create_access_token(subject=result.user.email)
    record_audit_event(
        entity_type=AuditEntityType.SESSION, entity_id=result.row.id if result.row else None,
        action=AuditAction.REFRESH, result=AuditResult.SUCCESS,
        organization_id=result.user.organization_id, actor_user_id=result.user.id,
    )
    return LoginResponse(
        access_token=access_token, refresh_token=result.raw_token, user=UserOut.model_validate(result.user),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(body: LogoutRequest, db: DbSession):
    """Revokes the session (refresh-token family) the presented token
    belongs to — independent logout per device, since each login/refresh
    chain has its own family. Deliberately does not require a valid
    access token: possessing the refresh token is itself sufficient proof
    of the session being logged out, and the response is identical
    whether the token was live, already revoked, or never existed, so
    this endpoint never becomes an oracle for refresh-token validity."""
    revoked_user_id = revoke_token(db, body.refresh_token)
    # Idempotent by design (see docstring above) — audit both outcomes,
    # since "someone tried to log out with an unknown/already-dead
    # token" is itself worth a record, just with no identifiable actor.
    record_audit_event(
        entity_type=AuditEntityType.SESSION, action=AuditAction.LOGOUT,
        result=AuditResult.SUCCESS if revoked_user_id else AuditResult.FAILURE,
        actor_user_id=revoked_user_id,
    )
    return LogoutResponse(message="Logged out")


@router.post("/logout-all", response_model=LogoutAllResponse)
def logout_all(db: DbSession, current_user: RawCurrentUser):
    """Revokes every live session for the authenticated caller across all
    devices. Always scoped to the caller's own identity (current_user.id)
    — there is no parameter for a target user, so this can never be used
    for cross-user session control, admin or otherwise."""
    count = revoke_all_for_user(db, current_user.id)
    record_audit_event(
        entity_type=AuditEntityType.SESSION, action=AuditAction.LOGOUT_ALL, result=AuditResult.SUCCESS,
        organization_id=current_user.organization_id, actor_user_id=current_user.id,
        after_state={"revoked_count": count},
    )
    return LogoutAllResponse(message="All sessions revoked", revoked_count=count)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: DbSession, current_user: RawCurrentUser):
    """Lists the authenticated caller's own active sessions only — same
    strict self-scoping as logout-all above. No admin or cross-user
    variant exists in this sprint."""
    return get_active_sessions(db, current_user.id)
