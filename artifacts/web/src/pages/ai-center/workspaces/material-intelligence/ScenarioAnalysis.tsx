import { useMemo, useState } from "react";
import { TrendingUp, Minus, TrendingDown, FlaskConical } from "lucide-react";
import type { MaterialProfile } from "@/lib/mockMaterialIntelligence";
import { FilterSelect } from "@/components/filter-select";
import { Slider } from "@/components/ui/slider";
import { DemoDataBadge, formatSar, formatPrice } from "./shared";

const SCENARIO_META = {
  best: { label: "Best Case", icon: TrendingUp, tone: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  expected: { label: "Expected Case", icon: Minus, tone: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
  worst: { label: "Worst Case", icon: TrendingDown, tone: "text-rose-600 dark:text-rose-400", bg: "bg-rose-500/10 border-rose-500/20" },
} as const;

function exposureAt(material: MaterialProfile, price: number, qtyMultiplier = 1): number {
  return material.affectedProjects.reduce((sum, p) => sum + p.plannedQuantity * qtyMultiplier * price, 0);
}

const DISRUPTION_LEVELS = [
  { value: "none", label: "None" },
  { value: "partial", label: "Partial (one supplier affected)" },
  { value: "full", label: "Full (all suppliers affected)" },
] as const;

// Scenario Analysis — a baseline Best/Expected/Worst read from the
// material's forecast, plus an interactive "what if" simulation (price
// increase %, delivery delay, supplier disruption, quantity change) that
// recomputes projected exposure client-side. Entirely frontend-only and
// clearly labeled as illustrative — this is not a forecasting model.

export function ScenarioAnalysis({ materials }: { materials: MaterialProfile[] }) {
  const [materialId, setMaterialId] = useState(materials[0]?.id ?? "");
  const [priceIncreasePct, setPriceIncreasePct] = useState(10);
  const [delayDays, setDelayDays] = useState(0);
  const [disruption, setDisruption] = useState<(typeof DISRUPTION_LEVELS)[number]["value"]>("none");
  const [qtyChangePct, setQtyChangePct] = useState(0);

  const material = materials.find((m) => m.id === materialId) ?? materials[0];
  if (!material) return null;

  const currentExposure = exposureAt(material, material.currentPrice);

  const simulated = useMemo(() => {
    const simulatedPrice = material.currentPrice * (1 + priceIncreasePct / 100);
    const disruptionSurcharge = disruption === "full" ? 1.08 : disruption === "partial" ? 1.03 : 1;
    const simulatedExposure = exposureAt(material, simulatedPrice * disruptionSurcharge, 1 + qtyChangePct / 100);
    const projectedLeadTime = material.avgLeadTimeDays + delayDays + (disruption === "full" ? 21 : disruption === "partial" ? 8 : 0);
    return { simulatedPrice, simulatedExposure, projectedLeadTime };
  }, [material, priceIncreasePct, disruption, qtyChangePct, delayDays]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <FilterSelect value={materialId} onChange={setMaterialId} className="w-56" ariaLabel="Select material for scenario analysis">
          {materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </FilterSelect>
        <DemoDataBadge label="Demo Data — Illustrative, Frontend-Only Simulation" />
      </div>

      {/* Baseline Best / Expected / Worst */}
      <div className="grid gap-3 sm:grid-cols-3">
        {(["best", "expected", "worst"] as const).map((key) => {
          const meta = SCENARIO_META[key];
          const Icon = meta.icon;
          const price = material.forecast[key];
          return (
            <div key={key} className={`rounded-xl border p-4 space-y-2 ${meta.bg}`}>
              <div className="flex items-center gap-2">
                <Icon className={`w-4 h-4 ${meta.tone}`} />
                <p className={`text-sm font-bold ${meta.tone}`}>{meta.label}</p>
              </div>
              <p className="text-xl font-bold text-foreground tabular-nums">SAR {formatPrice(price)}<span className="text-xs font-normal text-muted-foreground"> /{material.unit}</span></p>
              <p className="text-[11px] text-muted-foreground">Portfolio exposure: {formatSar(exposureAt(material, price))}</p>
            </div>
          );
        })}
      </div>

      {/* Interactive what-if simulation */}
      <div className="panel panel-body space-y-4">
        <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <FlaskConical className="w-3.5 h-3.5" /> "What if..." Simulation
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <label className="text-muted-foreground">Price increase</label>
              <span className="font-semibold text-foreground">{priceIncreasePct}%</span>
            </div>
            <Slider value={[priceIncreasePct]} onValueChange={([v]) => setPriceIncreasePct(v)} min={-20} max={50} step={1} />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <label className="text-muted-foreground">Delivery delay</label>
              <span className="font-semibold text-foreground">{delayDays} days</span>
            </div>
            <Slider value={[delayDays]} onValueChange={([v]) => setDelayDays(v)} min={0} max={60} step={1} />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <label className="text-muted-foreground">Quantity change</label>
              <span className="font-semibold text-foreground">{qtyChangePct > 0 ? "+" : ""}{qtyChangePct}%</span>
            </div>
            <Slider value={[qtyChangePct]} onValueChange={([v]) => setQtyChangePct(v)} min={-30} max={50} step={1} />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Supplier disruption</label>
            <FilterSelect value={disruption} onChange={(v) => setDisruption(v as typeof disruption)} className="w-full" ariaLabel="Supplier disruption level">
              {DISRUPTION_LEVELS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
            </FilterSelect>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/50">
          <div className="text-center">
            <p className="text-sm font-bold text-foreground tabular-nums">SAR {formatPrice(simulated.simulatedPrice)}</p>
            <p className="text-[10px] text-muted-foreground">simulated price /{material.unit}</p>
          </div>
          <div className="text-center">
            <p className={`text-sm font-bold tabular-nums ${simulated.simulatedExposure >= currentExposure ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}>
              {simulated.simulatedExposure >= currentExposure ? "+" : ""}{formatSar(simulated.simulatedExposure - currentExposure)}
            </p>
            <p className="text-[10px] text-muted-foreground">change in exposure</p>
          </div>
          <div className="text-center">
            <p className="text-sm font-bold text-foreground tabular-nums">{simulated.projectedLeadTime}d</p>
            <p className="text-[10px] text-muted-foreground">projected lead time</p>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground text-center">
          Illustrative, frontend-only simulation — recalculated instantly from the sliders above, not a live forecast.
        </p>
      </div>
    </div>
  );
}
