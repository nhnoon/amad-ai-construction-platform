# AMAD — UX Guidelines

Interaction and content conventions observed across the built (Complete/
Partial) pages in this audit — behavior patterns, not visual tokens (those
live in `AMAD_DESIGN_SYSTEM.md` / `amad-v2-design-system.md`). Every
pattern below is drawn from at least one real page; none are proposed.

## Loading, empty, and error states — the three-state contract

Every Complete page in the app follows the same three-state contract for
any data-fetching section:

1. **Loading** → `Skeleton` (or the `.skeleton` CSS utility on
   earlier-built pages), shaped to roughly mirror the real content's
   layout rather than a generic block.
2. **Empty** → `EmptyState` — icon, title, one-line description, optional
   action. Reserved for "the whole page/panel has nothing," not for a
   momentarily-empty list inside an otherwise-populated page (those use a
   plain muted one-line message instead — see AI Center Overview's "No
   active alerts" example).
3. **Error** → `ErrorState` — destructive icon, title, description, and
   (where the underlying query supports it) a `Retry` action wired to
   `refetch()`.

Pages that skip one of these three states (mostly the Placeholder pages,
which skip all three because they fetch nothing) are noted as such in
`PAGE_INVENTORY.md`.

## "Demo Data" labeling — real vs. synthetic data honesty

Any figure, chart, or section sourced from local deterministic mock data
(not a real API response) carries a small gold `DemoDataBadge` /
`badge-gold` pill in the UI. Real, already-fetched data is left unlabeled.
This convention is used consistently across AI Center Overview and all six
Flagship Modules — the user should never have to guess whether a number on
screen is real. When migrating or building a page that mixes real and
synthetic data, this label is not optional polish; it's the app's
honesty mechanism.

## Search and scope

- `Ctrl/Cmd+K` focuses a page's primary search input where one exists
  (established on AI Center Overview; not yet wired on every page with a
  `SearchInput`).
- Project-scoped AI workspaces (Site Report Intelligence, Meeting
  Intelligence, and others) use a `Project Select` dropdown as the primary
  scope control, defaulting to a specific project rather than "all" where
  a portfolio-wide view isn't meaningful for that workspace.
- Portfolio-wide surfaces (AI Center Overview, Executive Intelligence, the
  Flagship Modules) default to "All Projects" scope with a per-project
  override available via `FilterSelect`.

## Tooltips over truncation

Where a compact row/card doesn't have room for full detail (e.g. AI Center
Overview's Attention Projects card, which stacks health score and delay
days into one cell), the full detail is placed in a native `title`
attribute tooltip rather than dropped — established explicitly during the
Overview's density-tuning pass and worth carrying forward to any similarly
tight layout.

## Drawers for record detail, not full navigation

Flagship Modules use a `Sheet`-based detail drawer (e.g.
`SupplierDetailDrawer`, `MaterialDetailDrawer`, `MemoryDetailDrawer`) to
show a single record's full detail without leaving the list/grid view —
the established pattern for "inspect one row without losing your place,"
as opposed to navigating to a dedicated detail route (which is reserved
for entities with their own first-class page, like Project Detail or
Meeting Detail).

## Forms

- Login and Change Password validate client-side (length, confirmation
  match) before submitting, and surface server errors inline rather than
  via toast.
- Meetings' "Create Meeting" and the Admin Users/Organizations pages use
  `Dialog`-based modal forms rather than a dedicated create/edit route.
- Destructive/state-changing admin actions (deactivate user, reset
  password) confirm via the existing `useToast` pattern for success/failure
  feedback, not a blocking `window.confirm`.

## Print support

Reports (`/reports`) is the one page in the app with dedicated print
styling (`print:hidden` / `print:block` utility classes) — worth reusing
directly rather than reinventing if another page later needs a printable
view (e.g. a future Risk Register export).

## AI analysis timing

Site Report Detail's on-demand AI analysis sets a client-side abort timeout
(75s) deliberately longer than the backend's own analysis ceiling (60s), so
the UI never races or cancels a legitimate in-flight backend run. Any
future page adding an on-demand AI analysis action should follow the same
"client timeout > server timeout" rule rather than picking an arbitrary
shorter value.

## Known content/naming inconsistency

The sidebar labels `/admin/organization` as **"Settings"**, but the page's
own title, breadcrumb, and content are all **"Organizations."** Flagged
here as a real, existing inconsistency — not something this documentation
pass corrects, since that would be a code change.

## Accessibility and RTL

Already governed by the brand guidelines
(`../../docs/brand/amad-brand-guidelines.md` §9–10) — focus-visible rings,
WCAG contrast targets, `start`/`end` logical properties instead of
hard-coded `left`/`right`, and full LTR/RTL testing expectations. Not
restated here; treat that document as authoritative for accessibility and
RTL, and this one as covering interaction/content patterns layered on top.
