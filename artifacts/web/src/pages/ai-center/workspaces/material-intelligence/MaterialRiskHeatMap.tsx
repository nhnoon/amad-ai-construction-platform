import { Flame } from "lucide-react";
import type { MaterialRiskHeatRow } from "@/lib/mockMaterialIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { heatColor } from "./shared";

const FACTORS: { key: keyof Omit<MaterialRiskHeatRow, "materialId" | "materialName">; label: string }[] = [
  { key: "priceRisk", label: "Price Risk" },
  { key: "supplyRisk", label: "Supply Risk" },
  { key: "leadTimeRisk", label: "Lead-Time Risk" },
  { key: "supplierConcentration", label: "Supplier Concentration" },
  { key: "projectExposure", label: "Project Exposure" },
];

// Material Risk Heat Map — every material x every risk factor, colored by
// score (green -> amber -> red). Answers "where is risk concentrated"
// across the material portfolio in one glance.

export function MaterialRiskHeatMap({
  rows,
  onSelectMaterial,
}: {
  rows: MaterialRiskHeatRow[];
  onSelectMaterial?: (materialId: string) => void;
}) {
  if (rows.length === 0) {
    return <EmptyState icon={Flame} title="No materials to compare" />;
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[600px]">
        <div className="grid gap-1" style={{ gridTemplateColumns: `170px repeat(${FACTORS.length}, 1fr)` }}>
          <div />
          {FACTORS.map((f) => (
            <div key={f.key} className="text-[10px] text-muted-foreground text-center leading-tight px-1 pb-1.5">{f.label}</div>
          ))}
          {rows.map((row) => (
            <div key={row.materialId} className="contents">
              <button
                type="button"
                onClick={() => onSelectMaterial?.(row.materialId)}
                className="text-start px-2 py-1.5 rounded-md text-xs font-medium truncate text-foreground hover:bg-muted/50 transition-colors"
                title={row.materialName}
              >
                {row.materialName}
              </button>
              {FACTORS.map((f) => {
                const value = row[f.key];
                return (
                  <button
                    key={f.key}
                    type="button"
                    onClick={() => onSelectMaterial?.(row.materialId)}
                    className="rounded-md m-0.5 flex items-center justify-center text-[11px] font-semibold tabular-nums text-white transition-transform hover:scale-[1.04]"
                    style={{ backgroundColor: heatColor(value), minHeight: 28 }}
                    title={`${row.materialName} · ${f.label}: ${value}`}
                  >
                    {value}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2 justify-end mt-3 text-[10px] text-muted-foreground">
        <span>Low</span>
        <div className="h-2 w-32 rounded-full" style={{ background: "linear-gradient(90deg, hsl(142,72%,42%), hsl(45,72%,42%), hsl(0,72%,42%))" }} />
        <span>Critical</span>
      </div>
    </div>
  );
}
