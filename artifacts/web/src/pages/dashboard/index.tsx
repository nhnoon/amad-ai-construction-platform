import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { useGetDashboardSummary } from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertTriangle, AlertOctagon, FileText, HeartPulse, CheckCircle, ShieldAlert, FileStack,
  Sparkles, Clock,
} from "lucide-react";
import { useExecutive } from "../../lib/useExecutive";
import { useAlerts, useAlertsSummary } from "../../lib/useAlerts";
import { listDocuments } from "../../lib/aiCenterClient";
import { GLASS, IconChip, KpiTile, EXEC_LEVEL_CFG } from "./shared";
import { PortfolioHealthDonut, ProjectStatusCard, BiggestRisksCard } from "./Charts";
import { ExecutiveInsights } from "./ExecutiveInsights";
import { ActivityTimeline } from "./ActivityTimeline";
import { AlertsPanel } from "./AlertsPanel";
import { QuickActions } from "./QuickActions";

// ── Executive Dashboard ─────────────────────────────────────────────────────
// Landing page, read top-to-bottom in executive priority order: portfolio
// health -> what's active/delayed -> quality (NCRs) -> document library ->
// analytics -> plain-language insights -> what needs attention right now ->
// quick actions. Every number on this page comes from an endpoint already
// used elsewhere in the app (dashboard summary, executive intelligence,
// alerts, document list) — no new backend routes, schema, or AI logic.

export default function Dashboard() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useGetDashboardSummary();
  const { data: execData, isLoading: execLoading } = useExecutive();
  const { data: alertsSummary, isLoading: alertsSummaryLoading } = useAlertsSummary();
  const { data: alertsData, isLoading: alertsLoading } = useAlerts({ limit: 100 });
  const {
    data: documents, isLoading: documentsLoading,
  } = useQuery({
    queryKey: ["dashboard-documents"],
    queryFn: () => listDocuments({ scope: "all", limit: 100 }),
  });

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="space-y-2">
          <Skeleton className="h-9 w-72 rounded-lg" />
          <Skeleton className="h-4 w-52 rounded-lg" />
        </div>
        <Skeleton className={`${GLASS} h-16 w-full`} />
        <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className={`${GLASS} min-h-[100px] w-full`} />)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => <Skeleton key={i} className={`${GLASS} h-72 w-full`} />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={`${GLASS} flex items-center justify-center h-56`}>
        <div className="relative text-center text-muted-foreground p-6">
          <IconChip icon={AlertOctagon} className="h-10 w-10 mx-auto" tone="danger" />
          <p className="text-sm font-medium mt-3">Unable to load dashboard data</p>
          <p className="text-xs mt-1">Check your connection and try refreshing.</p>
        </div>
      </div>
    );
  }

  const ap = data?.active_projects || 0;
  const tp = data?.total_projects || 0;
  const dp = data?.delayed_projects || 0;
  const openNcrs = data?.open_ncrs || 0;
  const totalNcrs = data?.total_ncrs || 0;
  const documentCount = documents?.length;

  const projectStatusData = [
    { name: "Active", value: ap, color: "#16a34a" },
    { name: "Delayed", value: dp, color: "#dc2626" },
    { name: "On Hold", value: data?.on_hold_projects || 0, color: "#d97706" },
    { name: "Completed", value: data?.completed_projects || 0, color: "#2563eb" },
  ];

  const portfolioHealthData = execData
    ? [
        { name: "Excellent", value: execData.excellent_count, color: EXEC_LEVEL_CFG.Excellent.color },
        { name: "Good", value: execData.good_count, color: EXEC_LEVEL_CFG.Good.color },
        { name: "At Risk", value: execData.at_risk_count, color: EXEC_LEVEL_CFG["At Risk"].color },
        { name: "Critical", value: execData.critical_count, color: EXEC_LEVEL_CFG.Critical.color },
      ]
    : [];

  return (
    <div className="space-y-8">
      {/* ── 1. Executive Header ───────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-foreground">
            {t("Executive Dashboard")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Amad Construction Intelligence — real-time operations overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-500">Live</span>
          </span>
          <span className="badge badge-gold text-xs px-3 py-1.5">
            {new Date().toLocaleDateString("en-SA", { year: "numeric", month: "long", day: "numeric" })}
          </span>
        </div>
      </div>

      {/* ── 2. AI Executive Insight / Summary ─────────────────────────── */}
      <div className={GLASS}>
        <div className="relative flex items-center gap-4 px-5 py-4">
          <IconChip icon={Sparkles} />
          <p className="text-sm text-foreground/90 line-clamp-1 flex-1 min-w-0">
            {execLoading ? "Loading executive summary…" : execData?.executive_summary}
          </p>
          <Link
            href="/reports"
            className="shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-opacity hover:opacity-90"
            style={{ backgroundColor: "#eab308", color: "#1a1400" }}
          >
            <FileText className="w-3.5 h-3.5" /> Full Report
          </Link>
        </div>
      </div>

      {/* ── 3. KPI row — answers the executive questions in one glance ─── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiTile
          icon={HeartPulse} label="Portfolio Score"
          value={execData?.portfolio_score ?? "—"} sub={execData?.portfolio_status}
          tone={execData ? (execData.portfolio_status === "Critical" ? "danger" : execData.portfolio_status === "At Risk" ? "warning" : "success") : "neutral"}
          isLoading={execLoading} href="/reports"
        />
        <KpiTile
          icon={CheckCircle} label="Active Projects"
          value={ap} sub={`of ${tp} total`} tone="success"
        />
        <KpiTile
          icon={AlertTriangle} label="Delayed Projects"
          value={dp} sub="Behind schedule" tone={dp > 0 ? "warning" : "success"} href="/projects"
        />
        <KpiTile
          icon={ShieldAlert} label="Open NCRs"
          value={openNcrs} sub={`of ${totalNcrs} total`} tone={openNcrs > 0 ? "danger" : "success"} href="/safety"
        />
        <KpiTile
          icon={FileStack} label="Documents in Library"
          value={documentCount ?? "—"} sub="General + Project" isLoading={documentsLoading} href="/documents"
        />
        <KpiTile
          icon={AlertOctagon} label="Critical Projects"
          value={execData?.critical_count ?? 0} sub="Need intervention"
          tone={(execData?.critical_count ?? 0) > 0 ? "danger" : "success"}
          isLoading={execLoading}
        />
      </div>

      {/* ── 4. Executive Analytics ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <PortfolioHealthDonut data={portfolioHealthData} isLoading={execLoading} />
        <ProjectStatusCard data={projectStatusData} />
        <BiggestRisksCard data={execData} isLoading={execLoading} />
      </div>

      {/* ── 5. Executive Insights ───────────────────────────────────────── */}
      <ExecutiveInsights summary={data} execData={execData} documentCount={documentCount} isLoading={execLoading} />

      {/* ── 6 & 7. Activity Timeline + Alerts — what needs attention today ─ */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-muted-foreground shrink-0" />
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">What Needs Attention Today</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <ActivityTimeline documents={documents} isLoading={documentsLoading} />
          <AlertsPanel
            alerts={alertsData?.alerts}
            summary={alertsSummary}
            isLoading={alertsLoading || alertsSummaryLoading}
          />
        </div>
      </div>

      {/* ── 8. Quick Actions ─────────────────────────────────────────────── */}
      <QuickActions />
    </div>
  );
}
