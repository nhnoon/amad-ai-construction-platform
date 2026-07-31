import { useTranslation } from "react-i18next";
import { Link } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { PageHero } from "@/components/PageHero";
import { KpiStat } from "@/components/KpiStat";
import { InsightPanel } from "@/components/InsightPanel";
import {
  AlertTriangle, ArrowRight, CheckCircle, Download, FileText,
  FileWarning, HeartPulse, LayoutGrid, ShieldAlert,
} from "lucide-react";
import { useExecutive, usePortfolioTrend } from "../../lib/useExecutive";
import { useDashboardSummary } from "../../lib/useDashboardSummary";
import { GLASS, EXEC_LEVEL_CFG } from "./shared";
import { PortfolioHealthDonut, ProjectStatusChart, BiggestRisksBarChart, PortfolioTrendChart } from "./Charts";
import { QuickActions } from "./QuickActions";

// ── Executive Dashboard (AMAD v2) ───────────────────────────────────────────
// The app's landing/command surface — same tier as AI Center Overview, so it
// uses the same PageHero + InsightPanel primitives instead of the generic
// WorkspaceLayout list-page shell. Reading order is deliberately
// judgment-first: what needs a decision (Executive Summary + Attention
// Required, both real backend fields already fetched by useExecutive() but
// previously left unrendered) comes before the supporting KPIs and charts,
// not after. No new endpoints, no fabricated text — every figure and every
// listed project comes from useExecutive() / useDashboardSummary() /
// usePortfolioTrend(), the same three hooks this page already called.

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

