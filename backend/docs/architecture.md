# Construction AI Platform — Architecture

## Overview

The Construction AI Platform is a Python FastAPI backend providing a REST API for an AI-powered construction operations intelligence system. It follows a clean, layered architecture designed to scale from a single-server deployment to a distributed SaaS product.

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115 (Python 3.11) |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy 2.0 (sync) |
| Migrations | Alembic |
| Cache / Pub-Sub | Redis |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| LLM integration | Provider-agnostic adapter (Phase 2) |
| Testing | pytest + httpx TestClient |
| Frontend (Phase 2) | React + TypeScript (Vite) |

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── config.py            # Pydantic-settings (env-driven)
│   ├── database.py          # SQLAlchemy engine + session factory
│   ├── redis_client.py      # Redis client (graceful degradation)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # Aggregates all v1 routers
│   │       ├── health.py    # /healthz, /readyz
│   │       ├── projects.py
│   │       ├── procurement.py
│   │       ├── meetings.py
│   │       ├── site_reports.py
│   │       ├── documents.py
│   │       ├── claims.py
│   │       ├── safety.py
│   │       └── subcontractors.py
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   └── core/
│       ├── security.py      # JWT + password hashing
│       └── deps.py          # FastAPI dependency injection
├── alembic/                 # Database migrations
│   └── versions/
│       └── 0001_initial_schema.py
├── tests/                   # pytest test suite
├── scripts/
│   └── migrate_sqlite.py    # One-time SQLite → PostgreSQL migration
└── docs/
    ├── architecture.md      # This file
    └── migration.md         # Dataset migration report
```

## Database Schema

### Original Dataset Tables (18)
Migrated from the provided SQLite dataset. All date fields retained as `VARCHAR` (matching source data) for Phase 1; type migrations will be added in Phase 2.

| Table | Rows | Description |
|---|---|---|
| projects | 60 | Core project records |
| suppliers | 80 | Supplier directory |
| subcontractors | 70 | Subcontractor directory |
| meetings | 260 | Meeting records |
| project_decisions | 535 | Decisions per meeting |
| purchase_requests | 3,000 | PRs with gap fields (AI target) |
| purchase_orders | 2,550 | POs with delay data |
| site_reports | 1,200 | Daily site reports |
| daily_activities | 2,385 | Activity logs per subcontractor |
| documents | 120 | Project document records |
| generated_documents | 1,060 | Email-style correspondence |
| correspondence | 120 | Formal correspondence |
| safety_events | 449 | Safety incidents |
| ncrs | 739 | Non-conformance reports |
| claims | 120 | Commercial claims |
| change_orders | 120 | Change order records |
| subcontractor_evaluations | 499 | Performance evaluations |
| claim_evidence | 120 | Evidence chains |

### Extension Tables (9 new)
Added to satisfy specification requirements not covered by the dataset.

| Table | Purpose |
|---|---|
| project_phases | Spec: project lifecycle phases |
| project_milestones | Spec: milestone tracking |
| project_risks | Spec: risk register |
| project_issues | Spec: issue tracker |
| meeting_attendees | Spec: meeting intelligence |
| meeting_action_items | Spec: action item tracking |
| user_accounts | Auth: RBAC user management |
| ai_memories | AI: enterprise memory with pgvector |
| ai_audit_logs | Governance: AI output audit trail |
| approval_requests | Governance: human-in-the-loop |

## API Design

- All routes are prefixed with `/api/v1/`
- Base health check at `/api/healthz` (no auth required)
- OpenAPI docs at `/api/docs`
- Response format: JSON
- Pagination: `?skip=0&limit=20` on all list endpoints

## LLM Provider Architecture (Phase 2)

The platform uses a provider-agnostic `LLMGateway` interface:

```python
class LLMGateway(Protocol):
    def complete(self, messages: list[Message], **kwargs) -> str: ...
    def complete_structured(self, messages: list[Message], schema: type[T]) -> T: ...
```

Implementations: `MockLLM`, `OpenAILLM`, `AnthropicLLM`, `OpenRouterLLM`

The active provider is selected via `LLM_PROVIDER` environment variable — no business logic changes required.

## Security Model

- JWT tokens (HS256, 8-hour expiry)
- bcrypt password hashing
- RBAC roles: Admin, Executive, Project Manager, Site Engineer, Procurement Officer, Safety/Quality Officer
- Human-in-the-loop: high-risk AI actions create `approval_requests` records rather than executing immediately
- Full AI audit trail in `ai_audit_logs`

## Bilingual / i18n Support (Phase 2)

- API responses use English field names and values
- i18n translation layer will be in the frontend (react-i18next)
- RTL support in CSS via `dir="rtl"` attribute and Tailwind RTL plugin
- Arabic date/number formatting via `Intl` browser APIs
- Backend strings (error messages, labels) will be keyed and translatable in Phase 2
