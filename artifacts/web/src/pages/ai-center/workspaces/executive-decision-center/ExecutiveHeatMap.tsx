import { Link } from "wouter";
import { Flame } from "lucide-react";
import type { HeatMapRow } from "@/lib/mockExecutiveDecisionCenter";
import { EmptyState } from "@/components/ui/empty-state";
import { heatColor } from "./shared";

const DIMENSIONS: { key: keyof Omit<HeatMapRow, "projectId" | "projectCode" | "projectName">; label: string }[] = [
  { key: "schedule", label: "Schedule" },
  { key: "budget", label: "Budget" },
  { key: "safety", label: "Safety" },
  { key: "supplier", label: "Supplier" },
  { key: "material", label: "Material" },
];

// Executive Heat Map — every project x every risk dimension, colored by
// score (green -> amber -> red). Same radial-free grid heat map pattern
// used by Predictive Intelligence's Portfolio Heat Map, Supplier Risk's
// Portfolio Distribution, and Material Intelligence's Risk Heat Map — one
// consistent chart language across the AI Center.

export function ExecutiveHeatMap({ rows }: { rows: HeatMapRow[] }) {
  if (rows.length === 0) return <EmptyState icon={Flame} title="No projects to compare" />;

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[540px]">
        <div className="grid gap-1" style={{ gridTemplateColumns: `160px repeat(${DIMENSIONS.length}, 1fr)` }}>
          <div />
          {DIMENSIONS.map((d) => <div key={d.key} className="text-[10px] text-muted-foreground text-center leading-tight px-1 pb-1.5">{d.label}</div>)}
          {rows.map((row) => (
            <div key={row.projectId} className="contents">
              <Link href={`/projects/${row.projectId}`} className="text-start px-2 py-1.5 rounded-md text-xs font-medium truncate text-foreground hover:bg-muted/50 transition-colors" title={row.projectName}>
                {row.projectCode}
              </Link>
              {DIMENSIONS.map((d) => {
                const value = row[d.key];
                return (
                  <div key={d.key} className="rounded-md m-0.5 flex items-center justify-center text-[11px] font-semibold tabular-nums text-white" style={{ backgroundColor: heatColor(value), minHeight: 28 }} title={`${row.projectCode} · ${d.label}: ${value}`}>
                    {value}
                  </div>
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
