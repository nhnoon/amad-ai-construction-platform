import { useMemo, useState } from "react";
import { ArrowUpDown, Wallet } from "lucide-react";
import type { MaterialIntelligenceSnapshot, RiskLevel } from "@/lib/mockMaterialIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { FilterSelect } from "@/components/filter-select";
import { RISK_BADGE, PROCUREMENT_STATUS_BADGE, formatSar, heatColor } from "./shared";

type ExposureRow = MaterialIntelligenceSnapshot["exposureRows"][number];
type SortKey = "estimatedIncrease" | "currentCost" | "baselineCost";

// Portfolio Cost Exposure — every project x material combination where a
// planned quantity is exposed to the current illustrative price. Reused
// both on the main page (every row) and inside the Material Detail
// Drawer's Project Exposure tab (pre-filtered to one material, with the
// Material column hidden since it would be redundant there).

export function PortfolioExposureTable({
  rows,
  showMaterialColumn = true,
  showFilters = true,
}: {
  rows: ExposureRow[];
  showMaterialColumn?: boolean;
  showFilters?: boolean;
}) {
  const [exposureLevel, setExposureLevel] = useState<RiskLevel | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("estimatedIncrease");

  const filtered = rows.filter((r) => exposureLevel === "all" || r.exposureLevel === exposureLevel);
  const sorted = useMemo(() => [...filtered].sort((a, b) => b[sortKey] - a[sortKey]), [filtered, sortKey]);

  if (rows.length === 0) {
    return <EmptyState icon={Wallet} title="No cost exposure recorded" description="No project is currently assigned quantities for this material." />;
  }

  return (
    <div className="space-y-2">
      {showFilters && (
        <div className="flex flex-wrap items-center gap-2">
          <FilterSelect value={exposureLevel} onChange={(v) => setExposureLevel(v as typeof exposureLevel)} className="w-40" ariaLabel="Exposure level">
            <option value="all">All exposure levels</option>
            {(["Low", "Medium", "High", "Critical"] as RiskLevel[]).map((r) => <option key={r} value={r}>{r}</option>)}
          </FilterSelect>
          <button
            type="button"
            onClick={() => setSortKey((k) => (k === "estimatedIncrease" ? "currentCost" : k === "currentCost" ? "baselineCost" : "estimatedIncrease"))}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowUpDown className="w-3 h-3" /> Sorted by {sortKey === "estimatedIncrease" ? "cost increase" : sortKey === "currentCost" ? "current cost" : "baseline cost"}
          </button>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="data-table" data-testid="portfolio-exposure-table">
          <thead>
            <tr>
              <th>Project</th>
              {showMaterialColumn && <th>Material</th>}
              <th>Planned Qty</th>
              <th>Baseline Cost</th>
              <th>Current Cost</th>
              <th>Estimated Increase</th>
              <th>Exposure</th>
              <th>Procurement</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={`${r.materialId}-${r.projectId}-${i}`}>
                <td>
                  <p className="text-sm font-medium text-foreground">{r.projectCode}</p>
                  <p className="text-xs text-muted-foreground truncate max-w-[160px]">{r.projectName}</p>
                </td>
                {showMaterialColumn && <td className="text-sm text-muted-foreground">{r.materialName}</td>}
                <td className="text-sm tabular-nums">{r.plannedQuantity.toLocaleString()}</td>
                <td className="text-sm tabular-nums">{formatSar(r.baselineCost)}</td>
                <td className="text-sm tabular-nums">{formatSar(r.currentCost)}</td>
                <td className="text-sm font-semibold tabular-nums" style={{ color: heatColor(r.estimatedIncrease > 0 ? 70 : 20) }}>
                  {r.estimatedIncrease >= 0 ? "+" : ""}{formatSar(r.estimatedIncrease)}
                </td>
                <td><span className={`badge ${RISK_BADGE[r.exposureLevel]} text-[10px]`}>{r.exposureLevel}</span></td>
                <td><span className={`badge ${PROCUREMENT_STATUS_BADGE[r.procurementStatus]} text-[10px]`}>{r.procurementStatus}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
