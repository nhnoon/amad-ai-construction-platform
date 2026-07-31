import { Building2, AlertOctagon, AlertTriangle } from "lucide-react";
import { StatTile } from "@/components/stat-tile";
import { heatColor } from "./shared";

// Executive Decision Center Integration — this used to render a fully
// synthetic overview (portfolioHealthScore/Band, criticalAlerts,
// highRiskItems, all derived from a per-project random-walk risk score
// generated locally, unrelated to any other page). It now takes the exact
// same fields Dashboard's KPI row and Executive Intelligence's brief use —
// `useExecutive()`'s portfolio_score/portfolio_status/critical_count/
// at_risk_count — so this page's headline "how healthy is the portfolio"
// answer can never disagree with the other two. `pendingDecisions` was
// removed from this tile row entirely rather than kept demo-labeled next
// to three real numbers — it's still visible, just moved to the Decision
// Queue section's own count badge, where it belongs with the rest of that
// still-illustrative workflow.

const STATUS_BADGE: Record<string, string> = {
  Excellent: "badge-success", Good: "badge-success", "At Risk": "badge-warning", Critical: "badge-danger",
};

function HealthGauge({ score, status }: { score: number; status: string }) {
  const color = heatColor(100 - score);
  return (
    <div className="relative w-20 h-20 shrink-0">
      <svg viewBox="0 0 64 64" className="w-20 h-20 -rotate-90">
        <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted opacity-20" />
        <circle cx="32" cy="32" r="26" fill="none" strokeWidth="6" strokeDasharray={`${(score / 100) * 163.4} 163.4`} strokeLinecap="round" style={{ stroke: color, transition: "stroke-dasharray 0.6s ease" }} />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center"><span className="text-base font-bold tabular-nums" style={{ color }}>{score}</span></div>
      <span className="sr-only">{status} portfolio health, {score} out of 100</span>
    </div>
  );
}

export function ExecutiveOverview({ score, status, activeProjects, criticalCount, atRiskCount }: {
  score: number;
  status: string;
  activeProjects: number;
  criticalCount: number;
  atRiskCount: number;
}) {
  return (
    <div className="space-y-3">
      <div className="panel panel-body flex flex-wrap items-center gap-5">
        <HealthGauge score={score} status={status} />
        <div className="flex-1 min-w-[220px] space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${STATUS_BADGE[status] ?? "badge-neutral"}`}>{status}</span>
            <span className="text-xs text-muted-foreground">Portfolio Health &middot; {score}/100</span>
          </div>
          <p className="text-sm text-muted-foreground">A single glance at where leadership attention is needed most, right now.</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2.5">
        <StatTile icon={Building2} label="Active Projects" value={activeProjects} tone="neutral" />
        <StatTile icon={AlertOctagon} label="Critical" value={criticalCount} tone={criticalCount > 0 ? "danger" : "success"} />
        <StatTile icon={AlertTriangle} label="At Risk" value={atRiskCount} tone={atRiskCount > 0 ? "warning" : "success"} />
      </div>
    </div>
  );
}
