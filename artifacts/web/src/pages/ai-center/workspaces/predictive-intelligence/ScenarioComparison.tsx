import { TrendingUp, Minus, TrendingDown } from "lucide-react";
import type { ScenarioOutcome } from "@/lib/mockPredictiveIntelligence";
import { heatColor } from "./shared";

const SCENARIO_META: Record<ScenarioOutcome["case"], { label: string; icon: typeof TrendingUp; tone: string; bg: string }> = {
  best:     { label: "Best Case",     icon: TrendingUp,   tone: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  expected: { label: "Expected Case", icon: Minus,        tone: "text-blue-600 dark:text-blue-400",       bg: "bg-blue-500/10 border-blue-500/20" },
  worst:    { label: "Worst Case",    icon: TrendingDown, tone: "text-rose-600 dark:text-rose-400",       bg: "bg-rose-500/10 border-rose-500/20" },
};

function formatOffset(days: number): string {
  if (days === 0) return "On schedule";
  return days > 0 ? `${days} days late` : `${Math.abs(days)} days early`;
}

// "What if..." scenario comparison — Best / Expected / Worst case, side by
// side, for whatever scope (portfolio or a single project) is currently
// selected on the page.

export function ScenarioComparison({ scenarios, contextLabel }: { scenarios: ScenarioOutcome[]; contextLabel: string }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">Scenario range for <span className="font-medium text-foreground">{contextLabel}</span></p>
      <div className="grid gap-3 sm:grid-cols-3">
        {scenarios.map((s) => {
          const meta = SCENARIO_META[s.case];
          const Icon = meta.icon;
          return (
            <div key={s.case} className={`rounded-xl border p-4 space-y-3 ${meta.bg}`}>
              <div className="flex items-center gap-2">
                <Icon className={`w-4 h-4 ${meta.tone}`} />
                <p className={`text-sm font-bold ${meta.tone}`}>{meta.label}</p>
              </div>
              <div>
                <p className="text-2xl font-bold tabular-nums" style={{ color: heatColor(s.riskScore) }}>{s.riskScore}</p>
                <p className="text-[11px] text-muted-foreground">risk score / 100</p>
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Completion</span>
                  <span className="font-medium text-foreground">{formatOffset(s.completionDateOffsetDays)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Budget variance</span>
                  <span className="font-medium text-foreground">+{s.budgetVariancePct}%</span>
                </div>
              </div>
              <p className="text-[11px] text-foreground/70 leading-relaxed border-t border-border/40 pt-2">{s.narrative}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
