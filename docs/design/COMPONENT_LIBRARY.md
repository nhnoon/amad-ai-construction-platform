# AMAD — Component Library

Every reusable component below is verified to exist at the stated path —
read directly for this document, not inferred. Module-local components
(the 6–11 files inside each AI Center Flagship Module's own folder) are
listed by count and name in `PAGE_INVENTORY.md` rather than repeated here,
since they're not shared/reusable outside their own module.

## Page shell & layout

| Component | Path | Role |
|---|---|---|
| `Layout` | `components/layout.tsx` | The one shell every authenticated route renders inside — sidebar + topbar + `<main>`. |
| `SidebarItem` | `components/sidebar-item.tsx` | Single row component used for every sidebar entry: top-level link, group header, and child link alike. |
| `WorkspaceLayout` | `components/workspace-layout.tsx` | `<div className="space-y-6">` wrapping `PageContextHeader` + `children` — the standard non-hero page shell. |
| `PageContextHeader` | `components/page-context-header.tsx` | Breadcrumbs, back link, title, subtitle, optional badge, optional toolbar. |
| `PageHero` | `components/PageHero.tsx` | AMAD v2 — navy hero band for landing/command pages (currently used only by AI Center Overview). |
| `RoadmapPlaceholder` | `components/roadmap-placeholder.tsx` | The shared "not built yet" shell — status badge + capability-preview list. Used by 11 of the app's 14 placeholder/planned pages. |

## Data display

| Component | Path | Role |
|---|---|---|
| `StatTile` | `components/stat-tile.tsx` | Icon + label + live number card, built on `.panel`. Used across Operations and AI Center overview surfaces. |
| `KpiStat` | `components/KpiStat.tsx` | AMAD v2 — larger, richer KPI card (icon badge, tabular-nums value, description, trend delta). Currently used only by AI Center Overview. |
| `InsightPanel` | `components/InsightPanel.tsx` | AMAD v2 — the one "authoritative" panel per page (gold accent rule, larger padding). `variant="brief"` / `variant="decision"`. |
| `WorkspaceQuickLink` | `components/WorkspaceQuickLink.tsx` | Navigation row/card to another workspace. `variant="row"` (dense list) or `variant="card"` (quick-access grid). |
| `DemoDataBadge` | `components/DemoDataBadge.tsx` | The canonical "Demo Data"/"Demo" gold pill — extracted during this audit pass from repeated inline markup in `KpiStat` and AI Center Overview. |

## Controls

| Component | Path | Role |
|---|---|---|
| `SearchInput` | `components/search-input.tsx` | Icon + `Input`; `compact` variant for toolbar-embedded filters. |
| `FilterSelect` | `components/filter-select.tsx` | Shared native `<select>` shape for "filter this list by X." |
| `FilterChip` | `components/filter-chip.tsx` | Toggleable filter pill (multi-value filters). |
| `PageTabs` | `components/page-tabs.tsx` | Wraps the Radix-based `Tabs`/`TabsList`/`TabsTrigger` (`components/ui/tabs.tsx`) with a consistent in-page tab look. |

## States

| Component | Path | Role |
|---|---|---|
| `EmptyState` | `components/ui/empty-state.tsx` | Icon + title + description + optional action, on `.empty-state*` utility classes. |
| `ErrorState` | `components/ui/error-state.tsx` | The destructive counterpart — `.panel .panel-body`, `AlertOctagon`, optional retry action. |
| `Skeleton` (component) | `components/ui/skeleton.tsx` | `animate-pulse bg-primary/10` block — used by AI Center Overview and others. |
| `.skeleton` (CSS utility) | `index.css` | A second, separate shimmer-gradient loading treatment used by earlier-built pages — **known duplication**, not yet consolidated (see `AMAD_DESIGN_SYSTEM.md` / `amad-v2-design-system.md` §33). |

## AI-specific

| Component | Path | Role |
|---|---|---|
| `AIActionPanel` | `components/AIActionPanel.tsx` | The "run AI analysis" action panel used on Site Report Detail, Meeting Detail, Project Detail. |
| `CurrentlyAnalyzing` | `components/CurrentlyAnalyzing.tsx` | In-progress/loading state specific to an AI analysis run. |
| `AIDrawer` | `components/AIDrawer.tsx` | Slide-out AI panel (Sheet-based). |
| `FloatingAIButton` | `components/FloatingAIButton.tsx` | Persistent floating entry point into Copilot, rendered globally by `Layout`. |
| `CopilotAnswer` / `AIAnswerStructured` / `ai-answer-ui.tsx` | `components/` | Chat-answer rendering (citations, confidence, structured answer blocks) shared by Copilot and other AI surfaces. |
| `site-report-analysis-panel.tsx`, `site-report-stage-progress.tsx` | `components/` | Site Report Detail's AI-analysis-specific UI. |

## Overlays

| Component | Path | Role |
|---|---|---|
| `Sheet` family | `components/ui/sheet.tsx` | Radix Dialog-based drawer — the base for `AIDrawer` and the Flagship Modules' own detail drawers (e.g. `SupplierDetailDrawer`, `MaterialDetailDrawer`, `MemoryDetailDrawer`). |
| `Dialog` | `components/ui/dialog.tsx` (shadcn primitive, referenced by e.g. Meetings' "Create Meeting" flow and Admin Users/Organizations) | Modal dialogs. |

## Base primitives (shadcn-style, `components/ui/`)

`button.tsx`, `input.tsx`, `label.tsx`, `select.tsx`, `textarea.tsx`,
`tabs.tsx`, `tooltip.tsx`, `toaster.tsx`, `badge`-family CSS classes
(defined in `index.css`, not a component file) — the underlying Radix/cva
primitives every higher-level component above is built from. Not
re-documented individually here; see `AMAD_DESIGN_SYSTEM.md`
(`amad-v2-design-system.md`) §22–23 for the Button/Badge variant tables.

## What's genuinely module-local (not shared)

The six AI Center Flagship Modules each maintain their own component set
inside their own folder — these are intentionally not shared/reusable
components, and each module also independently redefines its own
`DemoDataBadge`/`CHART_TOOLTIP_STYLE`/tone-map pattern in a local
`shared.tsx` rather than using the new central `DemoDataBadge` documented
above. This is a known, already-flagged duplication (see
`amad-v2-design-system.md`'s closing "Duplication to remove during later
migrations" section) — not something this documentation pass changes.
