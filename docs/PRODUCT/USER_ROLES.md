# AMAD — User Roles

Two sources, both already in the codebase — nothing here is invented:

1. **The actual authorization roles** the backend/frontend recognize, from
   `components/layout.tsx`'s `ROLE_LABELS` map (used for the sidebar's role
   badge) and `AdminRoute`'s `user.role !== "admin"` check in `App.tsx`:
   `admin`, `executive`, `project_manager`, `site_engineer`,
   `procurement_officer`, `safety_quality_officer`, `viewer`.
2. **The primary-user inference per page**, from the page inventory audit —
   i.e., which role a page's content is clearly built for, based on what it
   actually displays (not a formal permissions system; the app does not
   currently gate individual pages by role beyond the single
   admin/non-admin split in `App.tsx`'s `AdminRoute`).

Only `admin` is enforced in code as a route guard today. Every other role
below is an inferred audience, not an access-control boundary — any
authenticated non-admin user can currently reach any non-`/admin/*` page
regardless of their role.

## admin

Enforced by `AdminRoute` in `App.tsx` — the only role-gated route group.

- Users (`/admin/users`)
- Organizations / "Settings" (`/admin/organization`)
- Audit Log (`/admin/audit-log`) — placeholder
- Integrations (`/admin/integrations`) — placeholder
- Billing & Subscription (`/admin/billing`) — placeholder

## executive

Inferred primary audience — dashboards, portfolio-wide analytics, and
decision-support surfaces built around aggregate figures rather than
record-level data entry.

- Executive Dashboard (`/`)
- Alerts (`/alerts`)
- Reports (`/reports`)
- Executive Intelligence (`/ai-center/executive`, cross-listed as "Insights")
- Executive Decision Center (`/ai-center/executive-decision-center`)
- Predictive Intelligence (`/ai-center/predictive-intelligence`)
- Supplier Risk Intelligence (`/ai-center/supplier-risk`) — shared with Procurement Officer
- Material Intelligence (`/ai-center/material-intelligence`) — shared with Procurement Officer
- Cross-Project Learning (`/ai-center/cross-project-learning`) — shared with all PM/cross-functional
- Operations Overview (`/operations`) — shared with Project Manager
- Projects (`/projects`) — shared with Project Manager
- Project Intelligence (`/ai-center/projects`) — shared with Project Manager
- AI Center Overview (`/ai-center`) — shared with all AI Center users

## project_manager

Inferred primary audience — the role touching the most pages in the app,
consistent with PM being the day-to-day operator of most Operations
modules.

- Operations Overview (`/operations`)
- Projects (`/projects`) / Project Detail (`/projects/:id`)
- Meetings (`/meetings`) / Meeting Detail (`/meetings/:projectId/:meetingId`)
- RFIs (`/rfis`)
- Change Orders (`/change-orders`) — shared with Commercial/Contracts
- Site Reports (`/site-reports`) / Site Report Detail — shared with Site Engineer
- Risk Register (`/risks`) — placeholder, shared with Executive
- Memory Center (`/ai-center/memory`)
- Project Memory (`/ai-center/project-memory`)
- Meeting Intelligence (`/ai-center/meetings`)
- Project Intelligence (`/ai-center/projects`)
- Tasks (`/tasks`) — placeholder

## site_engineer

Inferred primary audience — field-data-entry and site-condition pages.

- Site Reports (`/site-reports`) / Site Report Detail
- Safety & NCR (`/safety`) — shared with Safety Officer
- Project Detail (`/projects/:id`) — shared with PM/Executive
- Site Report Intelligence (`/ai-center/site-reports`)

## procurement_officer

Inferred primary audience — supply-chain and vendor pages.

- Procurement (`/procurement`)
- Suppliers (`/suppliers`)
- Supplier Risk Intelligence (`/ai-center/supplier-risk`) — shared with Executive
- Material Intelligence (`/ai-center/material-intelligence`) — shared with Executive
- Email Intelligence (`/ai-center/email`) — placeholder, intended audience

## safety_quality_officer

Inferred primary audience.

- Safety & NCR (`/safety`)
- Site Reports (`/site-reports`) — shared with Site Engineer/PM (risk/safety/quality indicator badges)

## Commercial / Contracts / Legal

Appears consistently as a primary-user inference across several pages, but
has **no corresponding entry in the backend's role enum** — worth flagging
as a gap between the product's implied audience and the actual
authorization model.

- Change Orders (`/change-orders`)
- Claims (`/claims`)
- Contract Intelligence (`/ai-center/contracts`)
- RFIs (`/rfis`)

## Client / External Stakeholder (future — not yet a real role)

Every page this role would use is a placeholder; the role itself does not
appear in the backend's role enum at all. This is a purely aspirational
audience described only in the placeholder pages' own capability-preview
copy.

- Client Portal Overview (`/client-portal`)
- Client Requests (`/client-portal/requests`)
- Client Documents (`/client-portal/documents`)

## viewer

Present in the backend role enum (`ROLE_LABELS.viewer` = "Viewer") but no
audited page names "Viewer" as its specific primary user — implied to be a
read-only variant of whichever pages a `viewer` account is granted access
to, rather than a role with its own dedicated surfaces.

## All users (no specific role inference)

Pages whose content is role-agnostic utility, not built around one role's
workflow.

- Documents (`/documents`)
- Requests & Approvals (`/requests`) — placeholder
- Notifications (`/notifications`) — placeholder
- AI Copilot (`/ai-center/copilot`, `/copilot`)
- Intelligent Search (`/ai-center/search`) — placeholder
- Login (`/login`) — unauthenticated
- Change Password (`/change-password`)
- Not Found (404)
