# AMAD — User Flows

Every flow below is a real navigation path found in the code (an actual
`<Link href=...>`/`setLocation(...)` between two audited pages, or a real
auth-guard redirect in `App.tsx`) — not a proposed or ideal flow. Where a
flow is currently a dead end (a page with no outbound links), that's noted
as a gap rather than papered over.

## Authentication

```
/login  →  (successful auth) →  /
       →  (user.must_change_password === true) →  /change-password  →  /
```

Guard logic lives in `App.tsx`'s `ProtectedRoute` / `AdminRoute` /
`ChangePasswordRoute`: any unauthenticated request to a protected route
redirects to `/login`; any authenticated request from a user with
`must_change_password` redirects to `/change-password` before anything
else is reachable; `/admin/*` additionally redirects non-admins to `/`.

## Executive daily-check flow

```
/  (Executive Dashboard)
  → /reports          (full Executive Weekly Report)
  → /projects          → /projects/:id
  → /safety
  → /rfis
  → /documents
  → /copilot            (Quick Actions → "Open Copilot")
  → /alerts
```

All seven links originate from `dashboard/QuickActions.tsx` and the
dashboard's chart click-throughs.

## AI Center hub-and-spoke

```
/ai-center  (Overview)
  → every other AI Center workspace (Quick Access grid, 8 of 15 shown, filterable by search)
  → /alerts             (hero bell icon)
  → /ai-center/executive-decision-center  (Executive Brief "View full brief", heat map "View full heat map")
```

Overview also pulls read-only data from three Flagship Modules'
generator functions directly (`generateExecutiveDecisionCenter`,
`generateMaterialIntelligence`, `generateSupplierRisk`) to build its own
brief/KPIs — a data dependency, not a navigation link.

## Project drill-down (the deepest flow in the app)

```
/projects  →  /projects/:id
                 ├── tab: Meetings        → /meetings/:projectId/:meetingId
                 ├── tab: Site Reports    → /projects/:projectId/site-reports/:reportId
                 ├── tab: Documents       (links to /documents conceptually — same document store)
                 ├── tab: AI Summary      → /ai-center/executive (via "Ask Hermes"/AI Summary content)
                 └── tab: Ask Hermes      → embeds CopilotPage (same component as /copilot)
```

Project Detail is the only page in the app that embeds three other
full page-level components inline as tabs (`MemoryCenter`, `CopilotPage`,
plus its own AI Action Panel) rather than linking out to them.

## Site Report analysis flow

```
/site-reports  (project-scoped gallery)
  → /projects/:projectId/site-reports/:reportId
       → (on-demand) POST .../analyze  →  AI findings/risk/recommendations tabs
```

Also reachable via `/ai-center/site-reports` (Site Report Intelligence),
which is a second, AI-Center-scoped entry point into the same detail
route.

## Meeting flow

```
/meetings  (create dialog, list)
  → /meetings/:projectId/:meetingId
```

Also reachable via `/ai-center/meetings` (Meeting Intelligence), and
referenced from Executive Intelligence's "Recent Decisions" section as a
substitute for a portfolio-wide decisions view that doesn't exist yet.

## Memory flow

```
/ai-center/memory  (Memory Center — full CRUD)
  ← RecentMemoriesPanel "View all"  (embedded in AI Copilot workspace and Project Detail)
```

`Project Memory` (`/ai-center/project-memory`, a Flagship Module) is a
distinct, richer, project-scoped view over a similar underlying concept —
it is not the same page as Memory Center and the two are not linked to
each other in the code.

## Dead ends (pages with no outbound links, per the audit)

These are real, complete pages — not placeholders — that currently have no
`<Link>` to anywhere else in the app. Noted as a gap, not a flaw to fix
here.

- Procurement (`/procurement`)
- Suppliers (`/suppliers`)
- Safety & NCR (`/safety`)
- RFIs (`/rfis`)
- Change Orders (`/change-orders`)
- Claims (`/claims`)
- Contract Intelligence links out (to `/documents`) but nothing links
  further from Contract Intelligence itself beyond that one target.

## Placeholder pages (no flow to document)

Tasks, Requests & Approvals, Notifications, Risk Register, Intelligent
Search, Email Intelligence, Audit Log, Integrations, Billing &
Subscription, and all three Client Portal pages render the shared
`RoadmapPlaceholder` shell with no outbound links and no real
functionality — there is no flow to trace on any of them yet.
