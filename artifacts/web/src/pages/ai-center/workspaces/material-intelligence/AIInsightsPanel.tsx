import { Link } from "wouter";
import { Sparkles, ListChecks, Wallet, PackageX, Target, Users, AlertTriangle } from "lucide-react";
import type { MaterialIntelligenceSnapshot } from "@/lib/mockMaterialIntelligence";
import { DemoDataBadge } from "./shared";

// AI Insights Panel — the portfolio-wide "so what should procurement do
// this week" synthesis, distinct from the per-material AI Insights tab
// inside the detail drawer. Always demo-labeled; never presented as a
// live AI output or a real market prediction.

export function AIInsightsPanel({ insights }: { insights: MaterialIntelligenceSnapshot["aiPortfolioInsights"] }) {
  return (
    <div className="panel panel-body space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
          <Sparkles className="w-4 h-4 text-primary" /> AI Insights Panel
        </h3>
        <DemoDataBadge />
      </div>
      <p className="text-xs text-muted-foreground -mt-2">
        Illustrative market analysis — the kind of synthesis Hermes would generate once grounded in real pricing and
        supply data. No live AI, no real market prediction.
      </p>
      <p className="text-sm text-foreground leading-relaxed">{insights.headline}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><ListChecks className="w-3 h-3" /> Top Material Risks</p>
          <ul className="space-y-1">
            {insights.topRisks.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {r}</li>
            ))}
          </ul>
        </div>

        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Wallet className="w-3 h-3" /> Highest Cost Exposure</p>
          <ul className="space-y-1">
            {insights.highestCostExposure.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-500" /> {r}</li>
            ))}
          </ul>
        </div>

        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><PackageX className="w-3 h-3" /> Emerging Shortages</p>
          {insights.emergingShortages.length === 0 ? (
            <p className="text-xs text-muted-foreground">No emerging shortages flagged this cycle.</p>
          ) : (
            <ul className="space-y-1">
              {insights.emergingShortages.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-red-500" /> {r}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Target className="w-3 h-3" /> Procurement Recommendations</p>
          <ul className="space-y-1">
            {insights.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {r}</li>
            ))}
          </ul>
        </div>
      </div>

      {insights.suggestedAlternatives.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Users className="w-3 h-3" /> Suggested Alternative Materials</p>
          <div className="flex flex-wrap gap-1.5">
            {insights.suggestedAlternatives.map((a) => (
              <span key={a} className="text-[11px] rounded-full bg-muted px-2.5 py-1 text-muted-foreground">{a}</span>
            ))}
          </div>
        </div>
      )}

      {insights.attentionProjects.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><AlertTriangle className="w-3 h-3" /> Projects Requiring Immediate Attention</p>
          <ul className="space-y-1">
            {insights.attentionProjects.map((p) => (
              <li key={p.projectCode} className="flex items-center justify-between text-xs rounded-lg border border-border/60 px-3 py-1.5">
                <Link href="/projects" className="text-primary hover:underline">{p.projectCode} &middot; {p.projectName}</Link>
                <span className="text-muted-foreground">{p.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
