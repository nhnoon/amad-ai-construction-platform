# AMAD Product Blueprint

A description of the product as it exists in code today — architecture,
modules, navigation, and what's built vs. planned. Companion documents:
`SITE_MAP.md` (navigation tree), `PAGE_INVENTORY.md` (every page in
detail), `USER_ROLES.md`, `USER_FLOWS.md`, `ROADMAP.md`.

## What AMAD is

A construction-operations platform (React/TypeScript frontend, FastAPI
backend) organized around two things: a conventional **Operations**
system-of-record (projects, meetings, procurement, site reports, safety,
claims, change orders, suppliers) and an **AI Center** — 16 AI-assisted
workspaces layered over that same data, ranging from a portfolio-wide
executive assistant to per-entity analysis tools to six large "Flagship"
predictive/analytical modules.

48 routed pages/surfaces exist today. 30 are Complete, 4 are Partial, 14
are Placeholder or Planned (not yet built). See `PAGE_INVENTORY.md` for the
full breakdown.

## Navigation shell

One `Layout` component (`components/layout.tsx`) wraps every authenticated
page: a collapsible left sidebar (accordion — one titled group open at a
time, auto-expanding the group containing the current route) and a minimal
utility topbar (mobile nav toggle, role badge, avatar — no page title,
since every page renders its own via `PageContextHeader`/`WorkspaceLayout`
or `PageHero`). The sidebar groups map directly to the product's own
information architecture:

- **Dashboard** and **Documents** — ungrouped, top-level, always visible.
- **My Workspace** — personal/cross-project surfaces (Tasks, Requests &
  Approvals, Alerts, Notifications).
- **Operations** — the system-of-record: Projects, Procurement, Site
  Reports, Meetings, RFIs, Change Orders, Claims, Suppliers, Safety, Risk
  Register, plus an Operations Overview landing page.
- **AI Center** — 16 workspaces under one route (`/ai-center/:workspace?`),
  sub-grouped in the sidebar as Workspace / Per-Entity Intelligence /
  Flagship Modules (see below).
- **Analytics** — Reports, plus a cross-listed link to AI Center's
  Executive Intelligence (labeled "Insights" here).
- **Client Portal** — a future client-facing section; every page in it is
  currently a placeholder.
- **Administration** — admin-only (the one role-enforced route group in
  the app): Users, Organizations, Audit Log, Integrations, Billing.

## Operations workspaces

The conventional half of the product — record-keeping and workflow across
projects. All 14 pages here are Complete or Partial and all use real
backend data (`Real` in the backend-integration sense; see
`../DEVELOPMENT/BACKEND_INTEGRATION_STATUS.md`). The one structural note:
**RFIs has no first-class backend entity** — it's a client-side keyword
filter over decisions/documents/correspondence rather than a true RFI
workflow, and **Risk Register is not yet built** (placeholder,
`in-development`). Project Detail is the densest single page in the app —
12 tabs unifying every entity type for one project, including embedded
copies of the Memory Center and Copilot components.

## AI Center

One route (`/ai-center/:workspace?`) rendering one of 16 components based
on the `:workspace` URL segment (`pages/ai-center/index.tsx`). Organized in
three tiers:

**Workspace** — general-purpose AI tools: **Overview** (the AI Center's own
landing page — see below), **AI Copilot** (a multi-turn, citation-grounded
chat assistant, also reachable standalone at `/copilot`), **Memory Center**
(structured, taggable memory records with full CRUD).

**Per-Entity Intelligence** — seven workspaces, each an AI lens over one
entity type: Project, Site Report, Meeting, and Contract Intelligence (all
Partial — real data, but each is a light AI-lens layer with visible gaps
rather than a fully-realized module), Executive Intelligence (Complete,
also cross-listed under Analytics), and Intelligent Search / Email
Intelligence (both Planned — placeholder shells only).

**Flagship Modules** — six large, fully-built modules (Project Memory,
Predictive Intelligence, Supplier Risk Intelligence, Material Intelligence,
Cross-Project Learning, Executive Decision Center), each combining real
project/supplier identity with locally-generated, clearly-labeled
"Demo Data" analytics. Each is its own substantial sub-application: 6–11
component files, 375–561-line mock-data generators, full loading/empty/
error states. See `PAGE_INVENTORY.md` for the per-module breakdown.

### AI Center Overview — the approved design benchmark

`/ai-center` (workspace `overview`) is the one page in the entire app that
has been through a dedicated design pass and is now treated as the
canonical **AMAD v2** visual/UX reference. Its extracted, documented design
language lives in `../DESIGN/AMAD_DESIGN_SYSTEM.md` — every other page's
eventual migration is measured against that document, not against this
one's prose description of it.

## Administration

Admin-only (`AdminRoute` in `App.tsx` — the sole enforced role gate in the
routing layer). Users and Organizations are Complete and real; Audit Log,
Integrations, and Billing & Subscription are all placeholders with explicit
in-code phase labels (see `ROADMAP.md`).

## Client Portal

A fully placeholder section — three pages (Overview, Requests, Documents),
all explicitly labeled in code as "Phase 4 · Client Collaboration,"
`status="planned"`. No client-facing functionality exists yet; the section
exists in navigation so the planned surface area is visible rather than
only described in a slide deck.

## Authentication

Outside the sidebar `Layout` shell entirely — `/login` and
`/change-password` use their own two-column branded layout. Route guards
(`App.tsx`): unauthenticated users are redirected to `/login`; a user
flagged `must_change_password` is redirected to `/change-password` before
any other route is reachable (the server enforces the same rule
independently — the frontend redirect is UX only, not the real security
boundary); non-admins are redirected away from `/admin/*`.

## Future roadmap (as declared in code, not proposed here)

14 pages are not yet built. The app has its own built-in convention for
this — a shared `RoadmapPlaceholder` component carrying a `status`
(`in-development`/`planned`) and, on several pages, an explicit `phase`
label. The fullest breakdown, including which phase labels are literally
present in the code today, is in `ROADMAP.md`. In short: Risk Register and
Audit Log are the nearest-term ("Phase 2 · Operational Workflows"); Client
Portal is "Phase 4 · Client Collaboration"; Integrations and Billing are
"Phase 5 · Commercial Scale"; Tasks, Requests & Approvals, Notifications,
Intelligent Search, and Email Intelligence are `in-development` without a
recorded phase label.
