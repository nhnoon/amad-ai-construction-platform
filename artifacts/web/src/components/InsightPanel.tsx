import type { ElementType, ReactNode } from "react";

// AMAD v2 — Primary Insight Panel / Decision Panel primitive (component
// hierarchy, via the `variant` prop). This is the one panel type on a
// page allowed to visually dominate: larger padding, a gold accent rule,
// bigger title than `.panel-title`. `variant="brief"` is the single
// authoritative AI/executive summary a page gets (there should only ever
// be one per page); `variant="decision"` is for action-oriented content
// (recommendations, decisions) and stays slightly more compact. Distinct
// from `.panel` — an InsightPanel is a statement, not a data container.

export function InsightPanel({
  icon: Icon,
  title,
  badge,
  variant = "brief",
  children,
  footer,
}: {
  icon: ElementType;
  title: string;
  badge?: ReactNode;
  variant?: "brief" | "decision";
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <section className={`relative rounded-xl border bg-card shadow-md overflow-hidden ${variant === "brief" ? "border-accent/25" : "border-border"}`}>
      <div className="absolute inset-y-0 start-0 w-1 bg-accent" aria-hidden="true" />
      <div className={`ps-4 pe-4 md:ps-5 md:pe-5 ${variant === "brief" ? "py-4" : "py-3.5"} space-y-2.5`}>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
              <Icon className="w-3.5 h-3.5 text-accent" />
            </div>
            <h3 className={`font-semibold text-foreground ${variant === "brief" ? "text-sm" : "text-[13px]"}`}>{title}</h3>
          </div>
          {badge}
        </div>
        <div className={variant === "brief" ? "text-sm" : "text-[13px]"}>{children}</div>
        {footer && <div className="pt-1.5 border-t border-border/50">{footer}</div>}
      </div>
    </section>
  );
}
