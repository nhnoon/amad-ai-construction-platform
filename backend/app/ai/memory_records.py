"""Structured Memory Records — write + search service layer for AIMemoryRecord.

Distinct from app/ai/memory.py's two bounded per-user blobs (AIMemoryNote /
AIUserProfileMemory): this is the durable, cross-conversation, one-row-per-
memory knowledge store the ticket's MEMORY BEHAVIOR section describes —
"Every important AI interaction should be eligible to become memory"
(meeting summary, risk report, supplier analysis, site report, contract
analysis, executive summary, project milestone, OCR extraction, decision,
action item, important user conversation).

Write side: record_memory() — a single generic writer called by each
domain's own completion point (see app/ai/meeting_memory.py,
app/ai/site_report_intelligence.py, app/ai/contract_extraction.py for the
call sites). Deterministic, no LLM call.

Read side: search_memory_records() — RBAC-scoped (organization + project,
matching the isolation axis dataset retrieval already uses — see
app/ai/scope.py) deterministic keyword/entity-code ranking, reusing the
exact scoring approach already proven in app/ai/memory_reader.py
(select_relevant_memory) rather than inventing a second algorithm.
"""
from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ai.memory_reader import _entity_codes, _keywords
from app.ai.scope import AIAuthScope
from app.models.copilot_memory import AIMemoryRecord

_MAX_TITLE_CHARS = 255
_MAX_SUMMARY_CHARS = 1000
_MAX_KEYWORDS_CHARS = 300
_DEFAULT_SEARCH_LIMIT = 5

_STOPWORDS_FOR_TITLE = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "in",
    "on", "at", "and", "or", "has", "have", "had", "this", "that",
})

# Defense-in-depth only — same spirit as app/ai/memory.py's
# _guard_not_evidence_dump, but for the free-form "remember X" path
# specifically: a user could type a password/API key/token by mistake and
# have it durably persisted. Not a security boundary (nothing stops a
# determined user from obfuscating a secret), just a guard against the
# common accidental case.
_SECRET_LOOKING_RE = re.compile(
    r"\b(password|passwd|api[_\s]?key|secret|token|credential)s?\s*[:=]\s*\S+",
    re.IGNORECASE,
)


class MemoryCommandRejected(ValueError):
    """Raised when a "remember X" directive's content looks like a secret/
    credential rather than a note worth persisting."""


# Product UX Phase 1 — Memory Center categories a user can pick explicitly
# when creating a memory from the new structured form (as opposed to the
# free-form "remember that..." chat path, which always writes category=
# "user_note"). Kept as a fixed, validated set rather than a free string so
# the Memory Center's category filter stays meaningful — see the frontend's
# memoryTaxonomy.ts, which maps these (plus the automatic writers' own
# source/category pairs) onto the 8 display buckets the UX ticket asks for
# (Project/Meeting/Decision/Risk/Contract/Supplier/Site Report/Personal
# Notes).
USER_MEMORY_CATEGORIES = frozenset({
    "project_note", "meeting_note", "decision_note", "risk_note",
    "contract_note", "supplier_note", "site_report_note", "personal_note",
})

# Deterministic, reproducible priority — NOT a stored column (the ticket
# for this phase explicitly disallows a PostgreSQL schema change), so it's
# computed the same way every time a record is serialized, from fields
# that already exist: which category a user explicitly picked (risk/
# decision notes default higher), and how much the writer itself trusts
# the record. Never randomized, never fabricated per-item.
_HIGH_PRIORITY_CATEGORIES = frozenset({"risk_note", "decision_note"})
_MEDIUM_PRIORITY_CATEGORIES = frozenset({
    "contract_note", "contract_extraction", "meeting_note", "meeting_summary",
    "site_report_note", "supplier_note", "project_note",
})


def derive_priority(source: str, category: str, confidence: int) -> str:
    """High/Medium/Low — see module docstring above for why this is
    computed rather than stored."""
    if category in _HIGH_PRIORITY_CATEGORIES:
        return "High"
    if category in _MEDIUM_PRIORITY_CATEGORIES or source in {"meeting", "site_report", "contract", "supplier"}:
        return "High" if confidence >= 90 else "Medium"
    return "Medium" if confidence >= 80 else "Low"


