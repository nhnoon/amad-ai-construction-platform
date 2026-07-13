import type { ElementType, ReactNode } from "react";
import { Link } from "wouter";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

// ── Visual system (Dashboard-only — no shared CSS touched) ─────────────────
// One accent color (gold) governs all neutral chrome: icon chips, CTA,
// highlights. Semantic color (severity/status) is reserved for data
// encoding — KPI tone, donut segments, status cards, risk bars — where
// dropping it would make the number/chart unreadable at a glance.

export const ACCENT = "#eab308";

export const GLASS =
  "relative overflow-hidden rounded-3xl border border-border/70 bg-card shadow-sm " +
  "dark:border-white/[0.07] dark:bg-white/[0.03] dark:backdrop-blur-xl dark:shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset,0_24px_60px_-32px_rgba(0,0,0,0.9)]";

export const GLASS_HEADER =
  "relative flex items-center gap-3 border-b border-border/60 dark:border-white/[0.05] px-5 py-4";

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

// ── Tone — the only place severity color is allowed to touch a KPI tile ────

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

// ── KPI tile ─────────────────────────────────────────────────────────────

export interface KpiTrend {
  direction: "up" | "down";
  label: string;
  positive?: boolean;
}

export function KpiTile({
  icon: Icon, label, value, sub, trend, tone = "neutral", isLoading, href,
}: {
  icon: ElementType;
  label: string;
  value: number | string;
  sub?: string;
  trend?: KpiTrend;
  tone?: Tone;
  isLoading?: boolean;
  href?: string;
}) {
  if (isLoading) return <Skeleton className={`${GLASS} min-h-[100px] w-full`} />;

  const body = (
    <div
      className={`${GLASS} p-4 min-h-[100px] flex flex-col justify-between transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${
        href ? "cursor-pointer" : ""
      }`}
    >
      <div className="relative flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <IconChip icon={Icon} className="h-7 w-7" tone={tone} />
          <p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground truncate">{label}</p>
        </div>
        {trend && (
          <span
            className={`shrink-0 flex items-center gap-0.5 text-[10px] font-semibold ${
              trend.positive ? "text-emerald-500" : "text-red-500"
            }`}
          >
            {trend.direction === "up" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
            {trend.label}
          </span>
        )}
      </div>
      <div className="relative mt-3">
        <p className="text-[26px] font-bold text-foreground leading-tight tabular-nums">{value}</p>
        {sub && <p className="text-[10px] text-muted-foreground/70 truncate mt-0.5">{sub}</p>}
      </div>
    </div>
  );

  return href ? <Link href={href}>{body}</Link> : body;
}

// ── Relative time — shared by Activity Timeline and Alerts panel ───────────

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
