import { useMemo, useState } from "react";
import { Link } from "wouter";
import { useListProjects } from "@workspace/api-client-react";
import {
  RotateCcw, LayoutDashboard, Clock3, Gavel, PieChart as PieChartIcon, Sparkles,
  Network, CalendarClock, Flame, AlertOctagon, Target, LineChart as LineChartIcon, FlaskConical,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { PageHero } from "@/components/PageHero";
import { InsightPanel } from "@/components/InsightPanel";
import { useExecutive } from "@/lib/useExecutive";
import { useExecutiveDecisionCenter } from "@/lib/useExecutiveDecisionCenter";
import type { Priority, SourceModule } from "@/lib/mockExecutiveDecisionCenter";
import { DemoDataBadge } from "./shared";
import { ExecutiveOverview } from "./ExecutiveOverview";
import { TodaysPriorities } from "./TodaysPriorities";
import { DecisionQueue } from "./DecisionQueue";
import { PortfolioRiskOverview } from "./PortfolioRiskOverview";
import { AIExecutiveBrief } from "./AIExecutiveBrief";
import { ModuleHighlights } from "./ModuleHighlights";
import { CriticalDecisionsTimeline } from "./CriticalDecisionsTimeline";
import { ExecutiveHeatMap } from "./ExecutiveHeatMap";
import { AttentionProjects } from "./AttentionProjects";
import { RecommendedActions } from "./RecommendedActions";
import { KpiTrends } from "./KpiTrends";

// ── Executive Decision Center Integration ───────────────────────────────
// This page is now the ACTION LAYER on top of the exact same executive
// data Dashboard, Reports, and Executive Intelligence already use — not a
// fourth, disconnected dashboard. Five sections were switched from this
// page's own synthetic generator onto useExecutive() (the same real
// /api/v1/executive data those three pages call):
//
//   1. Portfolio Health   → exec.portfolio_score / portfolio_status
//   2. Executive Summary  → exec.executive_summary (no fabricated brief)
//   3. Attention Projects → exec.attention_required (same list Dashboard's
//                           "Needs Attention" and Executive Intelligence's
//                           "Critical Projects" already show)
//   4. Risk Overview      → exec.excellent/good/at_risk/critical_count
//                           (the same 4-band split Dashboard's Portfolio
//                           Health donut already renders)
//
// This page's actual commercial differentiators — Today's Priorities, the
// Executive Decision Queue, the Critical Decisions Timeline, and
// cross-module recommended actions — have no real backend equivalent (no
// portfolio-wide decisions/priorities endpoint exists yet anywhere in the
// app) and stay exactly as they were: local demo data from
// lib/mockExecutiveDecisionCenter.ts + lib/useExecutiveDecisionCenter.ts,
// untouched by this pass. They're now grouped under an explicit "Decision
// Workspace — Illustrative" heading and each carries its own Demo badge,
// so the real/illustrative boundary is visible at a glance rather than
// left to a single page-level disclaimer to carry the whole page.

const MODULE_FILTER_OPTIONS: SourceModule[] = [
  "Project Memory", "Predictive Intelligence", "Supplier Risk Intelligence", "Material Intelligence", "Cross-Project Learning",
];

const EXEC_LEVEL_COLOR: Record<string, string> = {
  Excellent: "#16a34a", Good: "#2563eb", "At Risk": "#d97706", Critical: "#dc2626",
};

// The section container every multi-item list below renders inside — one
// bordered `.panel` with a proper `.panel-header` bar (icon, title,
// optional count/action) instead of a floating heading above bare content.
// Same {icon,title,subtitle,action} shape as Reports' PanelHeader and
// Executive Intelligence's SectionShell — a third independent
// implementation of the same pattern (see the migration report).
function SectionPanel({ icon: Icon, title, subtitle, action, children }: {
  icon: typeof LayoutDashboard; title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="flex items-center gap-2 min-w-0">
          <Icon className="w-4 h-4 text-primary shrink-0" />
          <span className="panel-title truncate">{title}</span>
        </span>
        {action ?? (subtitle ? <span className="text-[10px] text-muted-foreground shrink-0">{subtitle}</span> : null)}
      </div>
      <div className="panel-body space-y-2">{children}</div>
    </div>
  );
}

// Stabilization pass — the four executive pages (Dashboard, Reports,
// Executive Intelligence, Executive Decision Center) previously had no
// link to one another anywhere; a user had to already know all four
// existed and go back to the sidebar every time. This wayfinding strip
// makes them read as one connected suite. Defined identically (and
// intentionally duplicated, not extracted — out of scope for this pass)
// in all four pages; a real candidate for a shared primitive later.
const EXECUTIVE_SUITE_LINKS: { key: string; label: string; href: string }[] = [
  { key: "dashboard", label: "Dashboard", href: "/" },
  { key: "reports", label: "Reports", href: "/reports" },
  { key: "executive-intelligence", label: "Executive Intelligence", href: "/ai-center/executive" },
  { key: "decision-center", label: "Decision Center", href: "/ai-center/executive-decision-center" },
];

function ExecutiveSuiteNav({ current }: { current: string }) {
  return (
    <nav aria-label="Executive Suite" className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground me-0.5">Executive Suite</span>
      {EXECUTIVE_SUITE_LINKS.map((p) => p.key === current ? (
        <span key={p.key} className="badge badge-brand text-[11px] cursor-default" aria-current="page">{p.label}</span>
      ) : (
        <Link key={p.key} href={p.href} className="badge badge-neutral text-[11px] hover:bg-muted transition-colors">{p.label}</Link>
      ))}
    </nav>
  );
}

// Updated for the integration pass — this used to say every score,
// priority, decision, and recommendation on the page was illustrative.
// That's no longer true: Portfolio Health, Executive Summary, Attention
// Projects, and Risk Overview are now the same live data as Dashboard and
// Reports. Only the Decision Workspace tools below them remain synthetic.
function DemoDataStrategyNotice() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-dashed border-violet-400/60 bg-violet-500/5 px-3 py-2">
      <FlaskConical className="w-3.5 h-3.5 shrink-0 mt-0.5 text-violet-600 dark:text-violet-400" />
      <p className="text-xs text-violet-700 dark:text-violet-300 leading-normal">
        Portfolio Health, Executive Summary, Attention Projects, and Risk Overview below use the same live data as Dashboard
        and Reports. The Decision Workspace tools further down — Today's Priorities, the Decision Queue, the Decisions
        Timeline, and cross-module recommendations — are illustrative: no portfolio-wide decisions backend exists yet, so
        those sections demonstrate what this workspace will do once one does.
      </p>
    </div>
  );
}

