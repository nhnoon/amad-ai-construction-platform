from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.security import decode_access_token
from ..models.auth import UserAccount
from ..ai.scope import AIAuthScope, build_ai_scope

DbSession = Annotated[Session, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> UserAccount:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


RawCurrentUser = Annotated[UserAccount, Depends(get_current_user)]
"""Identity only — does NOT enforce the must-change-password gate below.
Only /auth/me and /auth/change-password should depend on this directly;
every other route should keep using CurrentUser/CurrentScope as before."""


def get_current_user_password_changed(current_user: RawCurrentUser) -> UserAccount:
    """Phase 2 — Security & Authentication Hardening: the gate almost
    every protected route goes through via the CurrentUser alias below. A
    user who still must change their initial/reset password is blocked
    here with a distinct, machine-checkable detail so the frontend can
    redirect to the Change Password screen rather than showing a generic
    error. Centralizing this in the CurrentUser alias means every existing
    router that already depends on CurrentUser/CurrentScope is covered
    with no changes to those routers; a belt-and-suspenders app-wide check
    also runs in app/core/password_gate_middleware.py for the few routes
    that don't declare CurrentUser/CurrentScope at all (e.g. the
    deliberately unscoped supplier/subcontractor catalog endpoints)."""
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="password_change_required",
        )
    return current_user


CurrentUser = Annotated[UserAccount, Depends(get_current_user_password_changed)]


def get_current_scope(current_user: CurrentUser, db: Session = Depends(get_db)) -> AIAuthScope:
    """Phase 1 production-hardening — the one dependency every core CRUD
    router should use to get an organization/project-authorized scope for
    the current request, instead of hand-rolling `build_ai_scope(user, db)`
    at the top of every handler. Reuses the exact same scope object the AI
    retrieval layer already relies on (app/ai/scope.py) — there is only one
    definition of "what can this user see" in the whole app, not a second
    one for non-AI routes."""
    return build_ai_scope(current_user, db)


CurrentScope = Annotated[AIAuthScope, Depends(get_current_scope)]


def require_roles(*roles: str):
    def role_checker(
        current_user: Annotated[UserAccount, Depends(get_current_user)],
    ) -> UserAccount:
        if current_user.role == "admin":
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}",
            )
        return current_user

    return Depends(role_checker)
