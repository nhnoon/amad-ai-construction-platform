import { Sparkles, ListChecks, Target, Eye, Users } from "lucide-react";
import { DemoDataBadge, heatColor } from "./shared";

// Portfolio-wide AI Insights Panel — the "so what should procurement do
// this week" synthesis across every supplier, distinct from the
// per-supplier AI Insights tab inside the detail drawer. Always
// demo-labeled; never presented as a live AI output.

export function AIInsightsPanel({
  headline,
  topRisks,
  recommendedActions,
  procurementObservations,
  exampleAlternatives,
}: {
  headline: string;
  topRisks: string[];
  recommendedActions: string[];
  procurementObservations: string[];
  exampleAlternatives?: { supplierId: number; name: string; riskScore: number }[];
}) {
  return (
    <div className="panel panel-body space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-primary" /> AI Insights Panel
        </h3>
        <DemoDataBadge />
      </div>
      <p className="text-xs text-muted-foreground -mt-2">
        Illustrative of the guidance Hermes would generate once grounded in real supplier records — not a live AI call.
      </p>
      <p className="text-sm text-foreground leading-relaxed">{headline}</p>

      <div className="space-y-1.5">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><ListChecks className="w-3 h-3" /> Top Supplier Risks</p>
        <ul className="space-y-1">
          {topRisks.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {r}</li>
          ))}
        </ul>
      </div>

      <div className="space-y-1.5">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Target className="w-3 h-3" /> Recommended Actions</p>
        <ul className="space-y-1">
          {recommendedActions.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {r}</li>
          ))}
        </ul>
      </div>

      {exampleAlternatives && exampleAlternatives.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Users className="w-3 h-3" /> Suggested Alternative Suppliers</p>
          <p className="text-[11px] text-muted-foreground">For the highest-risk supplier — open its detail drawer for the full comparison.</p>
          <ul className="space-y-1">
            {exampleAlternatives.map((alt) => (
              <li key={alt.supplierId} className="flex items-center justify-between text-xs rounded-lg border border-border/60 px-3 py-1.5">
                <span className="text-foreground">{alt.name}</span>
                <span className="font-semibold" style={{ color: heatColor(alt.riskScore) }}>{alt.riskScore}/100</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-1.5">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Eye className="w-3 h-3" /> Procurement Observations</p>
        <ul className="space-y-1">
          {procurementObservations.map((o, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" /> {o}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