def record_user_memory(
    db: Session,
    scope: AIAuthScope,
    *,
    content: str,
    project_code: Optional[str] = None,
) -> tuple[AIMemoryRecord, bool]:
    """Persist a user-directed "remember/save/store" directive as a
    structured memory. Returns (record, created) — created=False means an
    identical memory already existed for this org/project and the
    existing row was returned instead of creating a duplicate (AMAD AI
    Stabilization Part B §10.C: repeated identical commands must not
    create duplicates)."""
    if _SECRET_LOOKING_RE.search(content):
        raise MemoryCommandRejected(
            "This looks like it might contain a password, API key, or other "
            "credential — refusing to store it in memory."
        )

    project_id: Optional[int] = None
    if project_code:
        from app.models.projects import Project
        project = db.query(Project).filter(Project.project_code == project_code).first()
        if project is not None:
            scope.enforce_project_access(project.id)
            project_id = project.id

    normalized = " ".join(content.strip().lower().split())
    existing_q = db.query(AIMemoryRecord).filter(
        AIMemoryRecord.source == "user",
        AIMemoryRecord.user_id == scope.user_id,
    )
    if project_id is not None:
        existing_q = existing_q.filter(AIMemoryRecord.project_id == project_id)
    else:
        existing_q = existing_q.filter(AIMemoryRecord.project_id.is_(None))
    for existing in existing_q.all():
        if " ".join(existing.summary.strip().lower().split()) == normalized:
            return existing, False

    # Entity codes (PRJ-001, MTG-1, ...) are matched as whole tokens first
    # so a code never gets truncated at its own hyphen by the plain-word
    # pattern below.
    entity_tokens = re.findall(r"\b(?:PRJ|PO|PR|MTG|NCR|SE|DEC|ACT)-\w+\b", content, re.IGNORECASE)
    plain_words = [
        w for w in re.findall(r"[A-Za-z؀-ۿ]{3,}", content)
        if w.lower() not in _STOPWORDS_FOR_TITLE
    ]
    ordered_words = entity_tokens + [w for w in plain_words if w not in entity_tokens]
    title = " ".join(ordered_words[:8]) or content[:60]
    keywords = list(dict.fromkeys(ordered_words[:10]))
    if project_code and project_code not in keywords:
        keywords.append(project_code)

    record = record_memory(
        db, scope,
        source="user", category="user_note",
        title=title, summary=content,
        keywords=keywords, citation=project_code,
        confidence=100, project_id=project_id,
    )
    return record, True


