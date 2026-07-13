"""Meeting Memory Writer — Phase 2 of the Copilot Memory Layer.

Converts one authorized, real meeting record into a single bounded memory
note and appends it via the existing app/ai/memory.py service (never a
direct write to the memory tables). Deterministic and database-backed only
— no LLM/Hermes call is made anywhere in this module.

Not wired into app/ai/pipeline.py, the Copilot API, or retrieval routing.
Calling write_meeting_memory() is the only way this code runs; nothing
calls it automatically yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.memory import append_memory_note, get_memory_notes
from app.ai.retrieval.meetings import get_meeting_detail
from app.ai.scope import AIAuthScope
from app.models.copilot_memory import AIMemoryNote
from app.models.projects import Project

_NOT_RECORDED = "not recorded"
_MAX_ITEMS_PER_SECTION = 3
_FIELD_CHARS = 60
_MAX_NOTE_CHARS = 500


@dataclass
class MeetingMemoryResult:
    created: bool
    meeting_code: str
    memory_note_id: Optional[int] = None
    reason: Optional[str] = None


def _short(text: Optional[str], limit: int = _FIELD_CHARS) -> str:
    text = (text or "").strip()
    if not text:
        return _NOT_RECORDED
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _dedupe(values: list[str]) -> list[str]:
    seen: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.append(v)
    return seen


def _build_meeting_note(
    data: dict,
    meeting_code: str,
    marker: str,
    project_code: str,
) -> str:
    """Build a compact, single-line note from confirmed fields only.

    Single-line by design: app/ai/memory.py's append_memory_note() trims the
    OLDEST *line* first when the bounded blob overflows, so a note with
    embedded newlines would have its own internal lines individually
    trimmed on a later append instead of being dropped as one unit.
    """
    meeting_date = data.get("meeting_date") or _NOT_RECORDED
    # No dedicated summary field on the Meeting record — the confirmed
    # title IS the short summary; never fabricate one.
    short_summary = _short(data.get("meeting_title"))

    decisions = data.get("decisions") or []
    action_items = data.get("action_items") or []

    decision_texts = [_short(d.get("decision_text")) for d in decisions[:_MAX_ITEMS_PER_SECTION]]
    action_texts = [
        f"{_short(a.get('description'), 40)} (owner: {_short(a.get('owner'), 30)}, "
        f"due: {a.get('due_date') or _NOT_RECORDED})"
        for a in action_items[:_MAX_ITEMS_PER_SECTION]
    ]

    owners = _dedupe(
        [d.get("owner") for d in decisions] + [a.get("owner") for a in action_items]
    )[:_MAX_ITEMS_PER_SECTION]
    due_dates = _dedupe([a.get("due_date") for a in action_items])[:_MAX_ITEMS_PER_SECTION]

    unresolved = [
        _short(a.get("description"), 40)
        for a in action_items
        if (a.get("status") or "").lower() == "open"
    ][:_MAX_ITEMS_PER_SECTION]

    parts = [
        marker,
        meeting_code,
        meeting_date,
        project_code,
        short_summary,
        "Decisions: " + ("; ".join(decision_texts) if decision_texts else "None recorded"),
        "Action items: " + ("; ".join(action_texts) if action_texts else "None recorded"),
        "Owners: " + (", ".join(owners) if owners else _NOT_RECORDED),
        "Due dates: " + (", ".join(due_dates) if due_dates else _NOT_RECORDED),
        "Unresolved: " + ("; ".join(unresolved) if unresolved else "None recorded"),
    ]
    note = " | ".join(parts)
    if len(note) > _MAX_NOTE_CHARS:
        note = note[: _MAX_NOTE_CHARS - 1].rstrip() + "…"
    return note


def write_meeting_memory(
    db: Session,
    scope: AIAuthScope,
    meeting_id: int,
) -> MeetingMemoryResult:
    """Convert one authorized meeting into a bounded memory note.

    Raises the same exceptions get_meeting_detail() would (404 if the
    meeting doesn't exist, 403 if the caller's scope can't access its
    project) — this function does not swallow authorization errors into a
    soft "skipped" result. Returns created=False with a reason only for
    the legitimate no-op case: the meeting was already recorded.
    """
    detail = get_meeting_detail(db, scope, meeting_id)
    data = detail.data
    meeting_code = f"MTG-{data['meeting_id']}"
    marker = f"[MEETING_MEMORY:{meeting_code}]"

    existing = get_memory_notes(db, scope)
    if marker in existing:
        return MeetingMemoryResult(
            created=False, meeting_code=meeting_code, reason="already_recorded"
        )

    project = db.query(Project).filter(Project.id == data["project_id"]).first()
    project_code = project.project_code if project else _NOT_RECORDED

    note = _build_meeting_note(data, meeting_code, marker, project_code)
    append_memory_note(db, scope, note)

    row = (
        db.query(AIMemoryNote)
        .filter(AIMemoryNote.user_id == scope.user_id)
        .first()
    )
    return MeetingMemoryResult(
        created=True,
        meeting_code=meeting_code,
        memory_note_id=row.id if row else None,
    )
