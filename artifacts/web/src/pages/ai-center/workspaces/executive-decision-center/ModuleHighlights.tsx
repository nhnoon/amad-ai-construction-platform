import { Link } from "wouter";
import { ChevronRight } from "lucide-react";
import type { ModuleHighlight } from "@/lib/mockExecutiveDecisionCenter";
import { MODULE_META } from "./shared";

// Cross-Module Highlights — one card per source AI Center workspace
// (Project Memory, Predictive Intelligence, Supplier Risk Intelligence,
// Material Intelligence, Cross-Project Learning), each linking straight
// into the real workspace for the full picture. This is what a real
// executive-aggregation backend would summarize — it does not actually
// read those modules' data (see lib/mockExecutiveDecisionCenter.ts).

export function ModuleHighlights({ highlights }: { highlights: ModuleHighlight[] }) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
      {highlights.map((h) => {
        const meta = MODULE_META[h.module];
        const Icon = meta.icon;
        return (
          <Link key={h.module} href={h.href} className="panel panel-body space-y-2 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150 group">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${meta.color}1a` }}>
                  <Icon className="w-4 h-4" style={{ color: meta.color }} />
                </div>
                <span className="text-xs font-semibold text-foreground">{h.module}</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{h.headline}</p>
            {h.metricLabel && (
              <p className="text-sm font-bold text-foreground">{h.metric} <span className="text-[10px] font-normal text-muted-foreground">{h.metricLabel}</span></p>
            )}
          </Link>
        );
      })}
    </div>
  );
}