def record_memory(
    db: Session,
    scope: AIAuthScope,
    *,
    source: str,
    category: str,
    title: str,
    summary: str,
    keywords: list[str],
    citation: Optional[str] = None,
    confidence: int = 100,
    project_id: Optional[int] = None,
) -> AIMemoryRecord:
    """Write one structured memory record. Never fabricates content — the
    caller is responsible for passing only confirmed fields (same
    discipline as app/ai/meeting_memory.py's note builder). Confidence is
    the writer's own trust in the record (100 for deterministic writers
    reading confirmed DB fields), not a database record's own field."""
    row = AIMemoryRecord(
        user_id=scope.user_id,
        organization_id=scope.organization_id,
        project_id=project_id,
        source=source,
        category=category,
        title=(title or "").strip()[:_MAX_TITLE_CHARS] or "Untitled",
        summary=(summary or "").strip()[:_MAX_SUMMARY_CHARS],
        keywords=", ".join(keywords)[:_MAX_KEYWORDS_CHARS],
        confidence=max(0, min(100, confidence)),
        citation=citation,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def search_memory_records(
    db: Session,
    scope: AIAuthScope,
    question: str,
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = _DEFAULT_SEARCH_LIMIT,
) -> list[AIMemoryRecord]:
    """RBAC-scoped, deterministic keyword/entity-code search over
    structured memory records — same ranking approach as
    memory_reader.py's select_relevant_memory(), applied to title+summary+
    keywords instead of note-blob lines, and to a real, filterable table
    instead of one accumulated per-user string.

    Organization isolation: only records belonging to the caller's own
    organization (or with no organization at all — e.g. records written
    before an org was attached) are ever returned. Project isolation:
    when project_id is given, scope.enforce_project_access() gate applies
    before querying; when not given, only records visible to the caller's
    accessible projects (or org-wide/project-less records) are considered.
    """
    if project_id is not None:
        scope.enforce_project_access(project_id)

    q = db.query(AIMemoryRecord)

    # Organization isolation — mirrors AIAuthScope.enforce_organization_access:
    # never bypassed by has_global_read, since org membership is a separate
    # axis from project-level read privilege.
    if scope.organization_id is not None:
        q = q.filter(
            or_(
                AIMemoryRecord.organization_id == scope.organization_id,
                AIMemoryRecord.organization_id.is_(None),
            )
        )
    else:
        q = q.filter(AIMemoryRecord.organization_id.is_(None))

    if project_id is not None:
        q = q.filter(
            or_(AIMemoryRecord.project_id == project_id, AIMemoryRecord.project_id.is_(None))
        )
    elif not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        conditions = [AIMemoryRecord.project_id.is_(None)]
        if ids:
            conditions.append(AIMemoryRecord.project_id.in_(ids))
        q = q.filter(or_(*conditions))

    if category is not None:
        q = q.filter(AIMemoryRecord.category == category)

    # Bounded candidate pool (most recent first) — real ranking happens in
    # Python below, same as select_relevant_memory(), so this cap just
    # keeps the DB scan itself bounded rather than loading the whole table.
    candidates = q.order_by(AIMemoryRecord.created_at.desc()).limit(200).all()
    if not candidates:
        return []

    question_codes = _entity_codes(question)
    question_keywords = _keywords(question)

    scored: list[tuple[int, int, AIMemoryRecord]] = []
    for idx, rec in enumerate(candidates):
        searchable = f"{rec.title} {rec.summary} {rec.keywords} {rec.citation or ''}"
        code_matches = len(question_codes & _entity_codes(searchable))
        keyword_matches = len(question_keywords & _keywords(searchable))
        if code_matches == 0 and keyword_matches == 0:
            continue
        priority = code_matches * 1000 + keyword_matches
        scored.append((priority, idx, rec))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [rec for _, _, rec in scored[:limit]]


def list_memory_records_for_scope(
    db: Session, scope: AIAuthScope, limit: int = 100,
) -> list[AIMemoryRecord]:
    """All structured memory records visible to this scope, most recent
    first — unranked (unlike search_memory_records, which ranks against a
    specific question). Powers the Memory Viewer UI's full listing, not
    the per-turn Hermes-prompt injection."""
    q = db.query(AIMemoryRecord)
    if scope.organization_id is not None:
        q = q.filter(
            or_(AIMemoryRecord.organization_id == scope.organization_id, AIMemoryRecord.organization_id.is_(None))
        )
    else:
        q = q.filter(AIMemoryRecord.organization_id.is_(None))

    if not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        conditions = [AIMemoryRecord.project_id.is_(None)]
        if ids:
            conditions.append(AIMemoryRecord.project_id.in_(ids))
        q = q.filter(or_(*conditions))

    return q.order_by(AIMemoryRecord.created_at.desc()).limit(limit).all()


def delete_memory_record(db: Session, scope: AIAuthScope, record_id: int) -> None:
    """Delete one structured memory record.

    404 if the record doesn't exist or isn't visible to this scope
    (organization/project isolation — same convention as
    get_authorized_document). 403 if it IS visible but the caller is
    neither its owner nor a global-read role — "user-created memory can
    be deleted by its owner/admin" (AMAD AI Stabilization Part B §9)."""
    from fastapi import HTTPException, status as http_status

    visible_ids = {r.id for r in list_memory_records_for_scope(db, scope, limit=10_000)}
    if record_id not in visible_ids:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Memory record not found")
    record = db.query(AIMemoryRecord).filter(AIMemoryRecord.id == record_id).first()
    is_owner = record.user_id is not None and record.user_id == scope.user_id
    if not (is_owner or scope.has_global_read):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this memory")
    db.delete(record)
    db.commit()


def create_user_memory(
    db: Session,
    scope: AIAuthScope,
    *,
    title: str,
    summary: str,
    category: str,
    project_code: Optional[str] = None,
) -> AIMemoryRecord:
    """Create one structured memory directly from the Memory Center's "Add
    Memory" form — the structured-UI counterpart to record_user_memory()
    (which parses a free-form "remember that..." chat command). Same
    secret guard, same project resolution; no dedup check here, unlike
    record_user_memory(), because an explicit form submission is an
    intentional distinct entry, not a possibly-repeated chat command."""
    if _SECRET_LOOKING_RE.search(summary) or _SECRET_LOOKING_RE.search(title):
        raise MemoryCommandRejected(
            "This looks like it might contain a password, API key, or other "
            "credential — refusing to store it in memory."
        )
    if category not in USER_MEMORY_CATEGORIES:
        raise ValueError(f"Unknown memory category: {category}")

    project_id: Optional[int] = None
    if project_code:
        from app.models.projects import Project
        project = db.query(Project).filter(Project.project_code == project_code).first()
        if project is not None:
            scope.enforce_project_access(project.id)
            project_id = project.id

    keywords = [w for w in re.findall(r"[A-Za-z؀-ۿ]{3,}", f"{title} {summary}") if w.lower() not in _STOPWORDS_FOR_TITLE][:10]
    if project_code and project_code not in keywords:
        keywords.append(project_code)

    return record_memory(
        db, scope,
        source="user", category=category,
        title=title, summary=summary,
        keywords=keywords, citation=project_code,
        confidence=100, project_id=project_id,
    )


def update_memory_record(
    db: Session,
    scope: AIAuthScope,
    record_id: int,
    *,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    category: Optional[str] = None,
) -> AIMemoryRecord:
    """Edit an existing structured memory's editable fields. Same
    visibility/ownership rule as delete_memory_record — only a record's
    owner (or a global-read role) may edit it. Source, project, and
    citation are not editable here (re-scoping a memory to a different
    project is a delete+recreate, not an edit)."""
    from fastapi import HTTPException, status as http_status

    visible_ids = {r.id for r in list_memory_records_for_scope(db, scope, limit=10_000)}
    if record_id not in visible_ids:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Memory record not found")
    record = db.query(AIMemoryRecord).filter(AIMemoryRecord.id == record_id).first()
    is_owner = record.user_id is not None and record.user_id == scope.user_id
    if not (is_owner or scope.has_global_read):
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this memory")

    if title is not None:
        cleaned_title = title.strip()
        if _SECRET_LOOKING_RE.search(cleaned_title):
            raise MemoryCommandRejected("This looks like it might contain a credential — refusing to save it.")
        record.title = cleaned_title[:_MAX_TITLE_CHARS] or "Untitled"
    if summary is not None:
        cleaned_summary = summary.strip()
        if _SECRET_LOOKING_RE.search(cleaned_summary):
            raise MemoryCommandRejected("This looks like it might contain a credential — refusing to save it.")
        record.summary = cleaned_summary[:_MAX_SUMMARY_CHARS]
    if category is not None:
        if record.source == "user" and category not in USER_MEMORY_CATEGORIES:
            raise ValueError(f"Unknown memory category: {category}")
        record.category = category

    db.commit()
    db.refresh(record)
    return record


def build_memory_record_block(records: list[AIMemoryRecord], is_arabic: bool = False) -> str:
    """Format matched structured memory records as a clearly-labelled,
    non-authoritative prompt block — distinct from both live EVIDENCE and
    the note-blob MEMORY CONTEXT block, so the model can tell current
    database facts, historical memory, and missing information apart (per
    the ticket's PROMPT CONSTRUCTION requirement)."""
    if not records:
        return ""
    header_en = (
        "HISTORICAL MEMORY — PRIOR AI ANALYSIS, NOT CURRENT DATABASE FACTS:\n"
        "- These are summaries of past AI interactions, not live records.\n"
        "- Current EVIDENCE above always overrides memory if they conflict.\n"
        "- You may cite memory using its own code (shown in brackets), but\n"
        "  never present it as a live database source."
    )
    header_ar = (
        "الذاكرة التاريخية — تحليل سابق للذكاء الاصطناعي، وليست حقائق حالية من قاعدة البيانات:\n"
        "- هذه ملخصات لتفاعلات سابقة، وليست سجلات حية.\n"
        "- الأدلة الحالية أعلاه لها الأولوية دائماً عند وجود تعارض.\n"
        "- يمكن الاستشهاد بالذاكرة برمزها الخاص، لكن لا يجوز تقديمها كمصدر حي من قاعدة البيانات."
    )
    header = header_ar if is_arabic else header_en
    lines = []
    for rec in records:
        code = rec.citation or f"MEM-{rec.id}"
        lines.append(f"- [{code}] ({rec.category}, {rec.created_at.date() if rec.created_at else 'undated'}) {rec.title}: {rec.summary}")
    return f"{header}\n" + "\n".join(lines)