// A small heading used twice — once for the real-data section, once for
// the still-illustrative Decision Workspace — so the live/demo boundary is
// visible at the section-grouping level, not just in the page-level
// notice above.
function ZoneHeading({ tone, icon: Icon, children }: { tone: "live" | "demo"; icon: typeof LayoutDashboard; children: React.ReactNode }) {
  return (
    <h3 className={`text-xs font-semibold uppercase tracking-wide flex items-center gap-1.5 ${tone === "live" ? "text-emerald-700 dark:text-emerald-400" : "text-violet-700 dark:text-violet-400"}`}>
      <Icon className="w-3.5 h-3.5" /> {children}
    </h3>
  );
}

function ExecutiveDecisionCenterSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
      </div>
      <Skeleton className="h-64 w-full rounded-xl" />
      <Skeleton className="h-72 w-full rounded-xl" />
    </div>
  );
}

export default function ExecutiveDecisionCenter() {
  const { data: projects, isLoading: projectsLoading, isError: projectsError, refetch: refetchProjects } = useListProjects({ limit: 100 });
  const { data: snapshot, isLoading, isError, refetch, isRefetching } = useExecutiveDecisionCenter(projects);
  const { data: exec, isLoading: execLoading, isError: execError, refetch: refetchExec } = useExecutive();

  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState<SourceModule | "all">("all");
  const [priorityFilter, setPriorityFilter] = useState<Priority | "all">("all");
  const [projectFilter, setProjectFilter] = useState<string>("all");

  const filtersActive = moduleFilter !== "all" || priorityFilter !== "all" || projectFilter !== "all" || !!search;
  const clearFilters = () => { setSearch(""); setModuleFilter("all"); setPriorityFilter("all"); setProjectFilter("all"); };

  const matchesSearch = (...fields: (string | undefined)[]) => {
    if (!search.trim()) return true;
    const q = search.trim().toLowerCase();
    return fields.some((f) => f?.toLowerCase().includes(q));
  };

  const filteredPriorities = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.todaysPriorities.filter((p) =>
      (moduleFilter === "all" || p.module === moduleFilter) &&
      (projectFilter === "all" || p.projectCode === projectFilter) &&
      matchesSearch(p.title, p.description));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, moduleFilter, projectFilter, search]);

  const filteredDecisions = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.decisionQueue.filter((d) =>
      (moduleFilter === "all" || d.module === moduleFilter) &&
      (priorityFilter === "all" || d.priority === priorityFilter) &&
      (projectFilter === "all" || d.projectCode === projectFilter) &&
      matchesSearch(d.title, d.description));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, moduleFilter, priorityFilter, projectFilter, search]);

  const filteredTimeline = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.criticalTimeline.filter((e) =>
      (moduleFilter === "all" || e.module === moduleFilter) &&
      (projectFilter === "all" || e.projectCode === projectFilter));
  }, [snapshot, moduleFilter, projectFilter]);

  // Integration fix — was `snapshot.attentionProjects` (this page's own
  // synthetic ranking); now the real `exec.attention_required`, the same
  // field Dashboard and Executive Intelligence already filter/slice.
  const filteredAttention = useMemo(() => {
    if (!exec) return [];
    return exec.attention_required.filter((p) => projectFilter === "all" || p.project_code === projectFilter).slice(0, 6);
  }, [exec, projectFilter]);

  const filteredActions = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.recommendedActions.filter((a) =>
      (moduleFilter === "all" || a.module === moduleFilter) &&
      (priorityFilter === "all" || a.priority === priorityFilter) &&
      matchesSearch(a.title, a.description));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, moduleFilter, priorityFilter, search]);

  // Integration fix — the real Excellent/Good/At Risk/Critical split,
  // the exact same four counts Dashboard's Portfolio Health donut already
  // renders, replacing this page's own synthetic per-project risk bands.
  const portfolioRiskData = useMemo(() => {
    if (!exec) return [];
    return [
      { name: "Excellent", value: exec.excellent_count, color: EXEC_LEVEL_COLOR.Excellent },
      { name: "Good", value: exec.good_count, color: EXEC_LEVEL_COLOR.Good },
      { name: "At Risk", value: exec.at_risk_count, color: EXEC_LEVEL_COLOR["At Risk"] },
      { name: "Critical", value: exec.critical_count, color: EXEC_LEVEL_COLOR.Critical },
    ];
  }, [exec]);

  if (projectsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <ExecutiveDecisionCenterSkeleton />
      </div>
    );
  }

  if (projectsError) {
    return (
      <ErrorState title="Unable to load projects" description="Check your connection and try again." action={
        <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetchProjects()}>Retry</button>
      } />
    );
  }

  if (!projects?.length) {
    return <EmptyState icon={LayoutDashboard} title="No projects yet" description="The Executive Decision Center needs at least one active project to summarize." />;
  }

  return (
    <div className="space-y-6">
      {/* 1 — Hero ────────────────────────────────────────────────────── */}
      <PageHero
        eyebrow="AI Center"
        title="Executive Decision Center"
        description="Every decision that needs executive attention today — prioritized, explained, and ready to act on."
        meta={snapshot ? <span>Generated {new Date(snapshot.generatedAt).toLocaleString()}</span> : undefined}
        primaryAction={
          <button
            onClick={() => { refetch(); refetchExec(); }}
            disabled={isRefetching}
            className="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg border border-sidebar-border text-sidebar-foreground/70 text-xs font-semibold hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors disabled:opacity-50 disabled:pointer-events-none"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <ExecutiveSuiteNav current="decision-center" />
      <DemoDataStrategyNotice />

      {isLoading || !snapshot || execLoading || !exec ? (
        isError || execError ? (
          <ErrorState title="Unable to load the executive brief" description="Something went wrong generating the summary." action={
            <button className="text-xs font-medium text-primary hover:underline" onClick={() => { refetch(); refetchExec(); }}>Retry</button>
          } />
        ) : (
          <ExecutiveDecisionCenterSkeleton />
        )
      ) : (
        <>
          {/* 2 — Filters (a toolbar, not a card) ──────────────────────── */}
          <div className="flex flex-wrap items-center gap-2 pb-1 border-b border-border/50">
            <SearchInput value={search} onChange={setSearch} placeholder="Search priorities, decisions, and actions..." testId="input-executive-search" />
            <FilterSelect value={moduleFilter} onChange={(v) => setModuleFilter(v as typeof moduleFilter)} className="w-52" ariaLabel="Source module">
              <option value="all">All modules</option>
              {MODULE_FILTER_OPTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
            </FilterSelect>
            <FilterSelect value={priorityFilter} onChange={(v) => setPriorityFilter(v as typeof priorityFilter)} className="w-36" ariaLabel="Priority">
              <option value="all">All priorities</option>
              {(["High", "Medium", "Low"] as Priority[]).map((p) => <option key={p} value={p}>{p} priority</option>)}
            </FilterSelect>
            <FilterSelect value={projectFilter} onChange={setProjectFilter} className="w-48" ariaLabel="Project">
              <option value="all">All projects</option>
              {projects.map((p) => <option key={p.id} value={p.project_code}>{p.project_code} — {p.project_name}</option>)}
            </FilterSelect>
            {filtersActive && <button onClick={clearFilters} className="text-xs text-primary hover:underline shrink-0">Clear filters</button>}
          </div>

          {/* 3 — Live Portfolio Data (same source as Dashboard/Reports) ── */}
          <div className="space-y-3">
            <ZoneHeading tone="live" icon={Sparkles}>Live Portfolio Data</ZoneHeading>

            <div className="grid gap-3 lg:grid-cols-[1fr_340px] items-stretch">
              <InsightPanel icon={Sparkles} title="Executive Summary" variant="brief">
                <AIExecutiveBrief summary={exec.executive_summary} score={exec.portfolio_score} status={exec.portfolio_status} />
              </InsightPanel>

              <SectionPanel
                icon={AlertOctagon} title="Attention Projects"
                action={filteredAttention.length > 0 ? <span className="badge badge-danger text-[9px]">{filteredAttention.length}</span> : undefined}
              >
                <AttentionProjects projects={filteredAttention} />
              </SectionPanel>
            </div>

            <div className="grid gap-3 lg:grid-cols-[1fr_320px] items-stretch">
              <ExecutiveOverview
                score={exec.portfolio_score}
                status={exec.portfolio_status}
                activeProjects={exec.total_projects}
                criticalCount={exec.critical_count}
                atRiskCount={exec.at_risk_count}
              />
              <div className="panel h-full flex flex-col">
                <div className="panel-header">
                  <span className="flex items-center gap-2"><PieChartIcon className="w-4 h-4 text-primary" /><span className="panel-title">Risk Distribution</span></span>
                </div>
                <div className="panel-body flex-1 flex items-center">
                  <PortfolioRiskOverview data={portfolioRiskData} />
                </div>
              </div>
            </div>
          </div>

          {/* 4 — Decision Workspace (illustrative — this page's own value) */}
          <div className="space-y-3">
            <ZoneHeading tone="demo" icon={FlaskConical}>Decision Workspace — Illustrative</ZoneHeading>

            <SectionPanel icon={Clock3} title="Today's Priorities" action={<DemoDataBadge label="Demo" />}>
              <TodaysPriorities items={filteredPriorities} />
            </SectionPanel>

            <SectionPanel
              icon={Gavel} title="Executive Decision Queue"
              action={
                <span className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] text-muted-foreground">{filteredDecisions.length} of {snapshot.decisionQueue.length}</span>
                  <DemoDataBadge label="Demo" />
                </span>
              }
            >
              <DecisionQueue items={filteredDecisions} referenceIso={snapshot.generatedAt} />
            </SectionPanel>

            <SectionPanel
              icon={CalendarClock} title="Critical Decisions Timeline"
              action={<DemoDataBadge label="Demo" />}
            >
              <CriticalDecisionsTimeline events={filteredTimeline} referenceIso={snapshot.generatedAt} />
            </SectionPanel>
          </div>

          {/* 5 — Supporting detail (illustrative) ──────────────────────── */}
          <div className="panel">
            <div className="panel-header">
              <span className="flex items-center gap-2"><Flame className="w-4 h-4 text-primary" /><span className="panel-title">Executive Heat Map</span></span>
              <DemoDataBadge label="Demo" />
            </div>
            <div className="panel-body space-y-2">
              <p className="text-[11px] text-muted-foreground">
                Illustrative per-dimension risk scoring — no live schedule/budget/safety/supplier/material breakdown exists
                per project yet. The real portfolio-level risk split is shown above under Risk Distribution.
              </p>
              <ExecutiveHeatMap rows={snapshot.heatMapRows} />
            </div>
          </div>

          <InsightPanel
            icon={Target} title="Cross-Module Recommended Actions" variant="decision"
            badge={<DemoDataBadge />}
          >
            <p className="text-[11px] text-muted-foreground -mt-1 mb-2">
              Synthesized across the five AI Center modules below — illustrative, and independent of the{" "}
              <Link href="/reports" className="text-primary hover:underline">Weekly Report's</Link> recommended actions.
            </p>
            <RecommendedActions actions={filteredActions} />
          </InsightPanel>

          <SectionPanel icon={LineChartIcon} title="KPI Trends" action={<DemoDataBadge label="Demo" />}>
            <p className="text-[11px] text-muted-foreground -mt-1">
              Illustrative 8-week trend. A real single-line portfolio-score history already exists — see Dashboard's
              Portfolio Trend chart — but decision-backlog and critical-alert history are not yet tracked over time.
            </p>
            <KpiTrends data={snapshot.kpiTrend} />
          </SectionPanel>

          {/* 6 — Where to go next ────────────────────────────────────────── */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
              <Network className="w-3.5 h-3.5" /> Cross-Module Highlights <DemoDataBadge label="Demo" className="ms-1" />
            </h3>
            <ModuleHighlights highlights={snapshot.moduleHighlights} />
          </div>

          <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1.5">
            <Network className="w-3 h-3" /> Decision Workspace generated {new Date(snapshot.generatedAt).toLocaleString()} &middot;
            Today's Priorities, Decision Queue, Timeline, Heat Map, KPI Trends, and Cross-Module Recommended Actions are
            illustrative — everything else on this page is live portfolio data, shared with Dashboard and Reports.
          </p>
        </>
      )}
    </div>
  );
}
