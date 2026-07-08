---
name: Construction AI Platform Phase 2.5 UI
description: Dark/light mode, Amad brand identity, polished app shell and all 8 pages — key implementation decisions and hardening decisions
---

## Dark mode mechanism
- `.dark` class on `<html>` (set by ThemeContext in `artifacts/web/src/context/ThemeContext.tsx`)
- Tailwind v4 custom variant: `@custom-variant dark (&:is(.dark *))` — matches descendants of `.dark`
- CSS custom property overrides in `.dark { }` block in `index.css` — this is the primary theming mechanism
- Persisted to `localStorage["theme"]`; falls back to `prefers-color-scheme` on first visit

**Why:** Tailwind v4 dropped `darkMode: 'class'` config; the custom-variant approach is the correct replacement.
**How to apply:** Always add dark: variants when writing new Tailwind utilities; CSS variable approach handles component-level tokens automatically.

## Brand identity
- Product: "Amad Construction Intelligence" / "عَمَد"
- Logo mark: Arabic letter "عَ" in a gold (`bg-sidebar-primary`) rounded square; font-family: serif for the Arabic char
- Tagline: "Construction Intelligence" (or i18n "Command Center" key)

## Status badge utilities
Shared utility classes in `index.css` under `@layer components`:
`.badge`, `.badge-success`, `.badge-warning`, `.badge-danger`, `.badge-info`, `.badge-neutral`, `.badge-purple`, `.badge-gold`
These use `dark:` variants so they work in both modes. Always use these instead of hardcoding `bg-green-100 text-green-800`.

## RTL
- `document.documentElement.dir` toggled by language switcher in layout.tsx
- Use logical CSS properties: `ps-/pe-`, `ms-/me-`, `text-start/text-end`, `border-s/border-e`
- Mobile sidebar RTL slide direction: `isRtl ? "translate-x-full" : "-translate-x-full"` for hidden state
- Flex row naturally reverses in RTL so sidebar appears on the right without extra CSS

## Panel/table components
Shared in `index.css`:
- `.panel` → `rounded-xl border bg-card shadow-sm`
- `.panel-header / .panel-title / .panel-body`
- `.data-table` → semantic table with styled thead/tbody rows

## Design tokens (light/dark)
- Light: soft gray bg `220 18% 95%`, deep navy primary `222 55% 18%`, gold accent `44 58% 52%`, deep navy sidebar `222 60% 14%`
- Dark: deep navy-black bg `222 45% 7%`, gold primary `44 62% 62%`, dark card `222 42% 11%`, deepest navy sidebar `222 55% 5%`

## Tailwind v4 opacity class pattern
- `bg-primary/15` works; `bg-opacity-15` does NOT (v4 dropped opacity utilities)
- For icon container backgrounds use explicit suffix: `bg-primary/15`, `bg-emerald-500/15`

## OpenAPI spec → codegen flow
- `lib/api-spec/openapi.yaml` is static — edit it, then run `pnpm --filter @workspace/api-spec run codegen`
- Orval generates to `lib/api-client-react/src/generated/` and `lib/api-zod/src/generated/`
- Codegen also runs `typecheck:libs` so no separate lib step is needed

## Dashboard data correctness
- DB has 4 project statuses: Active(19), Delayed(17), On Hold(14), Completed(10); total=60
- `delayed_projects` and `on_hold_projects` are separate fields — both required in openapi.yaml schema
- Backend `dashboard.py` counts them with individual WHERE clauses — never combine Delayed + On Hold

## RBAC permission matrix (backend router.py)
- Dashboard + Projects: all authenticated roles
- Procurement: executive, project_manager, procurement_officer
- Safety/NCR: executive, project_manager, safety_quality_officer
- Site Reports: executive, project_manager, site_engineer
- Meetings/Docs/Claims: executive, project_manager
- Subcontractors: executive, project_manager, site_engineer, safety_quality_officer
- Implemented via `require_roles()` from `backend/app/core/deps.py`

## DB status values (exact, case-sensitive)
- Project: Active, Delayed, On Hold, Completed (+ Suspended, Planning)
- PR: Approved, Converted to PO, Needs Rework, Pending Clarification, Returned to Requester, Under Review
- PO: Delivered only; `is_late` boolean discriminates late vs on-time
- NCR: Closed, Open, Under Corrective Action
- Safety severities: High, Medium, Low
- Meeting types: Commercial, Safety, Technical, Weekly
- Weather: Clear, Dusty, Hot, Humid, Light Rain, Windy

## Error states pattern
- Projects, Suppliers, Dashboard, Project Detail: full-page error panel (no content rendered)
- Safety, Site Reports, Meetings, Procurement: error row inside table body (project selector still works)
- Always import `AlertOctagon` from lucide-react for the error icon

## Backend tests (121 passing as of B2B phase)
- `backend/tests/test_dashboard.py` — 13 SQL-verified tests for all dashboard aggregate fields
- `backend/tests/test_rbac.py` — full 403/200/401 coverage using `app.dependency_overrides`
- `backend/tests/test_admin_users.py` — 14 tests for admin user CRUD and access control
- `backend/tests/test_organizations.py` — 9 tests for org CRUD and access control
- `backend/tests/test_project_memberships.py` — membership add/remove/list/dedup tests
- Conftest overrides `get_current_user` globally with admin; test_rbac.py manipulates overrides per test

