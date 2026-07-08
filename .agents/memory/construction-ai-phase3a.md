---
name: Construction AI Platform — Phase 3A
description: AI Copilot backend foundation + read-only frontend page decisions
---

# Phase 3A: AI Intelligence Foundation + Read-Only Copilot

## Completed Work
- Migration `0004` adds: `ai_conversations`, `ai_messages`, `ai_citations`, `copilot_audit_logs`
- 4 AI routes: `POST /api/v1/ai/copilot/query`, `GET /api/v1/ai/conversations`, `GET /api/v1/ai/conversations/{id}`, `GET /api/v1/ai/conversations/{id}/messages`
- Frontend Copilot page at `/copilot` with conversation sidebar, suggested prompts, citation chips, confidence badges
- 113 new tests added across 5 test files; total test count raised from 121 → 234

## Critical Decisions

### test user real ID required
**Why:** `ai_conversations.user_id` has a FK to `user_accounts.id`. Test mock user `id=999` doesn't exist in the DB. Conftest now resolves the real admin user's ID (`admin@construction.ai`) at session start via `TEST_USER_ID = _resolve_test_user_id()`.

### PurchaseOrder has no monetary field
**Why:** The `PurchaseOrder` model has no `total_amount` or `delivery_date`. Real fields: `promised_delivery`, `actual_delivery`, `is_late`, `delay_days`. Procurement retrieval evidence snippets must use these.

### Word-boundary matching for "po", "pr" in intent router
**Why:** "po" appears as substring in "reports" (r-e-p-o-r-t-s), "pr" could collide similarly. Fixed via `_WORD_BOUNDARY_KEYWORDS = {"po", "pr"}` with `\b` regex. "ncr" must NOT be in this set — "ncrs" (plural) won't match `\bncr\b`.

### Grounding validator threshold: `>= 1` not `> 2`
**Why:** An answer with even one specific large number (e.g. "5500000 SAR") when no evidence is provided should be flagged as ungrounded.

### "weather" removed from site_reports keywords
**Why:** Too generic — "weather in Dubai" matched site_reports unintentionally. Removed from keyword list.

### FK violations in tests — use real user_ids
**Why:** Both `ai_conversations.user_id` and `ai_conversations.organization_id` have FK constraints. Tests that create "foreign" conversations must use real existing user IDs (via `_get_other_user_id()`) and `organization_id=None` (nullable).

## Provider Strategy
- `LLM_PROVIDER=mock` (default) → `FakeLLMProvider` always used when no API key
- Factory cached singleton; `reset_provider()` in tests to clear cache
- No vector/RAG in Phase 3A — all retrieval is typed SQL with auth filters

## Architecture
See `backend/docs/ai_architecture.md` for full reference.
