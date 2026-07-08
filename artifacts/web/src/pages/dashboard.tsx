import { useTranslation } from "react-i18next";
import { Link } from "wouter";
import { useGetDashboardSummary, useListProjectHealthScores } from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import {
  Briefcase, CheckCircle, AlertTriangle, TrendingUp,
  ShoppingCart, ShieldAlert, ClipboardCheck,
  PauseCircle, AlertOctagon, FileText, HeartPulse,
  Bell, CalendarDays, Zap, Target, Trophy, TrendingDown, BarChart2,
} from "lucide-react";
import { useAlerts, type Alert, type AlertCategory } from "../lib/useAlerts";
import { useExecutive, type ExecutiveIntelligence } from "../lib/useExecutive";

// ── Alerts Preview Widget ──────────────────────────────────────────────────────

const ALERT_CAT_ICON: Record<AlertCategory, React.ElementType> = {
  health:      HeartPulse,
  safety:      ShieldAlert,
  procurement: ShoppingCart,
  quality:     ClipboardCheck,
  schedule:    CalendarDays,
};

const ALERT_SEV_BADGE: Record<string, string> = {
  critical: "badge-danger",
  high:     "badge-warning",
  medium:   "badge-neutral",
  low:      "badge-success",
};

function AlertRow({ alert }: { alert: Alert }) {
  const CatIcon = ALERT_CAT_ICON[alert.category as AlertCategory] ?? Bell;
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-border/40 last:border-0">
      <CatIcon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-foreground truncate">{alert.title}</span>
          <span className={`badge ${ALERT_SEV_BADGE[alert.severity] ?? "badge-neutral"} text-[9px] shrink-0`}>
            {alert.severity}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{alert.description}</p>
      </div>
    </div>
  );
}

