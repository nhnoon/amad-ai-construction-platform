import { Target } from "lucide-react";
import type { RecommendedAction } from "@/lib/mockExecutiveDecisionCenter";
import { EmptyState } from "@/components/ui/empty-state";
import { MODULE_META, PRIORITY_BADGE } from "./shared";

// Recommended Executive Actions — concrete next steps synthesized across
// the portfolio, each attributed to the module that surfaced it. Renders
// as the content of a shared `InsightPanel variant="decision"` (see
// index.tsx — the same primitive Reports and Executive Intelligence's own
// recommended-actions sections use), so cards here are bordered rows, not
// their own elevated panels.

export function RecommendedActions({ actions }: { actions: RecommendedAction[] }) {
  if (actions.length === 0) return <EmptyState icon={Target} title="No recommended actions right now" />;

  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {actions.map((a) => {
        const meta = MODULE_META[a.module];
        const Icon = meta.icon;
        return (
          <div key={a.id} className="rounded-lg border border-border/60 p-3 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${meta.color}1a` }}>
                  <Icon className="w-4 h-4" style={{ color: meta.color }} />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{a.module}</span>
              </div>
              <span className={`badge ${PRIORITY_BADGE[a.priority]} text-[10px]`}>{a.priority}</span>
            </div>
            <p className="text-sm font-semibold text-foreground">{a.title}</p>
            <p className="text-xs text-muted-foreground leading-relaxed">{a.description}</p>
            <p className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 pt-1 border-t border-border/50">{a.estimatedImpact}</p>
          </div>
        );
      })}
    </div>
  );
}
