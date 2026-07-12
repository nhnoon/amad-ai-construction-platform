"""Copilot Memory Layer service — bounded, per-user agent memory.

Two independent, bounded stores per user (see app/models/copilot_memory.py
for the full design rationale, inspired by Hermes Agent's USER.md/MEMORY.md
split):

  * user profile memory — durable preferences/working style
  * memory notes         — short derived notes accumulated over time

Both are bounded by a character limit (app/config.py
AI_USER_PROFILE_CHAR_LIMIT / AI_MEMORY_NOTE_CHAR_LIMIT) and guarded against
accidentally storing retrieved evidence/records — this layer is never a
substitute for PostgreSQL's domain tables, which remain the sole source of
truth for project data.

Not yet called from app/ai/pipeline.py or any retrieval module — wiring
these into prompt construction / evidence resolution is a deliberately
separate, future change. This module is infrastructure only.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.config import settings
from app.models.copilot_memory import AIMemoryNote, AIUserProfileMemory

# Defense-in-depth heuristic: reject writes that look like a raw evidence
# dump rather than a short derived note/preference. The real guarantee is
# architectural — nothing in retrieval/pipeline code calls these setters
# yet — but this catches an accidental future misuse early and loudly
# rather than silently duplicating source-of-truth records.
_EVIDENCE_MARKER_RE = re.compile(r"\bEVIDENCE:\s", re.IGNORECASE)
_ENTITY_CODE_RE = re.compile(r"\b(?:PRJ|PO|PR|MTG|NCR|SE|DEC|ACT)-[\w-]+\b")
_MAX_ENTITY_CODES = 5


class MemoryContentRejected(ValueError):
    """Raised when content looks like a raw evidence/record dump, not a note."""


def _guard_not_evidence_dump(content: str) -> None:
    if _EVIDENCE_MARKER_RE.search(content):
        raise MemoryContentRejected(
            "Refusing to store memory content containing an 'EVIDENCE:' block — "
            "this layer holds derived notes/preferences, not retrieved records."
        )
    codes = _ENTITY_CODE_RE.findall(content)
    if len(codes) > _MAX_ENTITY_CODES:
        raise MemoryContentRejected(
            f"Refusing to store memory content with {len(codes)} entity codes — "
            "looks like a copy of retrieved records rather than a derived note."
        )


def _truncate(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# User profile memory (Hermes USER.md analogue)
# ---------------------------------------------------------------------------

def get_user_profile_memory(db: Session, scope: AIAuthScope) -> str:
    """Return the caller's own bounded profile memory, or "" if unset."""
    row = (
        db.query(AIUserProfileMemory)
        .filter(AIUserProfileMemory.user_id == scope.user_id)
        .first()
    )
    return row.content if row else ""


def set_user_profile_memory(db: Session, scope: AIAuthScope, content: str) -> str:
    """Overwrite the caller's profile memory. Returns the stored (possibly
    truncated) value. Raises MemoryContentRejected for evidence-shaped input."""
    _guard_not_evidence_dump(content)
    limit = settings.AI_USER_PROFILE_CHAR_LIMIT
    bounded = _truncate(content.strip(), limit)

    row = (
        db.query(AIUserProfileMemory)
        .filter(AIUserProfileMemory.user_id == scope.user_id)
        .first()
    )
    if row is None:
        row = AIUserProfileMemory(
            user_id=scope.user_id,
            organization_id=scope.organization_id,
            content=bounded,
            char_limit=limit,
        )
        db.add(row)
    else:
        row.content = bounded
        row.char_limit = limit
        row.organization_id = scope.organization_id
    db.commit()
    return bounded


def clear_user_profile_memory(db: Session, scope: AIAuthScope) -> None:
    db.query(AIUserProfileMemory).filter(
        AIUserProfileMemory.user_id == scope.user_id
    ).delete()
    db.commit()


# ---------------------------------------------------------------------------
# Derived memory notes (Hermes MEMORY.md analogue)
# ---------------------------------------------------------------------------

def get_memory_notes(db: Session, scope: AIAuthScope) -> str:
    """Return the caller's own bounded memory notes, or "" if unset."""
    row = (
        db.query(AIMemoryNote)
        .filter(AIMemoryNote.user_id == scope.user_id)
        .first()
    )
    return row.content if row else ""


def _write_memory_notes(db: Session, scope: AIAuthScope, bounded_content: str) -> str:
    row = (
        db.query(AIMemoryNote)
        .filter(AIMemoryNote.user_id == scope.user_id)
        .first()
    )
    if row is None:
        row = AIMemoryNote(
            user_id=scope.user_id,
            organization_id=scope.organization_id,
            content=bounded_content,
            char_limit=settings.AI_MEMORY_NOTE_CHAR_LIMIT,
        )
        db.add(row)
    else:
        row.content = bounded_content
        row.char_limit = settings.AI_MEMORY_NOTE_CHAR_LIMIT
        row.organization_id = scope.organization_id
    db.commit()
    return bounded_content


def set_memory_notes(db: Session, scope: AIAuthScope, content: str) -> str:
    """Overwrite the full notes blob. Raises MemoryContentRejected for
    evidence-shaped input."""
    _guard_not_evidence_dump(content)
    limit = settings.AI_MEMORY_NOTE_CHAR_LIMIT
    bounded = _truncate(content.strip(), limit)
    return _write_memory_notes(db, scope, bounded)


def append_memory_note(db: Session, scope: AIAuthScope, note: str) -> str:
    """Append one short derived note, trimming the OLDEST lines first (FIFO)
    to stay within the character bound — mirrors how Hermes rewrites
    MEMORY.md within its limit rather than growing it without bound.

    Only the new note is checked against the evidence-dump guard (the
    accumulated history may legitimately exceed the guard's entity-code
    threshold over time without any single write being a records dump).
    """
    _guard_not_evidence_dump(note)
    note = note.strip()
    if not note:
        return get_memory_notes(db, scope)

    limit = settings.AI_MEMORY_NOTE_CHAR_LIMIT
    existing = get_memory_notes(db, scope)
    lines = [ln for ln in existing.splitlines() if ln.strip()]
    lines.append(note)

    joined = "\n".join(lines)
    while len(joined) > limit and len(lines) > 1:
        lines.pop(0)
        joined = "\n".join(lines)
    bounded = _truncate(joined, limit)

    return _write_memory_notes(db, scope, bounded)


def clear_memory_notes(db: Session, scope: AIAuthScope) -> None:
    db.query(AIMemoryNote).filter(
        AIMemoryNote.user_id == scope.user_id
    ).delete()
    db.commit()
