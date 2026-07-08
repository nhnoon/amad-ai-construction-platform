"""Shared evidence and retrieval result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Evidence:
    source_type: str
    source_id: str
    label: str
    snippet: str
    project_id: Optional[int] = None
    ui_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    data: dict[str, Any]
    evidence: list[Evidence]
    retrieved_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def has_data(self) -> bool:
        return bool(self.data) and bool(self.evidence)
