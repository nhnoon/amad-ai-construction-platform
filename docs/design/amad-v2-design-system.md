# AMAD v2 — Master Design System

**Status: approved benchmark.** Extracted from the final, shipped AI Center
Overview implementation (`artifacts/web/src/pages/ai-center/workspaces/Overview.tsx`
and its primitives). This document does not invent new design language — it
names and centralizes the rules that page already follows, so every page
migrated to "v2" can be verified against a checklist instead of eyeballing a
reference screenshot.

For brand-level identity (logo, full color palette, type scale, motion,
accessibility, RTL) see `docs/brand/amad-brand-guidelines.md` — that remains
the source of truth for those topics; this document only adds the
component/layout implementation layer on top of it.

Token source: `artifacts/web/src/index.css` (`:root` / `.dark`). Component
source: `artifacts/web/src/components/*`.

---

## 1. Page shell

Every routed page renders inside `Layout` (`components/layout.tsx`):

```
<div class="min-h-screen flex w-full bg-background">
  <aside> … sidebar … </aside>
  <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
    <header class="h-12 …">  <!-- utility topbar, see §5 -->
    <main class="flex-1 overflow-auto">
      <div class="p-4 md:p-5 lg:p-6 max-w-screen-2xl mx-auto">
        {page content}
      </div>
    </main>
  </div>
</div>
```

A page's own root element is a single `<div className="space-y-6">` — every
top-level section of the page (hero, brief, KPI strip, card rows, trend
panel) is a direct child, spaced by that one `space-y-6`, never by per-section
margins. This is the pattern in `Overview.tsx:326`.

## 2. Maximum content width

`max-w-screen-2xl`, centered (`mx-auto`), applied once in `Layout`'s `<main>`
wrapper — not per-page. No page should re-apply its own max-width.

## 3. Responsive grid

Standard gap between grid siblings at the section level is `gap-3`
(0.75rem). Common patterns seen in Overview.tsx:

| Layout | Classes | Used for |
|---|---|---|
| Two-column, fixed side panel | `grid gap-3 lg:grid-cols-[1fr_300px] items-stretch` | Executive Brief + Mini Heat Map |
| Five-up KPI strip | `grid grid-cols-2 sm:grid-cols-5 gap-2.5` | KPI cards (tighter `gap-2.5`) |
| Equal thirds | `grid gap-3 lg:grid-cols-3 items-stretch` | Today's Attention / Recommendations / Attention Projects |
| Wide chart + fixed side panel | `grid gap-3 lg:grid-cols-[1fr_400px]` | KPI Trends + Quick Access |
| Dense inner grid | `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3` | KPI Trends sparkline cells |

Rule of thumb: mobile stacks to 1 column by default; `sm:`/`lg:` breakpoints
introduce the multi-column layout. `items-stretch` is used whenever sibling
cards must match height regardless of content length.

## 4. Sidebar behavior

`components/layout.tsx` + `components/sidebar-item.tsx`.

- Fixed on mobile (slide-in, `-translate-x-full` / RTL `translate-x-full`,
  backdrop overlay), `md:relative` and always visible on desktop.
- Width: `md:w-[220px]` expanded, `md:w-[64px]` collapsed (icon rail).
  Collapsed state persists in `localStorage` (`amad_sidebar_collapsed`).
- **Accordion navigation**: sections are titled groups; only one titled
  group is expanded at a time (`expandedGroup` state). Opening a group, or
  navigating to a route inside it, auto-collapses the others
  (`findActiveGroupKey`). The untitled top group (Dashboard/Documents)
  always renders, un-collapsible.
- Every row — top-level link, group header, or nested child — renders
  through the single shared `SidebarItem` component: same height (`h-9`),
  padding, icon size (`w-4 h-4`), hover/active treatment. Child rows differ
  only by `indent` (`ps-7` vs `ps-3`); group headers differ only by a
  trailing chevron that rotates 90° when expanded.
- Active row: `bg-sidebar-primary/15 text-sidebar-primary font-semibold`
  plus a 3px gold left rail (`absolute inset-y-1 start-0 w-[3px] rounded-full
  bg-sidebar-primary`).
