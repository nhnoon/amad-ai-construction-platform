"""Safe Memory Reader — Phase 3 of the Copilot Memory Layer.

Deterministic (no LLM/Hermes call anywhere in this module) helpers that let
app/ai/pipeline.py optionally supplement a prompt with a small, bounded slice
of the authenticated user's own memory (app/ai/memory.py). Memory is derived
context only: it is never treated as evidence, never becomes an AICitation,
and never overrides a live PostgreSQL record.

Three steps, used in order by the pipeline:
  1. is_memory_relevant()      — should we even look at memory for this turn?
  2. select_relevant_memory()  — pick a few matching lines from the user's
                                  existing bounded memory notes.
  3. build_memory_context_block() / build_user_preferences_block()
                                — format the selection as clearly-labelled,
                                  non-authoritative prompt text.
"""
from __future__ import annotations

import re

_MAX_MEMORY_CONTEXT_CHARS = 1200
_MAX_MEMORY_CONTEXT_LINES = 8
_MAX_PROFILE_CHARS = 800

# ---------------------------------------------------------------------------
# Phase A — relevance detection
# ---------------------------------------------------------------------------

# Phrases that indicate the user is asking about something already discussed
# or decided, rather than the current live state of the data. Deliberately
# phrase-based (not intent-based) so a "show me current X" question routed to
# the same intent as a "what did we decide about X before" question is still
# told apart correctly.
_MEMORY_TRIGGER_PHRASES_EN = (
    "last meeting", "previous meeting", "prior meeting", "earlier meeting",
    "past meeting", "previously", "in the past", "remember", "recall",
    "recollect", "what did we discuss", "did we discuss", "have we discussed",
    "did we talk about", "what happened in", "what was discussed",
    "still pending", "historical", "history of", "what we discussed",
    "remembered preference", "preferred language", "preferred style",
)

# Diacritics (tashkeel) are stripped before matching so a question typed with
# or without them still matches the same phrase list.
_ARABIC_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٟۖ-ۭ]")

_MEMORY_TRIGGER_PHRASES_AR = (
    "سبق", "سابق", "الاجتماع السابق", "القرارات السابقة", "الاجتماع الماضي",
    "أتذكره", "أتذكر", "تذكر", "ناقشنا", "ماذا حدث في", "ما الذي حدث",
    "سابقا",
)

_MEMORY_TRIGGER_PHRASES = _MEMORY_TRIGGER_PHRASES_EN + _MEMORY_TRIGGER_PHRASES_AR

# Domains where a short continuation question ("what about the owners?")
# still implies "...of the thing we were just discussing from memory".
_MEMORY_DOMAIN_INTENTS = frozenset({"meetings", "decisions"})
_CONTINUATION_PATTERN = re.compile(
    r"\b(what about|and (the )?(action items?|owners?|due dates?)|also)\b"
)


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    return _ARABIC_DIACRITICS.sub("", text)


def is_memory_relevant(
    question: str,
    intent: str | None = None,
    previous_intent: str | None = None,
) -> bool:
    """Deterministic yes/no: is this question about remembered/historical
    context rather than the current live state of the data?

    No LLM call is made here or anywhere else in this module.
    """
    normalized = _normalize(question)
    if not normalized:
        return False

    if any(phrase in normalized for phrase in _MEMORY_TRIGGER_PHRASES):
        return True

    if previous_intent in _MEMORY_DOMAIN_INTENTS and _CONTINUATION_PATTERN.search(normalized):
        return True

    return False


# ---------------------------------------------------------------------------
# Phase B — bounded, deterministic selection
# ---------------------------------------------------------------------------

_ENTITY_CODE_PATTERN = re.compile(
    r"\b(?:PRJ|MTG|DEC|ACT|PO|PR|NCR|SE)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*",
    re.IGNORECASE,
)

_STOPWORDS = frozenset(
    {
        # English
        "the", "a", "an", "is", "are", "was", "were", "did", "do", "does",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "in", "on", "at", "to", "of", "for", "about", "with", "and", "or",
        "previously", "previous", "last", "happened", "meeting", "discuss",
        "discussed", "we", "us", "our", "it", "its", "be", "been", "has",
        "have", "had", "will", "would", "should", "could", "can", "from",
        "by", "as", "if", "not", "still",
        # Arabic
        "ما", "ماذا", "هل", "في", "من", "عن", "إلى", "على", "هذا", "هذه",
        "التي", "الذي", "كان", "كانت", "سبق", "سابق", "سابقا",
    }
)

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)

