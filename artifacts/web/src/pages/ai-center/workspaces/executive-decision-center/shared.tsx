import {
  Brain, Gauge, Truck, Boxes, BookOpen, LineChart, FlaskConical, type LucideIcon,
} from "lucide-react";
import type { Priority, RiskBand, SourceModule } from "@/lib/mockExecutiveDecisionCenter";

// Shared display constants for the Executive Decision Center — one place
// mapping risk bands / priorities / source modules to color, badge class,
// and icon so every section agrees.

export const RISK_COLOR: Record<RiskBand, string> = {
  Low: "#16a34a", Medium: "#2563eb", High: "#d97706", Critical: "#dc2626",
};
export const RISK_BADGE: Record<RiskBand, string> = {
  Low: "badge-success", Medium: "badge-info", High: "badge-warning", Critical: "badge-danger",
};
export const PRIORITY_BADGE: Record<Priority, string> = {
  High: "badge-danger", Medium: "badge-warning", Low: "badge-neutral",
};

export const MODULE_META: Record<SourceModule, { icon: LucideIcon; color: string }> = {
  "Project Memory": { icon: Brain, color: "#8b5cf6" },
  "Predictive Intelligence": { icon: Gauge, color: "#6366f1" },
  "Supplier Risk Intelligence": { icon: Truck, color: "#0ea5e9" },
  "Material Intelligence": { icon: Boxes, color: "#f59e0b" },
  "Cross-Project Learning": { icon: BookOpen, color: "#22c55e" },
  "Executive Intelligence": { icon: LineChart, color: "#eab308" },
};

/** Continuous green -> amber -> red interpolation, 0 (safe) to 100 (severe). */
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
  return `${Math.abs(diffDays)} day${Math.abs(diffDays) === 1 ? "" : "s"} overdue`;
}

// Deliberately loud and consistent everywhere it's used — this workspace
// never presents synthetic aggregation as a live AI output (build
// constraint: no live AI; every insight must read Demo Data / Illustrative
// Executive Insight).
export function DemoDataBadge({ label = "Demo Data — Illustrative Executive Insight", className = "" }: { label?: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border border-dashed border-violet-400/60 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400 ${className}`}
      title="Illustrative demo executive insight — not a live AI output or real aggregation"
    >
      <FlaskConical className="w-3 h-3" />
      {label}
    </span>
  );
}
