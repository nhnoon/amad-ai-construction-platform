# AMAD — Page Inventory

Generated from a direct, read-only audit of `artifacts/web/src` (routes in
`App.tsx`, sidebar in `components/layout.tsx`, every page component under
`pages/`). Every page, route, and status below reflects code that exists in
the repository today — nothing here is proposed or invented. Where a page is
a stub, that is stated plainly rather than described as if it were built.

**Status legend**
- **Complete** — real data wiring, loading/empty/error states handled.
- **Partial** — real and working, but with visible gaps (proxy data, missing
  detail views, hardcoded limits).
- **Placeholder** — renders the shared `RoadmapPlaceholder` shell (status
  badge + capability preview list) with no real logic or data.
- **Planned** — route/nav entry exists; effectively no real page content.

**Backend legend**
- **Real** — real API hooks (`@workspace/api-client-react` or a typed
  `fetch` wrapper) hitting `/api/v1/...`.
- **Mixed** — real entity data (e.g. project/supplier identity) combined
  with locally-generated synthetic analytics on the same page.
- **Demo** — entirely local, deterministic mock/seeded data.
- **None** — static content or no data fetching at all.

48 routed pages/surfaces total.

---

## Summary table

| Page | Route | Sidebar Group | Parent | Status | Backend | Complexity | Primary User |
|---|---|---|---|---|---|---|---|
| Executive Dashboard | `/` | Dashboard (top, ungrouped) | None | Complete | Real | High | Executives |
| Documents | `/documents` | Documents (top, ungrouped) | None | Complete | Real | High | All users |
| Tasks | `/tasks` | My Workspace | None | Placeholder | None | Low | PM / Site Engineer |
| Requests & Approvals | `/requests` | My Workspace | None | Placeholder | None | Low | All users |
| Alerts | `/alerts` | My Workspace | None | Complete | Real | Medium | All users |
| Notifications | `/notifications` | My Workspace | None | Placeholder | None | Low | All users |
| Operations Overview | `/operations` | Operations | None | Complete | Real | Medium | PM / Executive |
| Projects | `/projects` | Operations | None | Complete | Real | Medium | PM / Executive |
| Project Detail | `/projects/:id` | Operations (drill-down) | Projects | Complete | Real | High | PM / Site Engineer / Executive |
| Procurement | `/procurement` | Operations | None | Complete | Real | Medium | Procurement Officer |
| Suppliers | `/suppliers` | Operations | None | Complete | Real | Low | Procurement Officer |
| Site Reports | `/site-reports` | Operations | None | Complete | Real | Medium | Site Engineer / PM |
| Site Report Detail | `/projects/:projectId/site-reports/:reportId` | Operations (drill-down) | Site Reports | Complete | Real | High | Site Engineer / PM |
| Safety & NCR | `/safety` | Operations | None | Complete | Real | Medium | Safety Officer / Site Engineer |
| Meetings | `/meetings` | Operations | None | Complete | Real | High | PM |
| Meeting Detail | `/meetings/:projectId/:meetingId` | Operations (drill-down) | Meetings | Complete | Real | Low | PM |
| RFIs | `/rfis` | Operations | None | Partial | Real | Medium | PM / Contracts staff |
| Change Orders | `/change-orders` | Operations | None | Complete | Real | Low | PM / Commercial |
| Claims | `/claims` | Operations | None | Complete | Real | Low | Commercial / Legal |
| Risk Register | `/risks` | Operations | None | Planned | None | Low | PM / Executive |
| AI Center Overview | `/ai-center` (workspace `overview`) | AI Center — Workspace | AI Center (shell) | Complete | Mixed | High | Executives / All AI Center users |
| AI Copilot | `/ai-center/copilot`, also `/copilot` | AI Center — Workspace | AI Center (shell) | Complete | Real | High | All users |
| Memory Center | `/ai-center/memory` | AI Center — Workspace | AI Center (shell) | Complete | Real | High | PM / Executive / Coordinators |
| Project Intelligence | `/ai-center/projects` | AI Center — Per-Entity Intelligence | AI Center (shell) | Partial | Real | Low | PM / Executive |
| Site Report Intelligence | `/ai-center/site-reports` | AI Center — Per-Entity Intelligence | AI Center (shell) | Partial | Real | Low | Site Engineer / PM |
| Meeting Intelligence | `/ai-center/meetings` | AI Center — Per-Entity Intelligence | AI Center (shell) | Partial | Real | Low | PM / Coordinators |
| Contract Intelligence | `/ai-center/contracts` | AI Center — Per-Entity Intelligence | AI Center (shell) | Partial | Real | Low | Commercial / Contracts |
| Executive Intelligence | `/ai-center/executive` (cross-listed as "Insights" under Analytics) | AI Center — Per-Entity Intelligence + Analytics | AI Center (shell) | Complete | Real | Medium | Executives |
| Intelligent Search | `/ai-center/search` | AI Center — Per-Entity Intelligence | AI Center (shell) | Planned | None | Low | All users (future) |
| Email Intelligence | `/ai-center/email` | AI Center — Per-Entity Intelligence | AI Center (shell) | Planned | None | Low | Procurement / Commercial (future) |
| Project Memory | `/ai-center/project-memory` | AI Center — Flagship Modules | AI Center (shell) | Complete | Mixed | High | PM / Executive |
| Predictive Intelligence | `/ai-center/predictive-intelligence` | AI Center — Flagship Modules | AI Center (shell) | Complete | Mixed | High | Executive / PM |
| Supplier Risk Intelligence | `/ai-center/supplier-risk` | AI Center — Flagship Modules | AI Center (shell) | Complete | Mixed | High | Procurement / Executive |
| Material Intelligence | `/ai-center/material-intelligence` | AI Center — Flagship Modules | AI Center (shell) | Complete | Mixed | High | Procurement / Executive |
| Cross-Project Learning | `/ai-center/cross-project-learning` | AI Center — Flagship Modules | AI Center (shell) | Complete | Mixed | High | PM / Executive / cross-functional |
| Executive Decision Center | `/ai-center/executive-decision-center` | AI Center — Flagship Modules | AI Center (shell) | Complete | Mixed | High | Executive |
| Reports | `/reports` | Analytics | None | Complete | Real | High | Executives |
| Users | `/admin/users` | Administration | None | Complete | Real | Medium | Admin |
| Organizations (labeled "Settings" in nav) | `/admin/organization` | Administration | None | Complete | Real | Medium | Admin |
| Audit Log | `/admin/audit-log` | Administration | None | Placeholder | None | Low | Admin |
| Integrations | `/admin/integrations` | Administration | None | Placeholder | None | Low | Admin |
| Billing & Subscription | `/admin/billing` | Administration | None | Placeholder | None | Low | Admin |
| Client Portal Overview | `/client-portal` | Client Portal | None | Placeholder | None | Low | Client (future) |
| Client Requests | `/client-portal/requests` | Client Portal | None | Placeholder | None | Low | Client (future) |
| Client Documents | `/client-portal/documents` | Client Portal | None | Placeholder | None | Low | Client (future) |
| Login | `/login` | None (public/system) | None | Complete | Real | Low | All users (unauthenticated) |
| Change Password | `/change-password` | None (public/system) | None | Complete | Real | Low | All users (forced first-login reset) |
| Not Found | (catch-all, 404) | None (no sidebar) | None | Complete | None | Low | All users |