# Bare entity-code prefixes (the "mtg" in "MTG-1", the "prj" in "PRJ-0099")
# must not double as generic keywords — otherwise "MTG-1" and "MTG-2" would
# both "match" on the shared token "mtg" even though only one is the actual
# code being asked about. Full codes are matched separately via
# _entity_codes(); this set keeps them out of the keyword-overlap signal.
_ENTITY_PREFIXES = frozenset({"prj", "mtg", "dec", "act", "po", "pr", "ncr", "se"})


def _entity_codes(text: str) -> set[str]:
    return {m.upper() for m in _ENTITY_CODE_PATTERN.findall(text or "")}


def _keywords(text: str) -> set[str]:
    return {
        tok for tok in (t.lower() for t in _TOKEN_PATTERN.findall(text or ""))
        if len(tok) >= 3 and tok not in _STOPWORDS and tok not in _ENTITY_PREFIXES
    }


def select_relevant_memory(
    memory_text: str,
    question: str,
    max_chars: int = _MAX_MEMORY_CONTEXT_CHARS,
    max_lines: int = _MAX_MEMORY_CONTEXT_LINES,
) -> list[str]:
    """Pick a small, bounded set of lines from the user's own memory notes
    that are actually relevant to the current question.

    Deterministic keyword/entity-code matching only — no embeddings, no new
    dependency, no LLM call. Exact entity-code matches (PRJ-, MTG-, DEC-,
    ACT-, PO-, PR-, NCR-, SE-) are prioritized over plain keyword overlap.
    Lines with no match at all are excluded rather than padding the budget.
    """
    raw_lines = [line.strip() for line in (memory_text or "").split("\n")]
    raw_lines = [line for line in raw_lines if line]  # ignore empty lines

    deduped: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)

    question_codes = _entity_codes(question)
    question_keywords = _keywords(question)

    scored: list[tuple[int, int, str]] = []
    for idx, line in enumerate(deduped):
        code_matches = len(question_codes & _entity_codes(line))
        keyword_matches = len(question_keywords & _keywords(line))
        if code_matches == 0 and keyword_matches == 0:
            continue  # not relevant to this question — excluded
        priority = code_matches * 1000 + keyword_matches
        scored.append((priority, idx, line))

    # Highest priority first; original (recency) order breaks ties.
    scored.sort(key=lambda item: (-item[0], item[1]))

    selected: list[str] = []
    total_chars = 0
    for _, _, line in scored:
        if len(selected) >= max_lines:
            break
        added_chars = len(line) + (1 if selected else 0)  # + join newline
        if total_chars + added_chars > max_chars:
            break
        selected.append(line)
        total_chars += added_chars

    return selected


# ---------------------------------------------------------------------------
# Formatting — clearly-labelled, non-authoritative prompt blocks
# ---------------------------------------------------------------------------

_MEMORY_HEADER_EN = (
    "MEMORY CONTEXT — DERIVED, NOT AUTHORITATIVE:\n"
    "- Memory may be outdated.\n"
    "- Live evidence overrides memory.\n"
    "- Do not cite memory as a database source."
)
_MEMORY_HEADER_AR = (
    "سياق الذاكرة — معلومات مشتقة وغير رسمية:\n"
    "- قد تكون هذه الذاكرة قديمة أو غير محدثة.\n"
    "- الأدلة الحية الحالية لها الأولوية دائماً على الذاكرة.\n"
    "- لا يجوز الاستشهاد بالذاكرة كمصدر بيانات رسمي من قاعدة البيانات."
)

_PROFILE_HEADER_EN = "USER PREFERENCES — NON-AUTHORITATIVE:"
_PROFILE_HEADER_AR = "تفضيلات المستخدم — معلومات غير رسمية:"


def build_memory_context_block(selected_lines: list[str], is_arabic: bool = False) -> str:
    """Format selected memory lines as a clearly separate, non-authoritative
    prompt block. Returns "" when there is nothing to inject."""
    if not selected_lines:
        return ""
    header = _MEMORY_HEADER_AR if is_arabic else _MEMORY_HEADER_EN
    body = "\n".join(f"- {line}" for line in selected_lines)
    return f"{header}\n{body}"


def build_user_preferences_block(
    profile_text: str,
    max_chars: int = _MAX_PROFILE_CHARS,
    is_arabic: bool = False,
) -> str:
    """Format the user's bounded profile memory as non-authoritative
    preference context only. Never overrides system rules, authorization,
    live evidence, or business/safety rules. Returns "" when empty."""
    text = (profile_text or "").strip()
    if not text:
        return ""
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    header = _PROFILE_HEADER_AR if is_arabic else _PROFILE_HEADER_EN
    return f"{header}\n{text}"
