import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "wouter";
import {
  Bell, ShieldAlert, ShoppingCart, ClipboardCheck,
  CalendarDays, HeartPulse, AlertOctagon, CheckCircle,
  ChevronDown, ChevronUp, ExternalLink,
} from "lucide-react";
import { useAlerts, useAlertsSummary, type Alert, type AlertSeverity, type AlertCategory } from "../lib/useAlerts";
import { Skeleton } from "@/components/ui/skeleton";

// ── Constants ──────────────────────────────────────────────────────────────────

const SEV_BADGE: Record<AlertSeverity, string> = {
  critical: "badge-danger",
  high:     "badge-warning",
  medium:   "badge-neutral",
  low:      "badge-success",
};

const SEV_LABEL: Record<AlertSeverity, string> = {
  critical: "Critical",
  high:     "High",
  medium:   "Medium",
  low:      "Low",
};

const CAT_ICON: Record<AlertCategory, React.ElementType> = {
  health:      HeartPulse,
  safety:      ShieldAlert,
  procurement: ShoppingCart,
  quality:     ClipboardCheck,
  schedule:    CalendarDays,
};

const CAT_LABEL: Record<AlertCategory, string> = {
  health:      "Health",
  safety:      "Safety",
  procurement: "Procurement",
  quality:     "Quality",
  schedule:    "Schedule",
};

const CAT_COLOR: Record<AlertCategory, string> = {
  health:      "text-rose-500",
  safety:      "text-orange-500",
  procurement: "text-blue-500",
  quality:     "text-violet-500",
  schedule:    "text-amber-500",
};

const CAT_BG: Record<AlertCategory, string> = {
  health:      "bg-rose-500/10",
  safety:      "bg-orange-500/10",
  procurement: "bg-blue-500/10",
  quality:     "bg-violet-500/10",
  schedule:    "bg-amber-500/10",
};

// ── Summary Card ───────────────────────────────────────────────────────────────

interface SummaryCardProps {
  label: string;
  value: number;
  accent: string;
  icon: React.ElementType;
  active?: boolean;
  onClick?: () => void;
}

