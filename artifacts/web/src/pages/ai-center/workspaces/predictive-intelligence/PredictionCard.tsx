import { useState } from "react";
import { ChevronDown, ChevronUp, ListChecks, Target } from "lucide-react";
import type { CategoryPrediction } from "@/lib/mockPredictiveIntelligence";
import { CATEGORY_META, ConfidenceTag, TrendIndicator, heatColor } from "./shared";

// One of the six flagship prediction cards (Delay / Budget Overrun / Cash
// Flow / Claim / Safety / Schedule). Collapsed it reads at a glance
// (probability, trend, confidence); expanded it shows the Contributing
// Factors and Recommended Actions the spec calls for, without needing a
// separate drawer for something this short.

export function PredictionCard({ prediction }: { prediction: CategoryPrediction }) {
  const [expanded, setExpanded] = useState(false);
  const meta = CATEGORY_META[prediction.category];
  const Icon = meta.icon;
  const color = heatColor(prediction.probability);

  return (
    <div className="panel overflow-hidden">
      <div className="h-1 w-full" style={{ backgroundColor: color }} />
      <div className="panel-body space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${meta.color}1a` }}>
              <Icon className="w-4 h-4" style={{ color: meta.color }} />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground leading-tight">{meta.label}</p>
              <ConfidenceTag level={prediction.confidence} />
            </div>
          </div>
          <TrendIndicator trend={prediction.trend} deltaPts={prediction.trendDeltaPts} />
        </div>

        <div className="flex items-end gap-2">
          <span className="text-3xl font-bold leading-none tabular-nums" style={{ color }}>{prediction.probability}%</span>
          <span className="text-xs text-muted-foreground pb-1">probability</span>
        </div>

        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${prediction.probability}%`, backgroundColor: color }} />
        </div>

        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Hide details" : "Contributing factors & actions"}
        </button>

        {expanded && (
          <div className="space-y-3 pt-1 border-t border-border/50">
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <ListChecks className="w-3 h-3" /> Contributing Factors
              </p>
              <ul className="space-y-1">
                {prediction.contributingFactors.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {f}
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Target className="w-3 h-3" /> Recommended Actions
              </p>
              <ul className="space-y-1">
                {prediction.recommendedActions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {a}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
