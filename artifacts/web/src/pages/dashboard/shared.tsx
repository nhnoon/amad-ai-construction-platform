import type { ElementType, ReactNode } from "react";

// ── Visual system ────────────────────────────────────────────────────────
// One accent color (gold) governs all neutral chrome: icon chips, CTA,
// highlights. Semantic color (severity/status) is reserved for data
// encoding — donut segments, tone-colored icon chips — where dropping it
// would make the number/chart unreadable at a glance.
//
// GLASS/GLASS_HEADER used to be a Dashboard-only card system (rounded-3xl,
// a bespoke dark-mode backdrop-blur/inset-shadow combo) — a second,
// independently-maintained implementation of the exact same concept as the
// app-wide `.panel`/`.panel-header` classes (index.css), just with a
// different corner radius and shadow treatment. Every Dashboard card still
// reads `GLASS`/`GLASS_HEADER` (Charts, QuickActions) — redefining them here
// to build on `.panel`/`.panel-header` converges all of it onto the one
// shared card language in a single place, with no per-usage edits.

export const ACCENT = "#eab308";

export const GLASS = "panel relative overflow-hidden";

export const GLASS_HEADER = "panel-header relative justify-start! gap-3 px-4 py-3";

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "hsl(var(--foreground))",
};

export const EXEC_LEVEL_CFG: Record<string, { color: string }> = {
  Excellent: { color: "#16a34a" },
  Good: { color: "#2563eb" },
  "At Risk": { color: "#d97706" },
  Critical: { color: "#dc2626" },
};

export const EXEC_SEV_COLOR: Record<string, string> = {
  critical: "#dc2626",
  high: "#d97706",
  medium: "#2563eb",
  low: "#16a34a",
};

// ── Tone — the only place severity color is allowed to touch an icon chip ──

export type Tone = "neutral" | "success" | "warning" | "danger";

const TONE_COLOR: Record<Tone, string> = {
  neutral: ACCENT,
  success: "#16a34a",
  warning: "#d97706",
  danger: "#dc2626",
};

export function IconChip({
  icon: Icon, className = "h-9 w-9", tone = "neutral",
}: { icon: ElementType; className?: string; tone?: Tone }) {
  const color = TONE_COLOR[tone];
  return (
    <div
      className={`relative flex shrink-0 items-center justify-center rounded-xl ${className}`}
      style={{ backgroundColor: `${color}17`, boxShadow: `0 0 0 1px ${color}30` }}
    >
      <Icon className="h-4 w-4" style={{ color }} />
    </div>
  );
}

// ── Section label — small uppercase eyebrow used to order the page into
// one executive-priority reading path, matching the Documents workspace's
// SectionHeading pattern. Kept local (rather than imported cross-page) so
// this page's GLASS design system stays self-contained. ────────────────────

export function SectionLabel({
  icon: Icon, title, description, action,
}: { icon: ElementType; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 mb-3">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
          {description && <p className="text-sm text-foreground mt-0.5">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

// ── Relative time — shared by Activity Timeline ─────────────────────────────

export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffMs = Date.now() - then;
  const diffMin = Math.round(diffMs / 60_000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