function AlertsPreviewWidget() {
  const { t } = useTranslation();
  const { data, isLoading } = useAlerts({ limit: 5 });
  const alerts = data?.alerts ?? [];
  const total  = data?.total ?? 0;

  return (
    <div className="panel">
      <div className="panel-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-destructive" />
          <span className="panel-title">{t("Active Alerts")}</span>
          {total > 0 && (
            <span className="min-w-[20px] h-5 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold flex items-center justify-center px-1.5">
              {total > 99 ? "99+" : total}
            </span>
          )}
        </div>
        <Link href="/alerts" className="text-xs text-primary hover:underline flex items-center gap-1">
          {t("View all")} →
        </Link>
      </div>
      <div className="panel-body">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : alerts.length === 0 ? (
          <div className="py-6 flex flex-col items-center gap-2 text-center">
            <CheckCircle className="w-8 h-8 text-emerald-500 opacity-60" />
            <p className="text-xs text-muted-foreground">No active alerts — systems nominal</p>
          </div>
        ) : (
          <div>
            {alerts.map((alert) => <AlertRow key={alert.id} alert={alert} />)}
            {total > 5 && (
              <Link href="/alerts" className="block mt-3 text-xs text-center text-primary hover:underline">
                +{total - 5} more alert{total - 5 !== 1 ? "s" : ""} — view all
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Executive Intelligence components ──────────────────────────────────────────

const EXEC_LEVEL_CFG: Record<string, { color: string; bg: string; border: string }> = {
  Excellent: { color: "#16a34a", bg: "rgba(22,163,74,0.08)",   border: "rgba(22,163,74,0.22)"  },
  Good:      { color: "#2563eb", bg: "rgba(37,99,235,0.08)",   border: "rgba(37,99,235,0.22)"  },
  "At Risk": { color: "#d97706", bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.22)" },
  Critical:  { color: "#dc2626", bg: "rgba(220,38,38,0.08)",   border: "rgba(220,38,38,0.22)"  },
  Unknown:   { color: "#6b7280", bg: "rgba(107,114,128,0.08)", border: "rgba(107,114,128,0.22)"},
};

const EXEC_SEV_CFG: Record<string, { color: string; bg: string }> = {
  critical: { color: "#dc2626", bg: "rgba(220,38,38,0.10)"  },
  high:     { color: "#d97706", bg: "rgba(245,158,11,0.10)" },
  medium:   { color: "#2563eb", bg: "rgba(37,99,235,0.10)"  },
  low:      { color: "#16a34a", bg: "rgba(22,163,74,0.10)"  },
};

const EXEC_CAT_ICON: Record<string, React.ElementType> = {
  safety:      ShieldAlert,
  procurement: ShoppingCart,
  quality:     ClipboardCheck,
  schedule:    CalendarDays,
  health:      HeartPulse,
};

// Portfolio status + score card
function ExecPortfolioCard({
  data, isLoading,
}: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="min-h-[220px] w-full rounded-xl" />;
  if (!data) return null;
  const cfg = EXEC_LEVEL_CFG[data.portfolio_status] ?? EXEC_LEVEL_CFG["Unknown"];
  const counts = [
    { label: "Critical", value: data.critical_count, color: "#dc2626" },
    { label: "At Risk",  value: data.at_risk_count,  color: "#d97706" },
    { label: "Good",     value: data.good_count,     color: "#2563eb" },
    { label: "Excellent",value: data.excellent_count,color: "#16a34a" },
  ];
  return (
    <div className="panel overflow-hidden" style={{ borderLeft: `3px solid ${cfg.color}` }}>
      <div className="panel-body flex flex-col items-center justify-center gap-3 py-6 text-center">
        <div>
          <div className="text-5xl font-black leading-none" style={{ color: cfg.color }}>
            {data.portfolio_score}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">/100 average</div>
        </div>
        <div
          className="px-4 py-1.5 rounded-full text-sm font-bold tracking-wide"
          style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}
        >
          {data.portfolio_status}
        </div>
        <div className="grid grid-cols-2 gap-2 w-full mt-1">
          {counts.map(({ label, value, color }) => (
            <div key={label}
              className="flex flex-col items-center rounded-lg py-2"
              style={{ backgroundColor: "hsl(var(--muted)/0.5)" }}
            >
              <span className="text-lg font-black leading-none" style={{ color }}>{value}</span>
              <span className="text-[10px] text-muted-foreground mt-0.5">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Executive summary + count badges
function ExecSummaryCard({
  data, isLoading,
}: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="min-h-[220px] w-full rounded-xl" />;
  if (!data) return null;
  return (
    <div className="panel h-full">
      <div className="panel-header">
        <span className="panel-title">Executive Summary</span>
        <span className="ml-auto text-[10px] text-muted-foreground">Deterministic · Live Data</span>
      </div>
      <div className="panel-body space-y-4">
        <p className="text-sm text-foreground leading-relaxed">{data.executive_summary}</p>
        <div className="flex flex-wrap gap-2">
          {data.total_projects > 0 && (
            <span className="badge badge-neutral">{data.total_projects} Projects</span>
          )}
          {data.critical_count > 0 && (
            <span className="badge badge-danger">{data.critical_count} Critical</span>
          )}
          {data.at_risk_count > 0 && (
            <span className="badge badge-warning">{data.at_risk_count} At Risk</span>
          )}
          {data.good_count > 0 && (
            <span className="badge badge-neutral">{data.good_count} Good</span>
          )}
          {data.excellent_count > 0 && (
            <span className="badge badge-neutral" style={{ color: "#16a34a" }}>
              {data.excellent_count} Excellent
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// Top priorities list (worst-performing active projects)
function ExecTopPrioritiesCard({
  data, isLoading,
}: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;
  if (!data) return null;
  return (
    <div className="panel">
      <div className="panel-header flex items-center gap-2">
        <Target className="w-4 h-4 text-amber-500 shrink-0" />
        <span className="panel-title">Top Priorities</span>
        <span className="ml-auto text-[10px] text-muted-foreground">Executive Action Required</span>
      </div>
      <div className="panel-body divide-y divide-border/40">
        {data.top_priorities.length === 0 ? (
          <p className="py-6 text-xs text-muted-foreground text-center">
            No priority issues detected
          </p>
        ) : (
          data.top_priorities.map((p, i) => {
            const cfg = EXEC_LEVEL_CFG[p.level] ?? EXEC_LEVEL_CFG["Unknown"];
            return (
              <div key={p.project_id} className="flex items-start gap-3 py-2.5">
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
                  style={{ backgroundColor: cfg.bg, color: cfg.color }}
                >
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-foreground">{p.project_code}</span>
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: cfg.bg, color: cfg.color }}
                    >
                      {p.level} · {p.score}/100
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">
                    {p.primary_reason}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// Biggest risks with horizontal bar visualization
function ExecBiggestRisksCard({
  data, isLoading,
}: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;
  if (!data) return null;
  const maxCount = Math.max(...data.biggest_risks.map((r) => r.count), 1);
  return (
    <div className="panel">
      <div className="panel-header flex items-center gap-2">
        <BarChart2 className="w-4 h-4 text-rose-500 shrink-0" />
        <span className="panel-title">Biggest Risks</span>
        <span className="ml-auto text-[10px] text-muted-foreground">Ranked by Severity</span>
      </div>
      <div className="panel-body space-y-3.5">
        {data.biggest_risks.map((risk) => {
          const CatIcon = EXEC_CAT_ICON[risk.category] ?? ShieldAlert;
          const sevCfg = EXEC_SEV_CFG[risk.severity] ?? EXEC_SEV_CFG["medium"];
          const barPct = (risk.count / maxCount) * 100;
          return (
            <div key={risk.category}>
              <div className="flex items-center gap-2 mb-1.5">
                <CatIcon className="w-3.5 h-3.5 shrink-0" style={{ color: sevCfg.color }} />
                <span className="text-xs font-medium text-foreground flex-1">{risk.label}</span>
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded capitalize shrink-0"
                  style={{ backgroundColor: sevCfg.bg, color: sevCfg.color }}
                >
                  {risk.severity}
                </span>
                <span className="text-xs font-bold text-foreground w-8 text-right shrink-0">
                  {risk.count}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${barPct}%`, backgroundColor: sevCfg.color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Best-performing projects (medal board)
function ExecBestProjectsCard({
  data, isLoading,
}: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;
  if (!data) return null;
  const medals = ["🥇", "🥈", "🥉"];
  return (
    <div className="panel">
      <div className="panel-header flex items-center gap-2">
        <Trophy className="w-4 h-4 text-amber-500 shrink-0" />
        <span className="panel-title">Best Performing Projects</span>
      </div>
      <div className="panel-body divide-y divide-border/40">
        {data.best_projects.length === 0 ? (
          <p className="py-6 text-xs text-muted-foreground text-center">
            No excellent/good active projects found
          </p>
        ) : (
          data.best_projects.map((p, i) => {
            const cfg = EXEC_LEVEL_CFG[p.level] ?? EXEC_LEVEL_CFG["Good"];
            return (
              <div key={p.project_id} className="flex items-center gap-3 py-2.5">
                <span className="w-6 text-center text-base leading-none shrink-0">
                  {medals[i] ?? <span className="text-xs text-muted-foreground font-bold">{i + 1}</span>}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-foreground">{p.project_code}</span>
                    <span className="text-[10px] font-medium" style={{ color: cfg.color }}>
                      {p.level}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate">{p.project_name}</p>
                </div>
                <div className="flex flex-col items-end shrink-0">
                  <span className="text-xl font-black leading-none" style={{ color: cfg.color }}>
                    {p.score}
                  </span>
                  <span className="text-[9px] text-muted-foreground">/100</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// Projects requiring immediate attention
function ExecAttentionCard({
  data, isLoading,
}: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;
  if (!data) return null;
  const hasCritical = data.attention_required.length > 0;
  return (
    <div
      className="panel"
      style={hasCritical ? { borderLeft: "3px solid #dc2626" } : undefined}
    >
      <div className="panel-header flex items-center gap-2">
        <TrendingDown className="w-4 h-4 text-destructive shrink-0" />
        <span className="panel-title">Requiring Immediate Attention</span>
        {hasCritical && (
          <span className="ml-auto min-w-[20px] h-5 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold flex items-center justify-center px-1.5 shrink-0">
            {data.attention_required.length}
          </span>
        )}
      </div>
      <div className="panel-body divide-y divide-border/40">
        {!hasCritical ? (
          <div className="py-6 flex flex-col items-center gap-2 text-center">
            <CheckCircle className="w-7 h-7 text-emerald-500 opacity-70" />
            <p className="text-xs text-muted-foreground">No projects require immediate attention</p>
          </div>
        ) : (
          data.attention_required.map((p) => {
            const cfg = EXEC_LEVEL_CFG[p.level] ?? EXEC_LEVEL_CFG["At Risk"];
            return (
              <div key={p.project_id} className="flex items-start gap-3 py-2.5">
                <div
                  className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  style={{ backgroundColor: cfg.color }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-foreground">{p.project_code}</span>
                    <span className="text-[10px]" style={{ color: cfg.color }}>
                      {p.level} · {p.score}/100
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
                    {p.primary_reason}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// Map accent class → icon container bg (safe explicit /15 Tailwind v4 syntax)
const ICON_BG: Record<string, string> = {
  "bg-primary":      "bg-primary/15",
  "bg-emerald-500":  "bg-emerald-500/15",
  "bg-red-500":      "bg-red-500/15",
  "bg-amber-500":    "bg-amber-500/15",
  "bg-blue-500":     "bg-blue-500/15",
  "bg-violet-500":   "bg-violet-500/15",
  "bg-orange-500":   "bg-orange-500/15",
  "bg-pink-500":     "bg-pink-500/15",
  "bg-cyan-500":     "bg-cyan-500/15",
  "bg-rose-600":     "bg-rose-600/15",
};

interface KpiCardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  accent: string;
  sub?: string;
  badge?: string;
}

function KpiCard({ label, value, icon: Icon, accent, sub, badge }: KpiCardProps) {
  const iconBg = ICON_BG[accent] ?? "bg-muted";
  return (
    <div className="panel relative overflow-hidden">
      <div className={`absolute inset-0 opacity-[0.04] ${accent}`} />
      <div className="panel-body flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            {label}
          </p>
          <p className="text-4xl font-bold text-foreground leading-none">
            {value}
          </p>
          {sub && (
            <p className="text-xs text-muted-foreground mt-2">{sub}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${iconBg}`}>
            <Icon className="w-5 h-5 text-foreground opacity-70" />
          </div>
          {badge && (
            <span className={`badge ${badge} text-[10px]`}>!</span>
          )}
        </div>
      </div>
      <div className={`h-1 w-full ${accent} opacity-60`} />
    </div>
  );
}

const CHART_TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "hsl(var(--foreground))",
};

const HEALTH_LEVEL_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  "Excellent": { color: "#16a34a", bg: "rgba(22,163,74,0.10)",   border: "rgba(22,163,74,0.25)"  },
  "Good":      { color: "#2563eb", bg: "rgba(37,99,235,0.10)",   border: "rgba(37,99,235,0.25)"  },
  "At Risk":   { color: "#d97706", bg: "rgba(245,158,11,0.10)",  border: "rgba(245,158,11,0.25)" },
  "Critical":  { color: "#dc2626", bg: "rgba(220,38,38,0.10)",   border: "rgba(220,38,38,0.25)"  },
};

export default function Dashboard() {
  const { t } = useTranslation();
  // The API returns on_hold_projects; cast through unknown while schema
  // types propagate through codegen
  const { data: rawData, isLoading, isError } = useGetDashboardSummary();
  const data = rawData as typeof rawData & { on_hold_projects?: number };
  const { data: healthData } = useListProjectHealthScores();
  const { data: execData, isLoading: execLoading } = useExecutive();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-1">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 w-full rounded-xl" />
          <Skeleton className="h-80 w-full rounded-xl" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="panel panel-body flex items-center justify-center h-48">
        <div className="text-center text-muted-foreground">
          <AlertOctagon className="w-8 h-8 mx-auto mb-2 text-destructive opacity-60" />
          <p className="text-sm font-medium">Unable to load dashboard data</p>
          <p className="text-xs mt-1">Check your connection and try refreshing.</p>
        </div>
      </div>
    );
  }

  const tp  = data?.total_projects || 0;
  const ap  = data?.active_projects || 0;
  const dp  = data?.delayed_projects || 0;
  const ohp = data?.on_hold_projects || 0;
  const cp  = data?.completed_projects || 0;

  const lpo = data?.late_purchase_orders || 0;
  const tpo = data?.total_purchase_orders || 0;
  const hse = data?.high_severity_events || 0;
  const tse = data?.total_safety_events || 0;
  const onc = data?.open_ncrs || 0;
  const tnc = data?.total_ncrs || 0;
  const opr = data?.open_purchase_requests || 0;
  const tpr = data?.total_purchase_requests || 0;

  // Portfolio health distribution
  const healthCounts: Record<string, number> = { Excellent: 0, Good: 0, "At Risk": 0, Critical: 0 };
  let avgScore = 0;
  if (healthData?.length) {
    healthData.forEach((h) => { if (h.level in healthCounts) healthCounts[h.level]++; });
    avgScore = Math.round(healthData.reduce((sum, h) => sum + h.score, 0) / healthData.length);
  }
  const healthTotal = healthData?.length ?? 0;

  const activePct    = tp > 0 ? Math.round((ap / tp) * 100) : 0;
  const delayedPct   = tp > 0 ? Math.round((dp / tp) * 100) : 0;
  const onHoldPct    = tp > 0 ? Math.round((ohp / tp) * 100) : 0;
  const completedPct = tp > 0 ? Math.round((cp / tp) * 100) : 0;
  const latePoPct    = tpo > 0 ? Math.round((lpo / tpo) * 100) : 0;
  const openNcrPct   = tnc > 0 ? Math.round((onc / tnc) * 100) : 0;
  const highSevPct   = tse > 0 ? Math.round((hse / tse) * 100) : 0;
  const openPrPct    = tpr > 0 ? Math.round((opr / tpr) * 100) : 0;

  const projectStatusData = [
    { name: "Active",    value: ap,  color: "hsl(var(--chart-2))" },
    { name: "Delayed",   value: dp,  color: "hsl(var(--chart-5))" },
    { name: "On Hold",   value: ohp, color: "hsl(var(--chart-4))" },
    { name: "Completed", value: cp,  color: "hsl(var(--chart-3))" },
  ].filter((s) => s.value > 0);

  const riskData = [
    { name: "Late POs",       value: lpo },
    { name: "Open NCRs",      value: onc },
    { name: "High Sev. Events",value: hse },
    { name: "Open PRs",       value: opr },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {t("Executive Dashboard")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Amad Construction Intelligence — real-time operations overview
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge badge-gold">
            {new Date().toLocaleDateString("en-SA", { year: "numeric", month: "long", day: "numeric" })}
          </span>
        </div>
      </div>

      {/* ── Executive Report action card ───────────────────────── */}
      <div className="panel overflow-hidden"
        style={{ borderLeft: "3px solid hsl(var(--sidebar-primary))" }}>
        <div className="panel-body flex items-center justify-between gap-4 py-3 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-sidebar-primary/10 flex items-center justify-center shrink-0">
              <FileText className="w-4 h-4 text-sidebar-primary" />
            </div>
            <div>
              <p className="text-sm font-bold text-foreground">Executive Weekly Report</p>
              <p className="text-[11px] text-muted-foreground">
                Portfolio summary · Risks · Priorities · Recommended actions
              </p>
            </div>
          </div>
          <Link
            href="/reports"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sidebar-primary text-sidebar-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity shrink-0"
          >
            <FileText className="w-3.5 h-3.5" />
            View Report
          </Link>
        </div>
      </div>

      {/* ── Executive Intelligence ─────────────────────────────── */}
      <div className="space-y-4">
        {/* Section label */}
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            {t("Executive Intelligence")}
          </p>
          <div className="flex-1 h-px bg-border/50" />
          <span className="text-[10px] text-muted-foreground">Portfolio-wide · Auto-generated</span>
        </div>

        {/* Row A: Portfolio Status + Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <ExecPortfolioCard data={execData} isLoading={execLoading} />
          <div className="lg:col-span-2">
            <ExecSummaryCard data={execData} isLoading={execLoading} />
          </div>
        </div>

        {/* Row B: Top Priorities + Biggest Risks */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ExecTopPrioritiesCard data={execData} isLoading={execLoading} />
          <ExecBiggestRisksCard  data={execData} isLoading={execLoading} />
        </div>

        {/* Row C: Best Projects + Attention Required */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ExecBestProjectsCard data={execData} isLoading={execLoading} />
          <ExecAttentionCard    data={execData} isLoading={execLoading} />
        </div>
      </div>

      {/* ── Row 1 — Project Health (5 KPIs) ──────────────────── */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          {t("Project Health")}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <KpiCard
            label={t("Total Projects")}
            value={tp}
            icon={Briefcase}
            accent="bg-primary"
            sub="All tracked"
          />
          <KpiCard
            label={t("Active")}
            value={ap}
            icon={TrendingUp}
            accent="bg-emerald-500"
            sub={`${activePct}% of portfolio`}
          />
          <KpiCard
            label={t("Delayed")}
            value={dp}
            icon={AlertTriangle}
            accent="bg-red-500"
            sub={`${delayedPct}% delay rate`}
            badge={dp > 0 ? "badge-danger" : undefined}
          />
          <KpiCard
            label={t("On Hold")}
            value={ohp}
            icon={PauseCircle}
            accent="bg-amber-500"
            sub={`${onHoldPct}% paused`}
          />
          <KpiCard
            label={t("Completed")}
            value={cp}
            icon={CheckCircle}
            accent="bg-blue-500"
            sub={`${completedPct}% done`}
          />
        </div>
      </div>

      {/* ── Row 2 — Operational Risk (4 critical indicators) ─── */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          {t("Operational Risk Indicators")}
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label={t("Late Purchase Orders")}
            value={lpo}
            icon={ShoppingCart}
            accent="bg-rose-600"
            sub={`${latePoPct}% of all POs`}
            badge={lpo > 0 ? "badge-danger" : undefined}
          />
          <KpiCard
            label={t("Open NCRs")}
            value={onc}
            icon={ClipboardCheck}
            accent="bg-orange-500"
            sub={`${openNcrPct}% unresolved`}
            badge={onc > 0 ? "badge-warning" : undefined}
          />
          <KpiCard
            label={t("High Severity Events")}
            value={hse}
            icon={ShieldAlert}
            accent="bg-violet-500"
            sub={`${highSevPct}% of safety events`}
            badge={hse > 0 ? "badge-warning" : undefined}
          />
          <KpiCard
            label={t("Open Purchase Requests")}
            value={opr}
            icon={FileText}
            accent="bg-cyan-500"
            sub={`${openPrPct}% pending approval`}
          />
        </div>
      </div>

      {/* ── Row 3 — Activity pulse ────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          {t("Activity Volume")}
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: "Suppliers",       value: data?.total_suppliers || 0 },
            { label: "Purchase Orders", value: tpo },
            { label: "Site Reports",    value: data?.total_site_reports || 0 },
            { label: "Meetings",        value: data?.total_meetings || 0 },
          ].map((item) => (
            <div key={item.label} className="panel panel-body flex items-center justify-between py-3">
              <span className="text-xs text-muted-foreground">{t(item.label)}</span>
              <span className="text-lg font-bold text-foreground">{item.value.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Row 4 — Portfolio Health ─────────────────────────────── */}
      {healthTotal > 0 && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
            <HeartPulse className="w-3.5 h-3.5" />
            {t("Portfolio Health")}
          </p>
          <div className="panel">
            <div className="panel-body">
              <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <div>
                  <p className="text-xs text-muted-foreground">Portfolio Average</p>
                  <p className="text-3xl font-bold text-foreground">{avgScore}<span className="text-base font-normal text-muted-foreground">/100</span></p>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {(["Excellent", "Good", "At Risk", "Critical"] as const).map((level) => {
                    const cfg = HEALTH_LEVEL_CONFIG[level];
                    const count = healthCounts[level] ?? 0;
                    const pct = healthTotal > 0 ? Math.round((count / healthTotal) * 100) : 0;
                    return (
                      <div key={level} className="flex flex-col items-center px-4 py-2 rounded-lg min-w-[68px]"
                           style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}>
                        <span className="text-xl font-bold" style={{ color: cfg.color }}>{count}</span>
                        <span className="text-xs font-semibold" style={{ color: cfg.color }}>{level}</span>
                        <span className="text-xs text-muted-foreground">{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              {/* Distribution bar */}
              <div className="h-2.5 rounded-full overflow-hidden flex gap-px">
                {(["Excellent", "Good", "At Risk", "Critical"] as const)
                  .filter((l) => (healthCounts[l] ?? 0) > 0)
                  .map((level) => {
                    const cfg = HEALTH_LEVEL_CONFIG[level];
                    const pct = (healthCounts[level] / healthTotal) * 100;
                    return (
                      <div key={level} className="h-full rounded-sm transition-all duration-500"
                           style={{ width: `${pct}%`, backgroundColor: cfg.color }} />
                    );
                  })}
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs text-muted-foreground">Critical</span>
                <span className="text-xs text-muted-foreground">Excellent</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Row 5 — Active Alerts preview ────────────────────── */}
      <AlertsPreviewWidget />

      {/* ── Row 6 — Charts ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Donut chart — all 4 project statuses */}
        <div className="panel lg:col-span-2">
          <div className="panel-header">
            <span className="panel-title">{t("Project Status Distribution")}</span>
          </div>
          <div className="panel-body h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={projectStatusData}
                  cx="50%"
                  cy="45%"
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={3}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {projectStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: "12px", paddingTop: "12px" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar chart — operational risk */}
        <div className="panel lg:col-span-3">
          <div className="panel-header">
            <span className="panel-title">{t("Operational Risk Overview")}</span>
          </div>
          <div className="panel-body h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={riskData}
                margin={{ top: 10, right: 10, left: -10, bottom: 5 }}
                barSize={36}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="hsl(var(--border))"
                />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={CHART_TOOLTIP_STYLE}
                  cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }}
                />
                <Bar
                  dataKey="value"
                  fill="hsl(var(--chart-5))"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