## Toast import
- **Correct**: `import { useToast } from "@/hooks/use-toast"`
- **Wrong**: `import { useToast } from "@/components/ui/toast"` (that file exports primitives, not the hook)

## SQLAlchemy mapper gotcha — projects.py
- When editing `backend/app/models/projects.py`, ALL relationships must be kept
- Missing `daily_activities = relationship("DailyActivity", back_populates="project")` causes mapper init failure on first DB query
- Actual DB column names differ from intuitive names:
  - `project_risks`: `title`, `description`, `probability` (NOT `risk_description`, `likelihood`)
  - `project_issues`: `title`, `description`, `severity`, `owner`, `resolved_at` (NOT `issue_description`, `raised_by`)
  - `project_phases`: `name`, `sequence` (NOT `phase_name`, `completion_pct`)
  - `project_milestones`: `name`, `phase_id` (NOT `milestone_name`)

## B2B SaaS additions (Phase 2 backend)
- `organizations` table, `organization_id` FK on `user_accounts`, `project_memberships` join table
- Migration: `0003_add_b2b_foundation.py`
- All admin endpoints under `/api/v1/admin/` require admin JWT
- `/auth/register` is admin-only (non-admins get 403); team members provisioned via POST /admin/users
- Seed script: `cd backend && python -m scripts.seed_organizations`
- See `backend/docs/b2b_saas_model.md` for full reference

## Favicon path
- File: `artifacts/web/public/favicon.svg`
- HTML href in index.html: `/web/favicon.svg` (Vite serves public/ at the artifact base path `/web/`)

## Phase 4A — Health Score Engine (completed)
- Scoring: 100 − penalties (schedule 0–35, safety 0–25, NCR 0–20, PO 0–15, risk 0–10); levels Critical/At Risk/Good/Excellent
- API: `GET /v1/projects/health-scores` (list), `GET /v1/projects/{id}/health` (detail with penalty breakdown)
- Copilot routes: `lowest_health`, `unhealthy_projects`, `health_explain` intents in analyst.py
- **Critical gotcha**: `execute_multi_domain_plan` in `planner.py` has an explicit domain allowlist — new retrieval functions must be added to `domain_retrieval_map` or they're silently skipped for multi-domain queries
- **Critical gotcha**: `_blocks_health_list` / `_blocks_health_card` in render_blocks.py must extract `e.source_id` strings before passing to `_citations_block()` — passing Evidence objects causes `TypeError: unhashable type`
- Live portfolio (60 projects): avg score=47, Good=10, At Risk=28, Critical=22, Excellent=0
- Copilot Copilot response field is `answer` not `answer_text` — the schema exposes both but the primary field is `answer`

## Phase 4C — Executive Intelligence Dashboard (completed)
- API: `GET /api/v1/executive` → ExecutiveIntelligence (registered under `_any_auth` in router.py)
- Response: portfolio_status/score, executive_summary, level counts (critical/at_risk/good/excellent), top_priorities (5), biggest_risks (always exactly 5 categories), best_projects (5), attention_required (6)
- Risk categories always exactly 5: safety, procurement, quality, schedule, health — any change to this breaks tests
- conftest.py auth pattern: `app.dependency_overrides[get_current_user]` set at module level — tests use `client: TestClient` fixture, NO `get_auth_headers` import; 401 tests are smoke-test only (not in pytest suite)
- 30 backend tests passing across 5 classes: TestExecutiveBasic, TestExecutiveShape, TestBiggestRisks, TestProjectLists, TestSeededData
- Frontend: 6 components (ExecPortfolioCard, ExecSummaryCard, ExecTopPrioritiesCard, ExecBiggestRisksCard, ExecBestProjectsCard, ExecAttentionCard) + useExecutive hook in dashboard.tsx; section renders before Row 1 KPIs
- Live portfolio result: status=At Risk, score=47, critical=22, at_risk=28, good=10, excellent=0 (60 active projects)

## Phase 4D — Executive Weekly Report (completed)
- API: `GET /api/v1/reports/executive-weekly` → ExecutiveWeeklyReport (registered under `_any_auth`)
- Report period computed as ISO week Mon–Sun via `date.isocalendar()` — start_date is always Monday
- Response: report_period, generated_at, portfolio_summary, portfolio_status, portfolio_score, health_distribution, top_priorities (5), biggest_risks (5), critical_alerts (≤10 sorted by sev), procurement_blockers, safety_highlights, quality_highlights, recommended_actions (sequential priority 1-N), sources (6 sources)
- Imports `_compute_executive_intelligence` helpers from executive.py — `_SEV_ORDER`, `_count_to_severity`, `_brief`, `ProjectBrief`, `RiskCategory`
- 42 backend tests passing across 7 classes: TestReportBasic, TestReportShape, TestReportPeriod, TestHealthDistribution, TestBiggestRisks, TestTopPriorities, TestCriticalAlerts, TestRecommendedActions, TestSources
- Frontend: `artifacts/web/src/pages/reports.tsx` + `artifacts/web/src/lib/useReports.ts`; route `/reports` added to App.tsx; `FileText` nav item in layout.tsx; "Executive Weekly Report" action card on dashboard above Executive Intelligence section
- Print/PDF: `window.print()` with `print:` Tailwind variants; print header shows Amad branding + period
