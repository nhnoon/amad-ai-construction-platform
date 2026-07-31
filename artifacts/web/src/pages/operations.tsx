import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  CalendarDays,
  ShoppingCart,
  ClipboardCheck,
  HelpCircle,
  AlertCircle,
  TrendingUp,
  ShieldAlert,
  Users,
  RefreshCw,
  AlertTriangle,
  ArrowRight,
  ChevronRight,
} from "lucide-react";
import { Link } from "wouter";
import { useGetDashboardSummary, useListProjects } from "@workspace/api-client-react";
import { PageHero } from "@/components/PageHero";
import { InsightPanel } from "@/components/InsightPanel";
import { StatTile, type StatTileTone } from "@/components/stat-tile";
import { SearchInput } from "@/components/search-input";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { ActivityTimeline } from "@/pages/dashboard/ActivityTimeline";
import { listDocuments } from "@/lib/aiCenterClient";

// ── AMAD v2 — Operations Overview ───────────────────────────────────────────
// The operational command center for Project Managers and Operations
// Managers — not an Executive Dashboard. Where the Executive Suite answers
// "what should leadership decide," this page answers "what does a PM need
// to do today": which projects are behind, what's waiting on approval,
// what's blocking procurement, and what changed since yesterday. Same
// PageHero/InsightPanel vocabulary as the rest of AMAD v2, applied here for
// the first time outside the Executive Suite. Every figure still comes
// from useGetDashboardSummary() (unchanged) plus useListProjects() (already
// used by Projects/Dashboard) — no new backend endpoints. The module grid
// keeps its original resilience design: it stays visible and navigable
// even if the live metrics fail to load, since a PM still needs to reach
// Projects/Procurement/Safety regardless of whether the counts loaded.

interface OperationModule {
  id: string;
  label: string;
  icon: React.ElementType;
  recordCount: number;
  description: string;
  route: string;
  tone: StatTileTone;
}

interface AttentionItem {
  id: string;
  label: string;
  route: string;
  icon: React.ElementType;
}

