"""Memory-command detector — user-directed "remember/save/store" directives.

Distinct from app/ai/memory_reader.py's is_memory_relevant(), which detects
whether a question is ASKING about historical memory (a READ signal).
This module detects the opposite: is the user TELLING the assistant to
create a new memory (a WRITE directive)?

Must run before context resolution / clarification / intent routing (see
app/ai/pipeline.py) — a save directive like "Remember that Project
PRJ-001..." previously fell into is_anaphoric()'s "that project" pattern
and was misrouted to clarification before it ever had a chance to be
recognized as a command. See app/ai/context_resolver.py for the
complementary fix (an explicit entity code in the same sentence also
suppresses that specific false positive generally, not just for memory
commands).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_PROJECT_CODE_RE = re.compile(r"\b(PRJ-\d+)\b", re.IGNORECASE)

# English triggers: remember/save this/store this/keep this (for later)/
# don't forget — each optionally followed by "that"/"to" and an optional
# colon/dash before the actual content.
_MEMORY_SAVE_EN_RE = re.compile(
    r"^\s*(?:please\s+)?"
    r"(?:remember(?:\s+that|\s+to)?"
    r"|save\s+this(?:\s+(?:info|information|note))?"
    r"|store\s+this(?:\s+(?:info|information|note))?"
    r"|keep\s+this(?:\s+for\s+later|\s+in\s+mind)?"
    r"|don'?t\s+forget(?:\s+that|\s+to)?"
    r"|do\s+not\s+forget(?:\s+that|\s+to)?"
    r")\s*[:\-]?\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Arabic triggers, per the ticket's own examples: تذكر أن.../احفظ هذه
# المعلومة.../خزّن هذا.../لا تنسَ.../احتفظ بهذا لاحقًا... — kept literal to
# these documented phrasings rather than attempting full morphological
# coverage of every conjugation.
_MEMORY_SAVE_AR_RE = re.compile(
    r"^\s*"
    r"(?:تذكر(?:\s+أن)?"
    r"|احفظ(?:\s+هذه\s+المعلومة|\s+هذا)?"
    r"|خزّن\s+هذا|خزن\s+هذا"
    r"|لا\s+تنس[ىَ]?"
    r"|احتفظ\s+بهذا(?:\s+لاحقًا|\s+لاحقا)?"
    r")\s*[:\-]?\s*(.+)$",
    re.DOTALL,
)


@dataclass
class MemoryCommand:
    content: str
    project_code: Optional[str]
    is_arabic: bool


def detect_memory_command(question: str) -> Optional[MemoryCommand]:
    """Return a MemoryCommand if `question` is a save/remember directive,
    else None. Deterministic — no LLM call."""
    text = (question or "").strip()
    if not text:
        return None

    m = _MEMORY_SAVE_EN_RE.match(text)
    is_arabic = False
    if m is None:
        m = _MEMORY_SAVE_AR_RE.match(text)
        is_arabic = m is not None
    if m is None:
        return None

    content = m.group(1).strip()
    if not content:
        return None

    code_match = _PROJECT_CODE_RE.search(content)
    project_code = code_match.group(1).upper() if code_match else None

    return MemoryCommand(content=content, project_code=project_code, is_arabic=is_arabic)


def _strip_project_lead_in(content: str, project_code: str) -> str:
    """Cosmetic only, never affects what's actually stored — "Project
    PRJ-001 has a crane inspection..." reads better as just "crane
    inspection..." once the confirmation already says "for PRJ-001:"."""
    patterns = [
        rf"^\s*project\s+{re.escape(project_code)}\s+has\s+(?:a\s+|an\s+)?",
        rf"^\s*project\s+{re.escape(project_code)}\s*[:\-,]?\s*",
        rf"^\s*مشروع\s+{re.escape(project_code)}\s*(?:لديه|فيه)?\s*",
    ]
    for pat in patterns:
        stripped = re.sub(pat, "", content, count=1, flags=re.IGNORECASE)
        if stripped != content:
            return stripped
    return content


_MAX_CONFIRMATION_PREVIEW_CHARS = 200


def build_confirmation_message(cmd: MemoryCommand) -> str:
    """Deterministic confirmation — never a Hermes call just to confirm a
    save (see AMAD AI Stabilization Part B §4)."""
    content = cmd.content.rstrip(". ").strip()
    if cmd.project_code:
        content = _strip_project_lead_in(content, cmd.project_code)
    if len(content) > _MAX_CONFIRMATION_PREVIEW_CHARS:
        content = content[: _MAX_CONFIRMATION_PREVIEW_CHARS - 1].rstrip() + "…"

    if cmd.is_arabic:
        if cmd.project_code:
            return f"تم الحفظ في ذاكرة المشروع لـ {cmd.project_code}: {content}."
        return f"تم الحفظ في الذاكرة: {content}."

    if cmd.project_code:
        return f"Saved to Project Memory for {cmd.project_code}: {content}."
    return f"Saved to memory: {content}."
