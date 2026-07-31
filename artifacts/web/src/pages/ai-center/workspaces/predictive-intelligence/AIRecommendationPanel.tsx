import { Sparkles, ListChecks, Target } from "lucide-react";
import { DemoDataBadge } from "./shared";

// AI Recommendation Panel — the "so what should we do" synthesis of every
// prediction on the page. Mirrors the Section pattern used by
// AIAnswerStructured.tsx / Project Memory's AI summary panel, so every
// "AI-style" surface in the app reads the same way. Always demo-labeled —
// see build constraint: never presented as a live AI output.

export function AIRecommendationPanel({
  headline,
  keyFindings,
  recommendations,
}: {
  headline: string;
  keyFindings: string[];
  recommendations: string[];
}) {
  return (
    <div className="panel panel-body space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-primary" /> AI Recommendation Panel
        </h3>
        <DemoDataBadge />
      </div>
      <p className="text-xs text-muted-foreground -mt-2">
        Illustrative of the guidance Hermes would generate once grounded in a real forecasting model — not a live AI call.
      </p>
      <p className="text-sm text-foreground leading-relaxed">{headline}</p>

      <div className="space-y-1.5">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <ListChecks className="w-3 h-3" /> Key Findings
        </p>
        <ul className="space-y-1">
          {keyFindings.map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground">
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
          {recommendations.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {r}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