- Large sections (AI Center, 16 items) may add a `subgroup` micro-label —
  `text-[10px] font-semibold uppercase tracking-[0.12em]
  text-sidebar-foreground/35` — a presentational-only divider, not a new
  collapsible level.
- Brand header: gold rounded-square logo chip (`w-9 h-9 rounded-lg
  bg-sidebar-primary`, `ring-1 ring-sidebar-primary/40`) + wordmark.
- Bottom: user card (`bg-sidebar-accent/40 border border-sidebar-border/60`)
  + theme/language toggles + sign out, all rendered as the same row style
  used elsewhere (icon + label, `text-xs`).

## 5. Top header behavior

`Layout`'s `<header>` is a **minimal utility bar only** — `h-12`,
`bg-card/80 border-b backdrop-blur-sm`, sticky (`sticky top-0 z-10`).
Contents: mobile nav toggle (hidden on `md:`), role badge, avatar circle.
**It does not repeat the page title** — every page renders its own title via
`PageHero` (landing pages) or `PageContextHeader` (detail/list pages)
directly below it, so the title appears exactly once.

## 6. Page title and subtitle treatment

Two approved patterns, chosen by page type — do not invent a third:

- **Landing/command pages** (e.g. AI Center Overview): `PageHero` — a
  navy `bg-sidebar` band (see §16) with a gold uppercase eyebrow
  (`text-[10px] font-bold uppercase tracking-[0.18em] text-sidebar-primary`),
  an `h1` (`text-xl md:text-2xl font-bold tracking-tight`), and a one-line
  description (`text-[13px] text-sidebar-foreground/70`).
- **List/detail pages**: the existing `.page-title` (`text-xl font-bold
  tracking-tight text-foreground`) / `.page-subtitle` (`text-sm
  text-muted-foreground mt-0.5`) utility classes inside `PageContextHeader`,
  on the neutral `bg-background` surface, not navy.

`.section-title` (`text-sm font-semibold text-foreground`) is for a
mid-page subsection heading — visually distinct from both of the above and
from `.panel-title`.

## 7. Search and scope controls

- Primary page search: shared `SearchInput` (`components/search-input.tsx`)
  — leading `Search` icon + `Input`, `h-9`, `ps-9`. A `compact` variant
  (`h-8`, `ps-8`, `text-xs`) exists for toolbar-embedded filters.
- Scope/context switching (e.g. "All Projects" vs one project): shared
  `FilterSelect` (`components/filter-select.tsx`) — native `<select>`,
  `h-9 rounded-lg border border-input bg-background px-3 text-sm`.
- On `PageHero` specifically, search and scope sit in a second row below a
  top border (`pt-3 border-t border-sidebar-border/60`), search capped at
  `max-w-sm`, scope selector `shrink-0`, with an optional `Ctrl+K` hint
  badge overlaid inside the search box (`text-[9px]` pill, `hidden md:inline-flex`).
- Keyboard shortcut convention: `Ctrl/Cmd+K` focuses the page's primary
  search input.

## 8. Card backgrounds

- Default surface: `.panel` → `bg-card` (white in light mode, `#0E1929` in
  dark). This is the only card background token used for panels, KPI
  cards, and list containers.
- The one exception is `PageHero`, which deliberately uses the sidebar's
  navy surface (`bg-sidebar`) to read as an anchor/command moment distinct
  from the neutral card language everywhere else on the page. This is a
  closed set — do not introduce a third background surface.

## 9. Border colors

- Cards/panels: `.panel`'s default `border` (→ `--border` /
  `--card-border` family via Tailwind's `border-border`).
- `PageHero` and other navy surfaces use `border-sidebar-border` /
  `border-sidebar-border/60` instead — never mix the two token families on
  one element.
- Emphasis border: the one "authoritative" panel per page (`InsightPanel
  variant="brief"`) uses `border-accent/25` instead of the neutral border,
  plus a solid `bg-accent` 1px left rule (`absolute inset-y-0 start-0 w-1
  bg-accent`) — reserved for exactly one panel per page.
- Dividers inside a panel (header/footer separators): `border-b`,
  `border-t border-border/50` or `/60` (lighter than the outer card border).

## 10. Border radius

