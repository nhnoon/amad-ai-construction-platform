from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError("Slug must be lowercase letters, numbers, and hyphens only")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not _SLUG_RE.match(v):
                raise ValueError("Slug must be lowercase letters, numbers, and hyphens only")
        return v


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
