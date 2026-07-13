"""Contextual query resolver — converts follow-up questions into standalone queries.

This is a DETERMINISTIC module.  It does not call the LLM.

Algorithm:
1. Detect if the current question contains pronouns, relative references, or
   is otherwise anaphoric (refers to previous conversation entities).
2. If anaphoric AND previous state exists: rewrite the question into a
   standalone query by injecting context (entity IDs, domain, filters).
3. If anaphoric AND no prior state: return clarification_needed=True.
4. If not anaphoric: return the original question unchanged.

The resolved query is persisted alongside the original for auditability.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.ai.conversation_state import ConversationState

# ------------------------------------------------------------------ #
# Pronoun / reference detection patterns                               #
# ------------------------------------------------------------------ #

# Patterns that signal the question refers to previous entities.
#
# Split into "strong" (essentially never has a same-sentence antecedent —
# "them"/"those"/"tell me more"/etc. only make sense pointing at prior
# conversation) and "weak" (common pronouns like "it"/"its" that just as
# often refer to an entity named earlier in the SAME sentence, e.g. "NCR-2,
# and which project is it linked to?"). Weak patterns are only treated as
# anaphoric when the question does not already contain an explicit entity
# code of its own — see is_anaphoric() below.
_STRONG_ANAPHORIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(them|they|those|these)\b", re.IGNORECASE),
    re.compile(r"\b(that project|this project|the project)\b", re.IGNORECASE),
    re.compile(r"\bwhich (one|ones)\b", re.IGNORECASE),
    re.compile(r"\bone of (them|those|these)\b", re.IGNORECASE),
    re.compile(r"\bthe (same|above|mentioned|previous|earlier)\b", re.IGNORECASE),
    re.compile(r"\btell me more\b", re.IGNORECASE),
    re.compile(r"\bmore (details?|info|information|about)\b", re.IGNORECASE),
    re.compile(r"\bwhat about (it|them|that|this)\b", re.IGNORECASE),
    re.compile(r"\bhow (is|are) (it|they|those) (doing|going|performing)\b", re.IGNORECASE),
    # Short explain/follow-up queries that implicitly refer to previous context
    re.compile(r"^\s*why\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*why (that|so|is (that|this)|not)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*explain\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*explain (that|this|why|more)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*what('?s| is) the reason\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*how (so|come)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*and (the other|the rest)\??\s*$", re.IGNORECASE),
    # Arabic anaphoric markers — standalone pronouns.
    # Negative lookbehind for Arabic interrogative "ما " (what) which uses
    # هو/هي/هم as copulas: "ما هو المشروع؟"="what is the project?" is NOT
    # anaphoric.  هذا/هذه/ذلك/تلك/نفس-forms always indicate prior reference.
    re.compile(r"(?<!ما )(هو|هي|هم)|(?:هذا|هذه|تلك|ذلك|نفسه|نفسها|نفسهم)"),
    re.compile(r"^\s*لماذا\??\s*$"),
    re.compile(r"^\s*اشرح\s*$"),
    # Arabic pronoun suffixes on prepositions / verbs — "from them", "compare it",
    # "does it have", "which one of them" etc.
    # These are common follow-up phrasings that reference prior context.
    re.compile(r"(?:منها|منهم|منه|لديه|لديها|عنده|عندها|فيه|فيها|به|بها)"),
    re.compile(r"(?:أي واحد|واحد منها|أيهم|أيها)"),
    re.compile(r"قارن[هاهيون]?"),      # قارنه, قارنها, قارني, قارنوا
    re.compile(r"(?:هل لديه|هل لها|هل له|هل فيه|هل عنده)"),
]

_WEAK_ANAPHORIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(it|its)\b", re.IGNORECASE),
]

# Same entity-code family used by app/ai/memory.py's evidence-dump guard —
# if one of these is already named in the question, a trailing "it" almost
# certainly refers back to it within the same sentence.
_ENTITY_CODE_RE = re.compile(r"\b(?:PRJ|PO|PR|MTG|NCR|SE|DEC|ACT)-\d+\b", re.IGNORECASE)

# "Which/what <domain noun> ... it?" also has a same-sentence antecedent —
# "it" refers back to the noun the question is already asking about (e.g.
# "Which purchase order has the longest delay, and how many days late is
# it?"), not to something from a prior turn.
_SELF_CONTAINED_WHICH_RE = re.compile(
    r"\b(which|what)\b.{0,40}\b(project|purchase order|purchase request|"
    r"po|pr|supplier|meeting|decision|ncr|safety event|site report)\b",
    re.IGNORECASE,
)

# Patterns that indicate intent-domain continuation without pronouns
_CONTINUATION_MARKERS = re.compile(
    r"\b(also|and what about|what else|anything else|furthermore)\b",
    re.IGNORECASE,
)

# Questions so vague that without context they require clarification
_REQUIRES_CLARIFICATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*(show|tell|give|get) me (the|a) (report|data|info|information|summary|detail|details)\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*how is it (doing|going|performing)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*compare them\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(what|how) about (it|them|that|this)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(tell me more|more details?|elaborate)\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*and\??\s*$", re.IGNORECASE),
]

_MAX_CONTEXT_MESSAGES = 10  # bounded: last 5 turns (user + assistant)


@dataclass
class RecentMessage:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ResolvedContext:
    """Result of context resolution."""
    resolved_query: str
    original_question: str
    is_follow_up: bool
    context_refs_used: list[str] = field(default_factory=list)
    hint_project_ids: list[int] = field(default_factory=list)
    hint_supplier_ids: list[int] = field(default_factory=list)
    hint_intent: Optional[str] = None
    clarification_needed: bool = False
    clarification_reason: Optional[str] = None


def is_anaphoric(question: str) -> bool:
    """Return True if the question contains references to prior context.

    Weak pronoun patterns ("it"/"its") are only counted when the question
    does not already name the entity they refer to in the same sentence
    (e.g. "NCR-2 ... is it linked to?" is self-contained, not a follow-up).
    """
    for pattern in _STRONG_ANAPHORIC_PATTERNS:
        if pattern.search(question):
            return True
    if _ENTITY_CODE_RE.search(question) or _SELF_CONTAINED_WHICH_RE.search(question):
        return False
    for pattern in _WEAK_ANAPHORIC_PATTERNS:
        if pattern.search(question):
            return True
    return False


def is_too_vague_without_context(question: str) -> bool:
    """Return True if the question is too vague to answer without prior context."""
    for pattern in _REQUIRES_CLARIFICATION_PATTERNS:
        if pattern.match(question):
            return True
    return False


def resolve_context(
    question: str,
    state: ConversationState,
    recent_messages: list[RecentMessage],
) -> ResolvedContext:
    """Resolve a potentially anaphoric question into a standalone query.

    Args:
        question: The current user question.
        state: Current conversation state (may be empty for first turn).
        recent_messages: Last N messages for prompt context (bounded).

    Returns:
        ResolvedContext describing the resolved standalone query.
    """
    original = question.strip()
    anaphoric = is_anaphoric(original)
    has_prior_context = state.has_context()

    # Case 1: Too vague and no prior context — request clarification
    if is_too_vague_without_context(original) and not has_prior_context:
        return ResolvedContext(
            resolved_query=original,
            original_question=original,
            is_follow_up=False,
            clarification_needed=True,
            clarification_reason="too_vague_no_context",
        )

    # Case 2: Not anaphoric — pass through unchanged
    if not anaphoric and not _CONTINUATION_MARKERS.search(original):
        return ResolvedContext(
            resolved_query=original,
            original_question=original,
            is_follow_up=False,
            hint_intent=None,
        )

    # Case 3: Anaphoric but no prior context — request clarification
    if anaphoric and not has_prior_context:
        return ResolvedContext(
            resolved_query=original,
            original_question=original,
            is_follow_up=False,
            clarification_needed=True,
            clarification_reason="anaphoric_no_context",
        )

    # Case 4: Anaphoric WITH prior context — rewrite to standalone query
    refs_used: list[str] = []
    hint_project_ids = list(state.active_project_ids)
    hint_supplier_ids = list(state.referenced_supplier_ids)

    # Build context injection suffix
    parts: list[str] = []

    if state.previous_intent:
        refs_used.append(f"previous_intent:{state.previous_intent}")

    if hint_project_ids:
        id_str = ", ".join(f"PRJ-{pid:04d}" for pid in hint_project_ids[:5])
        parts.append(f"from the previous result ({id_str})")
        refs_used.append(f"project_ids:{','.join(str(p) for p in hint_project_ids[:5])}")

    if state.last_answer_summary:
        parts.append(f"Context: {state.last_answer_summary}")
        refs_used.append("last_answer_summary")

    # Construct resolved query
    if parts:
        context_prefix = " | ".join(parts)
        resolved = f"{original} [{context_prefix}]"
    else:
        resolved = original

    return ResolvedContext(
        resolved_query=resolved,
        original_question=original,
        is_follow_up=True,
        context_refs_used=refs_used,
        hint_project_ids=hint_project_ids,
        hint_supplier_ids=hint_supplier_ids,
        hint_intent=state.previous_intent,
    )


def build_conversation_context_block(
    recent_messages: list[RecentMessage],
    max_messages: int = _MAX_CONTEXT_MESSAGES,
) -> str:
    """Build a bounded conversation history block for the LLM prompt.

    Only includes the last ``max_messages`` messages to keep token budget
    bounded.  Each message is summarised to a single line.
    """
    if not recent_messages:
        return ""

    bounded = recent_messages[-max_messages:]
    lines: list[str] = ["[PREVIOUS CONVERSATION]"]
    for msg in bounded:
        role = "User" if msg.role == "user" else "Assistant"
        # Truncate long messages to keep prompt size bounded
        content = msg.content[:400]
        if len(msg.content) > 400:
            content += "…"
        lines.append(f"{role}: {content}")
    lines.append("[END CONTEXT]")
    return "\n".join(lines)
