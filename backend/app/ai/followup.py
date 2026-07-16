"""Follow-up suggestion generator.

Generates 2–4 grounded follow-up questions based on:
- The current intent / domain
- Retrieved evidence (entity-specific suggestions where possible)
- Conversation state (avoid repeating past suggestions)
- Authorization scope (never suggest questions the user cannot access)

Design constraints:
- Suggestions are deterministic (no LLM).
- All suggestions must be within the user's authorized scope.
- Suggestions must be directly answerable by the Copilot's retrieval tools.
- Arabic suggestions are returned when the query language is Arabic.
"""
from __future__ import annotations

import re
from typing import Optional

from app.ai.retrieval.base import Evidence
from app.ai.scope import AIAuthScope

_MAX_SUGGESTIONS = 4

# ------------------------------------------------------------------ #
# Templates per intent                                                  #
# ------------------------------------------------------------------ #

_FOLLOW_UP_BY_INTENT_EN: dict[str, list[str]] = {
    "project_overview": [
        "Which project has the longest delay?",
        "Are there any safety incidents on these projects?",
        "Show me late purchase orders for these projects",
        "What decisions were made in recent meetings?",
        "What are the main risks for these projects?",
    ],
    "procurement": [
        "Which suppliers are responsible for the late orders?",
        "Show me a summary of active projects",
        "Are there any quality issues (NCRs) related to procurement?",
        "What is the total value of late purchase orders?",
    ],
    "suppliers": [
        "Which suppliers have the most late deliveries?",
        "Show me purchase orders from these suppliers",
        "Are there any NCRs related to supplier quality?",
    ],
    "safety": [
        "Which projects have the most safety incidents?",
        "Are there any open NCRs related to these incidents?",
        "Show me site reports for affected projects",
        "What decisions were made about safety in recent meetings?",
    ],
    "ncr": [
        "Which projects have the most open NCRs?",
        "Are these NCRs related to procurement quality issues?",
        "Show me recent safety events on these projects",
        "What corrective actions were decided in recent meetings?",
    ],
    "site_reports": [
        "Are there any safety incidents at these sites?",
        "Show me the project status for these sites",
        "What is the manpower utilization trend?",
        "Are there any delayed activities?",
    ],
    "meetings": [
        "What decisions were made that affect project timelines?",
        "Are there any procurement-related action items?",
        "Show me the project status for projects discussed",
        "Are there any safety-related decisions?",
    ],
    "decisions": [
        "Which decisions are still pending implementation?",
        "Are there any project risks related to these decisions?",
        "Show me site reports for projects affected by these decisions",
    ],
    "risks": [
        "Which projects have the highest risk scores?",
        "Are there related safety events for these risks?",
        "Show me procurement status for at-risk projects",
        "What decisions were made to mitigate these risks?",
    ],
    "executive_summary": [
        "Which projects need immediate management attention?",
        "Show me detailed safety incidents from last month",
        "What are the top procurement risks?",
        "Which projects are most delayed?",
    ],
    "unknown": [
        "What is the status of active projects?",
        "Show me late purchase orders",
        "Are there any recent safety incidents?",
        "Give me an executive summary",
    ],
}

_FOLLOW_UP_BY_INTENT_AR: dict[str, list[str]] = {
    "project_overview": [
        "أيّ مشروع لديه أطول تأخير؟",
        "هل هناك حوادث سلامة في هذه المشاريع؟",
        "أرني أوامر الشراء المتأخرة لهذه المشاريع",
        "ما هي المخاطر الرئيسية لهذه المشاريع؟",
    ],
    "procurement": [
        "أيّ موردين مسؤولون عن التأخيرات؟",
        "هل هناك مشاكل جودة (NCR) مرتبطة بالمشتريات؟",
        "أرني ملخص المشاريع النشطة",
    ],
    "safety": [
        "أيّ المشاريع لديها أكثر حوادث سلامة؟",
        "هل هناك NCRs مفتوحة مرتبطة بهذه الحوادث؟",
        "ما هي القرارات المتخذة بشأن السلامة في الاجتماعات الأخيرة؟",
    ],
    "unknown": [
        "ما هو وضع المشاريع النشطة؟",
        "أرني أوامر الشراء المتأخرة",
        "هل هناك أحداث سلامة حديثة؟",
        "أعطني ملخصاً تنفيذياً",
    ],
}


def _extract_project_labels(evidence: list[Evidence], max_n: int = 2) -> list[str]:
    """Extract up to max_n project labels from evidence for entity-specific suggestions."""
    seen: list[str] = []
    for ev in evidence:
        if ev.source_type == "project" and ev.label:
            name = ev.label.split("—")[-1].strip() if "—" in ev.label else ev.label
            # Shorten to first part (e.g. "Khobar School Project 1")
            short = name[:40]
            if short not in seen:
                seen.append(short)
                if len(seen) >= max_n:
                    break
    return seen


def generate_follow_up_suggestions(
    intent: str,
    evidence: list[Evidence],
    scope: AIAuthScope,
    is_arabic: bool,
    status: str,
    max_suggestions: int = _MAX_SUGGESTIONS,
) -> list[str]:
    """Generate 2–4 grounded follow-up suggestions.

    Args:
        intent: The resolved intent of the current query.
        evidence: Retrieved evidence (used for entity-specific suggestions).
        scope: Authorization scope (ensures suggestions are accessible).
        is_arabic: Response language, decided once by the caller (pipeline.py)
            from the user's message and shared with the answer itself —
            suggestions must always match the answer's language (requirement:
            "Follow-up suggestions must be generated in the same language as
            the answer"), so this takes the already-decided value instead of
            re-detecting it from question text a second time.
        status: Pipeline status (only generate for completed turns).
        max_suggestions: Maximum number of suggestions to return.

    Returns:
        List of suggestion strings (may be empty for failed queries).
    """
    # Don't suggest follow-ups for failed or clarification turns
    if status not in ("completed", "insufficient_evidence", "unsupported_intent"):
        return []

    template_map = _FOLLOW_UP_BY_INTENT_AR if is_arabic else _FOLLOW_UP_BY_INTENT_EN

    # Normalize unknown intent to executive summary templates if appropriate
    effective_intent = intent if intent in template_map else "unknown"

    base_suggestions = list(template_map.get(effective_intent, template_map["unknown"]))

    # Try to make 1-2 suggestions entity-specific
    project_labels = _extract_project_labels(evidence)
    if project_labels and not is_arabic:
        specific = [
            f"Show me more details about {project_labels[0]}",
        ]
        if len(project_labels) > 1:
            specific.append(f"Compare {project_labels[0]} and {project_labels[1]}")
        # Prepend entity-specific, then fill from base
        suggestions = specific + [s for s in base_suggestions if s not in specific]
    else:
        suggestions = base_suggestions

    # Remove suggestions for domains the restricted user cannot access
    # (viewers can only see their own projects; skip suggestions about all projects)
    if not scope.has_global_read and not is_arabic:
        restricted_phrases = ["across projects", "all projects", "executive summary"]
        suggestions = [
            s for s in suggestions
            if not any(phrase in s.lower() for phrase in restricted_phrases)
        ]

    return suggestions[:max_suggestions]
