# AI Architecture — Amad Construction Intelligence Platform

## Overview

Phase 3A implements a read-only AI Copilot grounded entirely in platform data.
The system is permission-aware, deterministically routed, and produces auditable
evidence-backed answers.

## 1. Provider Abstraction

### Files
- `app/ai/providers/base.py` — `LLMProvider` protocol, `LLMRequest`, `LLMResponse`, error types
- `app/ai/providers/fake.py` — `FakeLLMProvider` (deterministic, used when no API key)
- `app/ai/providers/openai_compat.py` — `OpenAICompatProvider` (OpenAI, OpenRouter)
- `app/ai/providers/factory.py` — `get_llm_provider()` cached singleton

### Decision: Deterministic retrieval over RAG
Vector search is NOT used in Phase 3A. All data retrieval uses typed SQL queries
with explicit authorization filters. This ensures:
- Zero hallucinated data from semantically similar but wrong records
- Deterministic, auditable results
- No pgvector embedding cost at query time

RAG / vector retrieval is scoped to Phase 3B when specific high-value semantic
use cases are identified.

### Provider Configuration

| `LLM_PROVIDER` | `LLM_API_KEY` | Behavior |
|---|---|---|
| `mock` (default) | any | `FakeLLMProvider` |
| anything | unset or empty | `FakeLLMProvider` |
| `openai` | set | `OpenAICompatProvider` → `api.openai.com` |
| `openrouter` | set | `OpenAICompatProvider` → `openrouter.ai` |
| `anthropic` + `LLM_BASE_URL` | set | `OpenAICompatProvider` → custom base |

The application starts normally when no API key is configured.  AI endpoints
return clear service-unavailable responses rather than crashing.

## 2. Database Tables

### New in Phase 3A (migration `0004`)

| Table | Purpose |
|---|---|
| `ai_conversations` | Groups messages into a user conversation |
| `ai_messages` | Individual user/assistant messages with metadata |
| `ai_citations` | Source evidence attached to assistant messages |
| `copilot_audit_logs` | One row per query attempt — full audit trail |

### Existing (reused, not modified)
- `ai_memories` — Phase 1 memory store (not used by Copilot in Phase 3A)
- `ai_audit_logs` — Phase 1 workflow audit (not used by Copilot in Phase 3A)

## 3. Authorization-Before-Retrieval

```
Request → Authentication → build_ai_scope() → AIAuthScope
→ Retrieval tools (receive scope) → SQL query with WHERE filters
→ LLM receives only authorized evidence
```

### `AIAuthScope` fields
- `organization_id` — enforces org isolation at conversation level
- `user_id` — conversation ownership
- `user_role` — determines global vs. project-scoped read
- `accessible_project_ids` — tuple of allowed project IDs for restricted roles
- `project_membership_roles` — role per project for display

### RBAC mapping

| Role | Access level |
|---|---|
| `admin` | Global read — all projects, all orgs |
| `executive` | Global read — all projects in their org |
| `project_manager` | Global read — all projects in their org |
| `site_engineer` | Project-scoped — only membership projects |
| `procurement_officer` | Project-scoped — only membership projects |
| `safety_quality_officer` | Project-scoped — only membership projects |
| `viewer` | Project-scoped — only membership projects |

**The LLM never enforces permissions.** Filters are applied by Python retrieval
code before any data is passed to the LLM.

## 4. Copilot Query Lifecycle

```
POST /api/v1/ai/copilot/query
  │
  ├─ Rate limit check (20 req/min per user, in-memory sliding window)
  │
  ├─ build_ai_scope(current_user, db)
  │    └─ Raises 403 for inactive users
  │
  ├─ route_intent(question, hint_project_id)
  │    └─ Deterministic keyword matching → intent domain
  │    └─ Returns "unknown" + unsupported=True for out-of-scope questions
  │
  ├─ _dispatch_retrieval(intent, db, scope, project_id)
  │    └─ SQL-backed domain retrieval with authorization filters
  │    └─ Returns RetrievalResult{data, evidence[]}
  │
  ├─ _build_evidence_block(evidence)
  │    └─ Formats evidence as numbered list in system prompt
  │
  ├─ provider.generate(LLMRequest(system_prompt, user_prompt))
  │    └─ System prompt contains RULES + EVIDENCE only
  │    └─ User question isolated from system instructions
  │
  ├─ GroundingValidator.validate(question, answer, evidence)
  │    └─ Checks answer is grounded in evidence
  │    └─ Returns controlled fallback if validation fails
  │
  ├─ Persist AIMessage + AICitation (only on success)
  │
  ├─ Persist CopilotAuditLog (always — success and failure)
  │
  └─ Return CopilotQueryResponse
```

## 5. Intent Domains