| Token | Value | Used for |
|---|---|---|
| `--radius` (base) | `0.375rem` (6px) | — |
| `rounded-md` (`--radius-md`) | 4px | small controls, table cells |
| `rounded-lg` (`--radius-lg`) | 6px | inputs, buttons, sidebar rows, quick-link cards |
| `rounded-xl` (`--radius-xl`) | 10px | `.panel` (all standard cards) |
| `rounded-2xl` | 16px (Tailwind default, not a CSS var) | `PageHero` only — the one larger-radius surface on a page |
| `rounded-full` | — | badges, avatars, icon circles, sparkline dots |

Rule: `.panel` is always `rounded-xl`; `PageHero` is the sole `rounded-2xl`
element; nothing on a page should introduce a radius outside this set.

## 11. Shadows

- `.panel` → `shadow-sm` (barely-there, card separation without heaviness).
- `PageHero` and `InsightPanel` → `shadow-md` (the two "elevated" surfaces
  on a page — hero and the single authoritative brief panel).
- Hover lift on interactive cards (`KpiStat` with `href`,
  `WorkspaceQuickLink` card variant): `hover:-translate-y-0.5
  transition-all duration-150` combined with a border-color change
  (`hover:border-primary/30`) — no shadow increase on hover, translation +
  border carries the affordance.

## 12. Gold accent usage

Gold (`--accent` / `--sidebar-primary`, `44 58% 52%` light / `44 62% 62%`
dark) is reserved, controlled, never decorative filler:

- The hero eyebrow label and the sidebar's active-group icon/indicator.
- Exactly one panel's accent rule per page (`InsightPanel variant="brief"`)
  and its icon chip (`bg-accent/10 text-accent`).
- `KpiStat tone="gold"` — reserved for the page's single "AI-derived
  confidence/quality" metric, not general emphasis.
- The `DemoDataBadge` badge (`badge-gold`) — gold here specifically means
  "synthetic," not "important."
- Hero primary action outline (`border-sidebar-primary/50
  text-sidebar-primary`).

Do not use gold for generic call-to-action buttons, generic active states
outside the sidebar/hero, or more than one "brief"-style panel per page —
brand guideline §4.6 already prohibits gold-on-gold and excessive gold
coverage; v2 additionally treats it as a **cardinality-limited** accent
(at most a small, fixed set of elements per page).

## 13. Typography sizes and weights

