import { AlertOctagon, ChevronRight } from "lucide-react";
import type { SupplierProfile } from "@/lib/mockSupplierRisk";
import { EmptyState } from "@/components/ui/empty-state";
import { BAND_BADGE, CONTRACT_STATUS_BADGE, heatColor } from "./shared";

// Top High Risk Suppliers — the ranked "who needs attention first" list,
// portfolio-wide. Clicking a row opens the same detail drawer the
// directory table uses.

export function TopHighRiskSuppliers({
  suppliers,
  onSelect,
}: {
  suppliers: SupplierProfile[];
  onSelect: (supplier: SupplierProfile) => void;
}) {
  if (suppliers.length === 0) {
    return <EmptyState icon={AlertOctagon} title="No high-risk suppliers" description="Every supplier is currently within acceptable risk levels." />;
  }

  return (
    <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
      {suppliers.map((s, rank) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onSelect(s)}
          className="panel panel-body text-start space-y-2 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-bold text-muted-foreground shrink-0">{rank + 1}</span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{s.name}</p>
                <p className="text-[11px] text-muted-foreground truncate">{s.category} &middot; {s.region}</p>
              </div>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold tabular-nums leading-none" style={{ color: heatColor(s.overallRiskScore) }}>{s.overallRiskScore}</span>
            <span className="text-[10px] text-muted-foreground pb-0.5">risk score</span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`badge ${BAND_BADGE[s.riskBand]} text-[10px]`}>{s.riskBand}</span>
            <span className={`badge ${CONTRACT_STATUS_BADGE[s.contractStatus]} text-[10px]`}>{s.contractStatus}</span>
            {s.openIssues.filter((i) => i.status !== "Resolved").length > 0 && (
              <span className="text-[10px] text-muted-foreground">{s.openIssues.filter((i) => i.status !== "Resolved").length} open issue{s.openIssues.filter((i) => i.status !== "Resolved").length === 1 ? "" : "s"}</span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