---

## Full detail

Every field the underlying audit captured, including purpose, components,
related pages, and a suggested design-migration priority (see
`../DEVELOPMENT/UI_MIGRATION_CHECKLIST.md` for the phased rollout that
priority feeds into).

### Dashboard (top-level, ungrouped)

**Executive Dashboard** — `/`
- Purpose: Glanceable portfolio-health snapshot — KPI row, three side-by-side charts, a trend chart — deliberately excludes lists/detail tables.
- Components: WorkspaceLayout, KpiTile, PortfolioHealthDonut, ProjectStatusChart, BiggestRisksBarChart, PortfolioTrendChart, QuickActions, IconChip.
- Related: `/reports`, `/projects`, `/safety`, `/rfis`, `/documents`, `/copilot`, `/alerts`.
- Note: `dashboard/ActivityTimeline.tsx` exists in the codebase but is not currently rendered by `dashboard/index.tsx` — dead/unused component, not a live "recent activity" feed on this page.
- Migration priority: **High** (Phase 1 — most-visited executive surface).

**Documents** — `/documents`
- Purpose: Upload (general or project-scoped), browse/filter/search a document library, and view OCR + contract-analysis results per document.
- Components: WorkspaceLayout, RadioGroup, Select, Tabs, SearchInput, EmptyState, Skeleton, DocumentDetailPanel, DocumentBadges, SectionHeading.
- Related: none (internal panel switching only, no outbound links).
- Migration priority: **Medium** (Phase 3 — grouped with Operations).

