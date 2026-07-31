import { Link } from "wouter";
import { CheckCircle2, XCircle, Clock3, History } from "lucide-react";
import type { PredictionHistoryEntry, PredictionOutcome } from "@/lib/mockPredictiveIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { CATEGORY_META, BAND_BADGE, formatDate } from "./shared";

const OUTCOME_META: Record<PredictionOutcome, { label: string; icon: typeof CheckCircle2; tone: string }> = {
  occurred: { label: "Outcome: occurred", icon: CheckCircle2, tone: "text-amber-600 dark:text-amber-400" },
  avoided:  { label: "Outcome: avoided",  icon: XCircle,      tone: "text-emerald-600 dark:text-emerald-400" },
  pending:  { label: "Outcome: pending",  icon: Clock3,       tone: "text-muted-foreground" },
};

// Prediction History — a track record of past forecasts against what
// actually happened, so leadership can judge the model's usefulness
// instead of taking each new forecast on faith. All demo data — see the
// page-level Demo Data badge.

export function PredictionHistory({ entries }: { entries: PredictionHistoryEntry[] }) {
  if (entries.length === 0) {
    return <EmptyState icon={History} title="No prediction history yet" description="Once forecasts age past their window, outcomes will appear here." />;
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => {
        const meta = CATEGORY_META[entry.category];
        const outcome = OUTCOME_META[entry.outcome];
        const OutcomeIcon = outcome.icon;
        return (
          <div key={entry.id} className="panel panel-body space-y-1.5">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground">{meta.label}</span>
                <span className={`badge ${BAND_BADGE[entry.predictedBand]} text-[10px]`}>{entry.predictedBand} &middot; {entry.predictedProbability}%</span>
              </div>
              <span className="text-[11px] text-muted-foreground">{formatDate(entry.date)}</span>
            </div>
            <p className="text-xs text-muted-foreground">{entry.note}</p>
            <div className="flex items-center justify-between gap-2">
              <Link href={`/projects/${entry.projectId}`} className="text-[11px] text-primary hover:underline">
                {entry.projectCode} &middot; {entry.projectName}
              </Link>
              <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${outcome.tone}`}>
                <OutcomeIcon className="w-3.5 h-3.5" /> {outcome.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
