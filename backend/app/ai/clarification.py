"""Clarification system — detects ambiguous questions and returns structured responses.

When a question cannot be answered without additional context (and the
conversation state does not supply enough), this module returns a structured
clarification response instead of a grounded answer.

Design constraints:
- Clarification detection is deterministic (no LLM).
- Clarification responses include suggested options where the domain can be
  inferred, so the user can click a chip rather than re-typing.
- Never guess when a question is genuinely ambiguous.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.ai.conversation_state import ConversationState

# ------------------------------------------------------------------ #
# Clarification triggers                                               #
# ------------------------------------------------------------------ #

_AMBIGUOUS_REPORT_RE = re.compile(
    r"\b(show|get|give|display|list|find)\s+me\s+(the|a)\s+(report|data|info|information|summary)\b",
    re.IGNORECASE,
)

_COMPARISON_WITHOUT_SUBJECTS_RE = re.compile(
    r"\bcompare\b(?!.*\b(project|procurement|safety|ncr|supplier|site|meeting)\b)",
    re.IGNORECASE,
)

_GENERIC_STATUS_RE = re.compile(
    r"^\s*(what is|how is|what's)\s+(the\s+)?status\s*\??\s*$",
    re.IGNORECASE,
)

# Questions like "which project?" without specifying what domain
_BARE_WHICH_RE = re.compile(
    r"^\s*which (project|one|supplier)\s*\??\s*$",
    re.IGNORECASE,
)


@dataclass
class ClarificationResponse:
    """Structured clarification request returned to the user."""
    clarification_required: bool
    clarification_question: str
    clarification_options: list[str] = field(default_factory=list)
    reason: Optional[str] = None


_DOMAIN_CLARIFICATION_OPTIONS: dict[str, list[str]] = {
    "report": [
        "Show me the latest site reports",
        "Show me the safety incident report",
        "Show me the procurement summary",
        "Show me the project status overview",
    ],
    "comparison": [
        "Compare project budget performance",
        "Compare safety incidents across projects",
        "Compare procurement delays across projects",
        "Compare NCR counts across projects",
    ],
    "status": [
        "What is the status of active projects?",
        "What is the status of open purchase orders?",
        "What is the status of open NCRs?",
        "What is the safety status across projects?",
    ],
    "generic": [
        "Show me active projects overview",
        "Show me late purchase orders",
        "Show me recent safety events",
        "Show me recent site reports",
    ],
}

_DOMAIN_CLARIFICATION_OPTIONS_AR: dict[str, list[str]] = {
    "report": [
        "أرني أحدث تقارير الموقع",
        "أرني تقرير حوادث السلامة",
        "أرني ملخص المشتريات",
        "أرني نظرة عامة على حالة المشاريع",
    ],
    "status": [
        "ما هو وضع المشاريع النشطة؟",
        "ما هو وضع أوامر الشراء المفتوحة؟",
        "ما هو وضع NCRs المفتوحة؟",
    ],
    "generic": [
        "أرني نظرة عامة على المشاريع",
        "أرني أوامر الشراء المتأخرة",
        "أرني أحداث السلامة الأخيرة",
    ],
}


def _detect_arabic(text: str) -> bool:
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return arabic_chars > len(text) * 0.15


def check_clarification_needed(
    question: str,
    state: ConversationState,
    context_resolver_said_clarify: bool = False,
    context_resolver_reason: Optional[str] = None,
) -> Optional[ClarificationResponse]:
    """Return a ClarificationResponse if the question is too ambiguous to answer.

    Returns None if no clarification is needed.

    Args:
        question: The resolved (or original) question.
        state: Current conversation state.
        context_resolver_said_clarify: Whether the context resolver flagged this.
        context_resolver_reason: Reason from the context resolver.
    """
    is_arabic = _detect_arabic(question)
    opts_map = _DOMAIN_CLARIFICATION_OPTIONS_AR if is_arabic else _DOMAIN_CLARIFICATION_OPTIONS

    # If context resolver already said clarify, honour that
    if context_resolver_said_clarify:
        if context_resolver_reason == "anaphoric_no_context":
            q = (
                "ما الذي تقصده بـ 'هم/ذلك/هذا'؟ يُرجى توضيح سؤالك."
                if is_arabic
                else "What are you referring to? Please clarify your question or start a new topic."
            )
            return ClarificationResponse(
                clarification_required=True,
                clarification_question=q,
                clarification_options=opts_map.get("generic", []),
                reason="anaphoric_no_context",
            )
        if context_resolver_reason == "too_vague_no_context":
            q = (
                "ما الموضوع الذي تريد معرفته؟"
                if is_arabic
                else "What would you like to know about?"
            )
            return ClarificationResponse(
                clarification_required=True,
                clarification_question=q,
                clarification_options=opts_map.get("generic", []),
                reason="too_vague",
            )

    q_lower = question.lower()

    # Generic "show me the report" without domain
    if _AMBIGUOUS_REPORT_RE.search(question) and not _has_domain_hint(q_lower):
        q = (
            "أي تقرير تريد رؤيته؟"
            if is_arabic
            else "Which report would you like to see?"
        )
        return ClarificationResponse(
            clarification_required=True,
            clarification_question=q,
            clarification_options=opts_map.get("report", []),
            reason="ambiguous_report",
        )

    # "compare them" without subjects and no prior context
    if _COMPARISON_WITHOUT_SUBJECTS_RE.search(question) and not state.has_context():
        q = (
            "ماذا تريد المقارنة؟"
            if is_arabic
            else "What would you like to compare?"
        )
        return ClarificationResponse(
            clarification_required=True,
            clarification_question=q,
            clarification_options=opts_map.get("comparison", []),
            reason="ambiguous_comparison",
        )

    # "what is the status?" without domain
    if _GENERIC_STATUS_RE.match(question) and not state.has_context():
        q = (
            "حالة ماذا؟"
            if is_arabic
            else "Status of what?"
        )
        return ClarificationResponse(
            clarification_required=True,
            clarification_question=q,
            clarification_options=opts_map.get("status", []),
            reason="ambiguous_status",
        )

    # Bare "which project?" without context
    if _BARE_WHICH_RE.match(question) and not state.has_context():
        q = (
            "أيّ مشروع تقصد؟"
            if is_arabic
            else "Which project are you asking about?"
        )
        return ClarificationResponse(
            clarification_required=True,
            clarification_question=q,
            clarification_options=opts_map.get("generic", []),
            reason="bare_entity_reference",
        )

    return None


def _has_domain_hint(lower: str) -> bool:
    """Return True if the question already has a domain keyword."""
    domain_words = [
        "project", "procurement", "safety", "ncr", "site",
        "meeting", "supplier", "purchase", "مشروع", "سلامة", "مشتريات",
    ]
    return any(w in lower for w in domain_words)
