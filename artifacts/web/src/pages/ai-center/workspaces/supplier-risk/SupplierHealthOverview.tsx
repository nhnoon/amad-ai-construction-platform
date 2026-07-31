import { Gauge, Truck, ClipboardCheck, FileCheck2, Banknote, AlertTriangle } from "lucide-react";
import { StatTile } from "@/components/stat-tile";
import type { SupplierRiskSnapshot } from "@/lib/mockSupplierRisk";
import { BAND_BADGE, heatColor } from "./shared";

function bandForScore(score: number): "Low" | "Medium" | "High" | "Critical" {
  if (score >= 75) return "Critical";
  if (score >= 55) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function RiskGauge({ score }: { score: number }) {
  const color = heatColor(score);
  return (
    <div className="relative w-20 h-20 shrink-0">
      <svg viewBox="0 0 64 64" className="w-20 h-20 -rotate-90">
        <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted opacity-20" />
        <circle
          cx="32" cy="32" r="26" fill="none" strokeWidth="6"
          strokeDasharray={`${(score / 100) * 163.4} 163.4`} strokeLinecap="round"
          style={{ stroke: color, transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-base font-bold tabular-nums" style={{ color }}>{score}</span>
      </div>
    </div>
  );
}

// Executive Summary + Supplier Health Score — the portfolio-wide "how are
// our suppliers doing" snapshot at the top of the page: an overall risk
// gauge plus the five headline metrics the spec calls out by name.

export function SupplierHealthOverview({
  stats,
  summary,
}: {
  stats: SupplierRiskSnapshot["portfolioStats"];
  summary: SupplierRiskSnapshot["executiveSummary"];
}) {
  const band = bandForScore(stats.overallRiskScore);
  return (
    <div className="space-y-3">
      <div className="panel panel-body flex flex-wrap items-center gap-5">
        <RiskGauge score={stats.overallRiskScore} />
        <div className="flex-1 min-w-[240px] space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${BAND_BADGE[band]}`}>{band} portfolio risk</span>
            <span className="text-xs text-muted-foreground">Overall Supplier Risk Score &middot; {stats.overallRiskScore}/100</span>
          </div>
          <p className="text-sm text-foreground leading-relaxed">{summary.headline}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <StatTile icon={Gauge} label="Overall Risk Score" value={stats.overallRiskScore} valueLabel="/ 100" tone={stats.overallRiskScore >= 55 ? "warning" : "success"} />
        <StatTile icon={Truck} label="Avg Delivery" value={stats.avgDeliveryPerformance} valueLabel="%" tone={stats.avgDeliveryPerformance >= 60 ? "success" : "warning"} />
        <StatTile icon={ClipboardCheck} label="Avg Quality" value={stats.avgQualityScore} valueLabel="%" tone={stats.avgQualityScore >= 60 ? "success" : "warning"} />
        <StatTile icon={FileCheck2} label="Contract Compliance" value={stats.avgContractCompliance} valueLabel="%" tone={stats.avgContractCompliance >= 60 ? "success" : "warning"} />
        <StatTile icon={Banknote} label="Financial Stability" value={stats.avgFinancialStability} valueLabel="%" tone={stats.avgFinancialStability >= 60 ? "success" : "warning"} />
      </div>

      <div className="panel panel-body space-y-1.5">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <AlertTriangle className="w-3 h-3" /> Executive Summary
        </p>
        <ul className="space-y-1">
          {summary.bullets.map((b, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {b}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