Beyond the brand type scale (brand-foundation §5.2), the v2 implementation
layer adds a **compact/dense scale** used specifically inside panels and
list rows, expressed as arbitrary Tailwind sizes (not new CSS tokens, since
Tailwind v4 doesn't need them for one-off values):

| Size | Weight | Usage |
|---|---|---|
| `text-xl md:text-2xl` / `font-bold` | Hero `h1` |
| `text-[13px]` | Hero description, `InsightPanel` body text, secondary panel headers |
| `text-sm` (14px) / `font-semibold` | `InsightPanel` title (brief variant), `.panel-title` |
| `text-xs` (12px) / `font-semibold` | compact panel header titles (e.g. "Today's Attention") |
| `text-[11px]` / `font-semibold` | row titles (`AttentionRow`/`CompactRow`), `KpiStat` label |
| `text-[10px]` | KPI description line, table micro-headers |
| `text-[9.5px]` | row subtitle (the smallest regular text on the page) |
| `text-[9px]` | badges, delta captions, quick-link meta — the floor of the scale |
| `text-xl` / `font-bold` `.kpi-number` | `KpiStat size="lg"` value |
| `text-base` / `font-bold` `.kpi-number` | `KpiStat size="sm"` value |

All numeric values (`kpi-number`, table figures) use `.tabular-nums` /
`.kpi-number` (`font-variant-numeric: tabular-nums`, `letter-spacing:
-0.02em`) — never plain text for a metric.

## 14. Section headers

Panel-internal section header row: `px-3.5 py-2.5 border-b flex
items-center justify-between` (standard density) or the tighter `px-3 py-1`
used by the three equal-width cards (§17). Title is `.panel-title`
(`font-semibold text-sm`) or the smaller `text-xs`/`text-[13px]` variants
from §13 depending on the panel's density tier. A trailing badge (demo tag)
or "View all →" link sits at the row's end, never wrapped to a second line.

## 15. KPI cards

`components/KpiStat.tsx`. Two sizes (`lg`/`sm`), five tones (`neutral`,
`success`, `warning`, `danger`, `gold`). Anatomy, top to bottom:

1. Row: circular tone-tinted icon badge (`w-7 h-7` lg / `w-6 h-6` sm,
   `rounded-full`) + label (`text-[11px] font-semibold text-muted-foreground`),
   optional `DemoDataBadge` at the row end.
2. Value: `.kpi-number font-bold` (`text-xl` lg / `text-base` sm), optional
   suffix, optional one-line description (`text-[10px] text-muted-foreground`).
3. Optional delta row, pinned to the card bottom (`mt-auto pt-2 border-t
   border-border/40`): trend icon + colored percentage + caption
   (`text-[10px]`). Delta color is driven by `deltaPositive`, independent of
   direction — a rising risk metric is still "bad" even though it went up.

Card shell is `.panel` (`p-3.5` lg / `p-2.5` sm), optionally wrapped in a
`Link` with the standard hover-lift (§11) when `href` is supplied.

## 16. Primary panels

`components/InsightPanel.tsx`, `variant="brief"`. The one panel per page
allowed to visually dominate: `shadow-md`, `border-accent/25`, solid gold
left rule, larger padding (`py-4`) and title size (`text-sm`) than a
standard panel. Composition: icon chip + title + optional badge row, body
content, optional footer separated by `border-t border-border/50`. There
should be at most one `variant="brief"` `InsightPanel` on a page.

## 17. Secondary panels

Everything else built on `.panel` (`rounded-xl border bg-card shadow-sm`).
Two observed density tiers inside Overview.tsx, both valid depending on
how much a section needs to fit above the fold:

- **Standard**: header `px-3.5 py-2.5`, body `p-3`. Used by the Mini Heat
  Map and KPI Trends / Quick Access panels.
- **Compact**: header `px-3 py-1`, body `p-1.5`. Used by the three
  equal-width cards (Today's Attention, Executive Recommendations,
  Attention Projects) specifically because three cards must share one row
  without vertical overflow. `InsightPanel variant="decision"` is the
  primitive equivalent of this tier when the section also needs the
  icon-chip/title header treatment.

Don't mix tiers within the same card — a panel is either standard or
compact throughout its header/body/footer.

## 18. Compact list rows

Two row primitives, deliberately kept separate rather than unified behind a
density prop (see the in-file rationale in `Overview.tsx`):

- `AttentionRow` — `px-1.5 py-1`, `w-6 h-6` icon circle, `leading-tight`.
  Used only inside the Executive Brief's "Top Signals" list, which must
  stay pixel-stable.
- `CompactRow` — `px-1.5 py-0`, `w-5 h-5` icon circle, `leading-[1.15]`.
  Used only inside Today's Attention and Executive Recommendations, where
  five rows must fit one compact card.

Shared anatomy for both: leading tone-tinted icon circle, title (`text-[11px]
font-semibold truncate`) + optional subtitle (`text-[9.5px]
text-muted-foreground truncate`), trailing end-aligned badge + meta text.
**Known duplication — see §33.**

## 19. Tables

The sitewide `.data-table` utility class (`index.css`) remains the standard
for real tabular data (header `bg-muted/50`, `text-xs uppercase
tracking-wide` column labels, `px-3 py-2` cells, row hover `hover:bg-muted/30`).

Overview.tsx's Attention Projects card uses a **lighter, non-`<table>`
pattern** instead — a CSS grid (`grid-cols-[auto_1fr_auto]`) with a
`text-[9px] uppercase tracking-wide` label row standing in for `<thead>`,
because the card is link-rows (each row navigates to a project) rather than
a data-inspection table. Use `.data-table` for genuine tabular data; use the
grid-row pattern only for a short, clickable "top N" list where secondary
columns are collapsed into one stacked, right-aligned cell with a `title`
tooltip for the full detail (exactly what Attention Projects does with
health score + delay days).

## 20. Tabs

Shared primitive: `PageTabs` (`components/page-tabs.tsx`), wrapping the
Radix-based `Tabs`/`TabsList`/`TabsTrigger` (`components/ui/tabs.tsx`).
Default `TabsList` is `h-9 rounded-lg bg-muted p-1`; active trigger gets
`bg-background text-foreground shadow`.

Overview.tsx's Today's Attention card needs a shorter tab strip to fit its
compact header — rather than editing the shared `Tabs` primitive (which
would affect every other page using it, e.g. Meetings), it applies a
**scoped Tailwind arbitrary-variant override** on the wrapping `div` only:
`[&_[role=tablist]]:!h-6 [&_[role=tab]]:!py-0 [&_[role=tablist]]:!mb-0`.
This is the sanctioned pattern for a page-local tab-density exception:
override via a scoped descendant selector on a local wrapper, never edit
`ui/tabs.tsx` itself.

## 21. Filters

`FilterSelect` (native `<select>`, §7) for single-value scope/category
filters. `FilterChip` (`components/filter-chip.tsx`, pre-existing) remains
the pattern for multi-value/toggleable filter pills elsewhere in the app —
Overview.tsx doesn't use chips itself (it filters Quick Access by the hero
search box instead), so no new filter-chip convention was introduced here.

