import { FlaskConical } from "lucide-react";
import type { ContractStatus, RiskBand } from "@/lib/mockSupplierRisk";

// Shared display constants for the Supplier Risk Intelligence workspace —
// one place mapping risk bands / contract statuses to color and badge
// class so the directory, cards, drawer, and charts all agree.

export const BAND_COLOR: Record<RiskBand, string> = {
  Low: "#16a34a",
  Medium: "#2563eb",
  High: "#d97706",
  Critical: "#dc2626",
};

export const BAND_BADGE: Record<RiskBand, string> = {
  Low: "badge-success",
  Medium: "badge-info",
  High: "badge-warning",
  Critical: "badge-danger",
};

export const CONTRACT_STATUS_BADGE: Record<ContractStatus, string> = {
  Active: "badge-success",
  "Expiring Soon": "badge-warning",
  "Under Negotiation": "badge-info",
  Expired: "badge-danger",
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

export function formatSar(amount: number): string {
  if (amount >= 1_000_000) return `SAR ${(amount / 1_000_000).toFixed(2)}M`;
  if (amount >= 1_000) return `SAR ${(amount / 1_000).toFixed(0)}K`;
  return `SAR ${amount.toLocaleString()}`;
}

export function formatRelativeDays(iso: string, referenceIso: string): string {
  const diffDays = Math.round((new Date(iso).getTime() - new Date(referenceIso).getTime()) / 86_400_000);
  if (diffDays === 0) return "Today";
  if (diffDays > 0) return `In ${diffDays} day${diffDays === 1 ? "" : "s"}`;
  return `${Math.abs(diffDays)} day${Math.abs(diffDays) === 1 ? "" : "s"} ago`;
}

// Deliberately loud and consistent everywhere it's used — this workspace
// never presents synthetic supplier scoring or AI insight as a live model
// output (build constraint: no fake live intelligence, no real prediction).
export function DemoDataBadge({ label = "Demo Data — Illustrative Analysis", className = "" }: { label?: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border border-dashed border-violet-400/60 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400 ${className}`}
      title="Illustrative demo analysis — not live AI or a real supplier score"
    >
      <FlaskConical className="w-3 h-3" />
      {label}
    </span>
  );
}
