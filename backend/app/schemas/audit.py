from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    event_id: UUID
    # Named `timestamp` on the wire per the Sprint 4 spec's field list,
    # even though the underlying column is `created_at` (this codebase's
    # consistent name for every other table's row-creation timestamp) —
    # see app/api/v1/audit.py, which maps the two explicitly rather than
    # via attribute-name auto-mapping.
    timestamp: datetime

    organization_id: Optional[int] = None
    actor_user_id: Optional[int] = None
    # Convenience join (app/api/v1/audit.py), not a column on AuditLog
    # itself — lets a human read a result list without a second lookup.
    actor_email: Optional[str] = None
    project_id: Optional[int] = None

    entity_type: str
    entity_id: Optional[int] = None
    action: str
    result: str

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None

    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    reason: Optional[str] = None