## 22. Buttons

Two coexisting patterns:

- **Standard card-surface actions**: the shared `Button`
  (`components/ui/button.tsx`, `cva`-based variants — `default`,
  `destructive`, `outline`, `secondary`, `ghost`, `link`; sizes `default`
  `min-h-9`, `sm` `min-h-8`, `lg` `min-h-10`, `icon` `h-9 w-9`). This is the
  default choice for any button on a `.panel`/neutral surface.
- **Hero actions on the navy surface**: `PageHero`'s `primaryAction` slot
  hand-rolls buttons directly against `sidebar-*` tokens instead of using
  `Button` (e.g. the Alerts icon button: `border border-sidebar-border
  … hover:bg-sidebar-accent/50`; the "AI Brief" link: `border
  border-sidebar-primary/50 text-sidebar-primary hover:bg-sidebar-primary/10`).
  This is intentional, not a missed reuse — `Button`'s variants are tuned
  for card-surface contrast and don't have a sidebar-token variant. Any
  future hero action should follow this same hand-rolled-but-consistent
  `sidebar-border`/`sidebar-primary` pattern rather than forcing `Button`
  onto the navy surface.

Both patterns share `h-9`/`w-9` sizing and `rounded-lg` — they read as one
button height system even though they're two implementations.

## 23. Badges

`.badge` base (`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs
font-medium`) + one semantic modifier: `-success`, `-warning`, `-danger`,
`-info`, `-neutral`, `-purple`, `-gold`, `-brand` (all defined in
`index.css`, unchanged this pass). Inside dense rows/cards, badges are
downsized with an inline `text-[9px]` override rather than a new badge
size variant — e.g. `<span className="badge text-[9px] badge-danger">`.
Severity → badge tone mapping is a small local `Record` (`SEV_BADGE`) kept
per-page; not yet centralized (see §33).

## 24. Demo Data labels

Every synthetic/mock-sourced figure or section carries the shared
`DemoDataBadge` (`components/DemoDataBadge.tsx`, new this pass —
`badge badge-gold text-[9px]`, default label `"Demo Data"`, `label="Demo"`
for tighter header slots). Real, already-fetched data carries no label.
`KpiStat`'s `demo` boolean prop now renders through this same component.
This was previously five inline copies of the identical span in
`Overview.tsx` plus one in `KpiStat.tsx` — now one component, zero visual
change.

## 25. Charts

Recharts, per brand guideline §7 (gold as primary series, 5-color palette,
no arbitrary chart colors for real analytical charts). Overview.tsx's KPI
Trends section uses a lighter **sparkline** treatment for at-a-glance demo
trends (`MiniSparkline` — `AreaChart`, `h-6`, gradient fill fading to 0
opacity, `strokeWidth={1.75}`, `isAnimationActive={false}`, no axes/legend/
tooltip) — appropriate only for a small inline trend indicator sitting next
to its own numeric value, never as a page's primary/only chart. A full
analytical chart (with axes, legend, tooltip) should still follow the
brand guideline's chart rules directly, not this sparkline pattern.

