"""Conversation state — bounded structured context for multi-turn conversations.

State is persisted as JSONB in ai_conversations.conversation_state and
re-loaded at the start of each pipeline execution.  It is always scoped to
a single (organization_id, user_id) pair and is never shared across users.

Design constraints:
- The state object must be JSON-serialisable (no ORM objects, no sets).
- State is updated AFTER a successful pipeline execution, not before.
- Entity IDs stored here are re-authorised against the live DB scope before
  any retrieval so stale IDs cannot bypass RBAC.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

_MAX_EVIDENCE_IDS = 20
_MAX_PROJECT_IDS = 10
_STATE_VERSION = 2


@dataclass
class ConversationState:
    """Structured conversation state persisted between turns."""

    version: int = _STATE_VERSION
    turn_count: int = 0

    # Domains / intents
    previous_intent: Optional[str] = None
    previous_domain: Optional[str] = None
    domains_used_history: list[str] = field(default_factory=list)

    # Entity references from previous evidence
    active_project_ids: list[int] = field(default_factory=list)
    referenced_project_ids: list[int] = field(default_factory=list)
    referenced_supplier_ids: list[int] = field(default_factory=list)

    # Filters / time range carried from previous turn
    active_filters: dict[str, Any] = field(default_factory=dict)
    time_range: Optional[dict[str, Any]] = None

    # Snippet of evidence IDs (source_id strings like "PRJ-0001")
    last_evidence_ids: list[str] = field(default_factory=list)

    # Short summary of the last answer (used for context injection)
    last_answer_summary: Optional[str] = None

    # Misc
    last_turn_clarification_required: bool = False

    # ------------------------------------------------------------------ #
    # Serialisation helpers                                                #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "ConversationState":
        if not data:
            return cls()
        # Be tolerant of missing keys from older versions
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    # ------------------------------------------------------------------ #
    # State update                                                         #
    # ------------------------------------------------------------------ #

    def apply_turn(
        self,
        intent: str,
        evidence_ids: list[str],
        project_ids: list[int],
        supplier_ids: list[int],
        answer_summary: str,
        clarification_required: bool = False,
    ) -> None:
        """Update state after a completed pipeline turn."""
        self.turn_count += 1
        self.previous_intent = intent
        self.previous_domain = intent

        # Keep bounded lists
        self.last_evidence_ids = evidence_ids[:_MAX_EVIDENCE_IDS]
        self.active_project_ids = project_ids[:_MAX_PROJECT_IDS]
        self.referenced_project_ids = list(
            dict.fromkeys(self.referenced_project_ids + project_ids)
        )[:_MAX_PROJECT_IDS]

        # Supplier references
        self.referenced_supplier_ids = list(
            dict.fromkeys(self.referenced_supplier_ids + supplier_ids)
        )[:_MAX_PROJECT_IDS]

        # Accumulate domain history (bounded)
        if intent and intent != "unknown":
            self.domains_used_history = (self.domains_used_history + [intent])[-10:]

        self.last_answer_summary = answer_summary[:300] if answer_summary else None
        self.last_turn_clarification_required = clarification_required

    def has_context(self) -> bool:
        """Return True if this state has meaningful prior context."""
        return (
            self.previous_intent is not None
            or bool(self.active_project_ids)
            or bool(self.last_evidence_ids)
        )


def extract_project_ids_from_evidence(evidence_ids: list[str]) -> list[int]:
    """Extract integer project IDs from evidence source_ids like 'PRJ-0001'.

    Used to populate active_project_ids in state so follow-up queries can
    filter to the same project set.
    """
    ids: list[int] = []
    for eid in evidence_ids:
        # Handle "PRJ-0001" → 1, or just bare integers
        if eid.upper().startswith("PRJ-"):
            try:
                ids.append(int(eid[4:]))
            except ValueError:
                pass
        elif eid.isdigit():
            ids.append(int(eid))
    return ids
