import re
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

VALID_ROLES = {
    "admin",
    "executive",
    "project_manager",
    "site_engineer",
    "procurement_officer",
    "safety_quality_officer",
    "viewer",
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegister(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "site_engineer"

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}")
        return v


class UserLogin(BaseModel):
    email: str
    password: str
    # RC1 Phase 1 Sprint 1 — Identity & Session Security. Both optional
    # and additive: existing clients that omit them get today's behavior
    # (short sliding refresh window, no device label recorded).
    remember_me: bool = False
    device: Optional[str] = None

    @field_validator("email")
    @classmethod
    def email_lower(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    organization_id: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginResponse(TokenResponse):
    """RC1 Phase 1 Sprint 1 — used by POST /auth/login and POST
    /auth/refresh, both of which mint a new refresh token alongside the
    access token. Deliberately NOT used by POST /auth/change-password
    (still plain TokenResponse, unchanged) — that endpoint issues a fresh
    access token but does not start or rotate a session. Subclassing
    TokenResponse keeps this purely additive: existing clients reading
    only access_token/token_type/user from the login response are
    unaffected by the new field."""

    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str
    device: Optional[str] = None


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str


class LogoutAllResponse(BaseModel):
    message: str
    revoked_count: int


class SessionOut(BaseModel):
    id: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    device: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    remember_me: bool = False

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
