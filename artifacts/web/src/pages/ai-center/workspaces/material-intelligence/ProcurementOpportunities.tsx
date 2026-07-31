import {
  ShoppingCart, Lock, Layers, Repeat, Recycle, CalendarClock, ArrowLeftRight, type LucideIcon,
} from "lucide-react";
import type { OpportunityType, ProcurementOpportunity } from "@/lib/mockMaterialIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { formatSar } from "./shared";

const TYPE_META: Record<OpportunityType, { label: string; icon: LucideIcon }> = {
  buy_early: { label: "Buy Early", icon: ShoppingCart },
  lock_contract: { label: "Lock Contract Price", icon: Lock },
  consolidate_demand: { label: "Consolidate Demand", icon: Layers },
  switch_supplier: { label: "Switch Supplier", icon: Repeat },
  use_alternative: { label: "Use Approved Alternative", icon: Recycle },
  renegotiate_schedule: { label: "Renegotiate Schedule", icon: CalendarClock },
  transfer_stock: { label: "Transfer Stock", icon: ArrowLeftRight },
};

const PRIORITY_BADGE: Record<ProcurementOpportunity["priority"], string> = {
  High: "badge-danger",
  Medium: "badge-warning",
  Low: "badge-neutral",
};

// Procurement Opportunities — demo-labeled, actionable suggestions
// (buy early, lock pricing, consolidate demand, switch supplier, use an
// approved alternative, renegotiate schedule, transfer stock) with an
// estimated saving so procurement can prioritize.

export function ProcurementOpportunities({ opportunities }: { opportunities: ProcurementOpportunity[] }) {
  if (opportunities.length === 0) {
    return <EmptyState icon={ShoppingCart} title="No procurement opportunities identified" />;
  }

  return (
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
      {opportunities.map((o) => {
        const meta = TYPE_META[o.type];
        const Icon = meta.icon;
        return (
          <div key={o.id} className="panel panel-body space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{meta.label}</span>
              </div>
              <span className={`badge ${PRIORITY_BADGE[o.priority]} text-[10px]`}>{o.priority}</span>
            </div>
            <p className="text-sm font-semibold text-foreground">{o.title}</p>
            <p className="text-xs text-muted-foreground leading-relaxed">{o.description}</p>
            <div className="flex items-center justify-between pt-1 border-t border-border/50">
              <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">{formatSar(o.estimatedSavingSar)} potential</span>
              <span className="text-[11px] text-muted-foreground truncate max-w-[120px]">{o.projects.join(", ") || "Portfolio-wide"}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