export default function Dashboard() {
  const { t } = useTranslation();
  const { data: execData, isLoading: execLoading, isError: execError, refetch: refetchExec } = useExecutive();
  const { data: summary, isLoading: summaryLoading, isError: summaryError, refetch: refetchSummary } = useDashboardSummary();
  const { data: trend, isLoading: trendLoading } = usePortfolioTrend();

  const isLoading = execLoading || summaryLoading;
  const isError = execError || summaryError;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-2xl" />
        <div className="grid gap-3 lg:grid-cols-[1fr_340px] items-stretch">
          <Skeleton className={`${GLASS} h-40 w-full`} />
          <Skeleton className={`${GLASS} h-40 w-full`} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className={`${GLASS} min-h-[92px] w-full`} />)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className={`${GLASS} h-64 w-full`} />)}
        </div>
        <Skeleton className={`${GLASS} h-64 w-full`} />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className={`${GLASS} h-16 w-full`} />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Unable to load dashboard data"
        description="Check your connection and try refreshing."
        action={
          <button
            className="text-xs font-medium text-primary hover:underline"
            onClick={() => { refetchExec(); refetchSummary(); }}
          >
            Retry
          </button>
        }
      />
    );
  }

  const portfolioHealthData = execData
    ? [
        { name: "Excellent", value: execData.excellent_count, color: EXEC_LEVEL_CFG.Excellent.color },
        { name: "Good", value: execData.good_count, color: EXEC_LEVEL_CFG.Good.color },
        { name: "At Risk", value: execData.at_risk_count, color: EXEC_LEVEL_CFG["At Risk"].color },
        { name: "Critical", value: execData.critical_count, color: EXEC_LEVEL_CFG.Critical.color },
      ]
    : [];

  const projectStatusData = [
    { name: "Active", value: summary?.active_projects ?? 0, color: "#16a34a" },
    { name: "Delayed", value: summary?.delayed_projects ?? 0, color: "#dc2626" },
    { name: "On Hold", value: summary?.on_hold_projects ?? 0, color: "#d97706" },
    { name: "Completed", value: summary?.completed_projects ?? 0, color: "#2563eb" },
  ];

  const portfolioTone = execData
    ? execData.portfolio_status === "Critical" ? "danger" : execData.portfolio_status === "At Risk" ? "warning" : "success"
    : "neutral";
  const attentionProjects = execData?.attention_required.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      {/* 1 — Hero ────────────────────────────────────────────────────── */}
      <PageHero
        eyebrow={t("Executive Dashboard")}
        title="Portfolio Overview"
        description="Portfolio health and performance across all active projects."
        meta={<span>{new Date().toLocaleDateString("en-SA", { year: "numeric", month: "long", day: "numeric" })}</span>}
        primaryAction={
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg border border-sidebar-primary/50 text-sidebar-primary text-xs font-semibold hover:bg-sidebar-primary/10 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> Download Report
          </Link>
        }
      />

      <ExecutiveSuiteNav current="dashboard" />

      {/* 2 — Executive Summary (dominant) + Attention Required — the two
          decision-oriented sections, surfaced before any chart or number. */}
      <div className="grid gap-3 lg:grid-cols-[1fr_340px] items-stretch">
        <InsightPanel
          icon={FileText}
          title="Executive Summary"
          variant="brief"
          footer={
            <Link href="/reports" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              View full executive report <ArrowRight className="w-3 h-3" />
            </Link>
          }
        >
          <p className="text-[13px] text-muted-foreground leading-normal">
            {execData?.executive_summary}
          </p>
        </InsightPanel>

        <div className="panel h-full flex flex-col">
          <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
            <span className="font-semibold text-[13px] text-foreground flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" /> Needs Attention
            </span>
            {attentionProjects.length > 0 && <span className="badge badge-warning text-[9px]">{attentionProjects.length}</span>}
          </div>
          <div className="p-1.5 flex-1">
            {attentionProjects.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2 px-1.5">No projects currently need urgent attention.</p>
            ) : (
              <div className="space-y-px">
                {attentionProjects.map((p) => {
                  const tone = EXEC_LEVEL_CFG[p.level] ?? EXEC_LEVEL_CFG.Good;
                  return (
                    <Link
                      key={p.project_id}
                      href={`/projects/${p.project_id}`}
                      title={`${p.project_name} — ${p.level}, score ${p.score}. ${p.primary_reason}`}
                      className="grid grid-cols-[auto_1fr_auto] items-center gap-1.5 px-1.5 py-1 rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: tone.color }} />
                      <span className="min-w-0">
                        <p className="text-[11px] font-semibold text-foreground truncate leading-tight">{p.project_code}</p>
                        <p className="text-[9.5px] text-muted-foreground truncate leading-tight mt-px">{p.primary_reason}</p>
                      </span>
                      <span className="text-end text-[11px] font-bold shrink-0" style={{ color: tone.color }}>{p.score}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
          <div className="px-3.5 pb-3">
            <Link href="/projects" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              View all projects <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* 3 — KPI Row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <KpiStat icon={HeartPulse} label="Portfolio Score" value={execData?.portfolio_score ?? "—"} description="Overall health" tone={portfolioTone} />
        <KpiStat icon={CheckCircle} label="Active Projects" value={summary?.active_projects ?? 0} description="In progress" tone="success" href="/projects" />
        <KpiStat icon={FileWarning} label="Delayed Projects" value={summary?.delayed_projects ?? 0} description="Behind schedule" tone={(summary?.delayed_projects ?? 0) > 0 ? "warning" : "success"} href="/projects" />
        <KpiStat icon={AlertTriangle} label="Critical Projects" value={execData?.critical_count ?? 0} description="Highest risk" tone={(execData?.critical_count ?? 0) > 0 ? "danger" : "success"} />
        <KpiStat icon={ShieldAlert} label="Open NCRs" value={summary?.open_ncrs ?? 0} description="Unresolved" tone={(summary?.open_ncrs ?? 0) > 0 ? "danger" : "success"} href="/safety" />
        <KpiStat icon={LayoutGrid} label="RFIs" value={summary?.total_rfis ?? 0} description="Total requests" tone="neutral" href="/rfis" />
      </div>

      {/* 4 — Analytics Row ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <PortfolioHealthDonut data={portfolioHealthData} />
        <ProjectStatusChart data={projectStatusData} />
        <BiggestRisksBarChart data={execData?.biggest_risks} />
      </div>

      {/* 5 — Portfolio Trend ─────────────────────────────────────────── */}
      <PortfolioTrendChart points={trend} isLoading={trendLoading} />

      {/* 6 — Quick Actions ───────────────────────────────────────────── */}
      <QuickActions />
    </div>
  );
}
