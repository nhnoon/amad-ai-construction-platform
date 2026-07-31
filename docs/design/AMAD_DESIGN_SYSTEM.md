# AMAD Design System — Index

The full, topic-by-topic AMAD v2 design specification (33 topics: page
shell, grid, sidebar, typography, KPI cards, panels, tabs, badges, demo
data labels, charts, empty/loading/error states, spacing, breakpoints,
hover/focus, dark mode, and more) already exists in this same `docs/`
design folder as **`amad-v2-design-system.md`** — extracted directly from
the approved AI Center Overview implementation
(`artifacts/web/src/pages/ai-center/workspaces/Overview.tsx`), with every
token and pattern traceable back to real source files.

This file is the short index into that document, written to satisfy the
documentation package's expected file name (`AMAD_DESIGN_SYSTEM.md`)
without duplicating — and risking drifting from — the source of truth.

**Read `amad-v2-design-system.md` for the actual specification.** It
covers, in order: page shell, maximum content width, responsive grid,
sidebar behavior, top header behavior, page title/subtitle treatment,
search/scope controls, card backgrounds, border colors, border radius,
shadows, gold accent usage, typography sizes/weights, section headers, KPI
cards, primary panels, secondary panels, compact list rows, tables, tabs,
filters, buttons, badges, Demo Data labels, charts, drawers, empty states,
loading states, error states, spacing/padding, breakpoints, hover/focus
states, and dark mode behavior — plus a closing summary of tokens
identified, primitives created/updated, and known duplication flagged for
later cleanup.

## What's approved vs. what's still pending

- **Approved benchmark**: AI Center Overview (`/ai-center`) only. Its
  implementation is what the design system document extracts from.
- **Not yet migrated**: every other page in the app. `PAGE_INVENTORY.md`
  and `../DEVELOPMENT/UI_MIGRATION_CHECKLIST.md` track which pages still
  need this treatment applied, in what order.
- This index file, and the design system it points to, describe **what
  already exists** — they are not a proposal for what should change on
  other pages. Applying the v2 system to another page is a separate,
  future task, out of scope for documentation work.

## Related documents

- `COMPONENT_LIBRARY.md` — every reusable component the design system
  above is built from, with real file paths and props.
- `UX_GUIDELINES.md` — interaction and content conventions (loading/empty/
  error patterns, keyboard shortcuts, tooltips, form validation) that sit
  alongside the visual system but aren't purely visual tokens.
- `../../docs/brand/amad-brand-guidelines.md` and
  `../../docs/brand/brand-foundation.md` — the brand-level source of truth
  (logo, full color palette, base type scale, motion, accessibility, RTL)
  that the v2 design system builds its component layer on top of, rather
  than restating.