function SummaryCard({ label, value, accent, icon: Icon, active, onClick }: SummaryCardProps) {
  return (
    <button
      onClick={onClick}
      className={`panel relative overflow-hidden text-start w-full transition-all duration-150 ${active ? "ring-2 ring-primary" : "hover:ring-1 hover:ring-border"}`}
    >
      <div className={`absolute inset-0 opacity-[0.04] ${accent}`} />
      <div className="panel-body flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">{label}</p>
          <p className="text-3xl font-bold text-foreground leading-none">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${accent}/15`}>
          <Icon className="w-5 h-5 text-foreground opacity-70" />
        </div>
      </div>
      <div className={`h-1 w-full ${accent} opacity-60`} />
    </button>
  );
}

// ── Alert Card ─────────────────────────────────────────────────────────────────

function AlertCard({ alert }: { alert: Alert }) {
  const [expanded, setExpanded] = useState(false);
  const CatIcon = CAT_ICON[alert.category as AlertCategory] ?? Bell;
  const catColor = CAT_COLOR[alert.category as AlertCategory] ?? "text-muted-foreground";
  const catBg    = CAT_BG[alert.category as AlertCategory]   ?? "bg-muted";
  const sevBadge = SEV_BADGE[alert.severity as AlertSeverity] ?? "badge-neutral";

  return (
    <div className={`panel overflow-hidden transition-shadow hover:shadow-md ${
      alert.severity === "critical" ? "border-destructive/30" : ""
    }`}>
      {/* Top accent strip */}
      <div className={`h-0.5 w-full ${
        alert.severity === "critical" ? "bg-destructive" :
        alert.severity === "high"     ? "bg-amber-500" :
        alert.severity === "medium"   ? "bg-muted-foreground/40" :
                                        "bg-emerald-500/40"
      }`} />

      <div className="panel-body space-y-3">
        {/* Header row */}
        <div className="flex items-start gap-3">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${catBg}`}>
            <CatIcon className={`w-4 h-4 ${catColor}`} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className={`badge ${sevBadge} text-[10px] uppercase font-bold`}>
                {SEV_LABEL[alert.severity as AlertSeverity] ?? alert.severity}
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                {CAT_LABEL[alert.category as AlertCategory] ?? alert.category}
              </span>
              {alert.project_code && (
                <>
                  <span className="text-muted-foreground/40">·</span>
                  <Link
                    href={`/projects/${alert.project_id}`}
                    className="text-[10px] font-mono text-primary hover:underline flex items-center gap-1"
                  >
                    {alert.project_code}
                    <ExternalLink className="w-2.5 h-2.5" />
                  </Link>
                </>
              )}
            </div>
            <h3 className="text-sm font-semibold text-foreground leading-snug">{alert.title}</h3>
          </div>
        </div>

        {/* Description */}
        <p className={`text-xs text-muted-foreground leading-relaxed ${expanded ? "" : "line-clamp-2"}`}>
          {alert.description}
        </p>

        {/* Recommended action (collapsible) */}
        <div>
          <button
            onClick={() => setExpanded((e) => !e)}
            className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? "Hide action" : "Recommended action"}
          </button>
          {expanded && (
            <div className="mt-2 p-3 rounded-lg bg-primary/5 border border-primary/10">
              <p className="text-xs text-foreground leading-relaxed">{alert.recommended_action}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-1 border-t border-border/50">
          <span className="text-[10px] text-muted-foreground font-mono">{alert.source_id}</span>
          <span className="text-[10px] text-muted-foreground">
            {new Date(alert.detected_at).toLocaleString(undefined, {
              month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

const SEVERITY_FILTERS: Array<{ key: string; label: string }> = [
  { key: "",         label: "All Severities" },
  { key: "critical", label: "Critical" },
  { key: "high",     label: "High" },
  { key: "medium",   label: "Medium" },
  { key: "low",      label: "Low" },
];

const CATEGORY_FILTERS: Array<{ key: string; label: string; icon: React.ElementType }> = [
  { key: "",            label: "All",         icon: Bell },
  { key: "health",      label: "Health",      icon: HeartPulse },
  { key: "safety",      label: "Safety",      icon: ShieldAlert },
  { key: "procurement", label: "Procurement", icon: ShoppingCart },
  { key: "quality",     label: "Quality",     icon: ClipboardCheck },
  { key: "schedule",    label: "Schedule",    icon: CalendarDays },
];

export default function Alerts() {
  const { t } = useTranslation();
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");

  const { data: summary, isLoading: summaryLoading } = useAlertsSummary();
  const { data, isLoading, isError } = useAlerts({ severity, category, limit: 200 });
  const alerts = data?.alerts ?? [];
  const total  = data?.total ?? 0;

  const handleSeverityCard = (sev: string) => {
    setSeverity((prev) => (prev === sev ? "" : sev));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Bell className="w-6 h-6 text-destructive" />
            {t("Alerts")}
          </h1>
          <p className="page-subtitle">
            {summaryLoading
              ? "Loading…"
              : summary
              ? `${summary.total} active alert${summary.total !== 1 ? "s" : ""} · ${summary.critical} critical, ${summary.high} high`
              : "Smart alerts derived from live project data"}
          </p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {summaryLoading ? (
          [1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)
        ) : (
          <>
            <SummaryCard
              label="Critical"
              value={summary?.critical ?? 0}
              accent="bg-red-500"
              icon={AlertOctagon}
              active={severity === "critical"}
              onClick={() => handleSeverityCard("critical")}
            />
            <SummaryCard
              label="High"
              value={summary?.high ?? 0}
              accent="bg-amber-500"
              icon={Bell}
              active={severity === "high"}
              onClick={() => handleSeverityCard("high")}
            />
            <SummaryCard
              label="Medium"
              value={summary?.medium ?? 0}
              accent="bg-blue-500"
              icon={Bell}
              active={severity === "medium"}
              onClick={() => handleSeverityCard("medium")}
            />
            <SummaryCard
              label="Low"
              value={summary?.low ?? 0}
              accent="bg-emerald-500"
              icon={CheckCircle}
              active={severity === "low"}
              onClick={() => handleSeverityCard("low")}
            />
          </>
        )}
      </div>

      {/* Category tabs + severity pills */}
      <div className="panel panel-body space-y-4">
        {/* Category filter */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            {t("Category")}
          </p>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_FILTERS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setCategory((p) => (p === key ? "" : key))}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 border ${
                  category === key
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
                }`}
              >
                <Icon className="w-3 h-3" />
                {label}
                {key && summary?.by_category[key] ? (
                  <span className={`min-w-[16px] h-4 rounded-full text-[9px] font-bold flex items-center justify-center px-1 ${
                    category === key ? "bg-primary-foreground/20 text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}>
                    {summary.by_category[key]}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        </div>

        {/* Severity pills */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            {t("Severity")}
          </p>
          <div className="flex flex-wrap gap-2">
            {SEVERITY_FILTERS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setSeverity((p) => (p === key ? "" : key))}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 border ${
                  severity === key
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {isLoading ? "Loading…" : `${total} alert${total !== 1 ? "s" : ""}${severity || category ? " (filtered)" : ""}`}
        </p>
        {(severity || category) && (
          <button
            onClick={() => { setSeverity(""); setCategory(""); }}
            className="text-xs text-primary hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Alert list */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
        </div>
      ) : isError ? (
        <div className="panel panel-body flex items-center justify-center h-48">
          <div className="text-center text-muted-foreground">
            <AlertOctagon className="w-8 h-8 mx-auto mb-2 text-destructive opacity-60" />
            <p className="text-sm font-medium">Unable to load alerts</p>
            <p className="text-xs mt-1">Check your connection and try refreshing.</p>
          </div>
        </div>
      ) : alerts.length === 0 ? (
        <div className="panel panel-body flex items-center justify-center h-48">
          <div className="text-center text-muted-foreground">
            <CheckCircle className="w-10 h-10 mx-auto mb-3 text-emerald-500 opacity-60" />
            <p className="text-sm font-semibold text-foreground">No alerts</p>
            <p className="text-xs mt-1">
              {severity || category ? "No alerts match the current filters." : "All systems are operating normally."}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
