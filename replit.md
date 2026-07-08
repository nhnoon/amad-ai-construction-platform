# Construction AI Platform

AI-powered Construction Operations Intelligence Platform for the Saudi construction market. Provides a REST API for project management, procurement, safety/quality, claims, site reporting, and AI memory — backed by PostgreSQL with pgvector.

## Run & Operate

- **Start API:** workflow "Start application" — runs `uvicorn app.main:app --host 0.0.0.0 --port 8080` from `backend/`
- **Run tests:** `cd backend && python -m pytest tests/ -v`
- **Run migrations:** `cd backend && python -m alembic upgrade head`
- **Migrate SQLite dataset:** `cd backend && python -m scripts.migrate_sqlite`
- **Check DB:** `DATABASE_URL` secret (Replit-managed PostgreSQL)
- Required env: `DATABASE_URL`, `SESSION_SECRET` (both set in Replit Secrets)

## Stack

- Python 3.11 / FastAPI 0.115 / Uvicorn
- PostgreSQL + pgvector (Replit-managed)
- SQLAlchemy 2.0 (sync) + Alembic (migrations)
- Pydantic-settings (config), python-jose (JWT), passlib/bcrypt (auth)
- Redis (optional cache — graceful degradation)
- pytest + httpx TestClient

## Where things live

- `backend/` — entire Python FastAPI application
  - `app/main.py` — FastAPI app entrypoint
  - `app/config.py` — environment-driven settings
  - `app/models/` — SQLAlchemy ORM models (12 files, 27 tables)
  - `app/schemas/` — Pydantic request/response schemas
  - `app/api/v1/` — route handlers
  - `app/core/` — JWT security + DI deps
  - `alembic/versions/0001_initial_schema.py` — single migration, all 27 tables
  - `scripts/migrate_sqlite.py` — one-time SQLite → PostgreSQL data migration
  - `docs/architecture.md` — full architecture reference
  - `docs/migration.md` — dataset migration report
- `artifacts/api-server/` — minimal pnpm stub (empty, routes `/api` to Python backend)

## Architecture decisions

- **Python FastAPI over Node.js** — capstone specification requires FastAPI
- **Provider-agnostic LLM** — `LLM_PROVIDER` env var selects mock/openai/anthropic/openrouter
- **Bilingual from start** — i18n/RTL architecture planned for Phase 2 frontend
- **Date fields as VARCHAR(50)** — matching SQLite source types; proper Date migration in Phase 2
- **Redis optional** — server starts without Redis; cache layer added in Phase 2
- **No `--reload` in workflow** — causes double-bind failures in Replit container

## Product

RESTful API covering 8 construction domains: Projects, Procurement (PRs, POs, Suppliers), Meetings & Decisions, Site Reports & Daily Activities, Documents, Claims & Change Orders, Safety Events & NCRs, Subcontractors. Phase 2 adds AI workflows, authentication, and bilingual React frontend.

## User preferences

- Phase 1: backend foundation only — no AI workflows, no frontend
- LLM: provider-agnostic (mock default), NOT locked to any vendor
- Auth: email/password + JWT
- Bilingual: Arabic + English, RTL from start
- Full capstone specification scope required

## Gotchas

- Do NOT use `--reload` with uvicorn in the Replit workflow (causes port binding failure on restart)
- Old Node.js api-server process can hold port 8080; use /proc/net/tcp inode lookup to kill it if `lsof`/`ss` are unavailable
- `SESSION_SECRET` (already set) is used as JWT `SECRET_KEY` — field is `SESSION_SECRET` in `Settings` class
- Always run `alembic upgrade head` before first data migration
- Run data migration only once; re-running will fail on PK conflicts unless tables are truncated first

## Pointers

- See `backend/docs/architecture.md` for full architecture reference
- See `backend/docs/migration.md` for dataset migration report and FK dependency order
- See the `pnpm-workspace` skill for workspace structure
