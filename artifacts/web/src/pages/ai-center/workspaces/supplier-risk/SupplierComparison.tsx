import { X, GitCompare } from "lucide-react";
import type { SupplierProfile } from "@/lib/mockSupplierRisk";
import { EmptyState } from "@/components/ui/empty-state";
import { BAND_BADGE, CONTRACT_STATUS_BADGE, heatColor } from "./shared";

const METRICS: { key: keyof SupplierProfile; label: string; higherIsBetter: boolean }[] = [
  { key: "overallRiskScore", label: "Overall Risk Score", higherIsBetter: false },
  { key: "deliveryPerformance", label: "Delivery Performance", higherIsBetter: true },
  { key: "qualityScore", label: "Quality Score", higherIsBetter: true },
  { key: "contractCompliance", label: "Contract Compliance", higherIsBetter: true },
  { key: "financialStability", label: "Financial Stability", higherIsBetter: true },
];

// Supplier comparison — select up to 3 suppliers in the Directory below,
// compare their headline metrics side by side. Cell color always reads
// "green is good" regardless of whether the underlying metric counts up
// or down, so the table stays scannable at a glance.

export function SupplierComparison({
  suppliers,
  onRemove,
}: {
  suppliers: SupplierProfile[];
  onRemove: (id: number) => void;
}) {
  if (suppliers.length === 0) {
    return (
      <EmptyState
        icon={GitCompare}
        title="Select suppliers to compare"
        description="Check up to 3 suppliers in the directory below to compare their scores side by side."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="data-table" data-testid="supplier-comparison-table">
        <thead>
          <tr>
            <th>Metric</th>
            {suppliers.map((s) => (
              <th key={s.id} className="min-w-[160px]">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-foreground font-semibold normal-case">{s.name}</p>
                    <span className={`badge ${BAND_BADGE[s.riskBand]} text-[10px] mt-1`}>{s.riskBand}</span>
                  </div>
                  <button type="button" onClick={() => onRemove(s.id)} aria-label={`Remove ${s.name} from comparison`} className="text-muted-foreground hover:text-foreground">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {METRICS.map((metric) => (
            <tr key={metric.key}>
              <td className="text-muted-foreground font-medium">{metric.label}</td>
              {suppliers.map((s) => {
                const value = s[metric.key] as number;
                const colorValue = metric.higherIsBetter ? 100 - value : value;
                return (
                  <td key={s.id}>
                    <span className="text-sm font-bold tabular-nums" style={{ color: heatColor(colorValue) }}>{value}</span>
                  </td>
                );
              })}
            </tr>
          ))}
          <tr>
            <td className="text-muted-foreground font-medium">Contract Status</td>
            {suppliers.map((s) => (
              <td key={s.id}><span className={`badge ${CONTRACT_STATUS_BADGE[s.contractStatus]} text-[10px]`}>{s.contractStatus}</span></td>
            ))}
          </tr>
          <tr>
            <td className="text-muted-foreground font-medium">Projects Served</td>
            {suppliers.map((s) => <td key={s.id} className="text-sm">{s.projectsServed.length}</td>)}
          </tr>
          <tr>
            <td className="text-muted-foreground font-medium">Open Issues</td>
            {suppliers.map((s) => <td key={s.id} className="text-sm">{s.openIssues.filter((i) => i.status !== "Resolved").length}</td>)}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
