"""Deterministic intent router — identifies query domain before LLM generation.

Rules:
- Routing uses explicit keyword matching, not the LLM.
- Intent is chosen by the highest-confidence keyword match.
- Short abbreviations ("po", "pr") use word-boundary matching to avoid
  false positives inside other words (e.g. "reports" contains "r" but not "\\bpr\\b").
- Unknown/unsupported intents are flagged explicitly.
- executive_summary is a special multi-domain intent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


_INTENT_KEYWORDS: dict[str, list[str]] = {
    "project_overview": [
        "project", "projects", "status", "overview", "summary", "active",
        "delayed", "budget", "client", "مشروع", "مشاريع", "حالة",
    ],
    "procurement": [
        "procurement", "purchase order", "purchase request",
        "delivery", "material", "مشتريات", "المشتريات", "طلب شراء", "أمر شراء",
        "أوامر الشراء", "طلبات الشراء", "أوامر متأخرة", "الشراء المتأخر",
        "مورد", "موردين",
    ],
    "suppliers": [
        "supplier", "suppliers", "vendor", "vendors", "مورد", "موردين",
    ],
    "safety": [
        "safety", "incident", "accident", "hazard", "سلامة", "حادث",
    ],
    "ncr": [
        "ncr", "non-conformance", "non conformance", "quality", "defect",
        "عدم مطابقة", "جودة",
    ],
    "site_reports": [
        "site report", "site reports", "daily report", "manpower", "activity",
        "تقرير موقع", "تقرير يومي", "نشاط",
    ],
    "meetings": [
        "meeting", "meetings", "اجتماع", "اجتماعات",
    ],
    "decisions": [
        "decision", "decisions", "قرار", "قرارات",
    ],
    "risks": [
        "risk", "risks", "issue", "issues", "riskiest", "most risky",
        "highest risk", "most at risk", "مخاطر", "مشكلة", "أكثر خطورة",
    ],
    "executive_summary": [
        "executive summary", "management attention", "operational risk",
        "key findings", "top issues", "critical areas", "what should i know",
        "what should management", "what should we focus", "what should we know",
        "summarize", "summarise", "prioritize", "prioritise", "recommend",
        "where to focus", "what to focus", "top priority", "most urgent",
        "ملخص تنفيذي", "ملخصاً تنفيذياً", "ملخصا تنفيذيا", "ملخص",
        "ما يجب أن يعرفه", "ما يجب معرفته", "ما الذي ينبغي",
    ],
    "health": [
        "health score", "health scores", "health level", "project health",
        "unhealthy", "least healthy", "lowest health", "worst health",
        "critical projects", "at risk projects", "at-risk projects",
        "poor health", "healthiest", "most healthy", "best health",
        "highest health", "best performing", "performing best",
        "top performing", "most successful",
        "درجة الصحة", "صحة المشروع", "مشاريع حرجة", "أفضل أداء",
    ],
    "documents": [
        "document", "documents", "contract", "contracts", "ocr", "scanned",
        "attachment", "attachments", "file", "files", "extracted text",
        "وثيقة", "وثائق", "مستند", "مستندات", "عقد", "عقود", "ملف",
    ],
    "alerts": [
        "alert", "alerts", "warning", "warnings", "flagged", "flag",
        "تنبيه", "تنبيهات", "إنذار",
    ],
    "action_items": [
        "action item", "action items", "open items", "outstanding items",
        "follow-up", "follow up", "follow-ups", "overdue task", "overdue tasks",
        "مهمة متابعة", "مهام متابعة", "إجراءات متابعة",
    ],
}

_PROJECT_CODE_PATTERN = re.compile(r"\b(PRJ-\d+)\b", re.IGNORECASE)
_PROJECT_ID_PATTERN = re.compile(r"\bproject\s+(\d+)\b", re.IGNORECASE)
_MEETING_CODE_PATTERN = re.compile(r"\bMTG-(\d+)\b", re.IGNORECASE)
_NCR_CODE_PATTERN = re.compile(r"\bNCR-(\d+)\b", re.IGNORECASE)
_DOCUMENT_CODE_PATTERN = re.compile(r"\bDOC-(\d+)\b", re.IGNORECASE)

_WORD_BOUNDARY_KEYWORDS = {"po", "pr"}

# Multi-domain detection: keywords that strongly suggest 2+ domains
_MULTI_DOMAIN_CONNECTORS = re.compile(
    r"\b(also|and their|compare|cross|both|alongside|as well as|"
    r"كذلك|مقارنة|أيضاً)\b",
    re.IGNORECASE,
)


@dataclass
class RoutedIntent:
    intent: str
    project_id: Optional[int]
    project_code: Optional[str]
    filters: dict
    confidence: float
    unsupported: bool
    is_multi_domain: bool = False
    secondary_intents: list[str] = field(default_factory=list)
    meeting_id: Optional[int] = None
    ncr_id: Optional[int] = None
    document_id: Optional[int] = None


def _kw_matches(kw: str, text: str) -> bool:
    """Return True if keyword matches in text.

    For single short tokens that could match inside other words, use
    word-boundary regex.  For multi-word phrases and longer tokens, plain
    substring is sufficient and avoids regex overhead.
    """
    if kw in _WORD_BOUNDARY_KEYWORDS:
        return bool(re.search(r"\b" + re.escape(kw) + r"\b", text))
    return kw in text


def route_intent(
    question: str,
    hint_project_id: Optional[int] = None,
    previous_intent: Optional[str] = None,
) -> RoutedIntent:
    """Deterministically route a user question to an intent domain.

    Args:
        question: The user's natural-language question.
        hint_project_id: Optional project_id passed explicitly by the client.
        previous_intent: Previous turn's intent for context carry-forward.

    Returns:
        RoutedIntent describing the best-matched domain.
    """
    lower = question.lower()

    project_code: Optional[str] = None
    m = _PROJECT_CODE_PATTERN.search(question)
    if m:
        project_code = m.group(1).upper()

    project_id_from_text: Optional[int] = None
    m2 = _PROJECT_ID_PATTERN.search(lower)
    if m2:
        try:
            project_id_from_text = int(m2.group(1))
        except ValueError:
            pass

    resolved_project_id = hint_project_id or project_id_from_text

    resolved_meeting_id: Optional[int] = None
    m3 = _MEETING_CODE_PATTERN.search(question)
    if m3:
        try:
            resolved_meeting_id = int(m3.group(1))
        except ValueError:
            pass

    resolved_ncr_id: Optional[int] = None
    m4 = _NCR_CODE_PATTERN.search(question)
    if m4:
        try:
            resolved_ncr_id = int(m4.group(1))
        except ValueError:
            pass

    resolved_document_id: Optional[int] = None
    m5 = _DOCUMENT_CODE_PATTERN.search(question)
    if m5:
        try:
            resolved_document_id = int(m5.group(1))
        except ValueError:
            pass

    # An explicit meeting code (e.g. "MTG-1") is a stronger, more specific
    # signal than any generic keyword match — short-circuit straight to the
    # meetings domain before keyword scoring. Without this, phrasings that
    # don't happen to contain "meeting"/"decision" (e.g. "What happened in
    # MTG-1?", "What are the action items from MTG-1?") fell through to
    # intent=unknown and triggered a full 10-domain open-domain retrieval —
    # and phrasings that DO contain a keyword belonging to a higher-priority
    # domain (e.g. "Summarize meeting MTG-1" matching "summarize" under
    # executive_summary) were misrouted to a portfolio-wide summary instead
    # of the one meeting actually named. Checked ahead of executive_summary
    # for the same reason: an explicit entity reference beats a generic verb.
    if resolved_meeting_id is not None:
        # A question can name a meeting AND ask about a second domain in the
        # same breath — "What decisions from MTG-1 could delay procurement?"
        # Without this, the original single-domain short-circuit above (added
        # to fix the "MTG-1 pulls in 52 unrelated items" bug) had the side
        # effect of making the meeting_id path ALWAYS single-domain, silently
        # dropping any other domain the question also asked about. Score the
        # question against every OTHER domain's keywords (meetings/decisions/
        # action_items are already covered by meeting_id itself — see
        # get_meeting_detail(), which returns the meeting's own decisions
        # AND action items in one call; executive_summary is a separate
        # portfolio-wide mechanism, not a per-meeting one) and carry forward
        # whatever matches as secondary_intents — the pipeline uses this to
        # run the multi-domain plan (still scoped to this one meeting's
        # project, not the whole portfolio) instead of the single-meeting
        # dispatch when a second, genuinely DIFFERENT domain is also named.
        secondary: list[str] = []
        for other_intent, keywords in _INTENT_KEYWORDS.items():
            if other_intent in ("meetings", "decisions", "action_items", "executive_summary"):
                continue
            if any(_kw_matches(kw, lower) for kw in keywords):
                secondary.append(other_intent)
        return RoutedIntent(
            intent="meetings",
            project_id=resolved_project_id,
            project_code=project_code,
            filters={},
            confidence=1.0,
            unsupported=False,
            is_multi_domain=bool(secondary),
            secondary_intents=secondary[:2],
            meeting_id=resolved_meeting_id,
            ncr_id=resolved_ncr_id,
            document_id=resolved_document_id,
        )

    # Same idea for an explicit document code (e.g. "DOC-3") — a stronger
    # signal than a generic "document"/"contract" keyword match. Checked
    # after meeting_id (a meeting can reference a document without the
    # document itself being the primary subject) but before executive_summary
    # for the same reason as the meeting short-circuit above.
    if resolved_document_id is not None:
        return RoutedIntent(
            intent="documents",
            project_id=resolved_project_id,
            project_code=project_code,
            filters={},
            confidence=1.0,
            unsupported=False,
            meeting_id=resolved_meeting_id,
            ncr_id=resolved_ncr_id,
            document_id=resolved_document_id,
        )

    # Check executive_summary first (highest priority multi-domain intent)
    exec_score = sum(
        1 for kw in _INTENT_KEYWORDS["executive_summary"]
        if _kw_matches(kw, lower)
    )
    if exec_score > 0:
        return RoutedIntent(
            intent="executive_summary",
            project_id=resolved_project_id,
            project_code=project_code,
            filters={},
            confidence=min(exec_score / len(_INTENT_KEYWORDS["executive_summary"]), 1.0),
            unsupported=False,
            is_multi_domain=True,
            meeting_id=resolved_meeting_id,
            ncr_id=resolved_ncr_id,
            document_id=resolved_document_id,
        )

    scores: dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        if intent == "executive_summary":
            continue
        score = sum(1 for kw in keywords if _kw_matches(kw, lower))
        if score > 0:
            scores[intent] = score

    if not scores:
        # If question is very short and has previous context, carry forward intent.
        # Threshold is 8 words to handle questions like "which one has the highest budget?"
        if previous_intent and len(lower.split()) <= 8:
            return RoutedIntent(
                intent=previous_intent,
                project_id=resolved_project_id,
                project_code=project_code,
                filters={},
                confidence=0.3,
                unsupported=False,
                is_multi_domain=False,
                meeting_id=resolved_meeting_id,
                ncr_id=resolved_ncr_id,
                document_id=resolved_document_id,
            )
        return RoutedIntent(
            intent="unknown",
            project_id=resolved_project_id,
            project_code=project_code,
            filters={},
            confidence=0.0,
            unsupported=True,
            meeting_id=resolved_meeting_id,
            ncr_id=resolved_ncr_id,
            document_id=resolved_document_id,
        )

    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]
    max_possible = len(_INTENT_KEYWORDS[best_intent])
    confidence = min(best_score / max_possible, 1.0)

    # Detect multi-domain: connector present AND multiple domains scored
    is_multi = False
    secondary: list[str] = []
    if _MULTI_DOMAIN_CONNECTORS.search(question) or len(scores) >= 2:
        for intent, score in sorted(scores.items(), key=lambda x: -x[1]):
            if intent != best_intent and score >= 1:
                secondary.append(intent)
                is_multi = True
        secondary = secondary[:2]  # cap secondary intents

    return RoutedIntent(
        intent=best_intent,
        project_id=resolved_project_id,
        project_code=project_code,
        filters={},
        confidence=confidence,
        unsupported=False,
        is_multi_domain=is_multi,
        secondary_intents=secondary,
        meeting_id=resolved_meeting_id,
        ncr_id=resolved_ncr_id,
        document_id=resolved_document_id,
    )
