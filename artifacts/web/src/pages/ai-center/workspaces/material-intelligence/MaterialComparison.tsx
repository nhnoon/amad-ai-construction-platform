import { X, GitCompare } from "lucide-react";
import type { MaterialProfile } from "@/lib/mockMaterialIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { RISK_BADGE, SUPPLY_STATUS_BADGE, heatColor, formatPct } from "./shared";
import { PriceTrendChart } from "./PriceTrendChart";

const COMPARE_COLORS = ["#0ea5e9", "#a855f7", "#f59e0b"];

// Material Comparison — select up to 3 materials in the Directory below,
// compare their price trend (index-normalized so wildly different price
// scales, e.g. diesel vs. copper, stay readable on one chart) plus
// volatility, lead time, supply risk, project exposure, and supplier
// availability.

export function MaterialComparison({
  materials,
  onRemove,
}: {
  materials: MaterialProfile[];
  onRemove: (id: string) => void;
}) {
  if (materials.length === 0) {
    return (
      <EmptyState
        icon={GitCompare}
        title="Select materials to compare"
        description="Check up to 3 materials in the directory below to compare their price trends and risk profile."
      />
    );
  }

  const periods = materials[0].priceHistory.map((p) => p.period);
  const chartData = periods.map((period, i) => {
    const row: Record<string, number | string> = { period };
    for (const m of materials) row[m.id] = Math.round((m.priceHistory[i].price / m.priceHistory[0].price) * 1000) / 10;
    return row;
  });
  const series = materials.map((m, i) => ({ key: m.id, label: m.name, color: COMPARE_COLORS[i % COMPARE_COLORS.length] }));

  return (
    <div className="space-y-4">
      <div className="panel panel-body">
        <p className="text-xs text-muted-foreground mb-2">Price trend, indexed to 100 at the start of the window (so different price scales stay comparable)</p>
        <PriceTrendChart data={chartData} series={series} valueSuffix=" idx" height={220} />
      </div>

      <div className="overflow-x-auto">
        <table className="data-table" data-testid="material-comparison-table">
          <thead>
            <tr>
              <th>Metric</th>
              {materials.map((m, i) => (
                <th key={m.id} className="min-w-[150px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="normal-case font-semibold" style={{ color: COMPARE_COLORS[i % COMPARE_COLORS.length] }}>{m.name}</span>
                    <button type="button" onClick={() => onRemove(m.id)} aria-label={`Remove ${m.name} from comparison`} className="text-muted-foreground hover:text-foreground">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="text-muted-foreground font-medium">Risk Level</td>
              {materials.map((m) => <td key={m.id}><span className={`badge ${RISK_BADGE[m.riskLevel]} text-[10px]`}>{m.riskLevel}</span></td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">30-Day Change</td>
              {materials.map((m) => <td key={m.id} className="text-sm font-semibold tabular-nums">{formatPct(m.change30dPct)}</td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">90-Day Change</td>
              {materials.map((m) => <td key={m.id} className="text-sm font-semibold tabular-nums">{formatPct(m.change90dPct)}</td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">Volatility</td>
              {materials.map((m) => <td key={m.id} className="text-sm font-bold tabular-nums" style={{ color: heatColor(m.volatility) }}>{m.volatility}/100</td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">Avg Lead Time</td>
              {materials.map((m) => <td key={m.id} className="text-sm tabular-nums">{m.avgLeadTimeDays}d ({m.leadTimeTrend.toLowerCase()})</td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">Supply Status</td>
              {materials.map((m) => <td key={m.id}><span className={`badge ${SUPPLY_STATUS_BADGE[m.supplyStatus]} text-[10px]`}>{m.supplyStatus}</span></td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">Project Exposure</td>
              {materials.map((m) => <td key={m.id} className="text-sm">{m.affectedProjects.length} project{m.affectedProjects.length === 1 ? "" : "s"}</td>)}
            </tr>
            <tr>
              <td className="text-muted-foreground font-medium">Supplier Availability</td>
              {materials.map((m) => <td key={m.id} className="text-sm">{m.suppliers.length} supplier{m.suppliers.length === 1 ? "" : "s"}</td>)}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
