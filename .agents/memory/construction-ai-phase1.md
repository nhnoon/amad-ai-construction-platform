---
name: Construction AI Platform — Phase 1
description: Key decisions and gotchas for the Saudi construction AI platform backend
---

## Backend location
- Code lives in `/home/runner/workspace/backend/` (NOT inside `artifacts/`)
- `artifacts/api-server/` is now a minimal pnpm stub (empty scripts)

## Workflow
- Name: "Start application"
- Command: `cd /home/runner/workspace/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080`
- Do NOT use `--reload` — causes double-bind failures on restart
- Old Node.js api-server (PID ~521) was blocking port 8080; needed manual kill via /proc inode lookup

**Why:** The existing artifacts/api-server Node.js process was running on port 8080 and standard tools (lsof, ss) are unavailable in the Replit nix container. Use /proc/net/tcp inode lookup to find it.

## Secret key
- Config reads `SESSION_SECRET` env var (already set in Replit secrets) as the JWT secret
- Field name in `app/config.py` is `SESSION_SECRET` exposed via `@property SECRET_KEY`

## Database schema
- 27 tables total: 18 original dataset tables + 9 extension tables
- Alembic revision: `0001` — creates pgvector extension, all tables, indexes
- `ai_memories.embedding` created as Text then ALTERed to `vector(1536)` in the same migration
- All date fields are `VARCHAR(50)` (matching SQLite source) — convert to Date in Phase 2

## Data migration
- Script: `backend/scripts/migrate_sqlite.py`
- Source: `attached_assets/sql_dataset/construction_ai_dataset_full_dump.sql`
- Result: 13,487 rows migrated, 0 errors
- `purchase_orders.is_late`: INTEGER (0/1) in SQLite → Boolean in PostgreSQL (handled in script)

## API structure
- All routes prefixed `/api/v1/`
- Health: `/api/healthz` (root), `/api/v1/healthz`, `/api/v1/readyz`
- Docs: `/api/docs`, `/api/redoc`
- Redis is optional — server degrades gracefully if unavailable

## Phase 2 priorities (approved by user)
- Auth endpoints (login, register, token refresh)
- LLM provider-agnostic gateway
- AI workflow engines (procurement gap filler, site report summarizer, etc.)
- React frontend with bilingual (AR/EN) + RTL support
- pgvector semantic search for ai_memories