### My Workspace

**Tasks** — `/tasks` — Placeholder shell (`RoadmapPlaceholder`), no data. Purpose (intended): personal task list linking assignments to projects. Priority: **Low** (defer — nothing to migrate until built).

**Requests & Approvals** — `/requests` — Placeholder shell, no data. Purpose (intended): auditable lifecycle for internal requests. Priority: **Low** (defer).

**Alerts** — `/alerts`
- Purpose: Lists/filters live smart alerts (severity + category) derived from project data, with expandable recommended actions.
- Components: WorkspaceLayout, SummaryCard, AlertCard, Skeleton, EmptyState, ErrorState.
- Related: `/projects/:id`.
- Migration priority: **High** (Phase 1 — complete, high-traffic, good migration ROI).

**Notifications** — `/notifications` — Placeholder shell, no data. Purpose (intended): unified notification center for approvals/assignments/status changes. Priority: **Low** (defer).

### Operations

**Operations Overview** — `/operations`
- Purpose: Interactive landing page — live record counts per operations module, a "Needs Attention" panel, a recent activity feed.
- Components: WorkspaceLayout, StatTile, SearchInput, ActivityTimeline.
- Related: `/projects`, `/procurement`, `/site-reports`, `/meetings`, `/rfis`, `/change-orders`, `/claims`, `/safety`, `/suppliers`.
- Migration priority: **High** (Phase 3, first in that phase — the section's own landing page).

**Projects** — `/projects`
- Purpose: Searchable/filterable project table with status badge and live AI health-score bar per row.
- Components: WorkspaceLayout, SearchInput, FilterSelect, EmptyState, ErrorState, Skeleton, data-table.
- Related: `/projects/:id`.
- Migration priority: **High** (Phase 3).

**Project Detail** — `/projects/:id`
- Purpose: Full project workspace — 12 tabs (Overview, Health Score, Meetings, Site Reports, Contracts, Documents, Suppliers, Risks, Timeline, Memory, AI Summary, Ask Hermes) unifying every data domain for one project.
- Components: WorkspaceLayout, Tabs/TabsContent, StatTile, AIActionPanel, CurrentlyAnalyzing, MemoryCenter, CopilotPage, FilterChip, ErrorBoundary, EmptyState.
- Related: `/projects`, `/meetings/:projectId/:meetingId`, `/projects/:id/site-reports/:reportId`, `/documents`, `/procurement`, `/meetings`, `/ai-center/executive`.
- Note: the most feature-dense page in the app — merges 7 entity types into a filterable "Smart Timeline" tab.
- Migration priority: **Medium** (Phase 3 — high value but highest-risk to touch given its density; migrate after simpler Operations pages establish the pattern).

**Procurement** — `/procurement`
- Purpose: Tabbed register of Purchase Requests and Purchase Orders across projects, search + late-PO badges.
- Components: WorkspaceLayout, PageTabs, TableSkeletonRows, EmptyState, ErrorState, Input.
- Related: none.
- Note: hard-capped at 100 rows/tab with a static count notice rather than real pagination; no per-record detail view.
- Migration priority: **Medium** (Phase 3).

**Suppliers** — `/suppliers`
- Purpose: Searchable/filterable directory of registered suppliers (category, city, status).
- Components: WorkspaceLayout, SearchInput, FilterSelect, EmptyState, ErrorState, data-table.
- Related: none — no supplier detail/profile page here (a richer supplier view exists separately, under AI Center → Supplier Risk Intelligence).
- Migration priority: **Medium** (Phase 3).

**Site Reports** — `/site-reports`
- Purpose: Project-scoped card gallery of daily site reports (weather, progress, risk/safety/quality indicators).
- Components: WorkspaceLayout, FilterSelect, EmptyState, Skeleton.
- Related: `/projects/:projectId/site-reports/:reportId`.
- Migration priority: **Medium** (Phase 3).

**Site Report Detail** — `/projects/:projectId/site-reports/:reportId`
- Purpose: Deep-dive on one report — raw evidence (manpower, equipment, work, delays, blockers, photos) plus an on-demand AI analysis pass (findings, risk scoring, recommendations).
- Components: WorkspaceLayout, Tabs, SiteReportAnalysisPanel, SiteReportStageProgress, AIActionPanel, CurrentlyAnalyzing, ErrorBoundary, EmptyState, Button.
- Related: `/site-reports`.
- Note: client-side 75s abort timeout deliberately exceeds the backend's own 60s analysis ceiling, so it never races a legitimate in-flight run.
- Migration priority: **Medium** (Phase 3).

**Safety & NCR** — `/safety`
- Purpose: Project-scoped tabbed register of safety events and NCRs, severity/status badges, alert banners for high-severity/open items.
- Components: WorkspaceLayout, PageTabs, FilterSelect, TableSkeletonRows, EmptyState.
- Related: none.
- Migration priority: **Medium** (Phase 3).

**Meetings** — `/meetings`
- Purpose: Project-scoped meetings/decisions register with a Create Meeting dialog, decision + open-action-item counts.
- Components: WorkspaceLayout, PageTabs, FilterSelect, Dialog, TableSkeletonRows, EmptyState, Button, Input, Textarea.
- Related: `/meetings/:projectId/:meetingId`.
- Migration priority: **Medium** (Phase 3).

**Meeting Detail** — `/meetings/:projectId/:meetingId`
- Purpose: Single meeting view — decisions and action items side-by-side, plus an AI action panel.
- Components: WorkspaceLayout, AIActionPanel, CurrentlyAnalyzing, back-button, EmptyState, Skeleton.
- Related: `/meetings`.
- Migration priority: **Low** (Phase 3, low complexity — fine last in its group).

**RFIs** — `/rfis`
- Purpose: A "unified RFI Timeline" merging project decisions, documents, and correspondence whose type/title/subject matches "rfi" into one chronological register.
- Components: WorkspaceLayout, FilterSelect, StatTile, Alert, TableSkeletonRows, EmptyState.
- Related: none.
- Note: **no first-class RFI entity in the backend** — this is a client-side keyword filter (`isRfiLike`) over decisions/documents/correspondence, not a true RFI create/track/respond workflow.
- Migration priority: **Medium** (Phase 3 — functional but structurally a proxy view; worth flagging to product before deep investment).

**Change Orders** — `/change-orders`
- Purpose: Project-scoped change-order register with summary stat tiles (total, open, approved, total value) and a status-badged table.
- Components: WorkspaceLayout, FilterSelect, StatTile, Alert, TableSkeletonRows, EmptyState.
- Related: none.
- Note: read-only — no create/edit/approve actions.
- Migration priority: **Low** (Phase 3).

**Claims** — `/claims`
- Purpose: Project-scoped contractual-claims register, structurally identical to Change Orders.
- Components: WorkspaceLayout, FilterSelect, StatTile, Alert, TableSkeletonRows, EmptyState.
- Related: none.
- Migration priority: **Low** (Phase 3).

**Risk Register** — `/risks` — Planned/placeholder shell (`RoadmapPlaceholder`, explicitly `status="in-development"`, `phase="Phase 2 · Operational Workflows"` in code). Purpose (intended): live, cross-project risk register rolling up to the executive dashboard. Priority: **Low** (defer until built).

### AI Center — Workspace

**AI Center Overview** — `/ai-center` (workspace `overview`)
- Purpose: Executive landing surface for AI Center — brief, KPI strip, three-card attention row, trends, quick access.
- Status: **already migrated to the AMAD v2 design system** (see `../DESIGN/AMAD_DESIGN_SYSTEM.md`) — the approved design benchmark this whole audit is measured against.
- Components: PageHero, KpiStat, InsightPanel, WorkspaceQuickLink, DemoDataBadge, PageTabs, SearchInput, FilterSelect, EmptyState, ErrorState, Skeleton.
- Related: every other AI Center workspace (quick-access grid), `/alerts`, `/projects`.
- Migration priority: **Done.**

**AI Copilot** — `/ai-center/copilot` (embedded, compact) and standalone `/copilot`
- Purpose: Multi-turn, citation-grounded chat assistant answering questions across projects, procurement, safety, suppliers, site reports, meetings.
- Components: CopilotPage (MessageBubble, RichAnswer renderer, CitationsSection, ConfidenceBadge, ClarificationChips, FollowUpChips, DomainBadges), RecentMemoriesPanel, ErrorBoundary.
- Related: `/ai-center/memory`; citation links into projects/documents/etc.
- Note: one component serves both routes — `compact` prop drops the full-height layout for the AI Center embed; a `projectId` prop (used elsewhere, e.g. Project Detail's "Ask Hermes" tab) scopes queries server-side.
- Migration priority: **Medium** (Phase 2).

**Memory Center** — `/ai-center/memory`
- Purpose: Browse, search, filter, add, edit, pin, delete structured memory records (project/meeting/decision/risk/contract/supplier/site-report/personal notes).
- Components: MemoryCard (grid/timeline views), FilterChip, MemoryFormDialog, EmptyState, Skeleton.
- Related: none direct (linked from RecentMemoriesPanel's "View all").
- Note: also embeds a "Legacy note memory" collapsible section preserving the old unstructured note store.
- Migration priority: **Medium** (Phase 2).

### AI Center — Per-Entity Intelligence

**Project Intelligence** — `/ai-center/projects`
- Purpose: Portfolio grid of projects with health score/level (where already ranked by Executive Intelligence) as a jump-off point into each project's AI workspace tab.
- Components: project card grid, status badges, HeartPulse indicator, Skeleton, EmptyState.
- Related: `/projects/:id?tab=ai-summary`.
- Note: health/level only shown for projects already ranked by Executive Intelligence — others show plain status only (deliberate, avoids N+1 calls).
- Migration priority: **Medium** (Phase 2).

**Site Report Intelligence** — `/ai-center/site-reports`
- Purpose: Project-scoped picker of recent site reports with risk/safety/quality badges, linking into each report's AI detail page.
- Components: Project Select, report card grid, Skeleton, EmptyState.
- Related: `/site-reports`, `/projects/:id/site-reports/:reportId`.
- Note: uses raw `fetch` + `getToken()` rather than a generated hook, unlike most other workspaces.
- Migration priority: **Medium** (Phase 2).

**Meeting Intelligence** — `/ai-center/meetings`
- Purpose: Project-scoped view of recent meetings and extracted decisions.
- Components: Project Select, two-column meeting/decisions list, badges, Skeleton, EmptyState.
- Related: `/meetings`, `/meetings/:projectId/:meetingId`.
- Note: also linked from Executive Intelligence's "Recent Decisions" section, standing in for a non-existent portfolio-wide decisions feed.
- Migration priority: **Medium** (Phase 2).

**Contract Intelligence** — `/ai-center/contracts`
- Purpose: Completed contract-extraction summaries (value/obligations/risks) sourced from memory records tagged as contracts.
- Components: card grid, Badge, EmptyState, Skeleton.
- Related: `/documents` (full extraction detail).
- Note: no dedicated contracts endpoint — piggybacks on the memory API filtered by taxonomy bucket.
- Migration priority: **Medium** (Phase 2).

**Executive Intelligence** — `/ai-center/executive` (cross-listed under Analytics as "Insights")
- Purpose: Portfolio-wide AI insight dashboard — executive summary, critical projects, top risks, procurement blockers, suggested actions.
- Components: SectionShell panels, ConfidenceTag, severity badges, EmptyState per section, Skeleton.
- Related: `/reports`, `/projects/:id`, `/ai-center/meetings`.
- Note: "Recent Decisions" is intentionally an EmptyState pointer to Meeting Intelligence rather than fabricated data — no portfolio-wide decisions endpoint exists.
- Migration priority: **High** (Phase 1 — pulled forward with the other executive-facing pages).

**Intelligent Search** — `/ai-center/search` — Planned/placeholder shell. Purpose (intended): natural-language cross-workspace search with source-linked results. Priority: **Low** (defer).

**Email Intelligence** — `/ai-center/email` — Planned/placeholder shell, same pattern. Purpose (intended): inbound message classification, routing, draft response generation. Priority: **Low** (defer).

### AI Center — Flagship Modules

All six share one architecture: real project/supplier identity in
(`useListProjects`/`useListSuppliers`), fully synthetic analytics out (a
pure `generate*()` function in `lib/mock<Module>.ts`, wrapped by a
`useQuery` hook in `lib/use<Module>.ts` with an artificial ~450–500ms
delay). Every "Demo Data"-tagged figure is clearly marked in the UI.

**Project Memory** — `/ai-center/project-memory`
- Purpose: Unifies everything captured about one project — documents, site reports, meetings, contracts, claims, decisions, risks, actions, approvals — into a searchable timeline, relationship graph, and summary.
- Mock source: `lib/mockProjectMemory.ts` (524 lines).
- Components: MemoryItemCard, MemoryTimeline, MemoryGraph, MemoryDetailDrawer, StatsPanel (6 component files).
- Related: other AI Center workspaces via the Overview quick-access grid; project scope ties to `/projects`.
- Migration priority: **Medium** (Phase 2).

**Predictive Intelligence** — `/ai-center/predictive-intelligence`
- Purpose: Forecasts delay, budget overrun, cash flow, claim, safety, and schedule risk portfolio-wide or per project, with scenario comparison and prediction history.
- Mock source: `lib/mockPredictiveIntelligence.ts` (461 lines).
- Components: PredictionCard, PredictionTrendChart, HighRiskProjectsTable, ScenarioComparison, PortfolioHeatMap, PredictionTimeline, EmergingRisks, PredictionHistory, AIRecommendationPanel (9 component files — largest sub-component count).
- Related: feeds Overview and Executive Decision Center previews.
- Migration priority: **Medium** (Phase 2).

**Supplier Risk Intelligence** — `/ai-center/supplier-risk`
- Purpose: Evaluates delivery, quality, contract compliance, and financial stability per supplier, with comparison and AI insights.
- Mock source: `lib/mockSupplierRisk.ts` (476 lines).
- Components: SupplierHealthOverview, TopHighRiskSuppliers, SupplierDirectory, SupplierDetailDrawer (306 lines), PortfolioDistribution, RiskTimeline, SupplierComparison, AIInsightsPanel (8 files).
- Related: used as a data source by AI Center Overview and Executive Decision Center.
- Migration priority: **Medium** (Phase 2).

**Material Intelligence** — `/ai-center/material-intelligence`
- Purpose: Tracks which materials are rising in price, which projects are exposed, cost/supply risk ranking, and recommended procurement actions.
- Mock source: `lib/mockMaterialIntelligence.ts` (561 lines — largest mock file in the app).
- Components: MaterialOverview, PriceTrendChart, MaterialDirectory, MaterialDetailDrawer (247 lines), PortfolioExposureTable, MaterialRiskHeatMap, SupplyChainAlerts, ProcurementOpportunities, ScenarioAnalysis, MaterialComparison, AIInsightsPanel (11 files — most of any module).
- Related: feeds AI Center Overview's cost-exposure KPI and Executive Decision Center highlights.
- Migration priority: **Medium** (Phase 2).

**Cross-Project Learning** — `/ai-center/cross-project-learning`
- Purpose: Searchable organizational knowledge base across all projects with similarity scoring and a knowledge graph — "has this happened before, what worked, what should we do now."
- Mock source: `lib/mockCrossProjectLearning.ts` (450 lines; search is keyword-matched, explicitly not real semantic/vector search).
- Components: KnowledgeItemCard, KnowledgeSearchBar, FilterBar, ExecutiveLearningSummary, ExecutiveInsights, KnowledgeGraph, KnowledgeTimeline, KnowledgeDetailDrawer (268 lines) (8 files).
- Related: none explicit beyond shared project/supplier pickers.
- Note: the one module with genuinely real client-side persistence (localStorage-backed recent/saved searches).
- Migration priority: **Medium** (Phase 2).

**Executive Decision Center** — `/ai-center/executive-decision-center`
- Purpose: Aggregates the other five modules into one executive view — today's priorities, decision queue, portfolio risk, AI brief.
- Mock source: `lib/mockExecutiveDecisionCenter.ts` (375 lines — standalone; does not literally call the other five modules' generators despite presenting as a rollup).
- Components: ExecutiveOverview, TodaysPriorities, DecisionQueue, PortfolioRiskOverview, AIExecutiveBrief, ModuleHighlights, CriticalDecisionsTimeline, ExecutiveHeatMap, AttentionProjects, RecommendedActions, KpiTrends (11 files, tied for most with Material Intelligence).
- Related: represents/links the other 5 Flagship Modules; reused directly by AI Center Overview (`generateExecutiveDecisionCenter` import).
- Migration priority: **High** (Phase 2, first in that group — executive-facing and already the reuse anchor for Overview).

### Analytics

**Reports** — `/reports`
- Purpose: Deterministic, printable Executive Weekly Report — portfolio score, health distribution, top priorities, risks, alerts, procurement/safety/quality highlights, recommended actions, data sources.
- Components: PageContextHeader, WorkspaceLayout, ErrorState, Skeleton, Button, plus dedicated section components (AlertsSection, PrioritiesSection, RisksSection, ProcurementSection, SafetySection, QualitySection, ActionsSection, SourcesSection).
- Related: `/`.
- Note: dedicated print stylesheet handling (`print:hidden` / `print:block`).
- Migration priority: **High** (Phase 1).

### Administration (admin role only)

**Users** — `/admin/users`
- Purpose: View/search/filter/create users, activate/deactivate, reset passwords.
- Components: WorkspaceLayout, Dialog, Select, EmptyState, Skeleton, data-table, useToast.
- Related: `/`.
- Migration priority: **Medium** (Phase 4).

**Organizations** — `/admin/organization` (sidebar labels it **"Settings"** — naming mismatch between nav label and in-page title/breadcrumb "Organizations", worth reconciling during migration)
- Purpose: List/create/edit/activate/deactivate tenant organizations.
- Components: WorkspaceLayout, Dialog, EmptyState, Skeleton, card grid, useToast.
- Related: `/`.
- Migration priority: **Medium** (Phase 4).

**Audit Log** — `/admin/audit-log` — Placeholder shell, `status="in-development"`, phase labeled **"Phase 2"** in code. Purpose (intended): full audit-history/traceability. Priority: **Low** (defer).

**Integrations** — `/admin/integrations` — Placeholder shell, `status="planned"`, phase labeled **"Phase 5 · Commercial Scale"** in code. Purpose (intended): third-party connectors, webhooks, ERP bridges. Priority: **Low** (defer).

**Billing & Subscription** — `/admin/billing` — Placeholder shell, `status="planned"`, phase labeled **"Phase 5 · Commercial Scale"** in code. Purpose (intended): subscription/plan/usage/invoice management. Priority: **Low** (defer).

### Client Portal

All three are placeholder shells explicitly labeled in code as **"Phase 4
· Client Collaboration"**, `status="planned"`, "not yet live." No mock or
real data is rendered on any of them.

**Client Portal Overview** — `/client-portal` — intended: self-service client experience (progress, requests, approvals). Priority: **Low** (defer — whole section is pre-build).

**Client Requests** — `/client-portal/requests` — intended: client request-submission/tracking workflow. Priority: **Low** (defer).

**Client Documents** — `/client-portal/documents` — intended: client-scoped, read-only view of approved project documents. Priority: **Low** (defer).

### Auth / System (no sidebar)

**Login** — `/login`
- Purpose: Authenticates via email/password, redirects to Dashboard.
- Components: useAuth (AuthContext), Button, Input, Label, LogoMark.
- Migration priority: **Not in scope** — uses its own two-column branded layout, not the sidebar `Layout` shell; a separate, lightweight pass rather than the 5-phase v2 rollout.

**Change Password** — `/change-password`
- Purpose: Forces a temporary-password user to set a new password before continuing (`POST /api/v1/auth/change-password`).
- Components: Button, Input, Label, LogoMark, useAuth.
- Migration priority: **Not in scope** (same reason as Login).

**Not Found** — catch-all 404
- Purpose: Generic fallback for unmatched routes, with a link back to `/`.
- Components: wouter Link, panel, lucide icons.
- Migration priority: **Not in scope**.
