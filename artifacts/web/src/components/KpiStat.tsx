import type { ElementType } from "react";
import { Link } from "wouter";
import { TrendingUp, TrendingDown } from "lucide-react";
import { DemoDataBadge } from "./DemoDataBadge";

// AMAD v2 — Executive KPI primitive (component hierarchy: Executive KPI /
// Supporting Metric, via the `size` prop). Number-forward: circular icon
// badge + label, one large tabular-nums figure, an optional one-line
// description, and an optional trend delta row — distinct from StatTile
// (icon chip + description, the right choice for quick-access/navigation
// tiles) and from the compact `size="sm"` variant used for denser
// supporting-metric rows.

export type KpiTone = "neutral" | "success" | "warning" | "danger" | "gold";

const TONE_TEXT: Record<KpiTone, string> = {
  neutral: "text-foreground",
  success: "text-emerald-600 dark:text-emerald-400",
  warning: "text-amber-600 dark:text-amber-400",
  danger: "text-red-600 dark:text-red-400",
  gold: "text-accent",
};

const TONE_ICON_BG: Record<KpiTone, string> = {
  neutral: "bg-muted text-muted-foreground",
  success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  danger: "bg-red-500/10 text-red-600 dark:text-red-400",
  gold: "bg-accent/10 text-accent",
};

export function KpiStat({
  icon: Icon,
  label,
  value,
  valueSuffix,
  description,
  tone = "neutral",
  size = "lg",
  demo = false,
  href,
  deltaValue,
  deltaDirection = "up",
  deltaPositive = true,
  deltaCaption = "vs last 30 days",
}: {
  icon: ElementType;
  label: string;
  value: string | number;
  valueSuffix?: string;
  /** One short line under the value, e.g. "Active projects". */
  description?: string;
  tone?: KpiTone;
  size?: "lg" | "sm";
  demo?: boolean;
  href?: string;
  /** e.g. "8%" — omit to hide the delta row entirely. */
  deltaValue?: string;
  deltaDirection?: "up" | "down";
  /** Controls delta color — an "increase" isn't always good (e.g. rising risk). */
  deltaPositive?: boolean;
  deltaCaption?: string;
}) {
  const DeltaIcon = deltaDirection === "up" ? TrendingUp : TrendingDown;

  const body = (
    <div className={`panel h-full flex flex-col ${href ? "hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150 cursor-pointer" : ""} ${size === "lg" ? "p-3.5" : "p-2.5"}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`${size === "lg" ? "w-7 h-7" : "w-6 h-6"} rounded-full flex items-center justify-center shrink-0 ${TONE_ICON_BG[tone]}`}>
            <Icon className={size === "lg" ? "w-3.5 h-3.5" : "w-3 h-3"} />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground truncate">{label}</p>
        </div>
        {demo && <span className="shrink-0"><DemoDataBadge label="Demo" /></span>}
      </div>

      <div className={size === "lg" ? "mt-2.5" : "mt-1.5"}>
        <p className={`kpi-number font-bold leading-none ${size === "lg" ? "text-xl" : "text-base"} ${TONE_TEXT[tone]}`}>
          {value}
          {valueSuffix && <span className="text-[11px] font-medium text-muted-foreground ms-1">{valueSuffix}</span>}
        </p>
        {description && <p className="text-[10px] text-muted-foreground mt-0.5">{description}</p>}
      </div>

      {deltaValue && (
        <div className="flex items-center gap-1.5 mt-auto pt-2 border-t border-border/40 text-[10px]">
          <span className={`inline-flex items-center gap-0.5 font-semibold ${deltaPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
            <DeltaIcon className="w-2.5 h-2.5" />{deltaValue}
          </span>
          <span className="text-muted-foreground">{deltaCaption}</span>
        </div>
      )}
    </div>
  );

  if (href) return <Link href={href} className="block h-full">{body}</Link>;
  return body;
}
