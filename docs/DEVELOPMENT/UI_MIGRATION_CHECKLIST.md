# AMAD v2 — UI Migration Checklist

Tracks which pages have been brought onto the AMAD v2 design system
(`../DESIGN/AMAD_DESIGN_SYSTEM.md` / `amad-v2-design-system.md`), extracted
from the approved AI Center Overview implementation. Grouped by sidebar
module, in suggested migration order within each group (see rationale in
`../PRODUCT/PAGE_INVENTORY.md`'s "Full detail" section for each page's
migration-priority note).

Placeholder/Planned pages are listed but **excluded from active migration
scope** — redesigning a "coming soon" stub before it has real content
returns little value; they're marked accordingly and should be revisited
once built (see `../PRODUCT/ROADMAP.md`).

Auth/system pages (Login, Change Password, Not Found) use their own
standalone layout outside the sidebar shell and are tracked separately at
the bottom rather than folded into the phase list.

## Phase 1 — Executive & high-visibility surfaces

- [ ] Executive Dashboard (`/`)
- [ ] Reports (`/reports`)
- [ ] Executive Intelligence (`/ai-center/executive`)
- [ ] Alerts (`/alerts`)

## Phase 2 — AI Center (15 remaining workspaces)

- [x] AI Center Overview (`/ai-center`) ✅ — **done; this is the benchmark the rest of this checklist migrates toward**
- [ ] Executive Decision Center (`/ai-center/executive-decision-center`)
- [ ] Project Memory (`/ai-center/project-memory`)
- [ ] Predictive Intelligence (`/ai-center/predictive-intelligence`)
- [ ] Supplier Risk Intelligence (`/ai-center/supplier-risk`)
- [ ] Material Intelligence (`/ai-center/material-intelligence`)
- [ ] Cross-Project Learning (`/ai-center/cross-project-learning`)
- [ ] AI Copilot (`/ai-center/copilot`, `/copilot`)
- [ ] Memory Center (`/ai-center/memory`)
- [ ] Project Intelligence (`/ai-center/projects`)
- [ ] Site Report Intelligence (`/ai-center/site-reports`)
- [ ] Meeting Intelligence (`/ai-center/meetings`)
- [ ] Contract Intelligence (`/ai-center/contracts`)
- [ ] Intelligent Search (`/ai-center/search`) — *placeholder, defer until built*
- [ ] Email Intelligence (`/ai-center/email`) — *placeholder, defer until built*

## Phase 3 — Operations (+ Documents)

- [ ] Operations Overview (`/operations`)
- [ ] Projects (`/projects`)
- [ ] Documents (`/documents`)
- [ ] Procurement (`/procurement`)
- [ ] Suppliers (`/suppliers`)
- [ ] Site Reports (`/site-reports`)
- [ ] Site Report Detail (`/projects/:projectId/site-reports/:reportId`)
- [ ] Safety & NCR (`/safety`)
- [ ] Meetings (`/meetings`)
- [ ] RFIs (`/rfis`)
- [ ] Change Orders (`/change-orders`)
- [ ] Claims (`/claims`)
- [ ] Meeting Detail (`/meetings/:projectId/:meetingId`)
- [ ] Project Detail (`/projects/:id`) — *highest complexity in the app; migrate last in this phase, after the pattern is proven on simpler pages*
- [ ] Risk Register (`/risks`) — *placeholder, defer until built*

## Phase 4 — Administration (+ remaining My Workspace)

- [ ] Users (`/admin/users`)
- [ ] Organizations / "Settings" (`/admin/organization`)
- [ ] Tasks (`/tasks`) — *placeholder, defer until built*
- [ ] Requests & Approvals (`/requests`) — *placeholder, defer until built*
- [ ] Notifications (`/notifications`) — *placeholder, defer until built*
- [ ] Audit Log (`/admin/audit-log`) — *placeholder, defer until built*
- [ ] Integrations (`/admin/integrations`) — *placeholder, defer until built*
- [ ] Billing & Subscription (`/admin/billing`) — *placeholder, defer until built*

## Phase 5 — Client Portal

All three pages are placeholders — this entire phase is deferred until the
section is actually built (per `ROADMAP.md`, "Phase 4 · Client
Collaboration" in the product's own roadmap labeling).

- [ ] Client Portal Overview (`/client-portal`) — *placeholder, defer*
- [ ] Client Requests (`/client-portal/requests`) — *placeholder, defer*
- [ ] Client Documents (`/client-portal/documents`) — *placeholder, defer*

## Not in migration scope (separate layout system)

- [ ] Login (`/login`)
- [ ] Change Password (`/change-password`)
- [ ] Not Found (404)

## Progress summary

- **Migrated**: 1 / 48 (AI Center Overview)
- **Active migration scope, not yet started**: 32 pages across Phases 1–4
- **Deferred (placeholder/planned — no real content to migrate yet)**: 12
  pages (9 Placeholder + 3 Planned — see `../PRODUCT/PAGE_INVENTORY.md`)
- **Out of scope (standalone auth/system layout)**: 3 pages
