// Executive Decision Center Integration — this used to render a fully
// fabricated brief (headline + keyPoints + recommendations, all synthetic
// text from lib/mockExecutiveDecisionCenter.ts's aiExecutiveBrief field).
// That was "another executive summary" competing with the real one on
// Dashboard and Executive Intelligence. It now renders the same
// `executive_summary` + `portfolio_score` + `portfolio_status` fields
// those two pages already show, in the same layout Executive
// Intelligence's "Today's AI Insights" panel uses — same data, same
// page, consistent product. No fabricated key points or recommendations
// are shown here anymore; recommendations live in the Recommended
// Actions section below, where they belong.

export function AIExecutiveBrief({ summary, score, status }: { summary: string; score: number; status: string }) {
  return (
    <div className="space-y-2">
      <p className="text-[13px] text-muted-foreground leading-normal">{summary}</p>
      <div className="flex items-center gap-4 pt-2 border-t border-border/50 text-xs text-muted-foreground">
        <span>Portfolio score: <strong className="text-foreground">{score}/100</strong></span>
        <span>Status: <strong className="text-foreground">{status}</strong></span>
      </div>
    </div>
  );
}
