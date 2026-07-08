---
name: Construction AI Platform Phase 3B
description: Multi-turn conversational Copilot — key bugs fixed and test infrastructure decisions
---

## Domain signal substring false-positives
`_DOMAIN_SIGNALS["procurement"]` originally included `"pr"` and `"po"`. These matched as substrings inside unrelated words (`"pr"` inside `"project"`, `"po"` inside `"portfolio"`), causing `detect_required_domains("What is the project status?", "project_overview")` to incorrectly return `["project_overview", "procurement"]`.

**Fix:** removed `"pr"`/`"po"` from `_DOMAIN_SIGNALS`; added `_signal_matches()` helper that applies `\bKW\b` regex for tokens ≤ 3 alpha characters or any token in `_WORD_BOUNDARY_SIGNALS`.

**Why:** substring matching is acceptable for long phrases (`"purchase order"`) but harmful for short acronyms. Always use word-boundary matching for 1–3 char alphabetic tokens.

## Arabic tanwin variant matching (intent router)
Intent keywords like `"ملخص تنفيذي"` (no tanwin) do not match `"ملخصاً تنفيذياً"` (with fatha+tanwin). `_kw_matches` uses `kw in text` so multi-word phrases require exact character match.

**Fix:** add both base form and common tanwin forms as separate keyword entries: `"ملخص تنفيذي"`, `"ملخصاً تنفيذياً"`, `"ملخصا تنفيذيا"`, `"ملخص"` (lone stem as last-resort fallback).

**Why:** Arabic tanwin (ً ٍ ٌ) and shaddah are frequent in formal Arabic text but alter byte sequences. The substring matcher requires the diacritised form to exactly match or a stem fallback.

## Rate limiter exhaustion in test suite
`SlidingWindowRateLimiter(max_requests=20, window_seconds=60)` is a module-level singleton keyed by `user_id`. All API tests run under the same `TEST_USER_ID`, so a test class with 20+ sequential API calls exhausts the window and causes every subsequent test to 429.

**Fix:** add an `autouse=True` function-scoped pytest fixture in every test module that fires many AI copilot queries:
```python
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.ai.ratelimit import get_ai_rate_limiter
    from tests.conftest import TEST_USER_ID
    get_ai_rate_limiter().reset(TEST_USER_ID)
    yield
```

**Why:** the test client is session-scoped and re-uses the same in-process server; the rate limiter is not reset between test functions. The fixture must be function-scoped (not class or session) so each API-calling test starts with a clean window.

## Multi-word executive_summary phrases
`"management attention"` does not match `"What should management pay attention to today?"` because the phrase splits across other words. Similarly `"what should i know"` misses `"what should management …"`.

**Fix:** add explicit phrase variants: `"what should management"`, `"what should we focus"`, `"what should we know"`.

**How to apply:** when adding new executive_summary keywords, think about the common English question forms (`"what should X …"`) and test each variant with a simple `kw in lower` check before adding.

## Phase 3B module inventory
- `backend/app/ai/conversation_state.py` — `ConversationState` dataclass; `from_dict`/`to_dict`; bounded to 20 evidence IDs, 10 project IDs
- `backend/app/ai/context_resolver.py` — `resolve_context`, `is_anaphoric`, `is_too_vague_without_context`, `build_conversation_context_block`
- `backend/app/ai/clarification.py` — `check_clarification_needed`, `ClarificationResponse`
- `backend/app/ai/planner.py` — `detect_required_domains`, `is_executive_summary_query`, `PlannerResult`
- `backend/app/ai/followup.py` — `generate_follow_up_suggestions` (RBAC-aware, bilingual)
- Migration `0005`: added `conversation_state JSONB` to `ai_conversations`; context-tracking columns to `ai_messages`; extended audit fields to `copilot_audit_logs`
- Final test count: **324 passing** (both passes, no flakes)
