import { Link } from "wouter";
import { Bell, CheckCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { GLASS, GLASS_HEADER, IconChip, formatRelativeTime } from "./shared";
import type { Alert, AlertsSummary } from "../../lib/useAlerts";

// Top alerts ranked by severity (most urgent first) — a distinct, priority-
// ranked lens on the same alert data the full /alerts page shows in a
// filterable list. Severity is condensed from the underlying 4-level scale
// (critical/high/medium/low) to the 3-tier Critical/Warning/Information
// badges this widget asks for, without altering the real severity value
// anywhere else in the app.

type Tier = "Critical" | "Warning" | "Information";

const TIER_BY_SEVERITY: Record<string, Tier> = {
  critical: "Critical",
  high: "Warning",
  medium: "Information",
  low: "Information",
};

const TIER_BADGE: Record<Tier, string> = {
  Critical: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  Warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  Information: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
};

const SEVERITY_RANK: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function AlertsPanel({
  alerts, summary, isLoading,
}: { alerts?: Alert[]; summary?: AlertsSummary; isLoading: boolean }) {
  const top = [...(alerts ?? [])]
    .sort((a, b) => (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9))
    .slice(0, 4);

  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={Bell} tone={summary && summary.critical > 0 ? "danger" : "neutral"} />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-bold text-foreground block">Alerts</span>
          <span className="text-[11px] text-muted-foreground">
            {isLoading ? "Loading…" : summary ? `${summary.total} active · ${summary.critical} critical, ${summary.high} high` : "Needs attention"}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="p-5 space-y-3">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
        </div>
      ) : top.length === 0 ? (
        <div className="p-5 min-h-[180px] flex flex-col items-center justify-center text-center gap-2">
          <CheckCircle className="w-8 h-8 text-emerald-500/60" />
          <p className="text-xs text-muted-foreground">All systems are operating normally</p>
        </div>
      ) : (
        <div className="p-5 space-y-2.5">
          {top.map((alert) => {
            const tier = TIER_BY_SEVERITY[alert.severity] ?? "Information";
            return (
              <div key={alert.id} className="flex items-start gap-2.5">
                <span className={`shrink-0 mt-0.5 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${TIER_BADGE[tier]}`}>
                  {tier}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground leading-snug truncate">{alert.title}</p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {alert.project_code ? `${alert.project_code} · ` : ""}{formatRelativeTime(alert.detected_at)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="px-5 py-3 border-t border-border/60 dark:border-white/[0.05]">
        <Link href="/alerts" className="text-xs font-medium text-primary hover:underline">
          View all alerts →
        </Link>
      </div>
    </div>
  );
}
