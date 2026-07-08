import { useTranslation } from "react-i18next";
import {
  FileText, Printer, AlertOctagon, ShieldAlert, ShoppingCart,
  ClipboardCheck, CalendarDays, HeartPulse, TrendingDown,
  Trophy, Target, Zap, BarChart2, CheckCircle, Clock,
  Database, ChevronRight,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useExecutiveWeeklyReport } from "../lib/useReports";
import type {
  ReportAlert, ProcurementBlocker, SafetyHighlight,
  QualityHighlight, RecommendedAction, SourceReference,
} from "../lib/useReports";
import type { ProjectBrief, RiskCategory } from "../lib/useExecutive";

// ── Severity config ────────────────────────────────────────────────────────────

const SEV_CFG: Record<string, { color: string; bg: string; label: string }> = {
  critical: { color: "#dc2626", bg: "rgba(220,38,38,0.10)",   label: "Critical" },
  high:     { color: "#d97706", bg: "rgba(245,158,11,0.10)",  label: "High"     },
  medium:   { color: "#2563eb", bg: "rgba(37,99,235,0.10)",   label: "Medium"   },
  low:      { color: "#16a34a", bg: "rgba(22,163,74,0.10)",   label: "Low"      },
};

const LEVEL_CFG: Record<string, { color: string; bg: string; border: string }> = {
  Excellent: { color: "#16a34a", bg: "rgba(22,163,74,0.08)",   border: "rgba(22,163,74,0.22)"   },
  Good:      { color: "#2563eb", bg: "rgba(37,99,235,0.08)",   border: "rgba(37,99,235,0.22)"   },
  "At Risk": { color: "#d97706", bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.22)"  },
  Critical:  { color: "#dc2626", bg: "rgba(220,38,38,0.08)",   border: "rgba(220,38,38,0.22)"   },
  Unknown:   { color: "#6b7280", bg: "rgba(107,114,128,0.08)", border: "rgba(107,114,128,0.22)" },
};

