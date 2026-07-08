import re
import secrets
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

from .auth import VALID_ROLES

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AdminUserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str = "site_engineer"
    organization_id: Optional[int] = None
    temporary_password: str = "Welcome123!"

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}")
        return v

    @field_validator("temporary_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    organization_id: Optional[int] = None

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}")
        return v


class AdminUserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    organization_id: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PasswordResetResponse(BaseModel):
    message: str
    temporary_password: str


class ProjectMembershipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    role_on_project: str = "viewer"

    @field_validator("role_on_project")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}")
        return v


class ProjectMembershipUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_on_project: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectMembershipOut(BaseModel):
    id: int
    user_id: int
    project_id: int
    role_on_project: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
