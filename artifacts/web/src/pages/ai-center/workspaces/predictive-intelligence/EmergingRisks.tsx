import { Link } from "wouter";
import { Flame } from "lucide-react";
import type { EmergingRisk } from "@/lib/mockPredictiveIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { CATEGORY_META, heatColor } from "./shared";

// Top Emerging Risks — the biggest week-over-week probability increases
// across every project x category combination, portfolio-wide. This is
// the "what changed recently" counterpart to the Heat Map's "what's true
// right now."

export function EmergingRisks({ risks }: { risks: EmergingRisk[] }) {
  if (risks.length === 0) {
    return <EmptyState icon={Flame} title="No sharply rising risks this week" description="Nothing has jumped enough to flag as emerging." />;
  }

  return (
    <div className="space-y-2">
      {risks.map((risk) => {
        const meta = CATEGORY_META[risk.category];
        const Icon = meta.icon;
        return (
          <div key={risk.id} className="panel panel-body flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${meta.color}1a` }}>
              <Icon className="w-4 h-4" style={{ color: meta.color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-sm font-semibold text-foreground">{meta.label}</span>
                <Link href={`/projects/${risk.projectId}`} className="text-xs text-primary hover:underline">
                  {risk.projectCode}
                </Link>
              </div>
              <p className="text-xs text-muted-foreground truncate">{risk.description}</p>
            </div>
            <div className="text-end shrink-0">
              <p className="text-sm font-bold tabular-nums" style={{ color: heatColor(risk.probability) }}>{risk.probability}%</p>
              <p className="text-[10px] font-semibold text-red-600 dark:text-red-400">+{risk.deltaPts} pts</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
