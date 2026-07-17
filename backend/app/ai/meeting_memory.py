"""Meeting Memory Writer — Phase 2 of the Copilot Memory Layer.

Converts one authorized, real meeting record into a single bounded memory
note (app/ai/memory.py's per-user blob) AND a structured AIMemoryRecord
(app/ai/memory_records.py) — never a direct write to either memory table.
Deterministic and database-backed only — no LLM/Hermes call anywhere in
this module.

Called automatically from app/api/v1/meetings.py whenever a meeting is
created or a decision/action item is added to one (see that router) — a
meeting's memory is only ever as complete as its record was at write time,
so this upserts (replaces its own prior note/record) rather than skipping
once written, keeping it current as decisions/action items are added.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.memory import _guard_not_evidence_dump, _write_memory_notes, append_memory_note, get_memory_notes
from app.config import settings as _settings
from app.ai.memory_records import record_memory
from app.ai.retrieval.meetings import get_meeting_detail
from app.ai.scope import AIAuthScope
from app.models.copilot_memory import AIMemoryNote, AIMemoryRecord
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
    upsert: bool = True,
) -> MeetingMemoryResult:
    """Convert one authorized meeting into a bounded memory note AND a
    structured AIMemoryRecord.

    Raises the same exceptions get_meeting_detail() would (404 if the
    meeting doesn't exist, 403 if the caller's scope can't access its
    project) — this function does not swallow authorization errors into a
    soft "skipped" result.

    upsert=True (default, and what every automatic call site uses):
    replaces this meeting's own prior note/record if one exists, since a
    meeting's decisions/action items are commonly added after its initial
    creation — a meeting recorded once and never refreshed would silently
    go stale the moment a decision is added, defeating the point of
    "persistent memory". upsert=False preserves the original skip-if-
    already-recorded behavior for callers that want a strict one-time
    write (e.g. a manual/administrative re-seed that must not clobber
    anything already written by normal traffic).
    """
    detail = get_meeting_detail(db, scope, meeting_id)
    data = detail.data
    meeting_code = f"MTG-{data['meeting_id']}"
    marker = f"[MEETING_MEMORY:{meeting_code}]"

    existing = get_memory_notes(db, scope)
    already_exists = marker in existing
    if already_exists and not upsert:
        return MeetingMemoryResult(
            created=False, meeting_code=meeting_code, reason="already_recorded"
        )

    project = db.query(Project).filter(Project.id == data["project_id"]).first()
    project_code = project.project_code if project else _NOT_RECORDED

    note = _build_meeting_note(data, meeting_code, marker, project_code)

    if already_exists:
        # Guard only the NEW note being written in, same discipline as
        # append_memory_note() — the accumulated blob (old lines PLUS this
        # one) legitimately exceeds the evidence-dump guard's entity-code
        # threshold over time as more meetings/reports accumulate; only a
        # single fresh note looking like a raw records dump should ever be
        # rejected. Calling set_memory_notes() here instead (which guards
        # the WHOLE blob on every write) was a real bug — it started
        # rejecting legitimate upserts once enough meetings had
        # accumulated distinct entity codes across their own notes.
        _guard_not_evidence_dump(note)
        remaining = "\n".join(
            ln for ln in existing.splitlines() if not ln.startswith(marker)
        )
        combined = (remaining + "\n" + note).strip() if remaining else note
        bounded = combined[: _settings.AI_MEMORY_NOTE_CHAR_LIMIT]
        _write_memory_notes(db, scope, bounded)
    else:
        append_memory_note(db, scope, note)

    # Structured record: same upsert semantics, keyed on citation+source
    # rather than a text marker, since AIMemoryRecord is a real table.
    db.query(AIMemoryRecord).filter(
        AIMemoryRecord.source == "meeting",
        AIMemoryRecord.citation == meeting_code,
        AIMemoryRecord.organization_id == scope.organization_id,
    ).delete()
    decisions = data.get("decisions") or []
    action_items = data.get("action_items") or []
    keywords = ["meeting", meeting_code, project_code] + [
        _short(d.get("decision_text"), 30) for d in decisions[:_MAX_ITEMS_PER_SECTION]
    ]
    record_memory(
        db, scope,
        source="meeting", category="meeting_summary",
        title=f"{meeting_code}: {data.get('meeting_title') or _NOT_RECORDED}",
        summary=note,
        keywords=[k for k in keywords if k],
        citation=meeting_code,
        project_id=data["project_id"],
    )

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