## 26. Drawers

No drawer is used on AI Center Overview itself. The existing sitewide
pattern (`components/ui/sheet.tsx`, Radix Dialog-based, used by e.g.
`AIDrawer`) already follows the same card language — `bg-background`
content panel, `text-lg font-semibold` header title, `text-sm
text-muted-foreground` description — and needs no change to stay
consistent with this document. Future drawers should keep using `Sheet`
as-is; nothing here supersedes it.

## 27. Empty states

Shared `EmptyState` (`components/ui/empty-state.tsx`), built on the
`.empty-state*` utility classes: centered icon (`w-12 h-12
text-muted-foreground/40`), title, optional description (`max-w-sm`),
optional action. Overview.tsx uses it once, page-level, when there are no
projects at all — the canonical "nothing to show yet" case. Smaller,
section-local empty states (e.g. "No active alerts", "Nothing pending")
are a plain `text-xs text-muted-foreground py-2` line, not a full
`EmptyState` — reserve `EmptyState` for a whole page/panel having no data,
not for a momentarily-empty list inside an otherwise-populated page.

## 28. Loading states

Two coexisting skeleton implementations, both currently valid:

- `ui/skeleton.tsx`'s `Skeleton` (`animate-pulse bg-primary/10
  rounded-md`) — what `Overview.tsx` uses for its full-page loading
  fallback, shaped to mirror the real layout (hero, brief+heatmap row, KPI
  strip, trends panel) at the same heights/radii the loaded page will use.
- `.skeleton` CSS utility (`index.css`) — a gradient shimmer
  (`skeleton-shimmer`, 1.6s) on `bg-muted`, used by other, earlier-built
  pages.

**Known duplication — see §33.** Until consolidated, match whichever one
the rest of the page/module already uses; for any new page built against
this document, prefer `Skeleton` (the component) since that's what the
approved benchmark page uses, and shape skeletons to the real layout's
proportions rather than a generic block.

## 29. Error states

Shared `ErrorState` (`components/ui/error-state.tsx`) — `.panel
.panel-body`, centered `AlertOctagon` (`text-destructive opacity-60`),
title + description, optional retry action. Overview.tsx uses it
page-level with a `Retry` action wired to `refetch()`. This is the only
approved error-state treatment; don't hand-roll a red box elsewhere.

## 30. Spacing and padding

- Page-level vertical rhythm: `space-y-6` between top-level sections (§1).
- Grid gaps: `gap-3` standard, `gap-2.5` for the KPI strip specifically.
- Panel padding tiers: `p-4`/`px-4 py-3` (`.panel-body`/`.panel-header`
  defaults) → `p-3`/`px-3.5 py-2.5` (standard secondary panel, §17) →
  `p-1.5`/`px-3 py-1` (compact tier, §17). Pick the tier per §17's guidance,
  don't invent an intermediate value.
- Row-internal gaps: `gap-1.5` (icon-to-text in compact rows), `gap-2`–`gap-2.5`
  (header rows, KPI card internals).

## 31. Breakpoints

Tailwind defaults, used consistently: unprefixed = mobile, `sm:` (640px)
introduces the first multi-column step (e.g. KPI strip 2→5 cols), `md:`
(768px) is the sidebar's desktop/mobile split point, `lg:` (1024px)
introduces the wide multi-column page layouts (hero side panels, the
equal-thirds row, KPI Trends + Quick Access). No custom breakpoints are
defined in `tailwind`/`index.css`.

## 32. Hover and focus states

- Hover: `transition-colors`/`transition-all duration-150`, typically a
  border-color shift (`hover:border-primary/30`) and/or background tint
  (`hover:bg-muted/60`, `hover:bg-muted/50`); interactive cards add
  `hover:-translate-y-0.5` (§11).
- Focus: global `:focus-visible` rule in `index.css` — `2px solid
  hsl(var(--focus-ring))`, `outline-offset: 2px`, keyboard-only (never on
  pointer click). Buttons/links get a slightly larger `border-radius: 4px`
  on the outline vs the generic `2px`. No page should override or suppress
  this.

## 33. Dark mode behavior

Entirely token-driven — every class in this document (`bg-card`,
`bg-sidebar`, `border-border`, `text-accent`, etc.) resolves through the
`.dark` CSS variable overrides in `index.css`; no component in Overview.tsx
branches on theme in JS. The only two structural differences dark mode
introduces, per brand guideline §8, are already respected by every
primitive listed here: gold is brighter in dark mode (`44 62% 62%` vs
`44 58% 52%`), and semantic badge colors swap to their `dark:` Tailwind
utility variants (e.g. `dark:bg-emerald-900/30 dark:text-emerald-400`) —
never simulated via opacity alone.

---

## Design tokens identified

All pre-existing in `artifacts/web/src/index.css`; nothing added or renamed.
Confirmed as the complete token surface Overview.tsx draws from: `--background`,
`--foreground`, `--card`/`--card-foreground`/`--card-border`, `--primary`,
`--secondary`, `--muted`/`--muted-foreground`, `--accent`, `--destructive`,
`--border`/`--input`/`--ring`, `--sidebar` family (7 tokens), `--chart-1`
through `--chart-5`, `--radius` (+ derived `sm`/`md`/`lg`/`xl`),
`--focus-ring`, `--transition-fast/base/slow`. Both light (`:root`) and dark
(`.dark`) value sets are unchanged.

## Shared primitives created or updated

- **New**: `components/DemoDataBadge.tsx` — extracted the identical
  `badge badge-gold text-[9px]` "Demo"/"Demo Data" span that appeared five
  times in `Overview.tsx` and once in `KpiStat.tsx` into one component.
  Zero visual change (verified: same class string, same markup).
- **Updated**: `KpiStat.tsx` now renders its `demo` badge through
  `DemoDataBadge`.
- **Updated**: `Overview.tsx` now renders its five demo badges through
  `DemoDataBadge`.
- All other primitives referenced in this document (`PageHero`, `KpiStat`,
  `InsightPanel`, `WorkspaceQuickLink`, `SidebarItem`, `SearchInput`,
  `FilterSelect`, `PageTabs`, `EmptyState`, `ErrorState`, `Skeleton`) are
  documented as-is — none were modified.

## Files modified

- `artifacts/web/src/components/DemoDataBadge.tsx` (new)
- `artifacts/web/src/components/KpiStat.tsx`
- `artifacts/web/src/pages/ai-center/workspaces/Overview.tsx`
- `docs/design/amad-v2-design-system.md` (new — this document)

No other page, route, or the six flagship AI modules' own files were
touched.

## Duplication to remove during later migrations

Documented above, deliberately **not** touched this pass (each would
require editing files outside this task's scope — other pages or the
flagship modules — or re-opening a just-finalized pixel-perfect layout):

1. **`AttentionRow` vs `CompactRow`** (§18, `Overview.tsx`) — near-identical
   row components differing only in padding/icon-size/line-height, kept
   separate specifically to protect the Executive Brief's pixel-stable
   list from the three cards' density work. A future pass could unify them
   behind a `density="cozy" | "compact"` prop once there's no active
   density-tuning risk.
2. **Per-module `DemoDataBadge`/`CHART_TOOLTIP_STYLE`/palette duplication**
   across the six flagship modules' own `shared.tsx` files (Project
   Memory, Predictive Intelligence, Supplier Risk, Material Intelligence,
   Cross-Project Learning, Executive Decision Center) — each independently
   redefines the same demo-badge markup, chart tooltip style object, and
   tone/color maps. Now that `DemoDataBadge` exists centrally, each
   module's local copy is a candidate for replacement the next time that
   module is touched — but per standing instructions those files stay
   untouched until then.
3. **Two coexisting skeleton implementations** (§28) — `ui/skeleton.tsx`'s
   `Skeleton` (used by Overview.tsx) vs the `.skeleton` CSS shimmer utility
   (used elsewhere). Should converge on one during migration rather than
   picking per-page.
4. **`SEV_BADGE`/`SEV_ICON_BG`-style severity→tone maps** — small local
   `Record`s re-declared per page/module (Overview.tsx's own copy is a
   fourth-plus instance of a pattern that already exists in the flagship
   modules). A single shared `severityToBadgeTone()`/`severityToIconBg()`
   helper would remove this once it's safe to touch those files.