const CAT_ICON: Record<string, React.ElementType> = {
  health:      HeartPulse,
  safety:      ShieldAlert,
  procurement: ShoppingCart,
  quality:     ClipboardCheck,
  schedule:    CalendarDays,
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function SevBadge({ severity }: { severity: string }) {
  const cfg = SEV_CFG[severity] ?? SEV_CFG["medium"];
  return (
    <span
      className="text-[10px] font-bold px-1.5 py-0.5 rounded capitalize shrink-0"
      style={{ backgroundColor: cfg.bg, color: cfg.color }}
    >
      {cfg.label}
    </span>
  );
}

function SectionHeader({ icon: Icon, title, subtitle, color = "text-muted-foreground" }: {
  icon: React.ElementType; title: string; subtitle?: string; color?: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon className={`w-4 h-4 shrink-0 ${color}`} />
      <span className="text-sm font-bold text-foreground">{title}</span>
      {subtitle && <span className="text-[10px] text-muted-foreground">{subtitle}</span>}
      <div className="flex-1 h-px bg-border/40 ms-1" />
    </div>
  );
}

// ── KPI Cards ──────────────────────────────────────────────────────────────────

function HealthKPIBar({ label, value, total, color }: {
  label: string; value: number; total: number; color: string;
}) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-bold" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

// ── Section panels ─────────────────────────────────────────────────────────────

function AlertsSection({ alerts }: { alerts: ReportAlert[] }) {
  if (!alerts.length) return null;
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={AlertOctagon} title="Critical Alerts" subtitle={`${alerts.length} items`} color="text-destructive" />
        <div className="space-y-2">
          {alerts.map((a, i) => {
            const cfg = SEV_CFG[a.severity] ?? SEV_CFG["medium"];
            const CatIcon = CAT_ICON[a.category] ?? AlertOctagon;
            return (
              <div key={i} className="flex items-start gap-3 py-2.5 border-b border-border/30 last:border-0">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{ backgroundColor: cfg.bg }}>
                  <CatIcon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-0.5">
                    <span className="text-xs font-semibold text-foreground">{a.title}</span>
                    <SevBadge severity={a.severity} />
                    {a.project_code && (
                      <span className="text-[10px] text-muted-foreground">{a.project_code}</span>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground">{a.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function PrioritiesSection({ priorities }: { priorities: ProjectBrief[] }) {
  if (!priorities.length) return null;
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={Target} title="Top Priorities" subtitle="Worst-performing active projects" color="text-amber-500" />
        <div className="space-y-0 divide-y divide-border/40">
          {priorities.map((p, i) => {
            const cfg = LEVEL_CFG[p.level] ?? LEVEL_CFG["Unknown"];
            return (
              <div key={p.project_id} className="flex items-start gap-3 py-2.5">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
                  style={{ backgroundColor: cfg.bg, color: cfg.color }}>
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold">{p.project_code}</span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: cfg.bg, color: cfg.color }}>
                      {p.level} · {p.score}/100
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{p.primary_reason}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function RisksSection({ risks }: { risks: RiskCategory[] }) {
  if (!risks.length) return null;
  const maxCount = Math.max(...risks.map(r => r.count), 1);
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={BarChart2} title="Biggest Risks" subtitle="Ranked by severity" color="text-rose-500" />
        <div className="space-y-3.5">
          {risks.map(risk => {
            const CatIcon = CAT_ICON[risk.category] ?? ShieldAlert;
            const sevCfg = SEV_CFG[risk.severity] ?? SEV_CFG["medium"];
            const barPct = (risk.count / maxCount) * 100;
            return (
              <div key={risk.category}>
                <div className="flex items-center gap-2 mb-1">
                  <CatIcon className="w-3.5 h-3.5 shrink-0" style={{ color: sevCfg.color }} />
                  <span className="text-xs font-medium flex-1">{risk.label}</span>
                  <SevBadge severity={risk.severity} />
                  <span className="text-xs font-bold w-8 text-right">{risk.count}</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${barPct}%`, backgroundColor: sevCfg.color }} />
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">{risk.detail}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ProcurementSection({ blockers }: { blockers: ProcurementBlocker[] }) {
  if (!blockers.length) return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={ShoppingCart} title="Procurement" />
        <div className="flex items-center gap-2 py-3">
          <CheckCircle className="w-4 h-4 text-emerald-500" />
          <span className="text-xs text-muted-foreground">No procurement blockers detected</span>
        </div>
      </div>
    </div>
  );
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={ShoppingCart} title="Procurement Blockers" subtitle={`${blockers.length} issues`} color="text-blue-500" />
        <div className="space-y-3">
          {blockers.map((b, i) => {
            const cfg = SEV_CFG[b.severity] ?? SEV_CFG["medium"];
            return (
              <div key={i} className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: cfg.color }} />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-semibold">{b.label}</span>
                    <SevBadge severity={b.severity} />
                    <span className="text-xs font-bold ms-auto">{b.count}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">{b.detail}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SafetySection({ highlights }: { highlights: SafetyHighlight[] }) {
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={ShieldAlert} title="Safety Highlights" color="text-orange-500" />
        {!highlights.length ? (
          <div className="flex items-center gap-2 py-3">
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            <span className="text-xs text-muted-foreground">No safety concerns</span>
          </div>
        ) : (
          <div className="space-y-3">
            {highlights.map((h, i) => {
              const cfg = SEV_CFG[h.severity] ?? SEV_CFG["low"];
              return (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: cfg.color }} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-semibold">{h.label}</span>
                      <SevBadge severity={h.severity} />
                      <span className="text-xs font-bold ms-auto">{h.count}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{h.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function QualitySection({ highlights }: { highlights: QualityHighlight[] }) {
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={ClipboardCheck} title="Quality / NCR Highlights" color="text-violet-500" />
        {!highlights.length ? (
          <div className="flex items-center gap-2 py-3">
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            <span className="text-xs text-muted-foreground">No quality issues</span>
          </div>
        ) : (
          <div className="space-y-3">
            {highlights.map((h, i) => {
              const cfg = SEV_CFG[h.severity] ?? SEV_CFG["low"];
              return (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: cfg.color }} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-semibold">{h.label}</span>
                      <SevBadge severity={h.severity} />
                      <span className="text-xs font-bold ms-auto">{h.count}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{h.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionsSection({ actions }: { actions: RecommendedAction[] }) {
  if (!actions.length) return null;
  const areaCfg: Record<string, { color: string; bg: string }> = {
    "Project Health":     { color: "#dc2626", bg: "rgba(220,38,38,0.08)"   },
    "Procurement":        { color: "#2563eb", bg: "rgba(37,99,235,0.08)"   },
    "Safety":             { color: "#d97706", bg: "rgba(245,158,11,0.08)"  },
    "Quality":            { color: "#7c3aed", bg: "rgba(124,58,237,0.08)"  },
    "Portfolio Recovery": { color: "#0891b2", bg: "rgba(8,145,178,0.08)"   },
    "Governance":         { color: "#6b7280", bg: "rgba(107,114,128,0.08)" },
  };
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={Zap} title="Recommended Executive Actions" subtitle={`${actions.length} actions`} color="text-amber-500" />
        <div className="space-y-3">
          {actions.map(a => {
            const cfg = areaCfg[a.area] ?? { color: "#6b7280", bg: "rgba(107,114,128,0.08)" };
            return (
              <div key={a.priority} className="flex items-start gap-3 p-3 rounded-lg"
                style={{ backgroundColor: cfg.bg }}>
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-black shrink-0"
                  style={{ backgroundColor: cfg.color, color: "#fff" }}>
                  {a.priority}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wide"
                      style={{ color: cfg.color }}>
                      {a.area}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-foreground mb-1">{a.action}</p>
                  <p className="text-[11px] text-muted-foreground">{a.rationale}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SourcesSection({ sources }: { sources: SourceReference[] }) {
  if (!sources.length) return null;
  return (
    <div className="panel">
      <div className="panel-body">
        <SectionHeader icon={Database} title="Data Sources" subtitle="Report citations" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {sources.map((s, i) => (
            <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-muted/40">
              <ChevronRight className="w-3 h-3 text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <p className="text-[11px] font-semibold text-foreground">{s.source}</p>
                <p className="text-[10px] text-muted-foreground">{s.record_count.toLocaleString()} records</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function Reports() {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch, isFetching } = useExecutiveWeeklyReport();

  function handlePrint() {
    window.print();
  }

  if (isError) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">{t("Reports")}</h1>
        </div>
        <div className="panel">
          <div className="panel-body flex flex-col items-center gap-3 py-12 text-center">
            <AlertOctagon className="w-8 h-8 text-destructive opacity-70" />
            <p className="text-sm font-semibold text-foreground">Failed to load report</p>
            <p className="text-xs text-muted-foreground">Could not retrieve data from the server</p>
            <button
              onClick={() => refetch()}
              className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const statusCfg = LEVEL_CFG[data?.portfolio_status ?? "Unknown"] ?? LEVEL_CFG["Unknown"];

  return (
    <div className="space-y-6 print:space-y-4">
      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 flex-wrap print:hidden">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileText className="w-5 h-5 text-primary shrink-0" />
            <h1 className="text-xl font-bold text-foreground">{t("Reports")}</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Executive Weekly Report · Deterministic · Live Data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:bg-muted transition-colors disabled:opacity-50"
          >
            <Clock className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
            {isFetching ? "Refreshing…" : "Refresh"}
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
          >
            <Printer className="w-3.5 h-3.5" />
            Print / Export PDF
          </button>
        </div>
      </div>

      {/* ── Print header (visible only on print) ──────────────────── */}
      <div className="hidden print:block">
        <h1 className="text-2xl font-black text-foreground">Amad Construction Intelligence</h1>
        <h2 className="text-lg font-bold text-foreground mt-1">Executive Weekly Report</h2>
        {data && (
          <p className="text-sm text-muted-foreground mt-1">
            {data.report_period.label} · Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* ── Report period + portfolio status ─────────────────────── */}
      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
      ) : data && (
        <>
          {/* Report period banner */}
          <div className="panel overflow-hidden" style={{ borderLeft: `3px solid ${statusCfg.color}` }}>
            <div className="panel-body flex items-center justify-between gap-4 flex-wrap py-4">
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
                  Report Period
                </p>
                <p className="text-base font-bold text-foreground">{data.report_period.label}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Generated {new Date(data.generated_at).toLocaleString()} UTC
                </p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <div className="text-4xl font-black leading-none" style={{ color: statusCfg.color }}>
                    {data.portfolio_score}
                  </div>
                  <div className="text-[10px] text-muted-foreground">/100 avg</div>
                </div>
                <div
                  className="px-4 py-2 rounded-full text-sm font-bold"
                  style={{
                    backgroundColor: statusCfg.bg,
                    border: `1px solid ${statusCfg.border}`,
                    color: statusCfg.color,
                  }}
                >
                  {data.portfolio_status}
                </div>
              </div>
            </div>
          </div>

          {/* Executive summary */}
          <div className="panel">
            <div className="panel-body">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">
                Executive Summary
              </p>
              <p className="text-sm text-foreground leading-relaxed">{data.portfolio_summary}</p>
            </div>
          </div>

          {/* ── KPI row ──────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: "Critical Projects", value: data.health_distribution.critical, color: "#dc2626" },
              { label: "At Risk Projects",  value: data.health_distribution.at_risk,  color: "#d97706" },
              { label: "Good Projects",     value: data.health_distribution.good,     color: "#2563eb" },
              { label: "Excellent Projects",value: data.health_distribution.excellent,color: "#16a34a" },
            ].map(({ label, value, color }) => (
              <div key={label} className="panel">
                <div className="panel-body text-center py-4">
                  <div className="text-3xl font-black leading-none" style={{ color }}>{value}</div>
                  <div className="text-[10px] text-muted-foreground mt-1">{label}</div>
                </div>
              </div>
            ))}
          </div>

          {/* ── Health distribution bars ───────────────────────── */}
          <div className="panel">
            <div className="panel-body">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
                Health Distribution — {data.health_distribution.total} Projects
              </p>
              <div className="space-y-2">
                <HealthKPIBar label="Critical"  value={data.health_distribution.critical}  total={data.health_distribution.total} color="#dc2626" />
                <HealthKPIBar label="At Risk"   value={data.health_distribution.at_risk}   total={data.health_distribution.total} color="#d97706" />
                <HealthKPIBar label="Good"      value={data.health_distribution.good}      total={data.health_distribution.total} color="#2563eb" />
                <HealthKPIBar label="Excellent" value={data.health_distribution.excellent} total={data.health_distribution.total} color="#16a34a" />
              </div>
            </div>
          </div>

          {/* ── Top Priorities + Biggest Risks ──────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <PrioritiesSection priorities={data.top_priorities} />
            <RisksSection risks={data.biggest_risks} />
          </div>

          {/* ── Critical Alerts ──────────────────────────────────── */}
          <AlertsSection alerts={data.critical_alerts} />

          {/* ── Procurement + Safety ────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ProcurementSection blockers={data.procurement_blockers} />
            <SafetySection highlights={data.safety_highlights} />
          </div>

          {/* ── Quality ──────────────────────────────────────────── */}
          <QualitySection highlights={data.quality_highlights} />

          {/* ── Recommended Actions ──────────────────────────────── */}
          <ActionsSection actions={data.recommended_actions} />

          {/* ── Sources ──────────────────────────────────────────── */}
          <SourcesSection sources={data.sources} />
        </>
      )}
    </div>
  );
}
