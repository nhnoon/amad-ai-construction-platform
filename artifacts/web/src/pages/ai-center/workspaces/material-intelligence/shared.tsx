import { FlaskConical } from "lucide-react";
import type { PriceTrend, ProcurementStatus, RiskLevel, SupplyStatus } from "@/lib/mockMaterialIntelligence";

// Shared display constants for the Material Intelligence workspace — one
// place mapping risk levels / trends / supply statuses to color and badge
// class so the overview, directory, drawer, and charts all agree.

export const RISK_COLOR: Record<RiskLevel, string> = {
  Low: "#16a34a",
  Medium: "#2563eb",
  High: "#d97706",
  Critical: "#dc2626",
};

export const RISK_BADGE: Record<RiskLevel, string> = {
  Low: "badge-success",
  Medium: "badge-info",
  High: "badge-warning",
  Critical: "badge-danger",
};

export const SUPPLY_STATUS_BADGE: Record<SupplyStatus, string> = {
  Available: "badge-success",
  Constrained: "badge-warning",
  Shortage: "badge-danger",
};

export const PROCUREMENT_STATUS_BADGE: Record<ProcurementStatus, string> = {
  "Not Started": "badge-neutral",
  "In Progress": "badge-info",
  Locked: "badge-success",
  Completed: "badge-neutral",
};

export function trendTone(trend: PriceTrend): string {
  if (trend === "Rising") return "text-red-600 dark:text-red-400";
  if (trend === "Falling") return "text-emerald-600 dark:text-emerald-400";
  return "text-muted-foreground";
}

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

export function formatSar(amount: number): string {
  if (Math.abs(amount) >= 1_000_000) return `SAR ${(amount / 1_000_000).toFixed(2)}M`;
  if (Math.abs(amount) >= 1_000) return `SAR ${(amount / 1_000).toFixed(1)}K`;
  return `SAR ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function formatPrice(amount: number): string {
  return amount >= 1000 ? amount.toLocaleString(undefined, { maximumFractionDigits: 0 }) : amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatPct(value: number): string {
  return `${value > 0 ? "+" : ""}${value}%`;
}

// Deliberately loud and consistent everywhere it's used — this workspace
// never presents synthetic prices, forecasts, or AI insight as real market
// data (build constraint: no live AI, no external market data yet, never
// present demo values as real prices).
export function DemoDataBadge({ label = "Demo Data — Illustrative Market Analysis", className = "" }: { label?: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border border-dashed border-violet-400/60 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400 ${className}`}
      title="Illustrative demo market data — not a real price, forecast, or live AI output"
    >
      <FlaskConical className="w-3 h-3" />
      {label}
    </span>
  );
}
