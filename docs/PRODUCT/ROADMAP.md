# AMAD — Product Roadmap (as declared in code)

This is **not** a proposed roadmap. Every phase label below is quoted
verbatim from the `phase` prop passed into `components/roadmap-placeholder.tsx`
on the actual placeholder page it appears on — this document only collects
those declarations in one place. Where a placeholder page exists but its
`phase` prop isn't one of the labels below, that's stated explicitly rather
than guessed at.

`RoadmapPlaceholder` (`components/roadmap-placeholder.tsx`) takes a
`status: "in-development" | "planned"` and a `phase: string`, and renders a
capability-preview list alongside a status badge — this is the app's own
built-in "coming soon" convention, already used consistently across every
unbuilt module.

## Phase 2 · Operational Workflows

Declared explicitly in code on:

- **Risk Register** (`/risks`) — `status="in-development"`

Confirmed by the audit but without a re-verified exact phase string on this
pass:

- **Audit Log** (`/admin/audit-log`) — `status="in-development"`, phase
  string recorded during the audit as "Phase 2"; re-check the component's
  literal `phase` prop before quoting it externally.

## Phase 4 · Client Collaboration

Declared explicitly in code, identically, on all three Client Portal pages:

- **Client Portal Overview** (`/client-portal`) — `status="planned"`
- **Client Requests** (`/client-portal/requests`) — `status="planned"`
- **Client Documents** (`/client-portal/documents`) — `status="planned"`

## Phase 5 · Commercial Scale

Declared explicitly in code on:

- **Integrations** (`/admin/integrations`) — `status="planned"`
- **Billing & Subscription** (`/admin/billing`) — `status="planned"`

## Unlabeled in code (status known, phase not recorded)

These render the same `RoadmapPlaceholder` shell with a `status` prop, but
the audit pass did not capture an explicit `phase` string for them — rather
than invent one, they're grouped here as "not yet phase-assigned" pending a
direct read of each component's `phase` prop:

- **Tasks** (`/tasks`) — `status="in-development"`
- **Requests & Approvals** (`/requests`) — `status="in-development"`
- **Notifications** (`/notifications`) — `status="in-development"`
- **Intelligent Search** (`/ai-center/search`) — `status="in-development"`
- **Email Intelligence** (`/ai-center/email`) — `status="in-development"`

## What "in-development" vs "planned" means here

Both are pre-build states — neither has real data or logic — but the app's
own convention distinguishes them (`STATUS_LABEL`/`STATUS_BADGE` in
`roadmap-placeholder.tsx`): `in-development` renders an info-blue badge,
`planned` renders a gold badge. Treat `in-development` pages as the nearer-
term backlog and `planned` pages as further out, per the app's own signal —
this document doesn't add a separate timeline on top of that.

## Everything else is already built

Every page not listed above and not marked Placeholder/Planned in
`PAGE_INVENTORY.md` is real, working product today (Complete or Partial),
including all six AI Center Flagship Modules, all of Operations, Documents,
Reports, and the AI Center Overview (the approved v2 design benchmark).
This roadmap file only tracks what is *not yet built* — see
`PAGE_INVENTORY.md` for the complete current-state picture, and
`../DEVELOPMENT/UI_MIGRATION_CHECKLIST.md` for the separate (unrelated)
question of which *already-built* pages still need the v2 visual design
applied.
