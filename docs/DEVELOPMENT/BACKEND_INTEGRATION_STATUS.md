# AMAD — Backend Integration Status

Which pages talk to a real backend, which mix real data with local
synthetic analytics, which are entirely local/demo, and which fetch
nothing at all. Verified per-page by reading actual hook imports and
`fetch` calls during the audit — not inferred from page names.

**Real** = real API hooks (`@workspace/api-client-react` or a typed `fetch`
wrapper) hitting `/api/v1/...`. **Mixed** = real entity identity combined
with local synthetic analytics. **Demo** = entirely local mock/seeded data.
**None** = static content, no fetching.

## Real (28 pages)

Executive Dashboard, Documents, Alerts, Operations Overview, Projects,
Project Detail, Procurement, Suppliers, Site Reports, Site Report Detail,
Safety & NCR, Meetings, Meeting Detail, RFIs, Change Orders, Claims, AI
Copilot, Memory Center, Project Intelligence, Site Report Intelligence,
Meeting Intelligence, Contract Intelligence, Executive Intelligence,
Reports, Users, Organizations, Login, Change Password.

Representative real endpoints confirmed during the audit (not an
exhaustive API list — see backend docs for that):

- `/api/v1/executive` (`useExecutive`) — Executive Dashboard, Executive
  Intelligence, Project Intelligence, Reports.
- `/api/v1/ai/memory[/:id]` (`lib/aiCenterClient.ts`) — Memory Center,
  Contract Intelligence (filtered by taxonomy bucket).
- `/api/v1/ai/copilot/query`, `/api/v1/ai/conversations[/:id/messages]` —
  AI Copilot.
- `/api/v1/documents`, `/api/v1/documents/:id/ocr`,
  `/api/v1/documents/:id/contract-extraction` — Documents.
- `/api/v1/projects/:id/site-reports/cards`,
  `/api/v1/projects/:id/site-reports/:id/intelligence`,
  `.../analyze` — Site Reports, Site Report Detail, Site Report
  Intelligence (the last one via raw `fetch` + `getToken()` rather than a
  generated hook — the one workspace not using the standard hook pattern).
- `/api/v1/projects/:id/change-orders`,
  `/api/v1/projects/:id/claims`,
  `/api/v1/projects/:id/documents`,
  `/api/v1/projects/:id/correspondence` — Change Orders, Claims, RFIs.
- `useListProjects`, `useListSuppliers`, `useListPurchaseRequests`,
  `useListPurchaseOrders`, `useListProjectMeetings`,
  `useListProjectDecisions`, `useListProjectHealthScores`,
  `useListProjectSafetyEvents`, `useListProjectNcrs`,
  `useGetDashboardSummary` — the generated `@workspace/api-client-react`
  hooks backing most Operations pages.
- `meetingsClient.ts` (typed `fetch` wrapper) — meeting creation and action
  items; no generated hook exists yet for this slice.
- `POST /api/v1/auth/change-password` — Change Password.

## Mixed — real identity, synthetic analytics (7 pages)

AI Center Overview, Project Memory, Predictive Intelligence, Supplier Risk
Intelligence, Material Intelligence, Cross-Project Learning, Executive
Decision Center.

Pattern, identical across all seven: `useListProjects`/`useListSuppliers`
supplies real project/supplier identity; a pure `generate*()` function in
`lib/mock<Module>.ts` synthesizes every analytical figure (scores,
predictions, trends, alerts) from that real identity plus a deterministic
seed. Wrapped in a `useQuery` hook (`lib/use<Module>.ts`) with a ~450–500ms
artificial delay and an explicit code comment marking where a real
`queryFn` would later replace the mock call. Every synthetic figure is
tagged with a `DemoDataBadge` in the UI — see `../DESIGN/UX_GUIDELINES.md`.

Mock generator sizes (proxy for dataset richness):

| Module | Generator file | Lines |
|---|---|---|
| Material Intelligence | `lib/mockMaterialIntelligence.ts` | 561 |
| Project Memory | `lib/mockProjectMemory.ts` | 524 |
| Supplier Risk Intelligence | `lib/mockSupplierRisk.ts` | 476 |
| Predictive Intelligence | `lib/mockPredictiveIntelligence.ts` | 461 |
| Cross-Project Learning | `lib/mockCrossProjectLearning.ts` | 450 |
| Executive Decision Center | `lib/mockExecutiveDecisionCenter.ts` | 375 |

Note: Executive Decision Center's generator is standalone — despite
presenting as an aggregation of the other five Flagship Modules, it does
not literally call their generator functions. AI Center Overview, by
contrast, does call `generateExecutiveDecisionCenter`,
`generateMaterialIntelligence`, and `generateSupplierRisk` directly
(read-only) to build its own preview sections.

## Demo (0 pages)

No audited page is *entirely* local/demo with zero real data — every
Mixed-status page has at least real project or supplier identity feeding
it. This category exists in the classification scheme but nothing in the
current app falls fully into it.

## None — static or unbuilt (13 pages)

**Placeholder/Planned (12)** — Tasks, Requests & Approvals, Notifications,
Risk Register, Intelligent Search, Email Intelligence, Audit Log,
Integrations, Billing & Subscription, Client Portal Overview, Client
Requests, Client Documents. All render `RoadmapPlaceholder` with no data
fetching of any kind.

**Static by design (1)** — Not Found (404): static content, correctly has
no fetching.

## Known integration gaps worth flagging (not fixed here — documentation only)

- **RFIs has no first-class backend entity.** The page is Real in the
  sense that every request it makes is a genuine API call, but there is no
  RFI table/endpoint — it's a client-side keyword filter
  (`isRfiLike`) over decisions, documents, and correspondence.
- **Site Report Intelligence uses raw `fetch`**, not a generated hook,
  unlike every sibling AI Center workspace.
- **Meetings' action items have no generated hook** — `meetingsClient.ts`
  is a hand-written typed `fetch` wrapper rather than going through
  `@workspace/api-client-react` like the rest of the meetings data.
- **Executive Intelligence's "Recent Decisions" section is an intentional
  EmptyState**, not fabricated data — there is no portfolio-wide decisions
  endpoint, so it points users to Meeting Intelligence instead of showing
  something misleading.
