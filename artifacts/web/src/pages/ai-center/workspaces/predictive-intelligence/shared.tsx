import {
  Clock, Banknote, Wallet, Scale, ShieldAlert, CalendarClock,
  TrendingUp, TrendingDown, Minus, FlaskConical, type LucideIcon,
} from "lucide-react";
import type {
  ConfidenceLevel, ForecastTrend, PredictionCategory, RiskBand,
} from "@/lib/mockPredictiveIntelligence";
import { CATEGORY_LABEL } from "@/lib/mockPredictiveIntelligence";

// Shared display constants for the Predictive Intelligence workspace — one
// place mapping the 6 forecast categories / confidence levels / risk bands
// to icon, label, and color so cards, charts, the heat map, and the table
// all agree on how each prediction looks.

export const CATEGORY_META: Record<PredictionCategory, { label: string; icon: LucideIcon; color: string }> = {
  delay:           { label: CATEGORY_LABEL.delay,           icon: Clock,         color: "#f59e0b" },
  budget_overrun:  { label: CATEGORY_LABEL.budget_overrun,  icon: Banknote,      color: "#dc2626" },
  cash_flow:       { label: CATEGORY_LABEL.cash_flow,       icon: Wallet,        color: "#0ea5e9" },
  claim:           { label: CATEGORY_LABEL.claim,           icon: Scale,         color: "#a855f7" },
  safety:          { label: CATEGORY_LABEL.safety,          icon: ShieldAlert,   color: "#e11d48" },
  schedule:        { label: CATEGORY_LABEL.schedule,        icon: CalendarClock, color: "#6366f1" },
};

export const CATEGORY_ORDER: PredictionCategory[] = [
  "delay", "budget_overrun", "cash_flow", "claim", "safety", "schedule",
];

export const BAND_COLOR: Record<RiskBand, string> = {
  Low: "#16a34a",
  Moderate: "#2563eb",
  Elevated: "#d97706",
  Critical: "#dc2626",
};

export const BAND_BADGE: Record<RiskBand, string> = {
  Low: "badge-success",
  Moderate: "badge-info",
  Elevated: "badge-warning",
  Critical: "badge-danger",
};

export const CONFIDENCE_META: Record<ConfidenceLevel, { label: string; dot: string }> = {
  high:   { label: "High confidence", dot: "bg-emerald-500" },
  medium: { label: "Medium confidence", dot: "bg-amber-500" },
  low:    { label: "Low confidence", dot: "bg-slate-400" },
};

export function ConfidenceTag({ level }: { level: ConfidenceLevel }) {
  const meta = CONFIDENCE_META[level];
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground"
      title="Illustrative confidence level for this demo forecast"
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}

export function TrendIndicator({ trend, deltaPts }: { trend: ForecastTrend; deltaPts: number }) {
  const Icon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const tone = trend === "up" ? "text-red-600 dark:text-red-400" : trend === "down" ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground";
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${tone}`}>
      <Icon className="w-3.5 h-3.5" />
      {deltaPts > 0 ? "+" : ""}{deltaPts} pts
    </span>
  );
}

/** Continuous green -> amber -> red interpolation for the heat map and any
 * other "how hot is this number" surface, 0 (safe) to 100 (severe). */
export function heatColor(value: number): string {
  const clamped = Math.max(0, Math.min(100, value));
  const hue = clamped <= 50 ? 142 - (clamped / 50) * (142 - 45) : 45 - ((clamped - 50) / 50) * 45;
  return `hsl(${hue.toFixed(0)}, 72%, 42%)`;
}

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "hsl(var(--foreground))",
};

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatRelativeDays(iso: string, referenceIso: string): string {
  const diffDays = Math.round((new Date(iso).getTime() - new Date(referenceIso).getTime()) / 86_400_000);
  if (diffDays === 0) return "Today";
  if (diffDays > 0) return `In ${diffDays} day${diffDays === 1 ? "" : "s"}`;
  return `${Math.abs(diffDays)} day${Math.abs(diffDays) === 1 ? "" : "s"} ago`;
}

// Deliberately loud and consistent everywhere it's used — this workspace
// never presents synthetic forecasts as a live model output (see build
// constraint: no fake live AI, no real prediction).
export function DemoDataBadge({ label = "Demo Data — Illustrative Forecast", className = "" }: { label?: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border border-dashed border-violet-400/60 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400 ${className}`}
      title="Illustrative demo forecast — not a live AI prediction or real model output"
    >
      <FlaskConical className="w-3 h-3" />
      {label}
    </span>
  );
}
