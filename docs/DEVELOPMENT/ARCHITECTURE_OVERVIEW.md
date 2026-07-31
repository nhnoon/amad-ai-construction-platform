# AMAD Frontend — Architecture Overview

Technical structure of `artifacts/web/src`, verified against `App.tsx`,
`components/layout.tsx`, and the lib/pages directory structure. Product-
level description lives in `../PRODUCT/AMAD_PRODUCT_BLUEPRINT.md`; this
document is the developer-facing counterpart.

## Stack

React + TypeScript on Vite, Tailwind CSS v4 (`index.css`, `@theme inline`
token block), `wouter` for routing, `@tanstack/react-query` for server
state, `recharts` for charts, Radix-based shadcn/ui-style primitives in
`components/ui/*`, `i18next` for EN/AR with RTL support. Backend is a
separate FastAPI service, untouched by anything in this documentation
pass — the frontend talks to it exclusively through the generated
`@workspace/api-client-react` package or, in a handful of not-yet-migrated
spots, hand-written typed `fetch` wrappers (`lib/aiCenterClient.ts`,
`lib/meetingsClient.ts`, `lib/copilotClient.ts`).

## Routing (`App.tsx`)

A single `wouter` `<Switch>`. Three route-guard wrapper components handle
auth, all defined in `App.tsx` itself:

- **`ProtectedRoute`** — redirects to `/login` if unauthenticated, to
  `/change-password` if `user.must_change_password`; otherwise renders the
  page inside `Layout`, wrapped in a route-keyed `ErrorBoundary` and a
  `Suspense` boundary (`RouteFallback`).
- **`AdminRoute`** — same, plus redirects non-admins to `/`. The only role
  enforced at the routing layer.
- **`ChangePasswordRoute`** — the inverse guard: only reachable when
  `must_change_password` is true, redirects elsewhere otherwise.

Every page component is `lazy()`-loaded — each page (and everything it
imports) ships to the browser only once its route is visited, not in the
initial bundle. `/ai-center/:workspace?` is the one route that fans out to
16 different page components internally rather than being 16 separate
`<Route>` entries — see "The AI Center pattern" below.

## Layout shell (`components/layout.tsx`)

One `Layout` component wraps every `ProtectedRoute`/`AdminRoute` page:
fixed/collapsible sidebar (accordion nav, collapse state in
`localStorage['amad_sidebar_collapsed']`) + a slim utility topbar +
`<main>` capped at `max-w-screen-2xl`. Active-route highlighting and
accordion auto-expand are driven by `matchesHref`/`findActiveGroupKey`
against the current `wouter` location. Login, Change Password, and the 404
page render entirely outside this shell.

## The AI Center pattern

`pages/ai-center/index.tsx` reads `:workspace` from the URL, looks it up
in a `WORKSPACE_CONTENT: Record<string, ComponentType>` map, and renders
that one component — falling back to `"overview"` if the param is missing
or unrecognized. All 16 entries share one `WorkspaceLayout` wrapper
(breadcrumb + title + subtitle) except `overview`, which renders its own
`PageHero` instead and skips the generic wrapper. This is the reason AI
Center has 16 real, bookmarkable, independently-linkable pages while only
occupying one line in `App.tsx`'s route table.

## The Flagship Module pattern

All six AI Center Flagship Modules (Project Memory, Predictive
Intelligence, Supplier Risk Intelligence, Material Intelligence,
Cross-Project Learning, Executive Decision Center) follow one identical
three-layer architecture:

```
lib/mock<Module>.ts     — pure, deterministic, seeded-PRNG data generator.
                           Zero React/network dependency; a generate*()
                           function taking real project/supplier arrays in
                           and returning fully-synthesized analytics out.

lib/use<Module>.ts       — a thin react-query useQuery wrapper around the
                           generator, with an artificial ~450–500ms delay
                           and an explicit comment marking this as the
                           future real-backend integration seam.

pages/ai-center/workspaces/<module-slug>/
    shared.tsx            — local DemoDataBadge, CHART_TOOLTIP_STYLE,
                             tone/color maps (independently redefined per
                             module — a known duplication, not centralized).
    <6–11 component files> — the module's own UI (cards, charts, tables,
                              detail drawers).
    index.tsx              — the page entry, composing the above.
```

This is a deliberate seam: swapping a module onto a real backend later
means replacing the body of one `useQuery`'s `queryFn` in `lib/use<Module>.ts`
— no component in the module needs to change.

## Component organization

- `components/` — shared, cross-page components (layout shell, page
  primitives, AI-specific panels, form controls).
- `components/ui/` — lower-level Radix/cva-based primitives (Button,
  Input, Dialog, Sheet, Tabs, Skeleton, etc.) — the base layer everything
  in `components/` is built from.
- `pages/` — one folder/file per route. Multi-tab or multi-section pages
  (Dashboard, Documents, the AI Center workspaces) get their own
  subdirectory with local sub-components rather than one large file.
- `lib/` — data-fetching hooks (`use*.ts`), API client wrappers
  (`*Client.ts`), and the Flagship Modules' mock generators (`mock*.ts`).
- `context/` — `AuthContext`, `ThemeContext`, `CurrentEntityContext` —
  the app's global providers, composed once in `App.tsx`.

## State management

`@tanstack/react-query` for all server state (one `QueryClient` created in
`App.tsx`); no separate global client-state library — local UI state
(filters, tab selection, drawer open/closed) is plain `useState` per page.
Auth/session state lives in `AuthContext`, backed by `lib/auth.ts`'s
`getToken()`; the API client's auth header is wired once via
`setAuthTokenGetter(() => getToken())` in `App.tsx`.

## Design system layer

Not re-described here — see `../DESIGN/AMAD_DESIGN_SYSTEM.md` (index) and
its target document `amad-v2-design-system.md` for the full extracted
token/component specification, and `../DESIGN/COMPONENT_LIBRARY.md` for
the component inventory with file paths.

## Known architectural gaps (documented, not fixed here)

- Two coexisting skeleton-loading implementations (`ui/skeleton.tsx`'s
  component vs. the `.skeleton` CSS utility) — not yet consolidated.
- A few pages use hand-written typed `fetch` wrappers instead of the
  generated `@workspace/api-client-react` hooks used everywhere else
  (Site Report Intelligence, meeting action items) — inconsistent, not
  incorrect.
- RFIs has no first-class backend entity — see
  `BACKEND_INTEGRATION_STATUS.md` for the full note.
