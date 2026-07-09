import { useTranslation } from "react-i18next";
import { Link } from "wouter";
import { useGetDashboardSummary } from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import {
  AlertTriangle, AlertOctagon, FileText, HeartPulse, CheckCircle, Building2,
  BarChart2, LayoutGrid, Sparkles,
} from "lucide-react";
import { useExecutive, type ExecutiveIntelligence } from "../lib/useExecutive";

// ── Visual system (Dashboard-only — no shared CSS touched) ─────────────────────
// One accent color (gold) governs all chrome: icon chips, CTA, highlights.
// Semantic color (severity/status) is reserved strictly for data encoding —
// donut segments, status cards, and risk bars — where dropping it would make
// the visualization unreadable.

const ACCENT = "#eab308";

const GLASS =
  "relative overflow-hidden rounded-3xl border border-border/70 bg-card shadow-sm " +
  "dark:border-white/[0.07] dark:bg-white/[0.03] dark:backdrop-blur-xl dark:shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset,0_24px_60px_-32px_rgba(0,0,0,0.9)]";

const GLASS_HEADER =
  "relative flex items-center gap-3 border-b border-border/60 dark:border-white/[0.05] px-5 py-4";

const CHART_TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "hsl(var(--foreground))",
};

const EXEC_LEVEL_CFG: Record<string, { color: string }> = {
  Excellent: { color: "#16a34a" },
  Good:      { color: "#2563eb" },
  "At Risk": { color: "#d97706" },
  Critical:  { color: "#dc2626" },
};

const EXEC_SEV_COLOR: Record<string, string> = {
  critical: "#dc2626",
  high:     "#d97706",
  medium:   "#2563eb",
  low:      "#16a34a",
};

function IconChip({ icon: Icon, className = "h-9 w-9" }: { icon: React.ElementType; className?: string }) {
  return (
    <div
      className={`relative flex shrink-0 items-center justify-center rounded-xl ${className}`}
      style={{ backgroundColor: `${ACCENT}17`, boxShadow: `0 0 0 1px ${ACCENT}30` }}
    >
      <Icon className="h-4 w-4" style={{ color: ACCENT }} />
    </div>
  );
}

// ── KPI tile ─────────────────────────────────────────────────────────────────