export default function Operations() {
  const { data: summary, isLoading, isError, refetch, isFetching } = useGetDashboardSummary();
  const { data: projects, isLoading: projectsLoading, isError: projectsError } = useListProjects({ limit: 100 });
  const [search, setSearch] = useState("");

  const { data: documents, isLoading: documentsLoading } = useQuery({
    queryKey: ["operations-documents"],
    queryFn: () => listDocuments({ scope: "all", limit: 100 }),
  });

  const modules: OperationModule[] = [
    {
      id: "projects", label: "Projects", icon: Briefcase,
      recordCount: summary?.total_projects ?? 0,
      description: `${summary?.active_projects ?? 0} active · ${summary?.delayed_projects ?? 0} delayed`,
      route: "/projects",
      tone: (summary?.delayed_projects ?? 0) > 0 ? "warning" : "success",
    },
    {
      id: "procurement", label: "Procurement", icon: ShoppingCart,
      recordCount: summary?.total_purchase_orders ?? 0,
      description: `${summary?.late_purchase_orders ?? 0} late POs · ${summary?.open_purchase_requests ?? 0} open PRs`,
      route: "/procurement",
      tone: (summary?.late_purchase_orders ?? 0) > 0 ? "warning" : "neutral",
    },
    {
      id: "site-reports", label: "Site Reports", icon: ClipboardCheck,
      recordCount: summary?.total_site_reports ?? 0,
      description: "Daily reporting and execution updates",
      route: "/site-reports",
      tone: "neutral",
    },
    {
      id: "meetings", label: "Meetings", icon: CalendarDays,
      recordCount: summary?.total_meetings ?? 0,
      description: `${summary?.total_decisions ?? 0} decisions captured`,
      route: "/meetings",
      tone: "neutral",
    },
    {
      id: "rfis", label: "RFIs", icon: HelpCircle,
      recordCount: summary?.total_decisions ?? 0,
      description: "Project clarifications and responses",
      route: "/rfis",
      tone: "neutral",
    },
    {
      id: "change-orders", label: "Change Orders", icon: AlertCircle,
      recordCount: summary?.open_ncrs ?? 0,
      description: "Contract scope and value adjustments",
      route: "/change-orders",
      tone: "neutral",
    },
    {
      id: "claims", label: "Claims", icon: TrendingUp,
      recordCount: summary?.high_severity_events ?? 0,
      description: "Dispute and entitlement tracking",
      route: "/claims",
      tone: (summary?.high_severity_events ?? 0) > 0 ? "danger" : "neutral",
    },
    {
      id: "safety", label: "Safety", icon: ShieldAlert,
      recordCount: summary?.open_ncrs ?? 0,
      description: "Site safety events and corrective actions",
      route: "/safety",
      tone: (summary?.open_ncrs ?? 0) > 0 ? "warning" : "success",
    },
    {
      id: "suppliers", label: "Suppliers", icon: Users,
      recordCount: summary?.total_suppliers ?? 0,
      description: `${summary?.active_suppliers ?? 0} active suppliers`,
      route: "/suppliers",
      tone: "neutral",
    },
  ];

  const filteredModules = useMemo(
    () => modules.filter((m) => m.label.toLowerCase().includes(search.trim().toLowerCase())),
    [modules, search],
  );

  // "What needs my attention today?" / "Which approvals are waiting?" /
  // "Which procurement issues are blocking work?" — one real, computed
  // list. `open_purchase_requests` is new here (the previous version only
  // ever flagged late POs, never PRs still awaiting approval/conversion —
  // the actual answer to "which approvals are waiting").
  const attentionItems: AttentionItem[] = useMemo(() => {
    if (!summary) return [];
    const items: AttentionItem[] = [];
    if (summary.delayed_projects > 0) {
      items.push({ id: "delayed", icon: Briefcase, route: "/projects", label: `${summary.delayed_projects} delayed project${summary.delayed_projects === 1 ? "" : "s"}` });
    }
    if (summary.open_purchase_requests > 0) {
      items.push({ id: "open-pr", icon: ShoppingCart, route: "/procurement", label: `${summary.open_purchase_requests} purchase request${summary.open_purchase_requests === 1 ? "" : "s"} awaiting approval` });
    }
    if (summary.late_purchase_orders > 0) {
      items.push({ id: "late-po", icon: ShoppingCart, route: "/procurement", label: `${summary.late_purchase_orders} late purchase order${summary.late_purchase_orders === 1 ? "" : "s"}` });
    }
    if (summary.open_ncrs > 0) {
      items.push({ id: "open-ncr", icon: ShieldAlert, route: "/safety", label: `${summary.open_ncrs} open safety NCR${summary.open_ncrs === 1 ? "" : "s"}` });
    }
    if (summary.high_severity_events > 0) {
      items.push({ id: "high-sev", icon: TrendingUp, route: "/claims", label: `${summary.high_severity_events} high-severity event${summary.high_severity_events === 1 ? "" : "s"}` });
    }
    return items;
  }, [summary]);

  // "Which projects are behind?" — named, not just counted. Reuses
  // useListProjects() (already called by Projects/Dashboard) filtered on
  // the real "Delayed" status value (see projects.tsx's own STATUS_BADGE
  // map) — no new endpoint, no synthetic scoring.
  const delayedProjects = useMemo(
    () => (projects ?? []).filter((p) => p.status === "Delayed"),
    [projects],
  );

  return (
    <div className="space-y-6">
      {/* 1 — Hero ────────────────────────────────────────────────────── */}
      <PageHero
        eyebrow="Operations"
        title="Operations Command Center"
        description="Today's cross-project operations at a glance — what's behind, what's waiting on you, and what changed since yesterday."
        meta={<span>{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</span>}
        search={
          <SearchInput
            compact
            value={search}
            onChange={setSearch}
            placeholder="Filter modules..."
            testId="input-operations-filter"
          />
        }
        primaryAction={
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg border border-sidebar-border text-sidebar-foreground/70 text-xs font-semibold hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors"
            data-testid="button-operations-refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} /> Refresh
          </button>
        }
      />

      {/* 2 — What needs attention today + which projects are behind ──── */}
      <div className="grid gap-3 lg:grid-cols-[1fr_340px] items-stretch">
        {isLoading ? (
          <Skeleton className="h-40 w-full rounded-xl" />
        ) : isError ? (
          <ErrorState title="Unable to load operational metrics" description="Navigation below still works." action={
            <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
          } />
        ) : (
          <InsightPanel
            icon={AlertTriangle}
            title="Needs Attention"
            variant="brief"
            badge={attentionItems.length === 0 ? <span className="badge badge-success text-[9px]">All Clear</span> : <span className="badge badge-warning text-[9px]">{attentionItems.length}</span>}
          >
            {attentionItems.length === 0 ? (
              <p className="text-[13px] text-muted-foreground leading-normal">
                All operational metrics are clear — no delayed projects, open approvals, late orders, or open safety issues.
              </p>
            ) : (
              <div className="space-y-1">
                {attentionItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.id}
                      href={item.route}
                      className="flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm text-foreground hover:bg-muted/50 transition-colors group"
                    >
                      <Icon className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                      <span className="flex-1">{item.label}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-primary transition-colors" />
                    </Link>
                  );
                })}
              </div>
            )}
          </InsightPanel>
        )}

        {projectsLoading ? (
          <Skeleton className="h-40 w-full rounded-xl" />
        ) : projectsError ? (
          <ErrorState title="Unable to load projects" description="Try refreshing the page." />
        ) : (
          <div className="panel h-full flex flex-col">
            <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
              <span className="font-semibold text-[13px] text-foreground flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5 text-red-600 dark:text-red-400" /> Projects Behind Schedule
              </span>
              {delayedProjects.length > 0 && <span className="badge badge-danger text-[9px]">{delayedProjects.length}</span>}
            </div>
            <div className="p-1.5 flex-1">
              {delayedProjects.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 px-1.5">No projects are currently marked delayed.</p>
              ) : (
                <div className="space-y-px">
                  {delayedProjects.slice(0, 6).map((p) => (
                    <Link
                      key={p.id}
                      href={`/projects/${p.id}`}
                      title={p.project_name}
                      className="grid grid-cols-[auto_1fr_auto] items-center gap-1.5 px-1.5 py-1 rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
                      <span className="min-w-0">
                        <p className="text-[11px] font-semibold text-foreground truncate leading-tight">{p.project_code}</p>
                        <p className="text-[9.5px] text-muted-foreground truncate leading-tight mt-px">{p.project_name}</p>
                      </span>
                      <ChevronRight className="w-3 h-3 text-muted-foreground/40 shrink-0" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
            <div className="px-3.5 pb-3">
              <Link href="/projects" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
                View all projects <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* 3 — Operations modules (navigational — stays visible even if
          the metrics above failed to load) ─────────────────────────── */}
      <div>
        <h2 className="section-title mb-2">Operations Modules</h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2.5">
          {filteredModules.map((module) => (
            <StatTile
              key={module.id}
              icon={module.icon}
              label={module.label}
              description={module.description}
              value={module.recordCount}
              valueLabel="items"
              tone={module.tone}
              href={module.route}
            />
          ))}
          {filteredModules.length === 0 && (
            <p className="col-span-full text-xs text-muted-foreground py-4 text-center">No modules match "{search}".</p>
          )}
        </div>
      </div>

      {/* 4 — What changed since yesterday ──────────────────────────── */}
      <ActivityTimeline documents={documents} isLoading={documentsLoading} />
    </div>
  );
}
