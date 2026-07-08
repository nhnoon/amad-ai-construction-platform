---
name: Construction AI Platform — Phase 4B
description: Smart Alerts Center — deterministic alert generation from live PostgreSQL data, 10 alert types, 2 API endpoints, full frontend (page + nav badge + dashboard widget).
---

## What was built

`backend/app/api/v1/alerts.py` — pure Python alert generation service + 2 FastAPI endpoints.  
`backend/tests/test_alerts.py` — 47 tests across 4 test classes.  
`artifacts/web/src/lib/useAlerts.ts` — shared TypeScript types + useAlerts / useAlertsSummary hooks (direct fetch, no codegen).  
`artifacts/web/src/pages/alerts.tsx` — full Alerts page with summary cards, category/severity filters, alert list with collapsible recommended actions.  
`artifacts/web/src/components/layout.tsx` — Alerts nav item with live critical+high count badge (useQuery, refetchInterval=60s).  
`artifacts/web/src/pages/dashboard.tsx` — AlertsPreviewWidget showing top 5 alerts with "View all" link.

## API endpoints

- `GET /api/v1/alerts` — all authenticated users; filters: severity, category, project_id, limit (1-500), offset  
- `GET /api/v1/alerts/summary` — counts by severity + by_category dict

Both routes registered under `_any_auth` in router.py.

## Alert types generated (10 types)

1. **health-critical-{id}** — project health score < 40 (Critical level) → severity=critical, category=health
2. **health-atrisk-{id}** — project health score 40-59 (At Risk) → severity=high, category=health
3. **safety-event-{id}** — SafetyEvent.severity=Critical → critical; High → high; category=safety
4. **safety-risk-{id}** — project with ≥3 high/critical events → safety risk aggregate
5. **quality-ncr-{id}** — ≥5 open NCRs → high; 2-4 → medium; category=quality
6. **procurement-late-po-{id}** — late PO, delay_days>30 → high; ≤30 → medium; category=procurement
7. **procurement-risk-{id}** — project with ≥3 late POs → systemic risk, severity=high
8. **schedule-delayed-{id}** — Project.status=Delayed → high, category=schedule
9. **schedule-onhold-{id}** — Project.status=On Hold → medium, category=schedule
10. **safety-risk-{id}** — ≥3 high/critical safety events per project → severity=critical if ≥2 critical

## Thresholds

NCR_HIGH=5, NCR_MEDIUM=2, LATE_PO_HIGH_DAYS=30, PROC_RISK=3, SAFETY_RISK=3

## Sample data from seeded DB

1089 total alerts: 22 critical, 792 high, 275 medium.  
By category: health=50, safety=174, procurement=774, quality=60, schedule=31.

## No DB schema changes

Alerts are entirely derived from live data. No new tables, no Alembic migration needed.  
`alembic check` → "No new upgrade operations detected."

## Frontend pattern

Direct fetch with `getToken()` from `lib/auth` — no OpenAPI codegen cycle.  
Pattern: `useQuery({queryKey, queryFn: () => fetch('/api/v1/alerts?...', {headers: {Authorization: Bearer token}})})`.  
Shared in `lib/useAlerts.ts`, imported by both alerts.tsx and dashboard.tsx.

## Why no codegen for alerts

The OpenAPI codegen cycle (update spec → pnpm codegen → lib rebuild) takes many steps and is fragile for one-off endpoints. Direct fetch in a shared hook file is faster and just as typed for new endpoints. Only use codegen for endpoints needed platform-wide.