function KpiTile({
  icon: Icon, label, value, sub, isLoading,
}: { icon: React.ElementType; label: string; value: number | string; sub?: string; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-[92px] w-full`} />;
  return (
    <div className={`${GLASS} p-4`}>
      <div className="relative flex items-center gap-2.5">
        <IconChip icon={Icon} className="h-7 w-7" />
        <p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground truncate">{label}</p>
      </div>
      <p className="relative text-[26px] font-bold text-foreground leading-tight tabular-nums mt-3">{value}</p>
      {sub && <p className="relative text-[10px] text-muted-foreground/70 truncate mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Portfolio Health — the only donut on the page ───────────────────────────

function PortfolioHealthDonut({
  data, isLoading,
}: { data: { name: string; value: number; color: string }[]; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={HeartPulse} />
        <span className="text-sm font-bold text-foreground">Portfolio Health</span>
      </div>
      <div className="relative p-5 flex items-center gap-5">
        <div className="relative h-32 w-32 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={40} outerRadius={58} paddingAngle={3} strokeWidth={0} isAnimationActive={false}>
                {data.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-black text-foreground leading-none tabular-nums">{total}</span>
            <span className="text-[9px] text-muted-foreground mt-0.5">scored</span>
          </div>
        </div>
        <div className="flex-1 space-y-2.5 min-w-0">
          {data.map((d) => (
            <div key={d.name} className="flex items-center justify-between gap-2 text-xs">
              <span className="flex items-center gap-1.5 text-muted-foreground truncate">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                {d.name}
              </span>
              <span className="font-semibold text-foreground tabular-nums shrink-0">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Project Status — premium status cards, deliberately NOT a donut ────────

function ProjectStatusCard({
  data, isLoading,
}: { data: { name: string; value: number; color: string }[]; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={LayoutGrid} />
        <span className="text-sm font-bold text-foreground">Project Status</span>
      </div>
      <div className="relative p-5 grid grid-cols-2 gap-3">
        {data.map((d) => {
          const pct = Math.round((d.value / total) * 100);
          return (
            <div
              key={d.name}
              className="rounded-2xl border border-border/50 dark:border-white/[0.05] bg-muted/30 dark:bg-white/[0.02] p-4"
            >
              <div className="flex items-center gap-2 mb-2.5">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground truncate">{d.name}</span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-bold text-foreground tabular-nums leading-none">{d.value}</span>
                <span className="text-[10px] text-muted-foreground">{pct}%</span>
              </div>
              <div className="h-1 rounded-full bg-muted/60 dark:bg-white/[0.06] overflow-hidden mt-2.5">
                <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: d.color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Biggest Risks — sparkline-style bars, severity color retained
//    intentionally, this is the one place color-coding IS the information ──

function BiggestRisksCard({ data, isLoading }: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  if (!data) return null;
  const risks = data.biggest_risks.slice(0, 5);
  const max = Math.max(...risks.map((r) => r.count), 1);
  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={BarChart2} />
        <span className="text-sm font-bold text-foreground">Biggest Risks</span>
      </div>
      <div className="relative p-5 space-y-4">
        {risks.map((r) => {
          const color = EXEC_SEV_COLOR[r.severity] ?? "#6b7280";
          const pct = (r.count / max) * 100;
          return (
            <div key={r.category}>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-muted-foreground truncate">{r.label}</span>
                <span className="font-bold text-foreground tabular-nums shrink-0 ml-2">{r.count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted/50 dark:bg-white/[0.05] overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useGetDashboardSummary();
  const { data: execData, isLoading: execLoading } = useExecutive();

  if (isLoading) {
    return (
      <div className="space-y-7">
        <div className="space-y-2">
          <Skeleton className="h-9 w-72 rounded-lg" />
          <Skeleton className="h-4 w-52 rounded-lg" />
        </div>
        <Skeleton className={`${GLASS} h-16 w-full`} />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className={`${GLASS} h-[92px] w-full`} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => <Skeleton key={i} className={`${GLASS} h-72 w-full`} />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={`${GLASS} flex items-center justify-center h-56`}>
        <div className="relative text-center text-muted-foreground p-6">
          <IconChip icon={AlertOctagon} className="h-10 w-10 mx-auto" />
          <p className="text-sm font-medium mt-3">Unable to load dashboard data</p>
          <p className="text-xs mt-1">Check your connection and try refreshing.</p>
        </div>
      </div>
    );
  }

  const ap = data?.active_projects || 0;
  const tp = data?.total_projects || 0;
  const dp = data?.delayed_projects || 0;
  const opr = data?.open_purchase_requests || 0;

  const projectStatusData = [
    { name: "Active",    value: ap,                            color: "#16a34a" },
    { name: "Delayed",   value: dp,                             color: "#dc2626" },
    { name: "On Hold",   value: data?.on_hold_projects || 0,    color: "#d97706" },
    { name: "Completed", value: data?.completed_projects || 0,  color: "#2563eb" },
  ];

  const portfolioHealthData = execData
    ? [
        { name: "Excellent", value: execData.excellent_count, color: EXEC_LEVEL_CFG.Excellent.color },
        { name: "Good",      value: execData.good_count,      color: EXEC_LEVEL_CFG.Good.color },
        { name: "At Risk",   value: execData.at_risk_count,   color: EXEC_LEVEL_CFG["At Risk"].color },
        { name: "Critical",  value: execData.critical_count,  color: EXEC_LEVEL_CFG.Critical.color },
      ]
    : [];

  return (
    <div className="space-y-7">
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
            style={{ backgroundColor: ACCENT, color: "#1a1400" }}
          >
            <FileText className="w-3.5 h-3.5" /> Full Report
          </Link>
        </div>
      </div>

      {/* ── 3. Compact KPI row ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiTile icon={HeartPulse}    label="Portfolio Score"   value={execData?.portfolio_score ?? "—"} sub={execData?.portfolio_status} isLoading={execLoading} />
        <KpiTile icon={AlertOctagon}  label="Critical Projects" value={execData?.critical_count ?? 0}    sub="Need intervention" isLoading={execLoading} />
        <KpiTile icon={AlertTriangle} label="Delayed Projects"  value={dp} sub="Behind schedule" />
        <KpiTile icon={CheckCircle}   label="Active Projects"   value={ap} sub={`of ${tp} total`} />
        <KpiTile icon={Building2}     label="Total Projects"    value={tp} sub="Portfolio-wide" />
        <KpiTile icon={FileText}      label="Pending Review"    value={opr} sub="Purchase requests" />
      </div>

      {/* ── 4. Executive Analytics ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <PortfolioHealthDonut data={portfolioHealthData} isLoading={execLoading} />
        <ProjectStatusCard data={projectStatusData} />
        <BiggestRisksCard data={execData} isLoading={execLoading} />
      </div>
    </div>
  );
}