| Intent | Keywords (sample) |
|---|---|
| `project_overview` | project, status, overview, budget |
| `procurement` | procurement, purchase order, po, delivery |
| `suppliers` | supplier, vendor |
| `safety` | safety, incident, accident |
| `ncr` | ncr, non-conformance, quality |
| `site_reports` | site report, daily report, weather |
| `meetings` | meeting |
| `decisions` | decision |
| `risks` | risk, issue |
| `unknown` | no keyword match → unsupported response |

Arabic keywords are also supported for each domain.

## 6. Retrieval Tools

Each tool is a pure function `(db, scope, project_id?, limit?) → RetrievalResult`.

| Tool | File |
|---|---|
| `get_project_overview` | `retrieval/projects.py` |
| `get_project_risks` | `retrieval/projects.py` |
| `get_procurement_summary` | `retrieval/procurement.py` |
| `get_late_purchase_orders` | `retrieval/procurement.py` |
| `get_supplier_information` | `retrieval/procurement.py` |
| `get_safety_summary` | `retrieval/safety.py` |
| `get_open_ncrs` | `retrieval/safety.py` |
| `get_recent_site_reports` | `retrieval/site_reports.py` |
| `get_recent_daily_activities` | `retrieval/site_reports.py` |
| `get_recent_meetings` | `retrieval/meetings.py` |
| `get_project_decisions` | `retrieval/meetings.py` |

## 7. Grounding Validator

`GroundingValidator.validate(question, answer, evidence)` returns
`GroundingResult{is_grounded, reason}`.

Logic:
1. If `evidence` is empty and the answer contains specific numerical claims → `is_grounded=False`
2. If the answer begins with `INSUFFICIENT_EVIDENCE:` → acknowledged, grounded=True
3. If the answer contains many large numbers not in the evidence → `is_grounded=False`
4. Otherwise → `is_grounded=True`

On grounding failure, the pipeline returns a controlled fallback message in the
user's detected language (Arabic or English).

## 8. Citation Model

Every successful completed response persists citations as `AICitation` rows.

Citation example response fields:
```json
{
  "source_type": "project",
  "source_id": "PRJ-001",
  "label": "Project PRJ-001 — King Salman Hospital",
  "evidence_snippet": "PRJ-001: status=Active, budget=50,000,000 SAR",
  "ui_metadata": {"href": "/projects/1", "icon": "briefcase"}
}
```

The frontend renders citation chips that are clickable where a page exists.

## 9. Audit Logging

`CopilotAuditLog` is written for **every query attempt** — success or failure.

| Field | Purpose |
|---|---|
| `organization_id` | Org isolation / multi-tenant reporting |
| `user_id` | User-level activity |
| `project_id` | Project-scoped queries |
| `conversation_id` | Links to full conversation |
| `intent` | Which domain was routed |
| `provider_name` / `model_name` | Provider audit |
| `status` | `completed` / `auth_denied` / `provider_unavailable` / `insufficient_evidence` / `grounding_failed` / `rate_limited` |
| `latency_ms` | End-to-end latency |
| `prompt_tokens` / `completion_tokens` | Token usage (when available) |
| `evidence_source_count` | How many evidence records were retrieved |
| `failure_category` | Structured failure code for debugging |

Secrets, full prompts, and raw user input are NOT stored in audit logs.

## 10. Security Controls

| Control | Implementation |
|---|---|
| Question length | 2000 char max — Pydantic schema |
| Rate limiting | 20 req/min per user — in-memory sliding window |
| Conversation ownership | `conversation.user_id == current_user.id` |
| Organization isolation | `conversation.organization_id == scope.organization_id` |
| Project authorization | `scope.enforce_project_access(project_id)` before retrieval |
| Prompt injection resistance | System prompt has explicit RULES section; evidence is formatted as numbered items, not raw user text |
| Evidence treated as untrusted | Evidence snippets are truncated at 500 chars, never executed |
| No stack traces in responses | FastAPI exception handlers return safe messages |
| No provider secrets in responses | Audit log only records provider name, not key |
| Inactive user denial | `build_ai_scope()` raises 403 for `is_active=False` |

## 11. Known Limitations (Phase 3A)

- Rate limiter is in-process only; resets on server restart. Phase 3B: Redis-backed.
- Vector search / RAG not used; semantic similarity queries not supported.
- No streaming responses; full answer returned after generation completes.
- Intent routing is keyword-based; multi-domain queries resolve to one intent.
- Native Anthropic API not implemented; use OpenRouter proxy for Anthropic models.
- No conversation branching or message editing.

## 12. Phase 3B Future Scope

- AI write actions with approval workflow (reuses existing `approval_requests` table)
- Vector embeddings for `ai_memories` (pgvector already installed)
- Streaming responses (Server-Sent Events)
- Redis-backed rate limiting
- Native Anthropic API adapter
- Conversation sharing / export
- Fine-grained per-domain role permissions
- Arabic-first NLP improvements
